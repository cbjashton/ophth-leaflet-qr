"""Pilot report from the app's anonymous usage counts.

1. In GoatCounter: Settings -> Export -> Start export. GoatCounter emails a CSV file.
2. Run:  python3 source/pilot_report.py goatcounter-export.csv
   (add --pages thumbs/pages.json for paper saved, if leaflet page counts are switched on)
3. Open pilot-report.html. pilot-events.csv has one tidy row per count, for Excel.

Each count's path is  <event>/<role>/<area>[/<site>][/<leaflet>]
and its title is      <yyyy-mm-dd hh:mm ddd> | <phone> | online|offline   (see pilot.js)
"""
import csv, html, json, os, sys
from collections import Counter, defaultdict
from datetime import datetime

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit(__doc__)
pages = {}
if "--pages" in sys.argv:
    pages = json.load(open(sys.argv[sys.argv.index("--pages") + 1]))
    args = [a for a in args if a != sys.argv[sys.argv.index("--pages") + 1]]

leaflets = {l["id"]: l for l in json.load(open(os.path.join(root, "leaflets.json"), encoding="utf-8"))["leaflets"]}
cfg = json.load(open(os.path.join(root, "leaflets.json"), encoding="utf-8")).get("pilot", {})
has_sites = bool(cfg.get("sites"))
EVENTS = {"install", "open", "signup", "code", "related", "view", "search", "fav", "share", "feedback"}

rows = []
with open(args[0], encoding="utf-8", newline="") as fh:
    r = csv.reader(fh)
    head = next(r)
    head[0] = head[0].lstrip("0123456789")            # GoatCounter puts its format version before the first heading
    col = {h.strip().lower(): i for i, h in enumerate(head)}
    for line in r:
        g = lambda k: line[col[k]] if k in col and col[k] < len(line) else ""
        path = g("path").strip("/")
        parts = path.split("/")
        if not parts or parts[0] not in EVENTS:
            continue                                      # page views and anything not from pilot.js
        t = g("title").split(" | ")
        try:
            when = datetime.strptime(t[0][:16], "%Y-%m-%d %H:%M")
        except ValueError:
            when = datetime.fromisoformat(g("date").replace("Z", "")[:19]) if g("date") else None
        if not when:
            continue
        ev, role, area = (parts + ["", "", ""])[:3]
        rest = parts[3:]
        site = rest.pop(0) if has_sites and rest else ""
        leaf = rest[0] if rest else ""
        rows.append({"when": when, "event": ev, "role": role, "area": area, "site": site, "leaflet": leaf,
                     "phone": t[1] if len(t) > 1 else "", "offline": len(t) > 2 and t[2] == "offline",
                     "system": g("system"), "browser": g("browser")})

if not rows:
    sys.exit("No pilot counts found in that file.")
rows.sort(key=lambda x: x["when"])
_slug = lambda v: "".join(c if c.isalnum() else "-" for c in v.lower().replace("&", "and")).strip("-")
LABELS = {}
for v in cfg.get("roles", []) + cfg.get("areas", []) + cfg.get("sites", []):
    k = _slug(v)
    while "--" in k: k = k.replace("--", "-")
    LABELS[k] = v
nice = lambda s: LABELS.get(s, s.replace("-and-", " & ").replace("-", " ").capitalize()) if s and s != "unknown" else "Not given"
week = lambda d: d.strftime("%G-W%V")

# tidy CSV for Excel
with open(os.path.join(root, "pilot-events.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "time", "weekday", "week", "event", "role", "area", "site", "leaflet", "leaflet title", "specialty", "phone", "offline", "system"])
    for x in rows:
        l = leaflets.get(x["leaflet"].removesuffix("-easy"), {})
        w.writerow([x["when"].date(), x["when"].strftime("%H:%M"), x["when"].strftime("%a"), week(x["when"]), x["event"], nice(x["role"]),
                    nice(x["area"]), nice(x["site"]) if x["site"] else "", x["leaflet"], l.get("title", ""), l.get("spec") or l.get("tag", ""),
                    x["phone"], "yes" if x["offline"] else "", x["system"]])

codes = [x for x in rows if x["event"] == "code"]
phones = {x["phone"] for x in rows if x["phone"]}
first, last = rows[0]["when"].date(), rows[-1]["when"].date()

def table(title, counter_rows, cols):
    out = [f"<h2>{html.escape(title)}</h2><table><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cols) + "</tr>"]
    for r in counter_rows:
        out.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>")
    return "".join(out) + "</table>"

parts = []
summary = [("Dates", f"{first:%d %b %Y} to {last:%d %b %Y}"), ("Phones used", len(phones)),
           ("Installed to home screen", sum(x["event"] == "install" for x in rows)),
           ("Times opened", sum(x["event"] == "open" for x in rows)), ("Codes shown", len(codes)),
           ("Leaflets viewed on staff phone", sum(x["event"] == "view" for x in rows)),
           ("Searches that found nothing", sum(x["event"] == "search" for x in rows)),
           ("Counts made with no signal", sum(x["offline"] for x in rows))]
if pages:
    summary.append(("Paper pages not printed (codes shown x pages)", sum(pages.get(x["leaflet"].removesuffix("-easy"), 0) for x in codes)))
parts.append(table("Summary", summary, ["Measure", "Value"]))

# weekly: active phones, opens, codes, and phones still using it after their first week
by_week = defaultdict(lambda: {"phones": set(), "open": 0, "code": 0})
first_week = {}
for x in rows:
    wk = week(x["when"]); by_week[wk]["phones"].add(x["phone"])
    if x["event"] in ("open", "code"): by_week[wk][x["event"]] += 1
    first_week.setdefault(x["phone"], wk)
wrows = []
for wk in sorted(by_week):
    returning = sum(1 for p in by_week[wk]["phones"] if first_week.get(p) and first_week[p] < wk)
    wrows.append((wk, len(by_week[wk]["phones"]), returning, by_week[wk]["open"], by_week[wk]["code"]))
parts.append(table("By week", wrows, ["Week", "Active phones", "Of which returning", "Opens", "Codes shown"]))

def by(key, label):
    users = defaultdict(set); c = Counter(); o = Counter()
    for x in rows:
        users[x[key]].add(x["phone"])
        if x["event"] == "code": c[x[key]] += 1
        if x["event"] == "open": o[x[key]] += 1
    return table(label, [(nice(k), len(users[k]), o[k], c[k]) for k in sorted(users, key=lambda k: -c[k])], [label.split()[-1].capitalize(), "Phones", "Opens", "Codes shown"])
parts.append(by("role", "By role"))
parts.append(by("area", "By area"))
if has_sites:
    parts.append(by("site", "By site"))

hours = Counter(x["when"].hour for x in codes)
parts.append(table("Codes shown by hour of day", [(f"{h:02d}:00", hours[h]) for h in range(24) if hours[h]], ["Hour", "Codes shown"]))
days = Counter(x["when"].strftime("%a") for x in codes)
parts.append(table("Codes shown by day of week", [(d, days[d]) for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]], ["Day", "Codes shown"]))

top = Counter(x["leaflet"] for x in codes)
def ltitle(i):
    l = leaflets.get(i.removesuffix("-easy"), {}); return (l.get("title", i) + (" (Easy Read)" if i.endswith("-easy") else ""))
parts.append(table("Leaflets: most codes shown", [(ltitle(i), leaflets.get(i.removesuffix("-easy"), {}).get("spec") or leaflets.get(i.removesuffix("-easy"), {}).get("tag", ""), n)
                                               for i, n in top.most_common(40)], ["Leaflet", "Specialty", "Codes shown"]))
spec = Counter((leaflets.get(x["leaflet"].removesuffix("-easy"), {}).get("spec") or leaflets.get(x["leaflet"].removesuffix("-easy"), {}).get("tag", "Unknown")) for x in codes)
parts.append(table("Codes shown by specialty", spec.most_common(), ["Specialty", "Codes shown"]))
unused = [l["title"] for i, l in leaflets.items() if i not in top and i + "-easy" not in top]
parts.append(f"<h2>Leaflets never shown</h2><p>{len(unused)} of {len(leaflets)} leaflets had no codes shown in this period.</p>")

sys_ = Counter((x["phone"], x["system"].split(" ")[0] or "Unknown") for x in rows)
per_phone = Counter(s for (_, s) in sys_)
parts.append(table("Phones by system", per_phone.most_common(), ["System", "Phones"]))

css = "body{font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#14212b}table{border-collapse:collapse;width:100%;margin:6px 0 22px}th,td{text-align:left;padding:6px 10px;border-bottom:1px solid #dbe3e8}th{background:#f2f5f7}td:last-child,th:last-child{text-align:right}h1{margin-bottom:4px}h2{font-size:1.05rem;margin:22px 0 4px}"
doc = f"<!doctype html><meta charset=utf-8><title>Pilot report</title><style>{css}</style><h1>Pilot report</h1><p>From anonymous app counts. {len(rows)} counts.</p>" + "".join(parts)
open(os.path.join(root, "pilot-report.html"), "w", encoding="utf-8").write(doc)
print(f"{len(rows)} counts from {len(phones)} phones -> pilot-report.html and pilot-events.csv")
