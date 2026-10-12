"""Builds index.html from index.src.html, leaflets.json and the QR library.
Run after editing leaflets.json or index.src.html:  python3 build.py path/to/qrcode.js
"""
import json, sys, os
from PIL import Image, ImageDraw

here = os.path.dirname(os.path.abspath(__file__))
qrlib = open(sys.argv[1], encoding="utf-8").read()
data = json.load(open(os.path.join(here, "leaflets.json"), encoding="utf-8"))
src = open(os.path.join(here, "index.src.html"), encoding="utf-8").read()
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = src.replace("/*__QRLIB__*/", qrlib).replace("/*__LEAFLETS__*/", blob)
assert "__QRLIB__" not in html and "__LEAFLETS__" not in html
open(os.path.join(here, "index.html"), "w", encoding="utf-8").write(html)

# Icon: a QR finder pattern on the app's blue
svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#1f5f8b"/><g fill="none" stroke="#fff" stroke-width="4"><rect x="12" y="12" width="16" height="16" rx="2"/><rect x="36" y="12" width="16" height="16" rx="2"/><rect x="12" y="36" width="16" height="16" rx="2"/></g><g fill="#fff"><rect x="17" y="17" width="6" height="6"/><rect x="41" y="17" width="6" height="6"/><rect x="17" y="41" width="6" height="6"/><rect x="36" y="36" width="6" height="6"/><rect x="46" y="36" width="6" height="6"/><rect x="36" y="46" width="6" height="6"/><rect x="46" y="46" width="6" height="6"/></g></svg>'''
open(os.path.join(here, "icon.svg"), "w").write(svg)
def png(n, rounded=True):
    s = n / 64
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0) if rounded else (31, 95, 139, 255))
    d = ImageDraw.Draw(im)
    if rounded: d.rounded_rectangle([0, 0, n - 1, n - 1], radius=int(14 * s), fill=(31, 95, 139, 255))
    w = max(1, round(4 * s))
    for x, y in [(12, 12), (36, 12), (12, 36)]:
        d.rounded_rectangle([x * s + w / 2, y * s + w / 2, (x + 16) * s - w / 2, (y + 16) * s - w / 2], radius=int(2 * s), outline="white", width=w)
    for x, y in [(17, 17), (41, 17), (17, 41), (36, 36), (46, 36), (36, 46), (46, 46)]:
        d.rectangle([x * s, y * s, (x + 6) * s, (y + 6) * s], fill="white")
    return im
png(180, rounded=False).save(os.path.join(here, "icon-180.png"))
png(192).save(os.path.join(here, "icon-192.png"))
png(512, rounded=False).save(os.path.join(here, "icon-512.png"))
print("built", len(data["leaflets"]), "leaflets,", len(html) // 1024, "KB")
