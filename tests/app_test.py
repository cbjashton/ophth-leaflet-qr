"""EyeLeaflets checks, run in a headless phone-sized Chromium.

    pip install playwright zxing-cpp opencv-python-headless
    python3 tests/app_test.py [path/to/chromium]

Serves the main folder locally, then checks: every QR code decodes to its leaflet's address,
the A-Z letter headings and side index, stars on each version, search ranking, tabs and filter,
Recent, text size, welcome cards, offline start-up, the pilot staying silent while switched off,
and that nothing scrolls sideways. Prints PASS/FAIL per check and a total.
"""
import asyncio, json, os, re, subprocess, sys, time
import cv2, numpy as np, zxingcpp
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8811
URL = f"http://localhost:{PORT}/index.html"
EXE = sys.argv[1] if len(sys.argv) > 1 else None
DATA = json.load(open(os.path.join(ROOT, "leaflets.json")))
LEAF = DATA["leaflets"]
SEEN = "try{localStorage.setItem('lqr-toured','true');localStorage.setItem('lqr-getAppHidden','true')}catch(e){}"
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   [{str(detail)[:300]}]"))


def decode(png):
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
    img = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
    r = zxingcpp.read_barcodes(img)
    return r[0].text if r else ""


async def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "-d", ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    async with async_playwright() as p:
        b = await p.chromium.launch(**({"executable_path": EXE} if EXE else {}))

        async def page(seen=True, **kw):
            c = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                    service_workers=kw.pop("sw", "block"), **kw)
            if seen:
                await c.add_init_script(SEEN)
            pg = await c.new_page()
            errs, gc = [], []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("request", lambda r: gc.append(r.url) if "goatcounter" in r.url else None)
            await pg.goto(URL)
            await pg.wait_for_timeout(800)
            return c, pg, errs, gc

        # ---------- every QR code ----------
        c, pg, errs, gc = await page()
        bad = []
        for l in LEAF:
            await pg.evaluate("id=>openCard(byId()[id])", l["id"])
            got = decode(await pg.locator("#sQr").screenshot())
            if got != l["url"]:
                bad.append((l["id"], got))
            await pg.evaluate("hideCard()")
        check(f"All {len(LEAF)} QR codes decode to their leaflet's address", not bad, bad[:3])
        await pg.click("#shareBtn")
        share = decode(await pg.locator("#shQr").screenshot())
        check("Share-the-app code decodes to the app's own address", share == URL.replace("index.html", ""), share)
        await pg.click("#shClose")
        check("No page errors while showing codes", not errs, errs)
        await c.close()

        # ---------- A-Z headings and side index ----------
        c, pg, errs, gc = await page()
        await pg.evaluate("localStorage.setItem('lqr-tab','\"all\"');localStorage.removeItem('lqr-specs')")
        await pg.reload(); await pg.wait_for_timeout(600)
        heads = await pg.locator("#list > li.lh").all_inner_texts()
        rows = await pg.locator("#list > li:not(.lh) .row .t").all_inner_texts()
        firsts = sorted({re.sub(r"[^A-Z]", "", t.upper()[:1]) or "#" for t in rows})
        check("A-Z: one heading per starting letter, in order", heads == firsts, (heads, firsts))
        order = await pg.evaluate("[...document.querySelectorAll('#list > li')].map(li=>li.classList.contains('lh')?'#'+li.textContent:(li.querySelector('.t')||{}).textContent)")
        ok, cur = True, ""
        for x in order:
            if x.startswith("#"):
                cur = x[1:]
            elif re.sub(r"[^A-Z]", "", x.upper()[:1]) != cur:
                ok = False
        check("A-Z: every leaflet sits under its own letter", ok)
        check("Index hidden at the top of the screen (doesn't cover tabs)", await pg.locator("#azIdx").is_hidden())
        await pg.evaluate("scrollTo(0, 150)"); await pg.wait_for_timeout(150)
        tb = await pg.locator("#tabs").bounding_box(); ib = await pg.locator("#azIdx").bounding_box() if await pg.locator("#azIdx").is_visible() else None
        check("Index never covers the tabs while they're on screen", ib is None or tb["y"] + tb["height"] < 0 or ib["y"] > tb["y"] + tb["height"], (tb, ib))
        await pg.evaluate("document.getElementById('az-C').scrollIntoView()"); await pg.wait_for_timeout(200)
        check("Index appears over the A-Z list", await pg.locator("#azIdx").is_visible())
        idx = await pg.locator("#azIdx button").all_inner_texts()
        check("Index lists the same letters as the headings", idx == heads, (idx, heads))
        await pg.locator("#azIdx button", has_text="M").click(); await pg.wait_for_timeout(250)
        top = await pg.evaluate("document.getElementById('az-M').getBoundingClientRect().top")
        check("Tapping M jumps to the M heading", 0 <= top < 40, top)
        bb = await pg.locator("#azIdx button", has_text="S").bounding_box()
        await pg.mouse.move(bb["x"] + 8, bb["y"] + 5); await pg.mouse.down()
        bt = await pg.locator("#azIdx button", has_text="T").bounding_box()
        await pg.mouse.move(bt["x"] + 8, bt["y"] + 5, steps=4); await pg.mouse.up(); await pg.wait_for_timeout(250)
        top = await pg.evaluate("document.getElementById('az-T').getBoundingClientRect().top")
        check("Sliding a finger down the index follows it (S to T)", 0 <= top < 40, top)
        rb = await pg.locator("#list > li:not(.lh)").first.bounding_box(); ib = await pg.locator("#azIdx").bounding_box()
        check("Index doesn't overlap the leaflet cards", rb["x"] + rb["width"] <= ib["x"] + 2, (rb, ib))
        await pg.fill("#q", "kera"); await pg.wait_for_timeout(150)
        check("No letter headings or index while searching", await pg.locator("#list > li.lh").count() == 0 and await pg.locator("#azIdx").is_hidden())
        await pg.fill("#q", "")

        # ---------- cards look ----------
        radius = await pg.locator("#list > li:not(.lh)").first.evaluate("e=>getComputedStyle(e).borderRadius")
        gap = await pg.evaluate("(()=>{const r=[...document.querySelectorAll('#list > li:not(.lh)')];const a=r[0].getBoundingClientRect(),b=r[1].getBoundingClientRect();return b.top-a.bottom})()")
        check("Each leaflet is its own rounded card with a gap between", radius == "18px" and gap >= 8, (radius, gap))

        # ---------- stars on versions ----------
        g = pg.locator("#list > li.grp", has_text="Blepharitis")
        await g.scroll_into_view_if_needed()
        star = g.get_by_role("button", name="Add to favourites: Blepharitis (for parents)")
        check("Each version has its own star", await g.locator(".audstar").count() == await g.locator(".audbtn").count() >= 2)
        await star.click(); await pg.wait_for_timeout(150)
        favs = await pg.evaluate("JSON.parse(localStorage.getItem('lqr-favs')||'[]')")
        check("Star saves that version to Favourites", "m-blepharitis-for-parents" in favs, favs)
        g = pg.locator("#list > li.grp", has_text="Blepharitis")
        on = await g.get_by_role("button", name="Remove from favourites: Blepharitis (for parents)").get_attribute("aria-pressed")
        check("Its star shows as filled", on == "true")
        await pg.locator('#tabs .tab[data-k="fav"]').click(); await pg.wait_for_timeout(150)
        check("It appears in the Favourites tab", "Blepharitis (for parents)" in await pg.locator("#list .row .t").all_inner_texts())
        await pg.locator('#tabs .tab[data-k="all"]').click(); await pg.wait_for_timeout(150)
        await pg.locator("#list > li.grp", has_text="Blepharitis").get_by_role("button", name="Remove from favourites: Blepharitis (for parents)").click()
        check("Tapping again removes it", "m-blepharitis-for-parents" not in await pg.evaluate("JSON.parse(localStorage.getItem('lqr-favs')||'[]')"))
        b2 = pg.locator("#list > li.grp", has_text="Blepharitis").get_by_role("button", name="Show code: Blepharitis (teens and parents)")
        await b2.click(); await pg.wait_for_timeout(200)
        check("Version button still opens its own code", await pg.locator("#sTitle").inner_text() == "Blepharitis (teens and parents)")
        await pg.evaluate("hideCard()")

        # ---------- search ----------
        for q, first in [("kera", "Keratoconus"), ("keratoconous", "Keratoconus"), ("kc", "Keratoconus"), ("lazy eye", None)]:
            await pg.fill("#q", q); await pg.wait_for_timeout(120)
            t = await pg.locator("#list .row .t").all_inner_texts()
            check(f"Search '{q}'" + (f" puts {first} first" if first else " finds amblyopia"),
                  (t and t[0] == first) if first else any("Amblyopia" in x for x in t), t[:3])
        await pg.fill("#q", "zzqxw"); await pg.wait_for_timeout(120)
        check("A search with no results offers 'Request this leaflet'", await pg.locator("#list .reqlink").is_visible())
        await pg.fill("#q", "")

        # ---------- tabs, filter ----------
        ys = await pg.locator("#tabs .tab").evaluate_all("a=>a.map(x=>Math.round(x.getBoundingClientRect().top))")
        check("Tabs on two rows of three", len(ys) == 6 and len(set(ys)) == 2, ys)
        await pg.locator('#tabs .tab[data-k="surgery"]').click(); await pg.wait_for_timeout(150)
        kinds = await pg.evaluate("[...document.querySelectorAll('#list > li:not(.lh) .row .t')].length")
        want = sum(1 for l in LEAF if l["kind"] == "surgery")
        check("Surgery tab shows surgery leaflets", 0 < kinds <= want, (kinds, want))
        await pg.locator('#tabs .tab[data-k="all"]').click()
        await pg.click("#specBtn"); await pg.locator("#specGrid .specopt", has_text="Paediatrics").first.click()
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)
        t = await pg.locator("#list .row .t").all_inner_texts()
        check("Paediatrics filter includes the pre-dilation drops and the red reflex",
              "Cyclopentolate eye drops for pre-dilation" in t and "The red reflex" in t)
        await pg.click("#specClear")
        check("Hospital passport removed", not any("passport" in l["title"].lower() for l in LEAF))

        # ---------- recent, text size, sideways scroll ----------
        for i in ["m-keratoconus", "m-corneal-cross-linking", "m-microbial-keratitis", "m-chalazion", "m-blepharitis"]:
            await pg.evaluate("id=>{openCard(byId()[id]);hideCard()}", i)
        ys = await pg.locator("#recent .chip").evaluate_all("a=>a.map(x=>x.offsetTop)")
        check("Recent: newest first, at most two lines", (await pg.locator("#recent .chip span").first.inner_text()) == "Blepharitis" and len(set(ys)) <= 2, ys)
        for s in (0, 2):
            await pg.click("#aaBtn"); await pg.locator("#aaSeg button").nth(s).click(); await pg.wait_for_timeout(150)
            wide = await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
            check(f"Nothing scrolls sideways at text size {['A','A+','A++'][s]}", not wide)
        await pg.click("#aaBtn"); await pg.locator("#aaSeg button").nth(0).click()
        check("No page errors", not errs, errs)
        check("Pilot off: nothing sent to GoatCounter", not gc and not DATA.get("statsCode"), gc)
        await c.close()

        # ---------- welcome cards ----------
        c, pg, errs, gc = await page(seen=False)
        check("Welcome cards show on first open", await pg.locator("#tour").is_visible())
        await pg.click("#tourSkip")
        await pg.reload(); await pg.wait_for_timeout(500)
        check("…and not again after Skip", await pg.locator("#tour").is_hidden())
        await c.close()

        # ---------- dark mode still readable ----------
        c, pg, errs, gc = await page(color_scheme="dark")
        bg = await pg.evaluate("getComputedStyle(document.body).backgroundColor")
        card = await pg.locator("#list > li:not(.lh)").first.evaluate("e=>getComputedStyle(e).backgroundColor")
        check("Dark mode: dark page with cards that stand out", bg != card and bg.startswith("rgb(") and int(re.findall(r"\d+", bg)[0]) < 60, (bg, card))
        await c.close()

        # ---------- offline ----------
        c, pg, errs, gc = await page(sw="allow")
        await pg.evaluate("navigator.serviceWorker.ready.then(()=>1)")
        for _ in range(80):
            if any(k.startswith("leaflet-qr-") for k in await pg.evaluate("caches.keys()")):
                break
            await pg.wait_for_timeout(100)
        await pg.reload(); await pg.wait_for_timeout(600)
        await c.set_offline(True)
        srv.terminate(); srv.wait()
        p2 = await c.new_page()
        await p2.goto(URL); await p2.wait_for_timeout(800)
        n = await p2.locator("#list > li:not(.lh)").count()
        await p2.evaluate("openCard(byId()['m-keratoconus'])")
        got = decode(await p2.locator("#sQr").screenshot())
        check("Offline: app opens and shows a working code", n > 100 and got == next(l["url"] for l in LEAF if l["id"] == "m-keratoconus"), (n, got))
        keys = await p2.evaluate("caches.keys()")
        check("Offline copy only uses its own 'leaflet-qr-' cache", keys and all(k.startswith("leaflet-qr-") for k in keys), keys)
        await c.close()
        await b.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


asyncio.run(main())
