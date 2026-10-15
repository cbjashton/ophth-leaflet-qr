"""Checks every leaflet link each week. Can also make front-page pictures and PDF copies.

Currently set to CHECK LINKS ONLY (both switches below are False). Turn SAVE_FRONT_PAGES
and/or SAVE_PDF_COPIES on later if Moorfields agrees to copies being hosted.

Runs on GitHub (see .github/workflows/thumbnails.yml), which can reach the
Moorfields website. Writes:
  thumbs/<leaflet id>.webp   front page, 360 px wide
  thumbs/index.json          which leaflets have a picture (the app pre-saves these for offline use)
  pdfs/<leaflet id>.pdf      a copy of each PDF so the app can show it inside the app
                             (set SAVE_PDF_COPIES = False below to turn this off)
  thumbs/pages.json          number of pages in each PDF, for working out paper saved
  link-report.md             any links that failed, so they can be fixed in leaflets.json
  link-problems.flag         only when links failed; tells the workflow to raise a GitHub issue (which emails you)
"""
import hashlib, json, os, subprocess, sys, tempfile, urllib.request
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "source" else HERE
LIST = os.path.join(ROOT, "leaflets.json")
OUT = os.path.join(ROOT, "thumbs")
INDEX = os.path.join(OUT, "index.json")
SAVE_PDF_COPIES = False   # copies of each PDF, for viewing inside the app
SAVE_FRONT_PAGES = False  # small front-page pictures for press-and-hold previews
PDFS = os.path.join(ROOT, "pdfs")
# Leaflets the check skips: checked by hand and fine for patients, but the website
# doesn't answer the GitHub checker properly. Add an id here to stop false alerts.
SKIP_CHECK = {
    "m-vitreoretinal-emergency-vre-waiting-list-information",  # opens the clinic web page (checked 15 Oct 2026)
}
UA = {"User-Agent": "Mozilla/5.0 (Leaflet QR thumbnail builder)"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status if hasattr(r, "status") else 200, r.headers.get("Content-Type", ""), r.read()


def render_first_page(pdf_bytes, dest):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        open(src, "wb").write(pdf_bytes)
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-png", "-scale-to", "720", src, os.path.join(tmp, "p")],
                       check=True, capture_output=True, timeout=120)
        png = next(f for f in os.listdir(tmp) if f.startswith("p") and f.endswith(".png"))
        im = Image.open(os.path.join(tmp, png)).convert("RGB")
        im.thumbnail((360, 720))
        im.save(dest, "WEBP", quality=70, method=6)


def page_count(pdf_bytes):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.pdf")
        open(src, "wb").write(pdf_bytes)
        out = subprocess.run(["pdfinfo", src], capture_output=True, text=True, timeout=60).stdout
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[1])
    return None


def main():
    data = json.load(open(LIST, encoding="utf-8"))
    old = json.load(open(INDEX)) if os.path.exists(INDEX) else {}
    index, problems, pages = {}, [], {}
    for item in data["leaflets"]:
        if item["id"] in SKIP_CHECK:
            continue
        url, lid = item["url"], item["id"]
        try:
            status, ctype, body = fetch(url)
        except Exception as e:  # noqa: BLE001 - report every kind of failure
            problems.append((item["title"], url, str(e)[:120]))
            continue
        is_pdf = url.lower().endswith(".pdf") or "pdf" in ctype.lower()
        if not is_pdf:
            continue  # web pages: the link works, but there is no front page to draw
        if not body.startswith(b"%PDF"):
            problems.append((item["title"], url, "did not return a PDF"))
            continue
        digest = hashlib.sha1(body).hexdigest()
        if not (SAVE_FRONT_PAGES or SAVE_PDF_COPIES):
            continue  # links only: the PDF opened, nothing to save
        try:
            n = page_count(body)
            if n:
                pages[lid] = n
        except Exception:  # noqa: BLE001
            pass
        if SAVE_PDF_COPIES:
            os.makedirs(PDFS, exist_ok=True)
            open(os.path.join(PDFS, lid + ".pdf"), "wb").write(body)
        if not SAVE_FRONT_PAGES:
            continue
        os.makedirs(OUT, exist_ok=True)
        dest = os.path.join(OUT, lid + ".webp")
        if old.get(lid) == digest and os.path.exists(dest):
            index[lid] = digest
            continue
        try:
            render_first_page(body, dest)
            index[lid] = digest
        except Exception as e:  # noqa: BLE001
            problems.append((item["title"], url, "could not draw front page: " + str(e)[:80]))
    # remove pictures for leaflets that are no longer listed
    if os.path.isdir(OUT):
        for f in os.listdir(OUT):
            if f.endswith(".webp") and (not SAVE_FRONT_PAGES or f[:-5] not in index):
                os.remove(os.path.join(OUT, f))
    if os.path.isdir(PDFS):
        for f in os.listdir(PDFS):
            if f.endswith(".pdf") and (not SAVE_PDF_COPIES or f[:-4] not in index and f[:-4] not in pages):
                os.remove(os.path.join(PDFS, f))
    if SAVE_FRONT_PAGES:
        json.dump(index, open(INDEX, "w"), indent=0, sort_keys=True)
        json.dump(pages, open(os.path.join(OUT, "pages.json"), "w"), indent=0, sort_keys=True)
    with open(os.path.join(ROOT, "link-report.md"), "w", encoding="utf-8") as r:
        if problems:
            r.write("# Leaflet links that need checking\n\n")
            for t, u, why in problems:
                r.write(f"- **{t}**: {why}\n  {u}\n")
        else:
            r.write("# Leaflet links\n\nAll links worked on the last check.\n")
    flag = os.path.join(ROOT, "link-problems.flag")
    if problems:
        open(flag, "w").write(str(len(problems)))
    elif os.path.exists(flag):
        os.remove(flag)
    print(f"checked {len(data['leaflets']) - len(SKIP_CHECK)} links (skipped {len(SKIP_CHECK)}): {len(problems)} problem(s)")


if __name__ == "__main__":
    sys.exit(main())
