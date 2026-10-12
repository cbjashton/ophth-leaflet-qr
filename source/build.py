"""Builds index.html from index.src.html, leaflets.json and the QR library.
Run after editing leaflets.json or index.src.html:  python3 build.py path/to/qrcode.js
"""
import json, sys, os

here = os.path.dirname(os.path.abspath(__file__))
qrlib = open(sys.argv[1], encoding="utf-8").read()
data = json.load(open(os.path.join(here, "leaflets.json"), encoding="utf-8"))
src = open(os.path.join(here, "index.src.html"), encoding="utf-8").read()
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = src.replace("/*__QRLIB__*/", qrlib).replace("/*__LEAFLETS__*/", blob)
assert "__QRLIB__" not in html and "__LEAFLETS__" not in html
open(os.path.join(here, "index.html"), "w", encoding="utf-8").write(html)

# Icons (icon.svg, icon-180.png, icon-192.png, icon-512.png) are separate files and are not touched here.

print("built", len(data["leaflets"]), "leaflets,", len(html) // 1024, "KB")
