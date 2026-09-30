#!/usr/bin/env python3
"""Cut lettering and ornaments out of the catalogued maps and keep only the ink.

Reads data/cuts.json. Each label and ornament names a map and a box in full-resolution pixels. The box is
fetched from the Library of Congress image server at its native size (the server blurs anything it is asked
to enlarge), the paper is estimated and removed, and what is left is saved as a small picture whose only
content is how much ink sits at each point. The pages paint that ink in the site's own text colour, so the
same cut works on the light and the dark theme.

Only Library of Congress pictures are cut, because the results are copied into the site (static/cuts/).
Ornament boxes come from _cache/cuts/<MAP>.json (the search notes) the first time and are then written into
data/cuts.json, so later runs need only that file.

Needs Pillow, numpy and OpenCV. Run:  python3 generator/fetch_cuts.py        (skips boxes already fetched)
"""
import json
import pathlib
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "_cache" / "cuts" / "raw2"
OUT = ROOT / "static" / "cuts"
LABEL_H = 132          # pixels tall for a line of lettering (shown at about a third of that)
ORN_MAX = 560          # longest side of an ornament
FRONT_PX = 4200        # width of the preview's copy of the front map
UA = "TartaryAtlas/1.0 (research site build)"


def fetch(base, box, out):
    if out.exists() and out.stat().st_size > 1500:
        return
    x, y, w, h = box
    size = "full" if max(w, h) <= 1600 else "!1600,1600"
    url = f"{base.rstrip('/')}/{x},{y},{w},{h}/{size}/0/default.jpg"
    subprocess.run(["curl", "-sS", "-m", "120", "--retry", "3", "-A", UA, "-o", str(out), url], capture_output=True)


def ink(path, lo=0.10, hi=0.55):
    """How much darker than the surrounding paper each pixel is, from 0 (paper) to 255 (full ink)."""
    g = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    k = min(151, max(31, int(min(g.shape) * 0.9) | 1))
    paper = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    paper = cv2.GaussianBlur(paper, (0, 0), 25)
    d = np.clip((paper - g) / np.maximum(paper, 1), 0, 1)
    return (np.clip((d - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def trim(a, margin):
    ys, xs = np.where(a > 60)
    if not len(ys):
        return a
    y0, y1 = max(0, ys.min() - margin), min(a.shape[0], ys.max() + 1 + margin)
    x0, x1 = max(0, xs.min() - margin), min(a.shape[1], xs.max() + 1 + margin)
    return a[y0:y1, x0:x1]


def save(a, out):
    """A picture that is black everywhere and only as opaque as the ink, in sixteen steps to keep it small."""
    a = (np.round(a / 17.0) * 17).astype(np.uint8)
    im = Image.merge("LA", (Image.new("L", (a.shape[1], a.shape[0]), 0), Image.fromarray(a)))
    im.save(out, optimize=True)


def main():
    path = ROOT / "data" / "cuts.json"
    cuts = json.loads(path.read_text())
    iiif = json.loads((ROOT / "data" / "iiif.json").read_text())
    RAW.mkdir(parents=True, exist_ok=True)
    for sub in ("labels", "ornaments"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    def base(rid):
        b = next(e["url"] for e in iiif[rid] if e["kind"] == "image" and e["status"] == "ok")
        if "loc.gov" not in b:
            raise SystemExit(f"{rid} is not a Library of Congress picture; cuts are copied into the site, so check its terms first")
        return b

    for c in cuts["labels"]:
        raw = RAW / f"label-{c['key']}.jpg"
        fetch(base(c["rec"]), c["box"], raw)
        a = trim(ink(raw, c.get("lo", 0.10), c.get("hi", 0.55)), 3)
        if c.get("vertical"):
            w = LABEL_H
            a = cv2.resize(a, (w, round(a.shape[0] * w / a.shape[1])), interpolation=cv2.INTER_AREA)
        else:
            a = cv2.resize(a, (round(a.shape[1] * LABEL_H / a.shape[0]), LABEL_H), interpolation=cv2.INTER_AREA)
        save(a, OUT / "labels" / f"{c['key']}.png")
        c["size"] = [int(a.shape[1]), int(a.shape[0])]

    for c in cuts["ornaments"]:
        if "box" not in c:
            notes = json.loads((ROOT / "_cache" / "cuts" / f"{c['rec']}.json").read_text())
            c["box"] = notes["ornaments"][c.pop("orn") - 1]["box"]
        c.pop("orn", None)
        raw = RAW / f"orn-{c['key']}.jpg"
        fetch(base(c["rec"]), c["box"], raw)
        a = trim(ink(raw, c.get("lo", 0.10), c.get("hi", 0.55)), 2)
        s = min(1.0, ORN_MAX / max(a.shape))
        if s < 1:
            a = cv2.resize(a, (round(a.shape[1] * s), round(a.shape[0] * s)), interpolation=cv2.INTER_AREA)
        save(a, OUT / "ornaments" / f"{c['key']}.png")
        c["size"] = [int(a.shape[1]), int(a.shape[0])]

    # The preview cannot load pictures from the library, so it carries one large copy of the front map.
    front = json.loads((ROOT / "data" / "front_map.json").read_text())
    out = ROOT / "_cache" / "pics" / "front.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not (out.exists() and out.stat().st_size > 100000):
        subprocess.run(["curl", "-sS", "-m", "240", "--retry", "3", "-A", UA, "-o", str(out),
                        f"{base(front['rec']).rstrip('/')}/full/{FRONT_PX},/0/default.jpg"], capture_output=True)

    path.write_text(json.dumps(cuts, indent=2, ensure_ascii=False) + "\n")
    total = sum(p.stat().st_size for p in OUT.rglob("*.png"))
    print(f"{len(cuts['labels'])} labels and {len(cuts['ornaments'])} ornaments, {total // 1024} KB in static/cuts/")


if __name__ == "__main__":
    sys.exit(main())
