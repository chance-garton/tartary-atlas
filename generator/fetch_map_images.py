#!/usr/bin/env python3
"""Fetch a small and a large picture of every map that has a working IIIF image route.

The pictures go to _cache/maps/ (not committed). The single-file preview publishes them beside
the page, because a Claude artifact cannot load images from other sites. The static site does not
use the copies: it loads each picture straight from the holding library's IIIF server.

Also writes data/map_images.json: the pixel size of each picture, so pages can reserve its space.

Run:  python3 generator/fetch_map_images.py        (skips pictures already fetched)
"""
import json
import pathlib
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "_cache" / "maps"
SIZES = {"s": 640, "l": 1400}


def jpeg_size(b):
    i = 2
    while i < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


def fetch(job):
    rid, base, key, px = job
    out = CACHE / f"{rid}-{key}.jpg"
    if not (out.exists() and out.stat().st_size > 2000):
        url = f"{base.rstrip('/')}/full/!{px},{px}/0/default.jpg"
        subprocess.run(["curl", "-sSL", "-m", "120", "--retry", "2", "-A", "TartaryAtlas/1.0 (research site build)",
                        "-o", str(out), url], capture_output=True)
    b = out.read_bytes() if out.exists() else b""
    size = jpeg_size(b) if b[:2] == b"\xff\xd8" else None
    if not size:
        out.unlink(missing_ok=True)
    return rid, key, size


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    iiif = json.loads((ROOT / "data" / "iiif.json").read_text())
    jobs = []
    for rid, routes in sorted(iiif.items()):
        img = next((e for e in routes if e["kind"] == "image" and e["status"] == "ok"), None)
        if img:
            for key, px in SIZES.items():
                jobs.append((rid, img["url"], key, px))
    sizes = {}
    with ThreadPoolExecutor(6) as ex:
        for rid, key, size in ex.map(fetch, jobs):
            if size:
                sizes.setdefault(rid, {})[key] = list(size)
            else:
                print("no picture:", rid, key, file=sys.stderr)
    sizes = {k: v for k, v in sizes.items() if "s" in v and "l" in v}
    (ROOT / "data" / "map_images.json").write_text(json.dumps(sizes, indent=0, sort_keys=True))
    print(f"{len(sizes)} maps with pictures")
    fetch_details(iiif)


def detail_url(pic, iiif):
    """Where a named picture in data/pictures.json loads from: a IIIF detail of a map, or a given address."""
    if pic.get("url"):
        return pic["url"]
    base = next(e["url"] for e in iiif[pic["rec"]] if e["kind"] == "image" and e["status"] == "ok")
    return f"{base.rstrip('/')}/{pic['region']}/{pic.get('width', 900)},/{pic.get('rotate', 0)}/default.jpg"


def fetch_details(iiif):
    path = ROOT / "data" / "pictures.json"
    pics = json.loads(path.read_text())
    out_dir = ROOT / "_cache" / "pics"
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, pic in pics.items():
        out = out_dir / f"{key}.jpg"
        stamp = out_dir / f"{key}.src"
        url = detail_url(pic, iiif)
        if not (out.exists() and stamp.exists() and stamp.read_text() == url):
            subprocess.run(["curl", "-sSL", "-m", "180", "--retry", "2", "-A", "TartaryAtlas/1.0 (research site build)",
                            "-o", str(out), url], capture_output=True)
            stamp.write_text(url)
        b = out.read_bytes() if out.exists() else b""
        size = jpeg_size(b) if b[:2] == b"\xff\xd8" else None
        if size:
            pic["size"] = list(size)
        else:
            print("no picture:", key, file=sys.stderr)
    path.write_text(json.dumps(pics, indent=2, ensure_ascii=False) + "\n")
    print(f"{sum(1 for p in pics.values() if p.get('size'))} of {len(pics)} detail pictures")


if __name__ == "__main__":
    main()
