#!/usr/bin/env python3
"""Download company logos (SVG only) from Wikimedia Commons into web/logos/.

Each company with a Wikidata id in data/universe.csv, plus the tech companies in
data/tech_entrants.csv, is checked for a Wikidata "logo image" (P154). SVG logos
are downloaded, cleaned and written to web/logos/<QID>.svg. Cleaning means:
  - removing scripts, event handlers, foreignObject and external references
  - removing a full-size white background rectangle, so the logo is transparent
web/logos/index.json maps each Wikidata id (and "name:<key>" for tech companies) to its file.
Raster logos (PNG/JPG) are skipped, and the front end draws an initials badge instead.

  python3 sweep/fetch_logos.py           # fetch logos that aren't on disk yet
  python3 sweep/fetch_logos.py --force   # re-download everything
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_universe import UA, key, sparql, warn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOGOS = ROOT / "web" / "logos"
MAX_BYTES = 400_000  # some Commons logos are multi-MB traced artwork; not worth embedding

# tech companies in tech_entrants.csv aren't biotech, so they're not in the universe; ids checked by hand
TECH_QIDS = {"Alphabet": "Q20800404", "Google DeepMind": "Q15733006", "NVIDIA": "Q182477", "Amazon": "Q3884",
             "OpenAI": "Q21708200", "Anthropic": "Q116758847", "Microsoft": "Q2283", "Meta": "Q380", "Apple": "Q312"}

SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
DANGEROUS = {"script", "foreignObject", "iframe", "object", "embed", "audio", "video"}
WHITE = re.compile(r"^\s*(#fff(fff)?|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))\s*$", re.I)


def fetch(url):
    """Download at most MAX_BYTES (None if larger); wait and retry when Commons says 429."""
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                if int(r.headers.get("Content-Length") or 0) > MAX_BYTES:
                    return None
                data = r.read(MAX_BYTES + 1)
                return None if len(data) > MAX_BYTES else data
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(min(int(e.headers.get("Retry-After") or 30), 120))


def local(tag):
    return tag.rsplit("}", 1)[-1]


def num(v):
    m = re.match(r"\s*(-?[\d.]+)", v or "")
    return float(m.group(1)) if m else None


def fill_of(el):
    style = dict(p.split(":", 1) for p in (el.get("style") or "").split(";") if ":" in p)
    return (style.get("fill") or el.get("fill") or "").strip()


def clean_svg(raw):
    """Return sanitized SVG bytes, or None if it doesn't parse as SVG."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None
    if local(root.tag) != "svg":
        return None
    for parent in list(root.iter()):
        for child in list(parent):
            if not isinstance(child.tag, str):  # comments / processing instructions
                parent.remove(child)
            elif local(child.tag) in DANGEROUS:
                parent.remove(child)
    for el in root.iter():
        for a in list(el.attrib):
            v = el.attrib[a]
            if local(a).lower().startswith("on"):
                del el.attrib[a]
            elif a in (XLINK, "href") and not (v.startswith("#") or v.startswith("data:image/")):
                del el.attrib[a]
    # viewBox is what lets the logo scale; derive it from width/height if missing
    vb = root.get("viewBox")
    if not vb and num(root.get("width")) and num(root.get("height")):
        vb = f"0 0 {num(root.get('width'))} {num(root.get('height'))}"
        root.set("viewBox", vb)
    if not vb:
        return None
    _, _, vw, vh = (float(x) for x in re.split(r"[\s,]+", vb.strip())[:4])
    # drop a white rectangle that covers the whole canvas (looked for in the first few shapes)
    shapes = [(p, c) for p in root.iter() for c in p if local(c.tag) == "rect"][:3]
    for parent, rect in shapes:
        w, h = rect.get("width", ""), rect.get("height", "")
        full = lambda s, total: s.strip() == "100%" or (num(s) or 0) >= 0.98 * total  # noqa: E731
        if full(w, vw) and full(h, vh) and WHITE.match(fill_of(rect)):
            parent.remove(rect)
    if "background" in (root.get("style") or ""):
        root.set("style", re.sub(r"background[^;]*;?", "", root.get("style")))
    return ET.tostring(root, encoding="utf-8", xml_declaration=False)


def pick(files):
    """Several logos listed: prefer an SVG, and the dark-on-light variant over a white one."""
    svgs = [f for f in files if f.lower().endswith(".svg")]
    return sorted(svgs, key=lambda f: bool(re.search(r"white|negative|invert|reverse|dark", f, re.I)))[0] if svgs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download logos already on disk")
    args = ap.parse_args()
    LOGOS.mkdir(parents=True, exist_ok=True)

    with open(ROOT / "data" / "universe.csv", newline="") as fh:
        qids = {r["wikidata"] for r in csv.DictReader(fh) if r["wikidata"]}
    qids |= set(TECH_QIDS.values())

    logos = {}
    qlist = sorted(qids)
    for i in range(0, len(qlist), 300):
        values = " ".join(f"wd:{q}" for q in qlist[i:i + 300])
        for b in sparql(f"SELECT ?c ?logo WHERE {{ VALUES ?c {{ {values} }} ?c wdt:P154 ?logo }}"):
            q = b["c"]["value"].rsplit("/", 1)[-1]
            logos.setdefault(q, []).append(urllib.parse.unquote(b["logo"]["value"].rsplit("/", 1)[-1]))
    print(f"{len(logos)} companies have a logo on Wikidata")

    index, got, skipped = {}, 0, {"raster": 0, "too big": 0, "unparseable": 0, "failed": 0}
    for q, files in sorted(logos.items()):
        f = pick(files)
        if not f:
            skipped["raster"] += 1
            continue
        out = LOGOS / f"{q}.svg"
        if out.exists() and not args.force:
            index[q] = f"logos/{q}.svg"
            continue
        try:
            raw = fetch("https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f))
        except Exception as e:  # noqa: BLE001
            warn(f"{q} {f}: {e}")
            skipped["failed"] += 1
            continue
        if raw is None:
            skipped["too big"] += 1
            continue
        svg = clean_svg(raw)
        if not svg:
            skipped["unparseable"] += 1
            continue
        out.write_bytes(svg)
        index[q] = f"logos/{q}.svg"
        got += 1
        if got % 25 == 0:
            print(f"  {got} downloaded…", flush=True)
        time.sleep(2)  # Commons throttles bulk original-file downloads hard; slow and steady gets through
    for name, q in TECH_QIDS.items():
        if q in index:
            index["name:" + key(name)] = index[q]
    (LOGOS / "index.json").write_text(json.dumps(index, indent=0, sort_keys=True))
    print(f"{len(index)} logos ready ({got} downloaded now); skipped: "
          + ", ".join(f"{v} {k}" for k, v in skipped.items() if v))


if __name__ == "__main__":
    main()
