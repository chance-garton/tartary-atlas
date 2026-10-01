#!/usr/bin/env python3
"""The time dial: bend old maps onto the real earth and find where each one letters Tartary.

Reads data/dial.json. Every map there names its Library of Congress picture, a list of matched places (a point on
the sheet in full-resolution pixels and the same place on the real earth) and the labels lettered on it (a line
through the lettering and its height). From the matched places a smooth bend (a thin plate spline) is fitted, the
sheet is redrawn on one shared sheet of the real earth, and each label's footprint is carried across with it.

Only Library of Congress pictures are bent, because the results are copied into the site (static/dial/).

Needs Pillow, numpy, scipy and OpenCV.

  python3 generator/dial_tools.py view  <key|iiif base> x y w h out.jpg    a piece of a sheet with a pixel grid drawn on it
  python3 generator/dial_tools.py check <work.json>                        fit one map, print how well, draw two check pictures
  python3 generator/dial_tools.py build                                    bend every map in data/dial.json into static/dial/
"""
import json
import math
import pathlib
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.interpolate import RBFInterpolator

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "_cache" / "dial"
OUT = ROOT / "static" / "dial"
UA = "TartaryAtlas/1.0 (research site build)"

# The shared sheet: an equidistant conic of Asia, the kind of projection the old mapmakers themselves reached for.
R_KM = 6371.0
PHI1, PHI2, PHI0, LAM0 = math.radians(30), math.radians(60), math.radians(46), math.radians(88)
N_CONE = (math.cos(PHI1) - math.cos(PHI2)) / (PHI2 - PHI1)
G_CONE = math.cos(PHI1) / N_CONE + PHI1
RHO0 = R_KM * (G_CONE - PHI0)
FRAME_KM = (-5000.0, -2900.0, 5000.0, 3350.0)     # x0, y0, x1, y1 in km east and north of 88 E, 46 N
FRAME_W = 1600
KM_PX = (FRAME_KM[2] - FRAME_KM[0]) / FRAME_W
FRAME_H = round((FRAME_KM[3] - FRAME_KM[1]) / KM_PX)
SRC_MAX = 4200                                      # longest side of the copy of a sheet that is bent
SMOOTHINGS = [1.5, 0.5, 0.15, 0.05]              # stiff to loose: a stiff bend keeps the sheet looking like itself


def project(lon, lat):
    """Longitude and latitude to pixels on the shared sheet."""
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    lon = np.where(lon < -60, lon + 360, lon)      # the far side of the Pacific sits east of Asia
    rho = R_KM * (G_CONE - np.radians(lat))
    th = N_CONE * (np.radians(lon) - LAM0)
    x = rho * np.sin(th)
    y = RHO0 - rho * np.cos(th)
    return (x - FRAME_KM[0]) / KM_PX, (FRAME_KM[3] - y) / KM_PX


def unproject(px, py):
    x = np.asarray(px, dtype=float) * KM_PX + FRAME_KM[0]
    y = FRAME_KM[3] - np.asarray(py, dtype=float) * KM_PX
    rho = np.hypot(x, RHO0 - y)
    th = np.arctan2(x, RHO0 - y)
    return np.degrees(th / N_CONE + LAM0), np.degrees(G_CONE - rho / R_KM)


def curl(url, out, tries=4):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(tries):
        subprocess.run(["curl", "-sS", "-m", "180", "--retry", "2", "-A", UA, "-o", str(out), url], capture_output=True)
        if out.exists() and out.stat().st_size > 2000:
            try:
                Image.open(out).verify()
                return out
            except Exception:
                pass
    raise SystemExit(f"could not fetch {url}")


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if pathlib.Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def view(base, x, y, w, h, out, px=1500):
    """A piece of a sheet at the best size the library gives, with full-resolution pixel coordinates ruled on it."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    size = "full" if max(w, h) <= px else f"!{px},{px}"
    raw = pathlib.Path(str(out) + ".raw.jpg")
    curl(f"{base.rstrip('/')}/{x},{y},{w},{h}/{size}/0/default.jpg", raw)
    im = Image.open(raw).convert("RGB")
    k = im.width / w
    if im.width < 900:                               # small pieces are enlarged so the ruling can be read
        f = 900 / im.width
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        k *= f
    d = ImageDraw.Draw(im, "RGBA")
    step = next(s for s in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000) if s * k >= 85)
    f = font(13)
    gx = (x // step + 1) * step
    while gx < x + w:
        X = (gx - x) * k
        d.line([(X, 0), (X, im.height)], fill=(0, 90, 255, 150), width=1)
        for Y in (2, im.height // 2, im.height - 16):
            d.rectangle([X + 2, Y, X + 4 + 8 * len(str(gx)), Y + 14], fill=(255, 255, 255, 215))
            d.text((X + 3, Y), str(gx), fill=(0, 60, 200, 255), font=f)
        gx += step
    gy = (y // step + 1) * step
    while gy < y + h:
        Y = (gy - y) * k
        d.line([(0, Y), (im.width, Y)], fill=(255, 40, 40, 150), width=1)
        for X in (2, im.width // 2, im.width - 8 * len(str(gy)) - 6):
            d.rectangle([X, Y + 2, X + 2 + 8 * len(str(gy)), Y + 16], fill=(255, 255, 255, 215))
            d.text((X + 1, Y + 2), str(gy), fill=(200, 0, 0, 255), font=f)
        gy += step
    im.save(out, quality=88)
    raw.unlink()
    print(f"{out}: sheet pixels x {x} to {x + w}, y {y} to {y + h}; grid every {step}; blue numbers are x, red numbers are y")


class Fit:
    """The bend between a sheet and the shared sheet, both ways."""

    def __init__(self, m, smoothing=None):
        pts = [p for p in m["points"] if not p.get("skip")]
        self.pts = pts
        self.size = m["size"]
        self.src = np.array([p["xy"] for p in pts], dtype=float)
        fx, fy = project([p["lonlat"][0] for p in pts], [p["lonlat"][1] for p in pts])
        self.dst = np.stack([fx, fy], axis=1)
        self.ks = max(self.size)                     # sheet pixels are scaled to about one
        self.kd = FRAME_W
        self.smoothing = smoothing if smoothing is not None else m.get("smoothing") or self.choose()
        self.to_sheet = self._rbf(self.dst / self.kd, self.src / self.ks, self.smoothing)
        self.to_frame = self._rbf(self.src / self.ks, self.dst / self.kd, self.smoothing)

    @staticmethod
    def _rbf(a, b, s):
        return RBFInterpolator(a, b, kernel="thin_plate_spline", smoothing=s, degree=1)

    def loo(self, s):
        """Leave each place out in turn and see how far the bend puts it from where it belongs, in km."""
        n = len(self.src)
        err = np.zeros(n)
        for i in range(n):
            keep = np.arange(n) != i
            f = self._rbf(self.src[keep] / self.ks, self.dst[keep] / self.kd, s)
            err[i] = np.hypot(*(f(self.src[i:i + 1] / self.ks)[0] * self.kd - self.dst[i])) * KM_PX
        return err

    def choose(self):
        best, best_s = None, None
        for s in SMOOTHINGS:
            e = float(np.sqrt(np.mean(self.loo(s) ** 2)))
            if best is None or e < best * 0.88:      # a stiffer bend wins unless a looser one is clearly better
                best, best_s = e, s
        return best_s

    def sheet(self, frame_xy):
        return self.to_sheet(np.asarray(frame_xy, dtype=float) / self.kd) * self.ks

    def frame(self, sheet_xy):
        return self.to_frame(np.asarray(sheet_xy, dtype=float) / self.ks) * self.kd

    def grid(self, step=8):
        """Where on the sheet every pixel of the shared sheet comes from."""
        gx, gy = np.meshgrid(np.arange(0, FRAME_W + step, step), np.arange(0, FRAME_H + step, step))
        s = self.sheet(np.stack([gx.ravel(), gy.ravel()], axis=1)).reshape(gy.shape + (2,)).astype(np.float32)
        mx = cv2.resize(s[..., 0], (gx.shape[1] * step, gx.shape[0] * step), interpolation=cv2.INTER_LINEAR)[:FRAME_H, :FRAME_W]
        my = cv2.resize(s[..., 1], (gx.shape[1] * step, gx.shape[0] * step), interpolation=cv2.INTER_LINEAR)[:FRAME_H, :FRAME_W]
        # cv2.resize treats samples as pixel centres; the half-step shift this causes is far below the fit's own error
        return mx, my


def source_picture(m):
    """A copy of the whole sheet, small enough to bend."""
    key = m["key"]
    out = CACHE / "src" / f"{key}.jpg"
    if not (out.exists() and out.stat().st_size > 50000):
        # the library blurs a picture it is asked to enlarge, so a small scan is taken at its own size
        size = "full" if max(m["size"]) <= SRC_MAX else f"!{SRC_MAX},{SRC_MAX}"
        curl(f"{m['iiif'].rstrip('/')}/full/{size}/0/default.jpg", out)
    return out


def neat_mask(m, shape, k):
    """What part of the copy is map: the neat line if one is given, else the whole sheet."""
    mask = np.zeros(shape[:2], np.uint8)
    neat = m.get("neat")
    if not neat:
        mask[:] = 255
    elif isinstance(neat[0], (list, tuple)):
        cv2.fillPoly(mask, [np.round(np.array(neat) * k).astype(np.int32)], 255)
    else:
        x0, y0, x1, y1 = [round(v * k) for v in neat]
        mask[y0:y1, x0:x1] = 255
    for hole in m.get("holes", []):                  # cartouches and tables that cover the sea of another sheet
        if isinstance(hole[0], (list, tuple)):
            cv2.fillPoly(mask, [np.round(np.array(hole) * k).astype(np.int32)], 0)
        else:
            x0, y0, x1, y1 = [round(v * k) for v in hole]
            mask[y0:y1, x0:x1] = 0
    return mask


def warp(m, fit):
    src = cv2.imread(str(source_picture(m)))
    k = src.shape[1] / m["size"][0]
    mx, my = fit.grid()
    mask = neat_mask(m, src.shape, k)
    img = cv2.remap(src, mx * k, my * k, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    a = cv2.remap(mask, mx * k, my * k, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # where the bend folds back on itself the sheet is not drawn
    jx = np.gradient(mx, axis=1) * np.gradient(my, axis=0) - np.gradient(mx, axis=0) * np.gradient(my, axis=1)
    a[jx <= 0] = 0
    # nothing is drawn far from every matched place: out there the bend is a guess
    far = m.get("reach_km", 3000) / KM_PX
    near = np.ones((FRAME_H, FRAME_W), np.uint8)
    for x, y in fit.dst:
        if 0 <= x < FRAME_W and 0 <= y < FRAME_H:
            near[int(y), int(x)] = 0
    dist = cv2.distanceTransform(near, cv2.DIST_L2, 5)
    a[dist > far] = 0
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((9, 9), np.uint8)), (0, 0), 5)
    return img, a, (mx, my)


def to_frame_exact(pts, grid):
    """Carry sheet points to the shared sheet by looking them up in the bend that drew the picture, so a
    footprint sits on its own lettering."""
    mx, my = grid
    out = []
    step = 4
    sx, sy = mx[::step, ::step], my[::step, ::step]
    for x, y in pts:
        d = (sx - x) ** 2 + (sy - y) ** 2
        i = np.unravel_index(np.argmin(d), d.shape)
        y0, x0 = i[0] * step, i[1] * step
        ya, yb, xa, xb = max(0, y0 - step), min(FRAME_H, y0 + step + 1), max(0, x0 - step), min(FRAME_W, x0 + step + 1)
        d2 = (mx[ya:yb, xa:xb] - x) ** 2 + (my[ya:yb, xa:xb] - y) ** 2
        j = np.unravel_index(np.argmin(d2), d2.shape)
        out.append((float(xa + j[1]), float(ya + j[0]), float(np.sqrt(d2[j]))))
    return out


def spine_points(spine, n=9):
    """The line through a label, resampled to n evenly spaced points."""
    p = np.array(spine, dtype=float)
    seg = np.hypot(*np.diff(p, axis=0).T)
    t = np.concatenate([[0], np.cumsum(seg)])
    if t[-1] == 0:
        return np.repeat(p[:1], n, axis=0)
    u = np.linspace(0, t[-1], n)
    return np.stack([np.interp(u, t, p[:, 0]), np.interp(u, t, p[:, 1])], axis=1)


def band(label, n=9):
    """The outline of a label on the sheet: its line, half its height to either side, with a little room."""
    p = spine_points(label["spine"], n)
    h = label["h"] * 0.5 * 1.25
    d = np.gradient(p, axis=0)
    ln = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
    nx, ny = -d[:, 1] / ln, d[:, 0] / ln
    ext = h * 0.7
    first = p[0] - d[0] / ln[0] * ext
    last = p[-1] + d[-1] / ln[-1] * ext
    q = np.vstack([first, p, last])
    nx = np.concatenate([[nx[0]], nx, [nx[-1]]])
    ny = np.concatenate([[ny[0]], ny, [ny[-1]]])
    up = np.stack([q[:, 0] + nx * h, q[:, 1] + ny * h], axis=1)
    dn = np.stack([q[:, 0] - nx * h, q[:, 1] - ny * h], axis=1)
    return p, np.vstack([up, dn[::-1]])


def coast_layer():
    """The modern coast on the shared sheet, for checking."""
    land = json.loads((ROOT / "static" / "basemap" / "land.json").read_text())
    lines = []
    for g in land["geometries"]:
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                a = np.array(ring)[:, :2]
                if a[:, 0].max() < -30 and a[:, 0].min() > -170 and not (a[:, 1].max() > 50 and a[:, 0].min() < -120):
                    continue
                x, y = project(a[:, 0], a[:, 1])
                if x.max() < -200 or x.min() > FRAME_W + 200 or y.max() < -200 or y.min() > FRAME_H + 200:
                    continue
                lines.append(np.stack([x, y], axis=1))
    return lines


def check(path):
    m = json.loads(pathlib.Path(path).read_text())
    key = m["key"]
    pts = [p for p in m["points"] if not p.get("skip")]
    if len(pts) < 6:
        raise SystemExit("at least six matched places are needed")
    fit = Fit(m)
    err = fit.loo(fit.smoothing)
    resid = np.hypot(*(fit.frame(fit.src) - fit.dst).T) * KM_PX
    print(f"{key}: {len(pts)} matched places, smoothing {fit.smoothing}")
    print(f"  left-one-out error: median {np.median(err):.0f} km, worst {err.max():.0f} km   (after fitting: median {np.median(resid):.0f} km)")
    order = np.argsort(-err)
    med = np.median(err)
    for i in order:
        flag = "  <-- look again" if err[i] > max(3 * med, 400) else ""
        print(f"  {i + 1:>3} {pts[i]['name'][:30]:<30} on map: {str(pts[i].get('on_map', ''))[:28]:<28} {err[i]:>6.0f} km{flag}")
    img, a, grid = warp(m, fit)
    covered = (a > 128).mean()
    print(f"  the bent sheet covers {covered * 100:.0f}% of the shared sheet")
    # picture 1: the sheet itself with the matched places and labels
    src = Image.open(source_picture(m)).convert("RGB")
    k = src.width / m["size"][0]
    d = ImageDraw.Draw(src, "RGBA")
    f = font(max(14, src.width // 150))
    r = max(5, src.width // 400)
    for i, p in enumerate(pts):
        x, y = p["xy"][0] * k, p["xy"][1] * k
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 0, 255), width=3)
        d.text((x + r + 2, y - r - 2), f"{i + 1} {p['name']}", fill=(200, 0, 0, 255), font=f, stroke_width=2, stroke_fill=(255, 255, 255, 230))
    for lb in m.get("labels", []) + m.get("also", []):
        _, poly = band(lb)
        col = (0, 90, 255, 255) if lb in m.get("labels", []) else (0, 150, 60, 255)
        d.line([tuple(q * k) for q in np.vstack([poly, poly[:1]])], fill=col, width=3)
        d.text(tuple(np.array(lb["spine"][0]) * k + [0, -lb["h"] * k]), lb["reads"], fill=col, font=f, stroke_width=2, stroke_fill=(255, 255, 255, 230))
    if m.get("neat") and not isinstance(m["neat"][0], (list, tuple)):
        x0, y0, x1, y1 = [v * k for v in m["neat"]]
        d.rectangle([x0, y0, x1, y1], outline=(255, 160, 0, 255), width=3)
    src.thumbnail((2400, 2400))
    CACHE.joinpath("check").mkdir(parents=True, exist_ok=True)
    p1 = CACHE / "check" / f"{key}-points.jpg"
    src.save(p1, quality=85)
    # picture 2: the bent sheet under the modern coast
    back = np.full((FRAME_H, FRAME_W, 3), 235, np.uint8)
    al = (a.astype(np.float32) / 255)[..., None]
    comp = (img[..., ::-1] * al + back * (1 - al)).astype(np.uint8)
    im = Image.fromarray(comp)
    d = ImageDraw.Draw(im, "RGBA")
    for line in coast_layer():
        d.line([tuple(q) for q in line], fill=(0, 200, 255, 230), width=2)
    for lon in range(20, 181, 20):
        x, y = project(np.full(60, lon), np.linspace(5, 85, 60))
        d.line(list(zip(x, y)), fill=(0, 0, 0, 60), width=1)
    for lat in range(10, 81, 10):
        x, y = project(np.linspace(0, 190, 120), np.full(120, lat))
        d.line(list(zip(x, y)), fill=(0, 0, 0, 60), width=1)
    f2 = font(13)
    for i, p in enumerate(pts):
        tx, ty = fit.dst[i]
        d.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=(255, 0, 0, 255))
        d.text((tx + 6, ty - 8), f"{i + 1} {p['name']}", fill=(160, 0, 0, 255), font=f2, stroke_width=2, stroke_fill=(255, 255, 255, 230))
    for lb in m.get("labels", []) + m.get("also", []):
        _, poly = band(lb)
        fr = to_frame_exact(poly, grid)
        col = (0, 60, 255, 255) if lb in m.get("labels", []) else (0, 140, 60, 255)
        d.line([(q[0], q[1]) for q in fr + fr[:1]], fill=col, width=2)
    p2 = CACHE / "check" / f"{key}-warp.jpg"
    im.save(p2, quality=85)
    print(f"  look at {p1} (the sheet: red rings are matched places, blue outlines Tartary labels, green other names)")
    print(f"  and at {p2} (the sheet bent onto the earth: the cyan line is the real coast, red dots are where each place really is)")


def build():
    path = ROOT / "data" / "dial.json"
    dial = json.loads(path.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for m in dial["maps"]:
        if not m.get("iiif"):
            continue
        if "loc.gov" not in m["iiif"]:
            raise SystemExit(f"{m['key']} is not a Library of Congress picture; bent sheets are copied into the site, so check its terms first")
        fit = Fit(m)
        m["smoothing"] = fit.smoothing
        err = fit.loo(fit.smoothing)
        img, a, grid = warp(m, fit)
        rgba = np.dstack([img[..., ::-1], a])
        out = OUT / f"{m['key']}.webp"
        Image.fromarray(rgba, "RGBA").save(out, "WEBP", quality=m.get("quality", 70), method=6)
        total += out.stat().st_size
        ys, xs = np.where(a > 128)
        m["drawn"] = {
            "places": len(fit.pts), "median_km": int(round(float(np.median(err)))), "worst_km": int(round(float(err.max()))),
            "box": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        }
        for group in ("labels", "also"):
            for lb in m.get(group, []):
                sp, poly = band(lb)
                fr = to_frame_exact(poly, grid)
                mid = to_frame_exact(sp, grid)
                lb["frame"] = [[round(q[0], 1), round(q[1], 1)] for q in fr]
                lb["mid"] = [[round(q[0], 1), round(q[1], 1)] for q in mid]
                lon, lat = unproject(np.mean([q[0] for q in mid]), np.mean([q[1] for q in mid]))
                lb["at"] = [round(float(lon), 1), round(float(lat), 1)]
        print(f"{m['key']}: {len(fit.pts)} places, median {m['drawn']['median_km']} km, {out.stat().st_size // 1024} KB")
    dial["frame"] = {"w": FRAME_W, "h": FRAME_H, "km_per_px": KM_PX, "projection": "equidistant conic, standard parallels 30 N and 60 N, centred 88 E 46 N"}
    path.write_text(json.dumps(dial, indent=1, ensure_ascii=False) + "\n")
    print(f"{total // 1024} KB in static/dial/")


def main():
    a = sys.argv[1:]
    if a and a[0] == "view":
        base = a[1]
        if not base.startswith("http"):
            work = CACHE / "work" / f"{base}.json"
            base = json.loads(work.read_text())["iiif"]
        view(base, *a[2:6], a[6])
    elif a and a[0] == "check":
        check(a[1])
    elif a and a[0] == "build":
        build()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
