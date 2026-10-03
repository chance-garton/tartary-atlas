#!/usr/bin/env python3
"""Build The Tartary Atlas.

Reads the site data layer in data/*.json and writes:
  docs/      the static site, one HTML file per page (GitHub Pages serves this folder)
  preview/   a single-file preview of the same pages, for a private Claude artifact

Run:  python3 generator/build.py            (both outputs)
      python3 generator/build.py --static   (docs/ only)
"""
import collections
import hashlib
import html
import json
import math
import pathlib
import re
import shutil
import sys
import experience
import storybook

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
OUT = ROOT / "docs"
PREVIEW = ROOT / "preview"

CONFIG = {
    "site_name": "The Tartary Atlas",
    "base_url": "https://tartary.innerversepodcast.com",
    "repo_url": "https://github.com/chance-garton/tartary-atlas",
    "researcher": "Chance Garton",
    "podcast_name": "InnerVerse Podcast",
    "podcast_url": "https://innerversepodcast.com",
    "maplibre_js": "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.js",
    "osd_js": "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js",
    "fonts": "https://fonts.googleapis.com/css2?family=IM+Fell+English&family=IM+Fell+English+SC&family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..500&family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400..700&display=swap",
}

LABEL_IDS = ["tartary", "great-tartary", "little-tartary", "chinese-tartary",
             "independent-tartary", "muscovite-tartary", "eastern-tartary", "desert-tartary"]

EVIDENCE = {
    "firsthand": "The author saw the places or people described.",
    "mixed": "Part firsthand observation, part drawn from other sources.",
    "compilation": "Assembled from earlier sources. The author did not observe it directly.",
    "informant testimony": "Written down from what informants reported.",
    "official or contemporary record": "An official document or a record made at the time.",
    "claimed or disputed": "Authorship, date or authenticity is claimed or contested.",
    "not stated": "The catalogue does not say how the author knew.",
}
EVIDENCE_ORDER = list(EVIDENCE)

PRECISION = {
    "exact": "exact year",
    "circa": "approximate",
    "decade": "within a decade",
    "range": "a range",
    "century": "within a century",
    "century (clamped to subject start)": "within a century",
    "century (inferred from subject; recension unverified)": "century, inferred",
    "debated range": "debated",
    "disputed": "disputed",
}

BASIS = {
    "exact": ("Surveyed point", "A modern coordinate for a town, site or feature, taken from Wikipedia or Wikidata."),
    "river": ("River, plotted at its mouth", "A river's reference coordinate, usually its mouth. The river itself runs far from the dot."),
    "capital": ("Polity, plotted at its capital", "A state or dynasty drawn at its capital city. Its territory was much larger."),
    "approx": ("Approximate point", "An editor's approximate point for a historical region. The region had no single location."),
    "anchor": ("Map label position", "Where this label usually sits on period maps. A label, not a surveyed place."),
    "none": ("No point by design", "The name covers too much, or moved too much from map to map, for one point to be honest."),
}

FAMILY_SHORT = {
    "jochid-tatars": "Golden Horde and Tatar khanates",
    "mongols": "Mongols",
    "manchus": "Jurchen and Manchus",
    "turkic-central-asia": "Turkic and Central Asian peoples",
    "western-mongols": "Western Mongols (Oirat, Kalmyk)",
    "region-label": "A regional label",
    "siberian": "Peoples of Siberia",
    "unspecified": "Not specified",
}

FAMILY_EXTRA = {
    "unspecified": "Not specified",
    "region-label": "A regional label rather than a people",
}

LINEAGE_TYPES = {
    "derived": "derived from",
    "same-plate": "same plate",
    "same-atlas": "same atlas",
    "same-work": "same work",
    "text": "accompanying text",
    "tradition": "same tradition",
    "reproduction": "reproduction",
    "corrected-by": "corrected by",
}

# How a lineage link reads from the record page. "in": this record is the edge target; "out": the source.
LINEAGE_PHRASE = {
    ("derived", "in"): "this one was drawn from it",
    ("derived", "out"): "drawn from this one",
    ("reproduction", "in"): "this one reproduces it",
    ("reproduction", "out"): "reproduces this one",
    ("corrected-by", "in"): "this one corrects it",
    ("corrected-by", "out"): "corrects this one",
    ("text", "in"): "accompanying text or map",
    ("text", "out"): "accompanying text or map",
}

DIRECTED = {"derived", "reproduction", "corrected-by"}

LINEAGE_SHORT = {
    "M001": "al-Idrisi", "M002": "Catalan Atlas", "M003": "Waldseemüller", "M004": "Ortelius",
    "M006": "Remezov", "M009": "Covens & Mortier", "M012": "Bellin", "M016": "d'Anville",
    "M019": "Stodart & Currier", "M021": "Miller after Idrisi", "M022": "d'Anville", "M027": "Fra Mauro",
    "M028": "Remezov", "M031": "Ptolemy, Ulm", "M032": "Psalter map", "M033": "Ides", "M035": "Georgi",
    "M038": "Hereford", "M039": "Catalan Estense", "M040": "Genoese map", "M042": "Bianco",
    "M043": "Ebstorf", "M044": "Carta marina", "M045": "Ptolemy, Rome", "M046": "Jenkinson (1914 copy)",
    "M047": "Ortelius (Vrients)", "M048": "de Wit", "M049": "Hondius", "M050": "Blaeu", "M051": "Allard",
    "M052": "Sanson", "M053": "Jaillot", "M054": "Cantelli", "M055": "Lotter", "M056": "Kirilov",
    "M057": "St Petersburg Academy", "M058": "SDUK", "M059": "SDUK", "M060": "SDUK", "M061": "Tanner",
    "M062": "Mitchell", "M063": "Mitchell", "M066": "Stieler", "M067": "Stieler",
    "M068": "Grimm & Mahlmann", "M069": "Grimm & Mahlmann", "M071": "Lapie", "M072": "Cary",
    "M073": "Cassini", "M074": "Meyer", "M077": "Fremin", "M079": "Mercator", "M080": "Strahlenberg",
    "M081": "Jenkinson", "M082": "Ortelius", "M083": "Witsen", "M084": "Homann Heirs", "M085": "Fries",
    "M086": "de Wit", "M088": "Klaproth", "M089": "Humboldt", "M091": "Gastaldi", "M093": "Istakhri",
    "M094": "Ibn Hawqal", "M095": "Kashgari", "M096": "Katib Çelebi", "M099": "Remezov",
    "M100": "Atlas Russicus", "M101": "Pyadyshev", "M102": "Verbiest", "M103": "Nagakubo",
    "M104": "Hua yi tu", "M105": "Yu ji tu", "M106": "Luo Hongxian", "M107": "Kangxi atlas copy",
    "M108": "Kangxi atlas (Fuchs)", "M110": "Li Zhaoluo", "M111": "Qianlong atlas copy",
    "M116": "Zuo Junheng", "M118": "Ricci", "W002": "Strahlenberg", "W039": "Ibn Hawqal",
    "W079": "Phil. Trans. notice", "W122": "Witsen", "W211": "Katib Çelebi", "W219": "Kashgari",
}

NAV = [
    ("passages", "In their words"), ("maps", "Map room"), ("map", "Wander the map"), ("sources", "Witnesses"),
    ("archive", "The vault"), ("about", "About"),
]

# Pages that sit under a main heading in the navigation.
NAV_GROUP = {
    "records": "archive", "places": "archive", "peoples": "archive", "labels": "archive",
    "meanings": "archive", "lineage": "archive", "method": "archive", "corrections": "archive",
}

# The five trails through the passages. Order is the order shown.
THEMES = collections.OrderedDict([
    ("cities", {
        "label": "Cities", "q": "Did the Tartars have cities?",
        "blurb": "Capitals, camps that worked as cities, towns taken and towns ruined, and who each source says built them.",
    }),
    ("architecture", {
        "label": "Buildings", "q": "What did they build, and what did they live in?",
        "blurb": "Felt tents, houses on wagons, timber, brick and stone, mosques, palaces and tombs, and whom each source credits as the builder.",
    }),
    ("customs", {
        "label": "Daily life", "q": "How did they live?",
        "blurb": "Food and drink, marriage, burial, faith, law, dress, horses, war and trade, as visitors and neighbours wrote them down.",
    }),
    ("names", {
        "label": "The name", "q": "Who were the Tartars, and where did the name come from?",
        "blurb": "Origin stories, the Tatar tribe and the Mongols, Tartar used for Manchus and for Siberian peoples, the Tartarus pun, and Tartary as a label on maps.",
    }),
    ("outliers", {
        "label": "Strange tales", "q": "What are the strangest things the sources say?",
        "blurb": "Monsters and marvels, Gog and Magog, Prester John, the vegetable lamb, and rumours the authors themselves doubted, each marked as seen, heard or legend.",
    }),
])

# How the author knew what a single passage says.
PBASIS = collections.OrderedDict([
    ("saw", ("Saw it", "The author describes something they saw themselves.")),
    ("heard", ("Heard it", "The author was told this by someone else.")),
    ("read", ("Read it", "The author took this from an earlier book or document.")),
    ("legend", ("Legend or rumour", "A legend, a rumour, or a tale the author repeats.")),
    ("record", ("Official record", "An official document or a record made at the time.")),
    ("mixed", ("Mixed", "Part seen, part heard or read.")),
])

# How the author of a whole source knew, from the reading profile.
HOW_KNEW = {
    "saw it": "Eyewitness", "mixed": "Part eyewitness", "heard it": "From informants",
    "compiled": "Compiled from others", "official record": "Official record", "legend collection": "Legends",
}

# Who holds each map picture, by the address of its image server.
HOLDERS = {
    "tile.loc.gov": "Library of Congress",
    "www.davidrumsey.com": "David Rumsey Map Collection (CC BY-NC-SA)",
    "iiif.bodleian.ox.ac.uk": "Bodleian Libraries, University of Oxford (CC BY-NC)",
    "digi.vatlib.it": "Biblioteca Apostolica Vaticana",
    "api.digitale-sammlungen.de": "Bayerische Staatsbibliothek, Munich",
    "www.e-rara.ch": "e-rara, the platform for rare books in Swiss libraries",
    "rmda.kulib.kyoto-u.ac.jp": "Kyoto University Rare Materials Digital Archive",
    "glam.uni.wroc.pl": "Wroclaw University Library",
    "imagines.manuscriptorium.com": "Manuscriptorium",
}
# Pictures that show a cover, a title page or a page of text from the volume, not the map itself.
NOT_MAP_VIEW = {"M001", "M016", "M106", "M111", "M116"}
MAP_PX = {"s": 640, "l": 1400}
# Maps shown on the front page, oldest first.
HOME_MAPS = ["M002", "M081", "M049", "M007", "M080", "M072"]
ERAS = [("e0", "Before 1500", None, 1499), ("e1", "1500s", 1500, 1599), ("e2", "1600s", 1600, 1699),
        ("e3", "1700s", 1700, 1799), ("e4", "1800s", 1800, None)]

COPY_BTN = '<button type="button" class="psg-copy" data-copy>Copy quote</button>'
PSG_PARTIAL = "The scan is too rough to double-check this quote by machine. Compare it with the page."
FIRST_FEATURE = "W043-05"     # what the front page shows when the page script does not run
FEATURE_PER_TRAIL = 20
FEATURE_PER_SOURCE = 2
FRONT_PREVIEW_PX = 4200  # width of the preview's own copy of the front map (_cache/pics/front.jpg)
FRONT_PER_PIN = 4       # passages each pin on the front map brings into the pool
PAGE_SIZE = 10

EM_DASH = "—"


# ---------------------------------------------------------------- helpers

def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def year(y):
    return f"{-y} BCE" if y < 0 else str(y)


def ordinal(n):
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def span_label(s, e, p):
    if s is None:
        return "Undated"
    p = p or ""
    if e is None or s == e:
        core = year(s)
    elif p.startswith("decade") and s % 10 == 0 and e == s + 9:
        core = f"{s}s"
    elif p.startswith("century") and s > 0 and s % 100 == 0 and e == s + 99:
        core = f"{ordinal(s // 100 + 1)} century"
    elif s < 0 and e < 0:
        core = f"{-s}–{-e} BCE"
    else:
        core = f"{year(s)}–{year(e)}"
    if p == "circa":
        core = "c. " + core
    return core


def made_label(r):
    d = r["date"]
    if d["made_start"] is None:
        return "Undated"
    return span_label(d["made_start"], d["made_end"], d["made_precision"])


def prec_label(p):
    return PRECISION.get(p or "", p or "")


def sort_key(r):
    d = r["date"]
    if d["made_start"] is None:
        return (1, 0, 0, r["id"])
    return (0, d["made_start"], d["made_end"] or d["made_start"], r["id"])


def short_title(t, n=64):
    t = t or ""
    for sep in [" (", ": ", "; ", " / "]:
        i = t.find(sep)
        if 10 < i:
            t = t[:i]
    t = t.strip().rstrip(",")
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return t


def short_creator(c, n=52):
    c = c or ""
    c = re.sub(r"^(Attributed (in the sheet |in edition )?to )", "", c, flags=re.I)
    seg = re.split(r";| \(|, (?:after|with|engraved|published|drawn|revised|printed|editor)\b", c)[0]
    seg = seg.strip().rstrip(",")
    if len(seg) > n:
        seg = seg[:n].rsplit(" ", 1)[0] + "…"
    return seg


def tradition_label(t):
    if t.startswith("English pass") or t.endswith("English pass lead re-check"):
        return "English-language sources"
    return t.replace("Multilingual pass: ", "")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def basis_group(b):
    b = b or ""
    if b.startswith("wikipedia (river"):
        return "river"
    if b.startswith("capital"):
        return "capital"
    if b in ("approx", "centroid"):
        return "approx"
    if b == "anchor":
        return "anchor"
    if b.startswith("none"):
        return "none"
    return "exact"


def coord_text(lat, lon):
    return f"{abs(lat):.2f}° {'N' if lat >= 0 else 'S'}, {abs(lon):.2f}° {'E' if lon >= 0 else 'W'}"


URL_RE = re.compile(r"https?://[^\s<>\"')\]]+[^\s<>\"')\].,;:]")
ID_RE = re.compile(r"\b([WM]\d{3})\b")


def first_sentence(t, n=158):
    t = (t or "").strip()
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    s = m.group(1) if m else t
    if len(s) > n:
        s = s[:n].rsplit(" ", 1)[0] + "…"
    return s


def smart(s):
    """Typographic quotes for display titles."""
    s = re.sub(r"(^|[\s(\[/])'", "\\1\u2018", s or "")
    s = s.replace("'", "\u2019")
    s = re.sub(r'(^|[\s(\[/])"', "\\1\u201c", s)
    return s.replace('"', "\u201d")


def no_em(s):
    return (s or "").replace(" — ", ", ").replace(EM_DASH, ", ")


def psg_best_key(p):
    return (-p["strength"], p["x"], p["id"])


def nav_group(nav):
    return NAV_GROUP.get(nav, nav)


def num(n):
    return f"{n:,}"


# ---------------------------------------------------------------- data

class Site:
    def __init__(self):
        self.records = json.loads((DATA / "records.json").read_text())
        self.places = json.loads((DATA / "places.json").read_text())
        self.peoples = json.loads((DATA / "peoples.json").read_text())
        self.families = json.loads((DATA / "people_families.json").read_text())
        self.lineage = json.loads((DATA / "lineage.json").read_text())
        self.iiif = json.loads((DATA / "iiif.json").read_text())
        self.meta = json.loads((DATA / "meta.json").read_text())
        self.map_img = self.optional("map_images.json")
        self.pics = {k: v for k, v in self.optional("pictures.json").items() if v.get("size")}
        cuts = self.optional("cuts.json")
        self.labels = [c for c in cuts.get("labels", []) if c.get("size")]
        self.orn = {c["key"]: c for c in cuts.get("ornaments", []) if c.get("size")}
        self.front = self.optional("front_map.json")
        self.journeys = self.optional("journeys.json").get("journeys", [])
        self.dial = self.optional("dial.json")
        corr_path = DATA / "corrections.json"
        self.corrections = json.loads(corr_path.read_text()) if corr_path.exists() else []
        self.apply_corrections()
        self.load_passages()

        self.rec = {r["id"]: r for r in self.records}
        self.place = {p["id"]: p for p in self.places}
        self.people = {p["id"]: p for p in self.peoples}
        self.people_records = collections.defaultdict(list)
        for r in self.records:
            for pid in r["peoples"]:
                self.people_records[pid].append(r["id"])
        self.edges_by = collections.defaultdict(list)
        for e in self.lineage:
            self.edges_by[e["source"]].append(("out", e))
            self.edges_by[e["target"]].append(("in", e))

    @staticmethod
    def optional(name):
        path = DATA / name
        return json.loads(path.read_text()) if path.exists() else {}

    def iiif_base(self, rid):
        img = next((e for e in self.iiif.get(rid, []) if e["kind"] == "image" and e["status"] == "ok"), None)
        return img["url"].rstrip("/") if img else None

    def holder(self, rid):
        base = self.iiif_base(rid)
        return HOLDERS.get(base.split("/")[2], base.split("/")[2]) if base else ""

    def load_passages(self):
        """Source profiles and themed passages from the reading pass (data/passages.json)."""
        path = DATA / "passages.json"
        d = json.loads(path.read_text()) if path.exists() else {"profiles": {}, "passages": [], "built": None}
        self.profiles = d["profiles"]
        self.passages = d["passages"]
        self.passages_built = d.get("built")
        self.psg = {}
        self.psg_by_rec = collections.defaultdict(list)
        self.psg_by_place = collections.defaultdict(list)
        self.psg_by_theme = collections.defaultdict(list)
        for p in self.passages:
            # A fixed scatter value, so "a mix of the best" is the same on every build and in the page script.
            p["x"] = int(hashlib.md5(p["id"].encode()).hexdigest()[:6], 16)
            self.psg[p["id"]] = p
        best = sorted(self.passages, key=psg_best_key)
        for p in best:
            self.psg_by_rec[p["rec"]].append(p)
            self.psg_by_theme[p["theme"]].append(p)
            for pid in p["place_ids"]:
                self.psg_by_place[pid].append(p)
        self.psg_best = best

    def apply_corrections(self):
        rec = {r["id"]: r for r in self.records}
        for c in self.corrections:
            r = rec[c["record"]]
            obj, field = r, c["field"]
            if "." in field:
                a, b = field.split(".", 1)
                obj, field = r[a], b
            if c["find"] not in (obj[field] or ""):
                raise SystemExit(f"Correction {c['id']}: text not found in {c['record']}.{c['field']}")
            obj[field] = obj[field].replace(c["find"], c["replace"])
            r.setdefault("_corrections", []).append(c["id"])

    def rkey(self, r):
        if isinstance(r, str):
            r = self.rec[r]
        return ("w/" if r["kind"] == "written" else "m/") + r["id"]

    def family_name(self, f):
        return self.families.get(f) or FAMILY_EXTRA.get(f) or f


# ---------------------------------------------------------------- link context

class Ctx:
    """Knows how to link from the page being rendered, in static or preview mode."""

    def __init__(self, mode, key):
        self.mode = mode
        self.key = key
        self.depth = 0 if key == "" else key.count("/") + 1

    @property
    def root(self):
        return "../" * self.depth if self.depth else "./"

    def link(self, key):
        if self.mode == "preview":
            return "#" + (key.replace("/", "-") if key else "home")
        return self.root + (key + "/" if key else "")

    def asset(self, name):
        if self.mode == "preview":
            return "assets/" + name
        return self.root + "assets/" + name

    def map_img(self, site, rid, size="s"):
        """A picture of a map. The preview serves its own copy; the static site asks the holding library."""
        if self.mode == "preview":
            return f"assets/maps/{rid}-{size}.jpg"
        return f"{site.iiif_base(rid)}/full/!{MAP_PX[size]},{MAP_PX[size]}/0/default.jpg"

    def pic(self, site, key):
        """A named picture from data/pictures.json: a detail of a map, or an image at a given address."""
        if self.mode == "preview":
            return f"assets/pics/{key}.jpg"
        pic = site.pics[key]
        if pic.get("url"):
            return pic["url"]
        return f"{site.iiif_base(pic['rec'])}/{pic['region']}/{pic.get('width', 900)},/{pic.get('rotate', 0)}/default.jpg"

    def land_href(self):
        return "#ta-land" if self.mode == "preview" else self.asset("eurasia.svg") + "#ta-land"


def linkify(site, ctx, text):
    """Escape card text, then link URLs and record IDs that have pages."""
    out, pos = [], 0
    text = no_em(text)
    for m in URL_RE.finditer(text):
        out.append(link_ids(site, ctx, text[pos:m.start()]))
        u = m.group(0)
        label = re.sub(r"^https?://(www\.)?", "", u)
        if len(label) > 48:
            label = label[:46] + "…"
        out.append(f'<a href="{esc(u)}" rel="noopener">{esc(label)}</a>')
        pos = m.end()
    out.append(link_ids(site, ctx, text[pos:]))
    return "".join(out)


def link_ids(site, ctx, s):
    s = esc(s)

    def rep(m):
        i = m.group(1)
        if i in site.rec:
            return f'<a class="rid" href="{ctx.link(site.rkey(i))}">{i}</a>'
        return i
    return ID_RE.sub(rep, s)


# ---------------------------------------------------------------- mini map

MM_W, MM_H = 594, 340


def mm_proj(lon, lat):
    if lon < -20:
        lon += 360
    return (lon + 20) * 0.707 * 4, (80 - lat) * 4


def build_land_svg():
    g = json.loads((ROOT / "generator" / "ne_110m_land.geojson").read_text())
    parts = []
    for f in g["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                shift = 360 if max(p[0] for p in ring) < -20 else 0
                pts = []
                for lon, lat in ring:
                    x, y = (lon + shift + 20) * 0.707 * 4, (80 - lat) * 4
                    pts.append(f"{x:.1f} {y:.1f}")
                parts.append("M" + "L".join(pts) + "Z")
    d = "".join(parts)
    return f'<symbol id="ta-land" viewBox="0 0 {MM_W} {MM_H}"><path d="{d}"/></symbol>'


def minimap(site, ctx, place_ids, caption=True):
    k = 1.5 if len(place_ids) == 1 else 1.0
    pts, missing = [], 0
    labels = []
    for pid in place_ids:
        p = site.place.get(pid)
        if not p or p["lat"] is None:
            continue
        x, y = mm_proj(p["lon"], p["lat"])
        if not (0 <= x <= MM_W and 0 <= y <= MM_H):
            missing += 1
            continue
        g = basis_group(p["coord_basis"])
        t = f'<title>{esc(p["name"])}: {esc(BASIS[g][0].lower())}</title>'
        href = ctx.link("place/" + pid)
        if g == "approx":
            shape = f'<circle class="approx-halo" cx="{x:.1f}" cy="{y:.1f}" r="{13 * k:.1f}"/><circle class="approx" cx="{x:.1f}" cy="{y:.1f}" r="{7 * k:.1f}"/>'
        elif g == "anchor":
            labels.append(f'<a href="{href}">{t}<text class="anchor" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">{esc(p["name"])}</text></a>')
            continue
        elif g == "capital":
            shape = f'<circle class="ring" cx="{x:.1f}" cy="{y:.1f}" r="{7 * k:.1f}"/><circle class="pt capital" cx="{x:.1f}" cy="{y:.1f}" r="{4 * k:.1f}"/>'
        elif g == "river":
            shape = f'<circle class="pt river" cx="{x:.1f}" cy="{y:.1f}" r="{4.5 * k:.1f}"/>'
        else:
            shape = f'<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="{4.5 * k:.1f}"/>'
        pts.append((g, f'<a href="{href}">{t}{shape}</a>'))
    if not pts and not labels:
        return ""
    order = {"approx": 0, "river": 1, "capital": 2, "exact": 3}
    pts.sort(key=lambda t: order.get(t[0], 9))
    body = "".join(s for _, s in pts) + "".join(labels)
    cap = ""
    if caption:
        n = len(pts) + len(labels)
        cap = '<p class="minimap-cap">Dashed rings are rough positions.' + ((" 1 more place lies off this map." if missing == 1 else f" {missing} more places lie off this map.") if missing else "") + "</p>"
    return (f'<figure style="margin:0"><svg class="minimap" viewBox="0 0 {MM_W} {MM_H}" role="img" aria-label="Map of the places named">'
            f'<use class="land" href="{ctx.land_href()}" width="{MM_W}" height="{MM_H}"/>{body}</svg>{cap}</figure>')


# ---------------------------------------------------------------- shared fragments

def kind_badge(r):
    if r["kind"] == "map":
        return '<span class="kind m" title="Map">M</span>'
    return '<span class="kind" title="Written source">W</span>'


def ev_chip(ev, button=False):
    """How the author knew, as a label. With button=True it is a control that filters the list it sits in."""
    cls = {"claimed or disputed": " ev-claimed", "firsthand": " ev-firsthand"}.get(ev, "")
    if button:
        return (f'<button type="button" class="chip{cls}" data-set="{esc(ev)}" '
                f'title="{esc(EVIDENCE.get(ev, ""))} Click to show only these.">{esc(ev)}</button>')
    return f'<span class="chip{cls}" title="{esc(EVIDENCE.get(ev, ""))}">{esc(ev)}</span>'


def record_list(site, ctx, ids, show_ev=True):
    rows = []
    for r in sorted((site.rec[i] for i in ids), key=sort_key):
        d = r["date"]
        prec = prec_label(d["made_precision"]) if d["made_start"] is not None else "no accepted date"
        rows.append(
            f'<li><div class="yr">{esc(made_label(r))}<span class="prec">{esc(prec)}</span></div>'
            f'<div class="body"><a class="t" href="{ctx.link(site.rkey(r))}">{esc(short_title(r["title"], 110))}</a>'
            f'<div class="meta">{kind_badge(r)}<span>{esc(short_creator(r["creator"]))}</span>'
            f'{ev_chip(r["evidence_class"]) if show_ev else ""}<span class="rid">{r["id"]}</span></div></div></li>')
    return f'<ol class="rlist">{"".join(rows)}</ol>'


def basis_dot(g):
    return f'<span class="basis-dot {g}" aria-hidden="true"></span>'


def cut_credit(site, c):
    return f'{c["by"]}, {c["year"]}'


def cut_style(url, w, h):
    """The picture is named in the element's own style, so its address is read from the page, not from the stylesheet."""
    return f"-webkit-mask-image:url({url});mask-image:url({url});aspect-ratio:{w}/{h}"


def cut(site, ctx, c, sub, cls="", label=None):
    """A piece cut from one of the maps: lettering or an ornament, kept as ink only and painted in the page's
    own text colour (see generator/fetch_cuts.py). `label` is what a screen reader says; None hides it."""
    w, h = c["size"]
    aria = f' role="img" aria-label="{esc(label)}"' if label else ' aria-hidden="true"'
    return (f'<span class="cut{(" " + cls) if cls else ""}"{aria} '
            f'style="{cut_style(ctx.asset("cuts/" + sub + "/" + c["key"] + ".png"), w, h)}"></span>')


def orn(site, ctx, key, cls=""):
    """An ornament from the maps, with its credit as a tooltip. Nothing if the cut is missing."""
    c = site.orn.get(key)
    if not c:
        return ""
    tip = f'{c["what"]}. From a map by {cut_credit(site, c)}.'
    return (f'<span class="orn{(" " + cls) if cls else ""}" title="{esc(tip)}">'
            f'{cut(site, ctx, c, "ornaments", label=tip)}</span>')


def orn_rule(site, ctx, key):
    """A rule between two parts of a page with one ornament set into it."""
    o = orn(site, ctx, key)
    return f'<div class="orn-rule">{o}</div>' if o else ""


def page_head(eyebrow, title, lede=None, extra="", ornament=""):
    lede_html = f'<p class="lede">{lede}</p>' if lede else ""
    long = ' class="long"' if len(html.unescape(title)) > 60 else ""
    head = f'<header class="page-head"><div class="eyebrow">{eyebrow}</div><h1{long}>{title}</h1>{lede_html}{extra}</header>'
    return f'<div class="page-top">{head}{ornament}</div>' if ornament else head


# ---------------------------------------------------------------- pictures

def map_name(r):
    """A short name for a map: the mapmaker, as the lineage diagrams call them."""
    return LINEAGE_SHORT.get(r["id"]) or short_creator(r["creator"], 34)


def map_alt(r):
    what = "A page from the volume that holds the map" if r["id"] in NOT_MAP_VIEW else "Map"
    return f'{what}: {short_title(no_em(r["title"]), 90)}, {map_name(r)}, {made_label(r)}'


def map_img_tag(site, ctx, r, size="s", eager=False):
    w, h = site.map_img[r["id"]][size]
    load = ' fetchpriority="high"' if eager else ' loading="lazy" decoding="async"'
    return f'<img src="{esc(ctx.map_img(site, r["id"], size))}" width="{w}" height="{h}" alt="{esc(map_alt(r))}"{load}>'


def map_card(site, ctx, r):
    """A map as a picture card, for the gallery and the strips on other pages."""
    y = r["date"]["made_start"]
    hay = " ".join([r["id"], r["title"], r["creator"] or "", r["language"] or "", made_label(r)]).lower()
    name, sub = map_name(r), smart(short_title(no_em(r["title"]), 64))
    sub_html = "" if sub.lower().startswith(name.lower()) else f'<span class="mapcard-sub">{esc(sub)}</span>'
    return (f'<a class="mapcard" href="{ctx.link(site.rkey(r))}" data-y="{"" if y is None else y}" data-h="{esc(hay)}">'
            f'<span class="mapcard-img">{map_img_tag(site, ctx, r)}</span>'
            f'<span class="mapcard-when">{esc(made_label(r))}</span>'
            f'<span class="mapcard-t">{esc(name)}</span>{sub_html}</a>')


def pictured_maps(site, ids=None):
    """Maps that have a picture, oldest first. Pictures of covers and text pages go last."""
    recs = [r for r in site.records if r["kind"] == "map" and r["id"] in site.map_img and (ids is None or r["id"] in ids)]
    return sorted(recs, key=lambda r: (r["id"] in NOT_MAP_VIEW,) + sort_key(r))


def pic_tag(site, ctx, key, eager=False):
    pic = site.pics[key]
    w, h = pic["size"]
    load = ' fetchpriority="high"' if eager else ' loading="lazy" decoding="async"'
    return f'<img src="{esc(ctx.pic(site, key))}" width="{w}" height="{h}" alt="{esc(pic["alt"])}"{load}>'


def pic_link(site, ctx, key):
    """Where a named picture leads: the map's own page, or the page it was taken from."""
    pic = site.pics[key]
    return ctx.link(site.rkey(pic["rec"])) if pic.get("rec") else pic.get("page", "")


# ---------------------------------------------------------------- passages

def words_span(s, e, p):
    """A date span in words: no dashes in the discovery pages."""
    return span_label(s, e, p).replace("–", " to ")


def source_when(r):
    d = r["date"]
    if d.get("subject_start") is not None:
        return words_span(d["subject_start"], d["subject_end"], d["subject_precision"])
    if d["made_start"] is not None:
        return words_span(d["made_start"], d["made_end"], d["made_precision"])
    return "Undated"


def source_year(r):
    d = r["date"]
    y = d.get("subject_start")
    return y if y is not None else d["made_start"]


def plural(n, word):
    return f"{num(n)} {word}{'' if n == 1 else 's'}"


def basis_chip(b, button=False):
    """How the author knew this passage. On a card it is a button: pressing it spells the label out (phones have no hover)."""
    label, tip = PBASIS[b]
    if button:
        return f'<button type="button" class="basis {b}" data-basis aria-expanded="false" title="{esc(tip)}">{esc(label)}</button>'
    return f'<span class="basis {b}" title="{esc(tip)}">{esc(label)}</span>'


def tale_meta(site, rid):
    """What waits on a source's page, for the way in from a passage card: (plain title, passages, when)."""
    return [site.profiles[rid]["plain_title"], len(site.psg_by_rec.get(rid, [])), source_when(site.rec[rid])]


def tale_link(href, title, n, when):
    """The way from one passage into its source's whole page. The page script builds the same markup in TA.card."""
    return (f'<a class="psg-tale" href="{href}"><span class="psg-tale-k">Continue in this source</span>'
            f'<span class="psg-tale-t">{esc(title)}</span>'
            f'<span class="psg-tale-n">{esc(when)} · {plural(n, "passage")}</span></a>')


def psg_card(site, ctx, p, theme_tag=True, source=True, cls="", book=False):
    """One passage. The page script builds the same markup in TA.card; keep the two in step."""
    meta = []
    if theme_tag:
        meta.append(f'<a class="ttag" href="{ctx.link("passages/" + p["theme"])}">{esc(THEMES[p["theme"]]["label"])}</a>')
    if p.get("place"):
        if p["place_ids"]:
            meta.append(f'<a href="{ctx.link("place/" + p["place_ids"][0])}">{esc(p["place"])}</a>')
        else:
            meta.append(f'<span>{esc(p["place"])}</span>')
    if p.get("when"):
        meta.append(f'<span>{esc(p["when"])}</span>')
    if p.get("translation"):
        quote = (f'<blockquote><p>{esc(p["translation"])}</p><p class="q-tag">Working translation</p>'
                 f'<details><summary>Original wording</summary><p class="orig" dir="auto">{esc(p["quote"])}</p></details></blockquote>')
    else:
        quote = f'<blockquote><p dir="auto">{esc(p["quote"])}</p></blockquote>'
    notes = []
    if p.get("caution"):
        notes.append(f'<p>{esc(p["caution"])}</p>')
    qn = psg_note(p)
    if qn:
        notes.append(f"<p>{esc(qn)}</p>")
    notes_label = "Keep in mind" if p.get("caution") else "A note on this quote"
    notes_html = f'<details class="psg-notes"{" open" if p.get("caution") else ""}><summary>{notes_label}</summary>{"".join(notes)}</details>' if notes else ""
    people = f'<p class="psg-people"><span>About</span> {esc(p["people"])}</p>' if p.get("people") else ""
    page = "See the original page" + (f' (p. {esc(p["p"])})' if p.get("p") else "")
    links = [f'<a href="{esc(p["url"])}" rel="noopener">{page}</a>', COPY_BTN]
    tale = tale_link(ctx.link(site.rkey(p["rec"])), *tale_meta(site, p["rec"])) if source else ""
    y = p.get("year")
    if book:
        original = (f'<details class="book-original"><summary>Original wording</summary>'
                    f'<p class="orig" dir="auto">{esc(p["quote"])}</p></details>') if p.get("translation") else ""
        reading = f'<blockquote><p dir="auto">{esc(p.get("translation") or p["quote"])}</p>'
        if p.get("translation"):
            reading += '<p class="q-tag">Working translation</p>'
        reading += '</blockquote>'
        date = f'<p class="book-date">{esc(p["when"])}</p>' if p.get("when") else ""
        return (f'<article class="psg book-entry" id="p-{p["id"]}" data-th="{p["theme"]}" data-b="{p["basis"]}">'
                f'<div class="book-binding"><div class="book-spread">'
                f'<div class="book-page book-verso"><p class="book-running">Leaves from the archive</p>'
                f'<h3 class="book-source-title">{esc(tale_meta(site, p["rec"])[0])}</h3>{date}'
                f'<p class="who book-byline">{esc(p["speaker"])}</p><span class="book-fleuron" aria-hidden="true">❦</span>'
                f'<section class="book-editorial"><h4>Editor’s introduction</h4><p class="gloss">{esc(p["gloss"])}</p></section>'
                f'<span class="book-colophon" aria-hidden="true">Collected in the Tartary Atlas</span></div>'
                f'<div class="book-page book-recto"><p class="book-running">In their own words</p>'
                f'<h4 class="book-passage-title">{esc(p["headline"])}</h4>{reading}'
                f'<span class="book-endmark" aria-hidden="true">❦</span></div></div></div>'
                f'<div class="book-apparatus"><div class="book-actions"><div class="psg-links">{"".join(links)}</div>'
                f'<a class="book-source-link" href="{ctx.link(site.rkey(p["rec"]))}">Read this source <span aria-hidden="true">↗</span></a></div>'
                f'<div class="book-catalogue"><div class="psg-meta">{"".join(meta)}</div>'
                f'<div class="book-evidence"><div class="psg-foot"><span class="book-evidence-label">How the author knew</span>'
                f'{basis_chip(p["basis"], button=True)}</div></div></div>{people}{original}{notes_html}</div></article>')

    return (f'<article class="psg{(" " + cls) if cls else ""}" id="p-{p["id"]}" data-th="{p["theme"]}" data-b="{p["basis"]}" data-y="{"" if y is None else y}">'
            f'<div class="psg-meta">{"".join(meta)}</div>'
            f'<h3>{esc(p["headline"])}</h3>'
            f'{quote}<details class="psg-context"><summary>Editorial context</summary><p class="gloss">{esc(p["gloss"])}</p></details>'
            f'<div class="psg-foot">{basis_chip(p["basis"], button=True)}<span class="who">{esc(p["speaker"])}</span></div>'
            f'<div class="psg-links">{"".join(links)}</div>{people}{notes_html}{tale}</article>')


def psg_note(p):
    parts = []
    qn = (p.get("quote_note") or "").strip()
    if qn and qn != "OCR normalized":
        parts.append(qn.rstrip(".") + ".")
    if p["check"] == "partial":
        parts.append(PSG_PARTIAL)
    return " ".join(parts)


def psg_compact(site, p):
    """The passage as the page script reads it. Short keys keep the data files small."""
    d = {"i": p["id"], "th": p["theme"], "h": p["headline"], "g": p["gloss"], "q": p["quote"],
         "s": p["speaker"], "u": p["url"], "b": p["basis"], "st": p["strength"], "x": p["x"]}
    opt = {"pl": p.get("place"), "pi": (p["place_ids"][0] if p["place_ids"] else None), "pe": p.get("people"),
           "w": p.get("when"), "y": p.get("year"), "t": p.get("translation"), "p": p.get("p"),
           "c": p.get("caution"), "n": psg_note(p) or None, "tg": " ".join(p.get("tags") or []) or None}
    d.update({k: v for k, v in opt.items() if v is not None})
    return d


def psg_block(site, ctx, plist, limit, theme_tag=True, source=True):
    """A set of passages: trail pills that filter it, an order switch, `limit` cards to begin with and the rest on request.
    The static site carries every card in the page, so it reads without the page script. The single-file preview
    carries only the IDs and lets the page script draw the cards from the passage data files, to stay small.
    Either way the page script (TA.modules.pset) takes over the pills and the paging."""
    rest = plist[limit:]
    counts = collections.Counter(p["theme"] for p in plist)
    pills = ""
    if len(counts) > 1:
        btns = [f'<button type="button" class="pill" data-f="" aria-pressed="true">All <span class="n">{len(plist)}</span></button>']
        btns += [f'<button type="button" class="pill" data-f="{t}" aria-pressed="false">{esc(THEMES[t]["label"])} <span class="n">{counts[t]}</span></button>'
                 for t in THEMES if counts[t]]
        pills = f'<div class="pills" role="group" aria-label="Show one trail">{"".join(btns)}</div>'
    order = ""
    if len(plist) >= 6 and len({p.get("year") for p in plist if p.get("year") is not None}) > 1:
        order = ('<div class="seg" role="group" aria-label="Order"><button type="button" data-ord="best" aria-pressed="true">Best first</button>'
                 '<button type="button" data-ord="old" aria-pressed="false">Oldest first</button></div>')
    bar = f'<div class="pset-bar" data-bar hidden>{pills}{order}</div>' if pills or order else ""
    foot = ('<p class="small muted pset-count" data-count aria-live="polite" hidden></p>'
            '<p class="px-more" data-more-row hidden><button type="button" class="btn" data-more>Show more</button>'
            '<button type="button" class="btn quiet" data-all>Show all</button></p>')
    if ctx.mode == "preview":
        opts = ("1" if theme_tag else "0") + ("1" if source else "0")
        return (f'<div class="pset" data-module="pset" data-ids="{",".join(p["id"] for p in plist)}" data-opts="{opts}" data-first="{limit}">{bar}'
                f'<div class="psg-list" data-list><p class="muted">Loading the passages…</p></div>{foot}</div>')
    first = "".join(psg_card(site, ctx, p, theme_tag, source) for p in plist[:limit])
    more = ""
    if rest:
        cards = "".join(psg_card(site, ctx, p, theme_tag, source) for p in rest)
        more = f'<details class="more"><summary class="btn">Show {plural(len(rest), "more passage")}</summary><div class="psg-list">{cards}</div></details>'
    return f'<div class="pset" data-module="pset" data-first="{limit}">{bar}<div class="psg-list" data-list>{first}</div>{more}{foot}</div>'


def write_passage_assets(site, outdir):
    """One data file per trail, read by the passage explorer."""
    for t in THEMES:
        ps = site.psg_by_theme[t]
        src = {rid: tale_meta(site, rid) for rid in sorted({p["rec"] for p in ps})}
        out = {"src": src, "p": [dict(psg_compact(site, p), r=p["rec"]) for p in ps]}
        (outdir / f"passages-{t}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))


def trail_tabs(site, ctx, current):
    cur_all = ' aria-current="page"' if current is None else ""
    items = [f'<a href="{ctx.link("passages")}"{cur_all}>All <span class="n">{num(len(site.passages))}</span></a>']
    for t, m in THEMES.items():
        cur = ' aria-current="page"' if t == current else ""
        items.append(f'<a href="{ctx.link("passages/" + t)}"{cur}>{esc(m["label"])} <span class="n">{num(len(site.psg_by_theme[t]))}</span></a>')
    return f'<nav class="trailtabs" aria-label="Trails">{"".join(items)}</nav>'


def trail_cards(site, ctx):
    cards = []
    for t, m in THEMES.items():
        ps = site.psg_by_theme[t]
        key = "trail-" + t
        img = f'<span class="trail-img">{pic_tag(site, ctx, key)}</span>' if key in site.pics else ""
        cards.append(
            f'<a class="trail" href="{ctx.link("passages/" + t)}">{img}<span class="trail-body"><span class="trail-label">{esc(m["label"])}</span>'
            f'<span class="trail-q">{esc(m["q"])}</span><span class="trail-blurb">{esc(m["blurb"])}</span>'
            f'<span class="trail-n">{plural(len(ps), "passage")}</span></span></a>')
    return f'<div class="trails">{"".join(cards)}</div>'


def source_card(site, ctx, rid):
    r, pr = site.rec[rid], site.profiles[rid]
    n = len(site.psg_by_rec.get(rid, []))
    return (f'<a class="witness" href="{ctx.link(site.rkey(r))}"><span class="witness-when">{esc(source_when(r))}</span>'
            f'<span class="witness-t">{esc(pr["plain_title"])}</span><span class="witness-one">{esc(pr["one_line"])}</span>'
            f'<span class="witness-n">{esc(HOW_KNEW.get(pr["how_they_knew"], pr["how_they_knew"]))} · {plural(n, "passage")}</span></a>')


def reading_progress(site):
    """(sources read for passages, written sources in the catalogue, sources with a profile only)."""
    written = [r for r in site.records if r["kind"] == "written"]
    profiled = [r for r in written if r["id"] in site.profiles]
    read = [r for r in profiled if site.profiles[r["id"]].get("read_quality") != "none"]
    return len(read), len(written), len(profiled) - len(read)


# ---------------------------------------------------------------- discovery pages

def page_home(site, ctx):
    return storybook.page(site, ctx)


def page_frontispiece(site, ctx):
    n_read, n_written, n_profile_only = reading_progress(site)
    n_psg = len(site.passages)
    n_maps = sum(1 for r in site.records if r["kind"] == "map")

    # The passage on the front page, and the pool the "another" button draws from.
    # The pool is the strongest page-checked passages, no more than FEATURE_PER_SOURCE from any one source in a
    # trail, so a reader who keeps pressing the button meets many witnesses. The page script opens on a random one.
    pool = []
    for t in THEMES:
        seen, good = collections.Counter(), []
        for p in site.psg_by_theme[t]:
            if (p["strength"] == 3 and p["check"] == "page" and (p["basis"] == "saw" or t in ("outliers", "names"))
                    and seen[p["rec"]] < FEATURE_PER_SOURCE):
                seen[p["rec"]] += 1
                good.append(p)
        pool += good[:FEATURE_PER_TRAIL]
    first = site.psg.get(FIRST_FEATURE) or (pool[0] if pool else None)
    if first and first not in pool:
        pool.append(first)
    # The front door is Ortelius's map. Places he lettered that the sources also write about are pinned on it,
    # and each pin brings its own passages into the pool, so drawing a passage can carry the reader to its place.
    fm = site.front or {}
    fw, fh = fm.get("size", [1, 1])
    per = collections.Counter((p["theme"], p["rec"]) for p in pool)
    in_pool = {p["id"] for p in pool}
    pin_of = {}
    pins = []
    for pin in fm.get("pins", []):
        pid = pin["id"]
        ps = site.psg_by_place.get(pid, [])
        if pid not in site.place or not ps:
            continue
        got = 0
        for p in ps:
            if p["id"] in in_pool:
                pin_of.setdefault(p["id"], pid)
                got += 1
        for p in ps:
            if got >= FRONT_PER_PIN:
                break
            if p["id"] in in_pool or p["check"] != "page" or per[(p["theme"], p["rec"])] >= FEATURE_PER_SOURCE:
                continue
            per[(p["theme"], p["rec"])] += 1
            in_pool.add(p["id"])
            pool.append(p)
            pin_of[p["id"]] = pid
            got += 1
        pins.append({"i": pid, "n": site.place[pid]["name"], "m": pin["on_map"], "x": round(pin["xy"][0] / fw, 5),
                     "y": round(pin["xy"][1] / fh, 5), "k": pin["kind"], "c": len(ps)})
    sights = [{"t": s["title"], "x": round(s["xy"][0] / fw, 5), "y": round(s["xy"][1] / fh, 5), "w": s["what"], "l": s.get("latin") or ""}
              for s in fm.get("sights", [])]
    pool.sort(key=lambda p: p["x"])
    front_map = None
    if fm and site.iiif_base(fm["rec"]):
        front_map = {"rec": fm["rec"], "ar": round(fh / fw, 6), "w": fw,
                     "src": (ctx.asset("pics/front.jpg") if ctx.mode == "preview" else site.iiif_base(fm["rec"]) + "/info.json"),
                     "tiled": ctx.mode != "preview", "pins": pins, "sights": sights}
    feat_json = json.dumps({"src": {p["rec"]: tale_meta(site, p["rec"]) for p in pool},
                            "p": [dict(psg_compact(site, p), r=p["rec"], **({"pn": pin_of[p["id"]]} if p["id"] in pin_of else {})) for p in pool],
                            "map": front_map},
                           ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    n_pictured = len(site.map_img)
    still = ""
    if "hero" in site.pics:
        still = f'<div class="front-still" data-still>{pic_tag(site, ctx, "hero", eager=True)}</div>'
    front_rec = site.rec.get(fm.get("rec", ""), None)
    credit = ""
    if front_rec:
        credit = (f'<p class="front-credit"><a href="{ctx.link(site.rkey(front_rec))}">Abraham Ortelius · Tartary · first printed 1570</a>'
                  f'<span>Library of Congress</span></p>')
    tools = ('<div class="front-tools" data-tools hidden>'
             '<button type="button" class="btn" data-roam>Roam the map</button>'
             '<span class="front-zoom"><button type="button" class="btn icon" data-zoom-out aria-label="Zoom out">−</button>'
             '<button type="button" class="btn icon" data-zoom-in aria-label="Zoom in">+</button></span>'
             '<button type="button" class="btn" data-home>Whole map</button>'
             '<button type="button" class="btn primary" data-close hidden>Close the map</button></div>')
    slip = '<div class="front-slip" data-slip hidden aria-live="polite"></div>'
    stage = (f'<div class="front-stage" data-stage>{still}<div class="front-osd"><div data-osd></div></div>{tools}{slip}</div>')
    # This is a homepage-only manuscript treatment. Shared passage cards keep their existing markup.
    card = ""
    if first:
        excerpt = psg_card(site, ctx, first, book=True)
        card = (f'<div class="hero-card passage-book" id="front-passage"><div class="hero-card-head"><h2>One passage from the record</h2>'
                f'<button type="button" class="btn book-next" data-next hidden aria-controls="home-book-pages">Turn the page <span aria-hidden="true">→</span></button></div>'
                f'<p class="front-at" data-at hidden></p>'
                f'<div class="feature-slot" id="home-book-pages" data-slot>{excerpt}</div>'
                f'<p class="book-status sr-only" data-book-status role="status" aria-live="polite" aria-atomic="true"></p></div>')
    hero = (f'<section class="front" data-module="feature"><script type="application/json">{feat_json}</script>'
            f'<div class="study-table"><div class="front-opening"><div class="front-intro">'
            f'<p class="front-kicker">The opening map · 1570</p>'
            f'<h1>Ortelius’s<br><em>Tartary.</em></h1>'
            f'<p class="study-invitation">Explore the places and curious notes on this original sheet. Let a place lead you to a witness.</p>'
            f'<div class="study-actions"><a class="btn primary" href="#explore">Enter the Atlas {experience.icon("arrow")}</a>'
            f'<a class="study-read" href="#front-passage">Open a page</a></div>'
            f'<p class="study-totals"><span><b>{num(n_psg)}</b> passages</span><span><b>{n_maps}</b> maps</span><span><b>{n_read}</b> voices</span></p></div>'
            f'<div class="study-map"><div class="front-map-mount">{stage}</div>'
            f'<div class="front-map-caption">{credit}<p class="front-how" data-how hidden>'
            f'<span><i class="key dot"></i>Places</span><span><i class="key dia"></i>Map notes</span></p></div></div></div></div>'
            f'<div class="page cabinet-home-content">{experience.home_rooms(ctx)}'
            f'<div class="front-body"><aside class="front-margin"><p class="front-kicker">The open volume</p>'
            f'<h2>A voice across the centuries.</h2><a href="{ctx.link("passages")}">All {num(n_psg)} passages {experience.icon("arrow")}</a>'
            f'<p class="front-independent">An independent account, alongside the map.</p></aside>{card}</div></div></section>')

    trails = (f'<section class="band"><div class="band-head"><h2>Follow a question</h2></div>{trail_cards(site, ctx)}</section>')

    picks_m = [site.rec[i] for i in HOME_MAPS if i in site.map_img]
    maps_band = ""
    if picks_m:
        maps_band = (f'<section class="band"><div class="band-head row"><div><h2>Step into the map room</h2>'
                     f'<p>Tartary as the mapmakers drew it, from 1375 to the last years the name was in use.</p></div>'
                     f'<a class="btn" href="{ctx.link("maps")}">See all {n_pictured} maps</a></div>'
                     f'<div class="mapstrip">{"".join(map_card(site, ctx, r) for r in picks_m)}</div></section>')

    # places with the most passages
    counts = [(len(v), pid) for pid, v in site.psg_by_place.items()
              if site.place[pid]["lat"] is not None and site.place[pid]["type"] == "settlement"]
    top = [pid for _, pid in sorted(counts, reverse=True)[:12]]
    chips = "".join(
        f'<li><a href="{ctx.link("place/" + pid)}"><span class="chip big">{esc(site.place[pid]["name"])} '
        f'<span class="mono muted">{len(site.psg_by_place[pid])}</span></span></a></li>' for pid in top)
    places = (f'<section class="band"><div class="band-head"><h2>Pick a place</h2>'
              f'<p>Twelve towns the sources keep coming back to.</p></div>'
              f'<div class="place-start"><div>{minimap(site, ctx, top, caption=False)}</div>'
              f'<div class="place-start-list"><ul class="tags">{chips}</ul>'
              f'<p class="small muted">Or <a href="{ctx.link("map")}">wander the map</a> and find all {len(site.places)}.</p></div></div></section>')

    picks = [rid for rid in ["W043", "W132", "W073", "W074", "W001", "W053"] if rid in site.profiles]
    witnesses = (f'<section class="band"><div class="band-head"><h2>Meet a witness</h2>'
                 f'<p>Six people who were there. <a href="{ctx.link("sources")}">Meet all {n_read}</a>.</p></div>'
                 f'<div class="witnesses">{"".join(source_card(site, ctx, rid) for rid in picks)}</div></section>')

    deeper = (f'<section class="band"><div class="band-head"><h2>Open the vault</h2></div><ul class="deeper">'
              f'<li><a href="{ctx.link("labels")}">The many Tartarys</a><span>Great, Little, Chinese, Independent: when each name shows up on the maps, and when it stops.</span></li>'
              f'<li><a href="{ctx.link("lineage")}">Who copied whom</a><span>Family trees for {n_maps} maps, from Jenkinson and Ortelius onward.</span></li>'
              f'<li><a href="{ctx.link("records")}">Every book and map</a><span>All {len(site.records)}, with dates and links.</span></li>'
              f'<li><a href="{ctx.link("archive")}">The rest of the vault</a><span>Places, peoples, and how the atlas was made.</span></li></ul></section>')

    rides = rides_band(site, ctx) or places
    body = (f'{hero}<div class="page home cabinet-home-bottom">{trails}'
            f'<details class="archive-cabinet"><summary><span>{experience.icon("vault")} Deeper in the cabinet</span><small>Maps, witnesses &amp; the source index</small></summary>'
            f'{maps_band}{rides}{witnesses}{deeper}</details></div>')

    desc = (f"What {n_written} historical texts and {n_maps} maps say about Tartary (Tartaria): {num(n_psg)} quoted passages on cities, "
            f"buildings, daily life and legends, each linked to its page.")
    return dict(title="Ortelius’s Tartary: the opening map", description=desc, body=body,
                nav="", modules=["feature"], bare_title=True, osd=True, homepage=True)


def page_passages(site, ctx, theme=None):
    plist = site.psg_by_theme[theme] if theme else site.psg_best
    n_src = len({p["rec"] for p in plist})
    if theme:
        m = THEMES[theme]
        head = page_head(f'{plural(len(plist), "passage")} from {n_src} sources', esc(m["q"]), esc(m["blurb"]))
        key = "trail-" + theme
        if key in site.pics:
            head = (f'<div class="trail-head">{head}<figure class="trail-fig"><a href="{pic_link(site, ctx, key)}">{pic_tag(site, ctx, key, eager=True)}</a>'
                    f'<figcaption>{esc(site.pics[key]["caption"])}</figcaption></figure></div>')
        title, desc = m["q"], f'{m["blurb"]} {num(len(plist))} quoted passages from {n_src} historical sources on Tartary.'
    else:
        head = page_head("The reading room", "Leaves from the archive",
                         f'{num(len(plist))} passages. {n_src} voices. Choose a trail, or follow a word.', ornament=orn(site, ctx, "scholar", "head"))
        title, desc = "Passages: what the sources say about Tartary", f'{num(len(plist))} quoted passages about the Tartars and Tartary from {n_src} historical sources, searchable by place, people and date.'
    basis_opts = "".join(f'<option value="{k}">{esc(v[0])}</option>' for k, v in PBASIS.items())
    when_opts = ('<option value="0">Before 1200</option>'
                 + "".join(f'<option value="{c}">{c}s</option>' for c in range(1200, 1900, 100)))
    legend = "".join(f'<span>{basis_chip(k)} {esc(v[1])}</span>' for k, v in list(PBASIS.items())[:4])
    cards = "".join(psg_card(site, ctx, p, theme_tag=theme is None) for p in plist[:PAGE_SIZE])
    body = (f'<div class="page">{head}{trail_tabs(site, ctx, theme)}'
            f'<div class="px-layout" data-module="pexplore" data-trail="{theme or ""}" data-total="{len(plist)}">'
            f'<aside class="px-side" aria-label="Narrow the passages"><div class="filterbar stack"><label for="px-q">Search<input type="search" id="px-q" placeholder="Karakorum, felt, mosque…"></label>'
            f'<details class="px-filters" data-filters open><summary>Narrow it down<span class="n" data-nf></span></summary><div class="px-filters-body">'
            f'<label for="px-b">How the author knew<select id="px-b"><option value="">Any</option>{basis_opts}</select></label>'
            f'<label for="px-w">When<select id="px-w"><option value="">Any time</option>{when_opts}</select></label>'
            f'<label for="px-o">Order<select id="px-o"><option value="best">Best first</option><option value="old">Oldest first</option><option value="new">Newest first</option></select></label>'
            f'<button type="button" class="btn" data-shuffle>Shuffle</button></div></details></div>'
            f'<details class="basis-legend"><summary>Saw it? Heard it?</summary>{legend}</details></aside>'
            f'<div class="px-main" data-main><div class="reading-mode-bar"><button type="button" class="btn primary" data-read-first hidden>{experience.icon("book")} Open the reading desk</button></div><p class="small muted px-count" aria-live="polite"><span data-count>{num(len(plist))}</span><span data-of hidden> of {num(len(plist))}</span> passages'
            f'<button type="button" class="linkbtn" data-clear hidden>Clear filters</button></p>'
            f'<div class="psg-list" data-list>{cards}</div>'
            f'<p class="px-more"><button type="button" class="btn" data-more>Show {PAGE_SIZE} more</button></p></div></div></div>')
    return dict(title=title, description=desc, body=body, nav="passages", modules=["pexplore"])


def page_sources(site, ctx):
    n_read, n_written, n_profile_only = reading_progress(site)
    n_maps = sum(1 for r in site.records if r["kind"] == "map")
    rows = []
    order = sorted(site.profiles, key=lambda rid: (-len(site.psg_by_rec.get(rid, [])), rid))
    for i, rid in enumerate(order):
        r, pr = site.rec[rid], site.profiles[rid]
        n = len(site.psg_by_rec.get(rid, []))
        y = source_year(r)
        hay = " ".join([rid, pr["plain_title"], pr["one_line"], r["creator"] or "", r["title"], r["language"] or ""]).lower()
        rows.append(
            f'<li data-h="{esc(hay)}" data-hk="{esc(pr["how_they_knew"])}" data-y="{"" if y is None else y}" data-n="{n}"{" hidden" if i >= 30 else ""}>'
            f'<div class="yr">{esc(source_when(r))}</div><div class="body"><a class="t" href="{ctx.link(site.rkey(r))}">{esc(pr["plain_title"])}</a>'
            f'<p class="one">{esc(pr["one_line"])}</p><div class="meta"><button type="button" class="chip" data-set="{esc(pr["how_they_knew"])}" title="Click to show only these">{esc(HOW_KNEW.get(pr["how_they_knew"], pr["how_they_knew"]))}</button>'
            f'<span>{plural(n, "passage") if n or pr.get("read_quality") != "none" else "no quotes yet"}</span></div></div></li>')
    hk_opts = "".join(f'<option value="{esc(k)}">{esc(v)}</option>' for k, v in HOW_KNEW.items()
                      if any(p["how_they_knew"] == k for p in site.profiles.values()))
    head = page_head(f"{n_read + n_profile_only} sources", "The witnesses",
                     f'Who wrote it, how they knew, and what to watch out for. The richest come first. Six of them left a road you can follow: <a href="{ctx.link("ride")}">ride with a traveler</a>.', ornament=orn(site, ctx, "archer", "head"))
    body = (f'<div class="page">{head}<div data-module="slist">'
            f'<div class="filterbar"><label for="sl-q">Search<input type="search" id="sl-q" placeholder="Rubruck, Crimea, Chinese, 1253…"></label>'
            f'<label for="sl-hk">How they knew<select id="sl-hk"><option value="">Any</option>{hk_opts}</select></label>'
            f'<label for="sl-o">Order<select id="sl-o"><option value="n">Most passages</option><option value="old">Oldest first</option><option value="new">Newest first</option></select></label>'
            f'{surprise_btn(site)}'
            f'<p class="small muted list-count" aria-live="polite"><span data-count>{len(rows)}</span><span data-of hidden> of {len(rows)}</span> sources'
            f'<button type="button" class="linkbtn" data-clear hidden>Clear filters</button></p></div>'
            f'<ol class="rlist slist" data-rows>{"".join(rows)}</ol>'
            f'<p class="muted" data-empty hidden>No source matches. Try a shorter word, or clear the filters.</p>'
            f'<p class="px-more"><button type="button" class="btn" data-all>Show all {len(rows)} sources</button></p></div>'
            f'<p class="progress">{n_profile_only} of these have no quotes yet. Looking for a map? <a href="{ctx.link("maps")}">Step into the map room</a>.</p></div>')
    return dict(title="Sources: the witnesses", description=f"{n_read} historical sources on Tartary described in plain words: who wrote each one, how they knew, and what to watch out for.",
                body=body, nav="sources", modules=["slist"])


def page_maps(site, ctx):
    maps = [r for r in site.records if r["kind"] == "map"]
    shown = pictured_maps(site)
    rest = [r["id"] for r in maps if r["id"] not in site.map_img]
    btns = ['<button type="button" class="pill" data-era="" aria-pressed="true">All</button>']
    for key, label, lo, hi in ERAS:
        n = sum(1 for r in shown if r["date"]["made_start"] is not None
                and (lo is None or r["date"]["made_start"] >= lo) and (hi is None or r["date"]["made_start"] <= hi))
        btns.append(f'<button type="button" class="pill" data-era="{key}" data-lo="{"" if lo is None else lo}" data-hi="{"" if hi is None else hi}" aria-pressed="false">{label} <span class="n">{n}</span></button>')
    holders = collections.Counter(site.holder(r["id"]).split(" (")[0] for r in shown)
    credit = "; ".join(f"{h} ({n})" for h, n in holders.most_common())
    head = page_head("Map room", "Tartary on the old maps",
                     f'{len(shown)} maps, oldest first. Open one and look closer.',
                     extra=(f'<p class="hero-actions"><a class="btn primary" href="{ctx.link("dial")}">Turn the dial: watch the name move</a></p>' if dial_stops(site) else ""),
                     ornament=orn(site, ctx, "ship", "head"))
    rest_html = ""
    if rest:
        rest_html = (f'<section class="section"><h2>{len(rest)} more maps, no picture yet</h2>'
                     f'{record_list(site, ctx, rest, show_ev=False)}</section>')
    body = (f'<div class="page">{head}<div data-module="gallery">'
            f'<div class="gallery-bar"><div class="pills" role="group" aria-label="Century">{"".join(btns)}</div>'
            f'<label class="gallery-find" for="gl-q"><span class="sr">Find a map</span><input type="search" id="gl-q" placeholder="Find a map: Ortelius, Siberia, 1706…"></label></div>'
            f'<p class="small muted px-count" aria-live="polite"><span data-count>{len(shown)}</span><span data-of hidden> of {len(shown)}</span> maps'
            f'<button type="button" class="linkbtn" data-clear hidden>Clear filters</button></p>'
            f'<div class="gallery" data-grid>{"".join(map_card(site, ctx, r) for r in shown)}</div>'
            f'<p class="muted" data-empty hidden>No map matches. Try a shorter word, or choose All.</p></div>'
            f'{rest_html}'
            f'<p class="progress">Pictures courtesy of the libraries that hold the maps: {esc(credit)}.</p></div>')
    return dict(title="Old maps of Tartary", description=f"{len(shown)} old maps of Tartary (Tartaria) pictured, from medieval world maps to nineteenth-century atlases, each with its date and source library.",
                body=body, nav="maps", modules=["gallery"])


def page_archive(site, ctx):
    n_w = sum(1 for r in site.records if r["kind"] == "written")
    n_m = len(site.records) - n_w
    items = [
        ("labels", "The many Tartarys", "Great, Little, Chinese, Independent, Muscovite: when each name shows up, and when it stops."),
        ("dial", "Turn the dial", "Old maps laid on the real earth, one after another. Watch the name move."),
        ("meanings", "Who counted as a Tartar?", "The same word, different peoples, century by century."),
        ("lineage", "Who copied whom", "Which maps copied, reissued or corrected which."),
        ("records", "Every book and map", f"All {n_w} written sources and {n_m} maps, in date order."),
        ("places", "Every place", f"{len(site.places)} places the sources name."),
        ("peoples", "Who’s who", f"{len(site.peoples)} peoples and powers the sources name."),
        ("method", "How it was made", "How the dating, plotting, choosing and checking were done, and what the atlas does not claim."),
        ("corrections", "Spot a mistake?", "Send a correction, and see the ones already made."),
    ]
    lis = "".join(f'<li><a href="{ctx.link(k)}">{esc(t)}</a><span>{esc(d)}</span></li>' for k, t, d in items if k != "dial" or dial_stops(site))
    head = page_head("Everything behind the passages", "The vault",
                     "Check a date, trace a map, or see it all at once.", ornament=orn(site, ctx, "khan", "head"))
    return dict(title="The vault", description="The Tartary Atlas catalogue and research tools: records, places, peoples, label timelines, map lineage, method and corrections.",
                body=f'<div class="page">{head}<ul class="deeper wide">{lis}</ul></div>', nav="archive")


def profile_section(site, ctx, r):
    """The plain-words reading card for a source that has been read."""
    pr = site.profiles[r["id"]]
    ps = site.psg_by_rec.get(r["id"], [])
    cells = [("How they knew", f'<span class="chip ev-firsthand">{esc(HOW_KNEW.get(pr["how_they_knew"], pr["how_they_knew"]))}</span>'
              if pr["how_they_knew"] == "saw it" else f'<span class="chip">{esc(HOW_KNEW.get(pr["how_they_knew"], pr["how_they_knew"]))}</span>'),
             ("Who “Tartar” means here", esc(pr["tartar_means"])),
             ("Why read it", esc(pr["why_read"])),
             ("Watch out", esc(pr["watch_out"]))]
    grid = "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in cells)
    out = [f'<section class="section profile" style="margin-top:0"><p class="prose-p">{esc(pr["summary"])}</p><dl class="readcard">{grid}</dl></section>']
    if ps:
        order = {t: i for i, t in enumerate(THEMES)}
        ps = sorted(ps, key=lambda p: (order[p["theme"]], -p["strength"], p["id"]))
        out.append(f'<section class="section" id="what-it-says" tabindex="-1"><h2>What it says: {plural(len(ps), "passage")}</h2>'
                   f'{psg_block(site, ctx, ps, 4, theme_tag=True, source=False)}</section>')
    else:
        why = ("No quotes from this one yet. Its text is out of reach for now, or the scan could not be read."
               if pr.get("read_quality") == "none" else "Nothing here says anything specific about the Tartars.")
        out.append(f'<section class="section"><h2>What it says</h2><p class="muted">{why}</p></section>')
    return "".join(out)


def surprise_btn(site, label="Surprise me", cls="btn"):
    """A button that opens a source picked at random from those with passages. TA.modules.lucky reads the pool."""
    pool = ",".join(rid for rid in sorted(site.profiles) if site.psg_by_rec.get(rid))
    return f'<button type="button" class="{cls}" data-module="lucky" data-pool="{pool}">{label}</button>'


def onward_section(site, ctx, r):
    """Where to go next from a record page, so no page is a dead end: the neighbours in time, and a lucky dip."""
    if r["kind"] == "map":
        if r["id"] not in site.map_img:
            return ""
        maps = [m for m in pictured_maps(site) if m["id"] not in NOT_MAP_VIEW or m["id"] == r["id"]]
        maps.sort(key=sort_key)
        i = next(k for k, m in enumerate(maps) if m["id"] == r["id"])
        near = maps[max(0, i - 2):i] + maps[i + 1:i + 3]
        if not near:
            return ""
        return (f'<section class="band onward"><div class="band-head row"><div><h2>Keep exploring</h2>'
                f'<p>The maps drawn just before and just after this one.</p></div>'
                f'<a class="btn" href="{ctx.link("maps")}">Back to the map room</a></div>'
                f'<div class="mapstrip small">{"".join(map_card(site, ctx, m) for m in near)}</div></section>')
    if r["id"] not in site.profiles or not site.psg_by_rec.get(r["id"]):
        return ""
    order = sorted((rid for rid in site.profiles if site.psg_by_rec.get(rid)),
                   key=lambda rid: (source_year(site.rec[rid]) is None, source_year(site.rec[rid]) or 0, rid))
    i = order.index(r["id"])
    cards = []
    if i > 0:
        cards.append(f'<div class="onward-slot"><div class="eyebrow">The witness before</div>{source_card(site, ctx, order[i - 1])}</div>')
    if i < len(order) - 1:
        cards.append(f'<div class="onward-slot"><div class="eyebrow">The witness after</div>{source_card(site, ctx, order[i + 1])}</div>')
    lucky = surprise_btn(site, orn(site, ctx, "wind", "gust") + '<span class="witness-t">Surprise me</span><span class="witness-one">Open one of the '
                         f'{len(order)} sources at random and see who turns up.</span>', "witness lucky")
    cards.append(f'<div class="onward-slot"><div class="eyebrow">Or take a chance</div>{lucky}</div>')
    return (f'<section class="band onward"><div class="band-head"><h2>Keep exploring</h2></div>'
            f'<div class="witnesses">{"".join(cards)}</div></section>')


# ---------------------------------------------------------------- pages

def page_record(site, ctx, r):
    d = r["date"]
    is_map = r["kind"] == "map"
    kind_word = "Map" if is_map else "Written source"
    lang = (r["language"] or "").split(" (")[0]
    if len(lang) > 34:
        lang = lang[:34].rsplit(" ", 1)[0] + "…"
    eyebrow = " · ".join(esc(x) for x in [kind_word, lang] if x)
    title_html = esc(smart(no_em(r["title"])))
    prof = site.profiles.get(r["id"])
    extra = ""
    if prof:
        # A source that has been read opens with its plain-words title; the catalogue title sits beneath.
        extra += f'<p class="cat-title"><span>Full title</span> {title_html}</p>'
        if r.get("original_script_title"):
            extra += f'<p class="muted" lang="und">{esc(r["original_script_title"])}</p>'
        extra += f'<p class="muted">{esc(no_em(r["creator"]))}</p>'
        n_here = len(site.psg_by_rec.get(r["id"], []))
        acts = []
        if n_here:
            acts.append(f'<a class="btn primary" href="#what-it-says">Read the {plural(n_here, "passage")}</a>')
        if r.get("primary_access"):
            acts.append(f'<a class="btn" href="{esc(r["primary_access"])}" rel="noopener">Open the original book</a>')
        ride = next((j for j in site.journeys if j["rec"] == r["id"]), None)
        if ride:
            acts.append(f'<a class="btn" href="{ctx.link("ride/" + ride["key"])}">Ride the route</a>')
        if acts:
            extra += f'<p class="hero-actions">{"".join(acts)}</p>'
        head = page_head(eyebrow, esc(prof["plain_title"]), esc(prof["one_line"]), extra=extra)
    else:
        if r.get("original_script_title"):
            extra += f'<p class="lede" lang="und">{esc(r["original_script_title"])}</p>'
        extra += f'<p class="muted">{esc(no_em(r["creator"]))}</p>'
        head = page_head(eyebrow, title_html, extra=extra)

    # How we know
    ev = r["evidence_class"]
    cautions = [c.strip() for c in (r["cautions"] or "").split(" | ") if c.strip()]
    caut_html = "".join(f"<li>{linkify(site, ctx, c)}</li>" for c in cautions)
    corr_note = ""
    if r.get("_corrections"):
        corr_note = f'<p class="small muted">This page has been corrected. <a href="{ctx.link("corrections")}">See what changed</a>.</p>'
    how = (f'<section class="panel how{" claimed" if ev == "claimed or disputed" else ""}" aria-labelledby="how-{r["id"]}">'
           f'<h2 id="how-{r["id"]}">How we know</h2>'
           f'<p>{ev_chip(ev)} {esc(EVIDENCE.get(ev, ""))}</p>'
           + (f'<div><p>{linkify(site, ctx, r["evidence_text"])}</p></div>' if (r.get("evidence_text") or "").strip() else '')
           + (f'<details class="small"><summary>Research notes</summary><ul class="note-list">{caut_html}</ul></details>' if caut_html else "")
           + corr_note + '</section>')

    sections = []
    if prof:
        sections.append(profile_section(site, ctx, r))
        sections.append('<h2 class="divider">The fine print</h2>')
    elif not is_map:
        sections.append(f'<p class="banner" style="margin:0"><strong>No quotes from this one yet.</strong> '
                        f'<a href="{ctx.link("sources")}">Meet the witnesses that have them</a>.</p>')
    sections.append(how)
    if r.get("research_value"):
        sections.append(f'<section class="section"><h2>Why it matters</h2><p class="prose">{linkify(site, ctx, r["research_value"])}</p></section>')

    if r["tartar_referents_card"] and not prof:
        items = "".join(f'<li><span class="chip">{esc(site.family_name(f))}</span></li>' for f in r["tartar_referents_card"])
        sections.append(
            f'<section class="section"><h2>What “Tartar” means here</h2>'
            f'<p class="small muted"><span class="chip prov">first pass</span> '
            f'<a href="{ctx.link("meanings")}">Who counted as a Tartar?</a></p><ul class="tags">{items}</ul></section>')

    # places
    if r["places"]:
        tags = []
        for pid in r["places"]:
            p = site.place.get(pid)
            if not p:
                continue
            g = basis_group(p["coord_basis"])
            tags.append(f'<li><a href="{ctx.link("place/" + pid)}"><span class="chip" title="{esc(BASIS[g][0])}">{basis_dot(g)}{esc(p["name"])}</span></a></li>')
        card = f'<p class="small muted">{linkify(site, ctx, r["regions_text"])}</p>' if r.get("regions_text") else ""
        sections.append(f'<section class="section"><h2>Places named</h2><ul class="tags">{"".join(tags)}</ul>{card}</section>')

    if r["peoples"]:
        byfam = collections.OrderedDict()
        for pid in r["peoples"]:
            p = site.people.get(pid)
            if p:
                byfam.setdefault(p["family"], []).append(p)
        rows = []
        for fam, ps in byfam.items():
            chips = "".join(f'<li><a href="{ctx.link("peoples/" + p["id"])}"><span class="chip">{esc(p["name"])}</span></a></li>' for p in ps)
            rows.append(f'<div style="display:grid;gap:6px"><div class="eyebrow">{esc(site.family_name(fam))}</div><ul class="tags">{chips}</ul></div>')
        card = f'<p class="small muted">{linkify(site, ctx, r["peoples_text"])}</p>' if r.get("peoples_text") else ""
        sections.append(f'<section class="section"><h2>Peoples named</h2>{"".join(rows)}{card}</section>')

    if is_map or site.edges_by.get(r["id"]):
        sections.append(lineage_section(site, ctx, r))

    # aside
    aside = []
    figure = ""
    if r["id"] in site.map_img:
        note = " This picture shows a page from the volume, not the map itself." if r["id"] in NOT_MAP_VIEW else ""
        target = r.get("primary_access") or site.iiif_base(r["id"])
        figure = (f'<figure class="mapfig"><a href="{esc(target)}" rel="noopener" data-zoom="{esc(ctx.map_img(site, r["id"], "l"))}" '
                  f'data-zoom-title="{esc(map_name(r))}, {esc(made_label(r))}">{map_img_tag(site, ctx, r, "l", eager=True)}'
                  f'<span class="zoom-hint" aria-hidden="true">Look closer</span></a>'
                  f'<figcaption>Picture: {esc(site.holder(r["id"]))}.{note} '
                  f'<a href="{esc(target)}" rel="noopener">See it at full size at the library</a></figcaption></figure>')
    else:
        thumb = thumbnail(site, r)
        if thumb:
            aside.append(thumb)
    facts = [("Atlas number", f'<span class="mono">{r["id"]}</span>'), ("Kind", esc(r["type"] or kind_word))]
    if r.get("language"):
        facts.append(("Language", esc(r["language"])))
    if d["made_start"] is not None:
        facts.append(("Made" if is_map else "Written", f'<strong>{esc(made_label(r))}</strong> <span class="muted small">({esc(prec_label(d["made_precision"]))})</span>'))
    else:
        facts.append(("Made", f'<strong>Undated</strong> <span class="muted small">({esc(prec_label(d["made_precision"]))})</span>'))
    if d.get("made_text"):
        facts.append(("Date, in full", linkify(site, ctx, d["made_text"])))
    if d.get("subject_start") is not None:
        facts.append(("Years it describes", esc(span_label(d["subject_start"], d["subject_end"], d["subject_precision"])) + (f'<br><span class="small muted">{linkify(site, ctx, d["subject_text"])}</span>' if d.get("subject_text") else "")))
    if d.get("later_editions_to"):
        facts.append(("Later editions", f"to {d['later_editions_to']}"))
    if d.get("issue_year"):
        facts.append(("This impression", str(d["issue_year"])))
    if d.get("facsimile_year"):
        facts.append(("Facsimile", str(d["facsimile_year"])))
    if d.get("content_start") is not None:
        facts.append(("Content date", esc(span_label(d["content_start"], d["content_end"], None)) + (f'<br><span class="small muted">{esc(d["content_note"])}</span>' if d.get("content_note") else "")))
    if d.get("override"):
        facts.append(("Dating note", linkify(site, ctx, d["override"])))
    facts_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
    aside.append(f'<dl class="facts">{facts_html}</dl>')

    acc = []
    if r.get("primary_access"):
        acc.append(f'<p><a href="{esc(r["primary_access"])}" rel="noopener"><strong>Open the source</strong></a></p>')
    if is_map:
        routes = site.iiif.get(r["id"], [])
        if routes:
            li = []
            for e in routes:
                st = e["status"]
                ok = st == "ok"
                st_txt = "verified" if ok else ("not yet confirmed" if st.startswith("pattern") else "did not answer when checked")
                li.append(f'<li><a href="{esc(e["url"])}" rel="noopener">Library {esc(e["kind"])}</a> <span class="small muted">{st_txt}</span></li>')
            acc.append(f'<div><div class="eyebrow">For zooming and reuse</div><ul class="note-list" style="padding-left:1em">{"".join(li)}</ul></div>')
    aside.append(f'<div class="panel"><h2>Find the original</h2>{"".join(acc)}</div>')

    mm = minimap(site, ctx, r["places"])
    if mm:
        aside.append(mm)
    aside.append(f'<p class="small"><a href="{ctx.link("corrections")}">Spot a mistake? Send a correction</a></p>')

    crumb = (f'<a href="{ctx.link("sources")}">Witnesses</a>' if prof else
             f'<a href="{ctx.link("maps")}">Map room</a>' if is_map else f'<a href="{ctx.link("records")}">Every book and map</a>')
    body = (f'<div class="page"><nav class="crumbs" aria-label="Breadcrumb">{crumb} / <span class="mono">{r["id"]}</span></nav>'
            f'{head}{figure}<div class="record-grid"><div style="display:grid;gap:28px">{"".join(sections)}</div>'
            f'<aside style="display:grid;gap:18px">{"".join(aside)}</aside></div>{onward_section(site, ctx, r)}</div>')

    title = f'{smart(short_title(no_em(r["title"]), 60))} ({made_label(r)}) · {r["id"]}'
    desc = first_sentence(no_em(r.get("research_value") or r["title"]))
    if prof:
        title = f'{short_title(prof["plain_title"], 70)} · {r["id"]}'
        desc = first_sentence(prof["one_line"], 170)
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Map" if is_map else "CreativeWork",
        "name": r["title"], "creator": r["creator"], "identifier": r["id"],
        "inLanguage": r.get("language"),
        "url": f'{CONFIG["base_url"]}/{site.rkey(r)}/',
    }
    if d["made_start"] is not None:
        jsonld["dateCreated"] = str(d["made_start"]) if d["made_start"] >= 0 else None
    if r.get("primary_access"):
        jsonld["sameAs"] = r["primary_access"]
    return dict(title=title, description=desc, body=body, nav="sources" if prof else ("maps" if is_map else "records"), jsonld=jsonld,
                modules=["pset", "lucky"] if prof else [])


def thumbnail(site, r):
    if r["kind"] != "map":
        return ""
    routes = site.iiif.get(r["id"], [])
    img = next((e for e in routes if e["kind"] == "image" and e["status"] == "ok"), None)
    if not img:
        return ""
    src = img["url"].rstrip("/") + "/full/!640,480/0/default.jpg"
    host = img["url"].split("/")[2]
    return (f'<a class="thumb" href="{esc(r["primary_access"] or img["url"])}" rel="noopener">'
            f'<img src="{esc(src)}" alt="{esc(short_title(r["title"], 90))}" loading="lazy" onerror="this.parentNode.classList.add(\'broken\')">'
            f'<div class="cap">Picture from {esc(host)}.</div></a>')


def lineage_section(site, ctx, r):
    edges = site.edges_by.get(r["id"], [])
    if not edges:
        return (f'<section class="section"><h2>Who copied whom</h2><p class="muted">No copying traced for this map yet. '
                f'<a href="{ctx.link("lineage")}">See the family trees</a>.</p></section>')
    ins = [e for d, e in edges if d == "in"]
    outs = [e for d, e in edges if d == "out"]

    def item(e, other, direction):
        o = site.rec[other]
        cert = e["certainty"]
        phrase = LINEAGE_PHRASE.get((e["type"], direction)) or LINEAGE_TYPES.get(e["type"], e["type"])
        return (f'<li><div><a href="{ctx.link(site.rkey(o))}">{esc(smart(short_title(o["title"], 80)))}</a> '
                f'<span class="rid">{o["id"]}, {esc(made_label(o))}</span></div>'
                f'<div class="edge-kind {cert}">{esc(phrase)} ({cert})</div>'
                f'<div class="small muted">{linkify(site, ctx, e["basis"])}</div></li>')
    parts = []
    if ins:
        parts.append('<div class="eyebrow">Earlier in the chain</div><ul class="lineage-list">' + "".join(item(e, e["source"], "in") for e in ins) + "</ul>")
    if outs:
        parts.append('<div class="eyebrow">Later in the chain</div><ul class="lineage-list">' + "".join(item(e, e["target"], "out") for e in outs) + "</ul>")
    return (f'<section class="section"><h2>Who copied whom</h2>{"".join(parts)}'
            f'<p class="small"><a href="{ctx.link("lineage")}">See the family trees</a></p></section>')


def page_place(site, ctx, p):
    g = basis_group(p["coord_basis"])
    eyebrow = " · ".join(["Place", esc(p["type"].replace("-", " "))])
    lede = esc(p["note"]) if p.get("note") else None
    head = page_head(eyebrow, esc(p["name"]), lede)
    n = len(p["records"])
    ps = site.psg_by_place.get(p["id"], [])
    main = []
    if ps:
        main.append(f'<section class="section" style="margin-top:0"><h2>What the sources say here: {plural(len(ps), "passage")}</h2>'
                    f'{psg_block(site, ctx, ps, 4)}</section>')
    top0 = "" if ps else ' style="margin-top:0"'
    main.append(f'<section class="section"{top0}><h2>{n} source{"s" if n != 1 else ""} and maps name this place</h2>{record_list(site, ctx, p["records"])}</section>')
    on_maps = pictured_maps(site, set(p["records"]))
    on_maps = [r for r in on_maps if r["id"] not in NOT_MAP_VIEW]
    if on_maps:
        more = f' Eight of {len(on_maps)}.' if len(on_maps) > 8 else ""
        strip = (f'<section class="section"><h2>On the old maps</h2><p class="muted">Maps that name {esc(p["name"])}.{more}</p>'
                 f'<div class="mapstrip small">{"".join(map_card(site, ctx, r) for r in on_maps[:8])}</div></section>')
        main.insert(1 if ps else 0, strip)
    if p["id"] in LABEL_IDS:
        main.insert(0, f'<p class="banner"><strong>A name, not a spot on the map.</strong> Its edges moved from map to map. '
                       f'<a href="{ctx.link("labels")}">See the many Tartarys</a>.</p>')
    facts = []
    if p["lat"] is not None:
        facts.append(("Point", f'<span class="mono">{coord_text(p["lat"], p["lon"])}</span>'))
    facts.append(("How it is plotted", f'{basis_dot(g)} {esc(BASIS[g][0])}<br><span class="small muted">{esc(BASIS[g][1])}</span>'))
    if p.get("wikidata"):
        facts.append(("Wikidata", f'<a href="https://www.wikidata.org/wiki/{esc(p["wikidata"])}" rel="noopener">{esc(p["wikidata"])}</a>'))
    if p.get("wikipedia"):
        wp = p["wikipedia"]
        url = wp if wp.startswith("http") else "https://en.wikipedia.org/wiki/" + wp.replace(" ", "_")
        facts.append(("Wikipedia", f'<a href="{esc(url)}" rel="noopener">{esc(wp if not wp.startswith("http") else "article")}</a>'))
    forms = sorted(set(p.get("aliases") or []) | set(f for f in (p.get("card_forms") or []) if len(f) < 40))
    if forms:
        shown = forms[:24]
        more = f' <span class="muted">and {len(forms) - 24} more</span>' if len(forms) > 24 else ""
        facts.append(("Also spelled", esc("; ".join(shown)) + more))
    aside = [f'<dl class="facts">{"".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)}</dl>']
    mm = minimap(site, ctx, [p["id"]], caption=False)
    if mm:
        aside.insert(0, mm)
    body = (f'<div class="page"><nav class="crumbs" aria-label="Breadcrumb"><a href="{ctx.link("map")}">Wander the map</a> / <a href="{ctx.link("places")}">Every place</a> / {esc(p["name"])}</nav>'
            f'{head}<div class="record-grid"><div>{"".join(main)}</div><aside style="display:grid;gap:18px">{"".join(aside)}</aside></div></div>')
    desc = f'{p["name"]}: {n} historical source{"s" if n != 1 else ""} and maps that name it, in date order, with how each author knew.'
    if ps:
        desc = f'{p["name"]} in the historical record: {len(ps)} quoted passages and {n} sources and maps that name it, with how each author knew.'
    jsonld = {"@context": "https://schema.org", "@type": "Place", "name": p["name"], "url": f'{CONFIG["base_url"]}/place/{p["id"]}/'}
    if p["lat"] is not None and g in ("exact", "river", "capital"):
        jsonld["geo"] = {"@type": "GeoCoordinates", "latitude": p["lat"], "longitude": p["lon"]}
    if p.get("wikidata"):
        jsonld["sameAs"] = f'https://www.wikidata.org/wiki/{p["wikidata"]}'
    return dict(title=f'{p["name"]} in the sources', description=desc, body=body, nav="map", jsonld=jsonld, modules=["pset"])


def page_people(site, ctx, p):
    ids = site.people_records.get(p["id"], [])
    head = page_head(esc(site.family_name(p["family"])), esc(p["name"]),
                     f'Named in {len(ids)} source{"s" if len(ids) != 1 else ""} and maps.')
    aliases = sorted(set(a for a in p.get("aliases", []) if len(a) < 60))
    aside = ""
    if aliases:
        aside = f'<dl class="facts"><dt>Also spelled</dt><dd>{esc("; ".join(aliases[:40]))}</dd></dl>'
    fam = [q for q in site.peoples if q["family"] == p["family"] and q["id"] != p["id"]]
    if fam:
        aside += ('<div style="display:grid;gap:6px"><div class="eyebrow">Same family</div><ul class="tags">'
                  + "".join(f'<li><a href="{ctx.link("peoples/" + q["id"])}"><span class="chip">{esc(q["name"])}</span></a></li>' for q in fam)
                  + "</ul></div>")
    body = (f'<div class="page"><nav class="crumbs" aria-label="Breadcrumb"><a href="{ctx.link("peoples")}">Who’s who</a> / {esc(p["name"])}</nav>'
            f'{head}<div class="record-grid"><div>{record_list(site, ctx, ids)}</div><aside style="display:grid;gap:18px">{aside}</aside></div></div>')
    return dict(title=f'{p["name"]} in the sources', description=f'Historical sources and maps that name the {p["name"]}, in date order.', body=body, nav="peoples")


def page_records(site, ctx):
    rows = []
    for r in sorted(site.records, key=sort_key):
        s = r["date"]["made_start"]
        hay = " ".join([r["id"], r["title"], r["creator"] or "", r["language"] or "", r.get("regions_text") or "", r.get("peoples_text") or ""]).lower()
        rows.append(
            f'<tr data-k="{r["kind"]}" data-ev="{esc(r["evidence_class"])}" data-y="{"" if s is None else s}" data-h="{esc(hay)}">'
            f'<td class="num">{esc(made_label(r))}</td><td>{kind_badge(r)}</td>'
            f'<td><a href="{ctx.link(site.rkey(r))}">{esc(short_title(r["title"], 90))}</a><div class="small muted">{esc(short_creator(r["creator"]))}</div></td>'
            f'<td>{ev_chip(r["evidence_class"], button=True)}</td><td class="rid">{r["id"]}</td></tr>')
    ev_opts = "".join(f'<option value="{esc(e)}">{esc(e)}</option>' for e in EVIDENCE_ORDER)
    counts = collections.Counter(r["kind"] for r in site.records)
    head = page_head("The vault", "Every book and map",
                     f'{counts["written"]} written sources and {counts["map"]} maps, from antiquity to the 1870s.')
    body = (f'<div class="page">{head}<div data-module="rtable">'
            f'<div class="filterbar"><label for="rt-q">Search<input type="search" id="rt-q" placeholder="Witsen, Tobolsk, Tartaria, W122…"></label>'
            f'<label for="rt-k">Kind<select id="rt-k"><option value="">All</option><option value="written">Written sources</option><option value="map">Maps</option></select></label>'
            f'<label for="rt-ev">How the author knew<select id="rt-ev"><option value="">Any</option>{ev_opts}</select></label>'
            f'<p class="small muted list-count" aria-live="polite"><span data-count>{len(site.records)}</span><span data-of hidden> of {len(site.records)}</span> books and maps'
            f'<button type="button" class="linkbtn" data-clear hidden>Clear filters</button></p></div>'
            f'<p class="muted" data-empty hidden>Nothing matches. Try a shorter word, or clear the filters.</p>'
            f'<div class="table-wrap"><table class="data"><thead><tr><th class="num">Date</th><th>Kind</th><th>Title and maker</th><th>How they knew</th><th>No.</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div></div>')
    return dict(title="Records", description=f"All {len(site.records)} written sources and maps in the Tartary Atlas, in date order, searchable by name, place and ID.", body=body, nav="records", modules=["rtable"])


def page_places(site, ctx):
    groups = collections.defaultdict(list)
    for p in site.places:
        groups[p["type"]].append(p)
    order = sorted(groups, key=lambda t: -sum(len(p["records"]) for p in groups[t]))
    secs = []
    for t in order:
        items = "".join(
            f'<li><span>{basis_dot(basis_group(p["coord_basis"]))} <a href="{ctx.link("place/" + p["id"])}">{esc(p["name"])}</a></span><span class="n">{len(p["records"])}</span></li>'
            for p in sorted(groups[t], key=lambda p: (-len(p["records"]), p["name"])))
        secs.append(f'<section><h3>{esc(t.replace("-", " ").capitalize())} <span class="muted small">{len(groups[t])}</span></h3><ul>{items}</ul></section>')
    legend = "".join(f'<div>{basis_dot(g)}<span><strong>{esc(v[0])}.</strong> {esc(v[1])}</span></div>' for g, v in BASIS.items())
    head = page_head("The vault", "Every place",
                     f'{len(site.places)} places, and how many sources and maps name each one.')
    body = f'<div class="page">{head}<div class="legend panel" style="margin-bottom:28px;max-width:78ch">{legend}</div><div class="cols">{"".join(secs)}</div></div>'
    return dict(title="Places", description="Every place named in the Tartary Atlas records, with how each map point was chosen.", body=body, nav="places")


def page_peoples(site, ctx):
    secs = []
    for fam, name in site.families.items():
        ps = sorted((p for p in site.peoples if p["family"] == fam), key=lambda p: (-p["record_count"], p["name"]))
        if not ps:
            continue
        items = "".join(f'<li><a href="{ctx.link("peoples/" + p["id"])}">{esc(p["name"])}</a><span class="n">{p["record_count"]}</span></li>' for p in ps)
        secs.append(f'<section><h3>{esc(name)}</h3><ul>{items}</ul></section>')
    head = page_head("The vault", "Who’s who",
                     f'{len(site.peoples)} peoples and powers, and how many sources and maps name each one.')
    return dict(title="Peoples and polities", description="Peoples and polities named in the Tartary Atlas records, grouped into families.", body=f'<div class="page">{head}<div class="cols">{"".join(secs)}</div></div>', nav="peoples")


# ------------------------------------------------ Tartary labels timeline

def page_labels(site, ctx):
    rows = []
    for lid in LABEL_IDS:
        p = site.place[lid]
        recs = [site.rec[i] for i in p["records"]]
        rows.append((p, recs))
    years = [r["date"]["made_start"] for _, recs in rows for r in recs if r["date"]["made_start"] is not None]
    y0 = (min(years) // 50) * 50
    y1 = 1900
    left, right, rowh, top = 188, 20, 46, 30
    width = 1080
    plot_w = width - left - right
    height = top + rowh * len(rows) + 30

    def X(y):
        return left + (y - y0) / (y1 - y0) * plot_w

    parts = [f'<svg class="wide" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Timeline of Tartary labels on maps and in texts" data-y0="{y0}" data-y1="{y1}" data-left="{left}" data-plotw="{plot_w}">']
    parts.append(f'<rect class="window" x="0" y="{top - 10}" width="0" height="{rowh * len(rows) + 10}" data-window/>')
    step = 50
    for yv in range(y0, y1 + 1, step):
        parts.append(f'<g class="axis"><line x1="{X(yv):.1f}" x2="{X(yv):.1f}" y1="{top - 10}" y2="{top + rowh * len(rows)}" class="grid"/>'
                     f'<text class="yr" x="{X(yv):.1f}" y="{top + rowh * len(rows) + 18}" text-anchor="middle">{yv}</text></g>')
    for i, (p, recs) in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        parts.append(f'<line class="rowline" x1="{left}" x2="{width - right}" y1="{cy}" y2="{cy}"/>')
        parts.append(f'<text class="rowlab" x="{left - 12}" y="{cy + 4}" text-anchor="end">{esc(p["name"])} <tspan class="yr" style="font-family:var(--font-mono);fill:var(--ink-3)">{len(recs)}</tspan></text>')
        placed = []
        for r in sorted(recs, key=sort_key):
            s = r["date"]["made_start"]
            if s is None:
                continue
            x = X(s)
            for off in (0, -9, 9, -18, 18, -27, 27):
                if all(abs(x - px) >= 10.5 or abs(off - po) >= 10.5 for px, po in placed):
                    break
            placed.append((x, off))
            cls = "mk" if r["kind"] == "map" else "mk w"
            parts.append(f'<a href="{ctx.link(site.rkey(r))}" data-y="{s}" data-label="{p["id"]}" data-lname="{esc(p["name"])}"><title>{esc(r["id"])} {esc(short_title(r["title"], 70))}, {esc(made_label(r))}</title>'
                         f'<circle class="{cls}" cx="{x:.1f}" cy="{cy + off:.1f}" r="5.5"/></a>')
    parts.append(f'<line class="cursor" x1="0" x2="0" y1="{top - 10}" y2="{top + rowh * len(rows)}" data-cursor style="display:none"/>')
    parts.append("</svg>")

    # static list per label
    lists = []
    for p, recs in rows:
        forms = sorted(set(m for f in p.get("card_forms", []) for m in re.findall(r"\b(?:Gran |Grande |Great |Magna )?Tart[a-zA-Z]+(?: [A-Z][a-z]+)?", f)))
        forms_html = f'<p class="small muted">Spelled: {esc("; ".join(forms[:14]))}</p>' if forms else ""
        lists.append(f'<section class="section"><h2><a href="{ctx.link("place/" + p["id"])}">{esc(p["name"])}</a> <span class="muted small">{len(recs)}</span></h2>{forms_html}{record_list(site, ctx, [r["id"] for r in recs])}</section>')

    def first_map(lid, last=False):
        ms = sorted((r for r in rows_by[lid] if r["kind"] == "map" and r["date"]["made_start"] is not None), key=sort_key)
        r = ms[-1] if last else ms[0]
        return f'<a href="{ctx.link(site.rkey(r))}">{r["date"]["made_start"]}</a>'
    rows_by = {p["id"]: recs for p, recs in rows}
    lede = (f"Tartaria first appears on a map here in {first_map('tartary')} and last in {first_map('tartary', True)}. "
            f"Great Tartary reaches the maps in {first_map('great-tartary')}. Chinese Tartary follows in {first_map('chinese-tartary')}, "
            f"Muscovite Tartary in {first_map('muscovite-tartary')}, Independent Tartary in {first_map('independent-tartary')} "
            f"and Little Tartary in {first_map('little-tartary')}. Each name covered a region whose edges moved from map to map.")
    head = page_head("The vault", "The many Tartarys", lede,
                     extra=(f'<p class="hero-actions"><a class="btn primary" href="{ctx.link("dial")}">Turn the dial: see it on the maps</a></p>' if dial_stops(site) else ""))
    mid = 1700
    body = (f'<div class="page">{head}<div data-module="labels">'
            f'<div class="figure"><div class="slider-row"><label for="lab-y" class="small">Which names were in use around</label>'
            f'<input type="range" id="lab-y" min="{y0}" max="{y1}" step="5" value="{mid}"><output for="lab-y" data-out>{mid}</output>'
            f'<span class="small muted">within 25 years either side</span></div>'
            f'<div class="scroll">{"".join(parts)}</div>'
            f'<div class="fig-legend"><span><span class="sw"></span>Map</span><span><span class="sw w"></span>Written source</span>'
            f'<span class="muted">Click a mark to open it.</span></div></div>'
            f'<div class="section" data-window-list aria-live="polite"></div></div>'
            f'{"".join(lists)}</div>')
    return dict(title="Tartaria on the map: Tartary labels by date", description="When Tartary, Great Tartary, Little, Chinese, Independent and Muscovite Tartary appear on maps and in texts, record by record.", body=body, nav="labels", modules=["labels"])


# ------------------------------------------------ What "Tartar" meant

def page_meanings(site, ctx):
    recs = [r for r in site.records if r["tartar_referents_card"] and r["date"]["made_start"] is not None]
    fams = collections.Counter(f for r in recs for f in r["tartar_referents_card"])
    order = [f for f, _ in fams.most_common()]
    order = [f for f in order if f != "unspecified"] + (["unspecified"] if "unspecified" in fams else [])
    left, right, rowh, top = 262, 20, 40, 24
    width = 1080
    plot_w = width - left - right
    height = top + rowh * len(order) + 34
    brk = 1200
    lo = min(r["date"]["made_start"] for r in recs)
    lo = (lo // 100) * 100
    comp = 0.12

    def X(y):
        if y < brk:
            return left + (y - lo) / (brk - lo) * plot_w * comp
        return left + plot_w * comp + (y - brk) / (1900 - brk) * plot_w * (1 - comp)

    parts = [f'<svg class="wide" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Dot chart of what Tartar meant in each written source, by date">']
    ticks = [lo, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
    parts.append(f'<rect x="{left}" y="{top - 8}" width="{X(brk) - left:.1f}" height="{rowh * len(order) + 8}" style="fill:var(--rule-soft)"/>')
    parts.append(f'<text class="yr" x="{(left + X(brk)) / 2:.1f}" y="{top - 12}" text-anchor="middle" style="font-size:10px;fill:var(--ink-3)">compressed</text>')
    for yv in ticks:
        if yv < lo or (yv < brk and yv != lo):
            continue
        parts.append(f'<g class="axis"><line class="grid" x1="{X(yv):.1f}" x2="{X(yv):.1f}" y1="{top - 8}" y2="{top + rowh * len(order)}"/>'
                     f'<text class="yr" x="{X(yv):.1f}" y="{top + rowh * len(order) + 18}" text-anchor="middle">{yv}</text></g>')
    ypos = {f: top + i * rowh + rowh / 2 for i, f in enumerate(order)}
    for f in order:
        cy = ypos[f]
        parts.append(f'<line class="rowline" x1="{left}" x2="{width - right}" y1="{cy}" y2="{cy}"/>')
        parts.append(f'<text class="rowlab" x="{left - 12}" y="{cy + 4}" text-anchor="end">{esc(FAMILY_SHORT.get(f, site.family_name(f)))} <tspan style="font-family:var(--font-mono);fill:var(--ink-3)">{fams[f]}</tspan></text>')
    for r in recs:
        x = X(r["date"]["made_start"])
        ys = sorted(ypos[f] for f in r["tartar_referents_card"])
        if len(ys) > 1:
            parts.append(f'<line class="link-v" x1="{x:.1f}" x2="{x:.1f}" y1="{ys[0]}" y2="{ys[-1]}"/>')
    placed = collections.defaultdict(list)
    for r in sorted(recs, key=sort_key):
        x = X(r["date"]["made_start"])
        for f in r["tartar_referents_card"]:
            cy = ypos[f]
            for off in (0, -8, 8, -15, 15):
                if all(abs(x - px) >= 9 or abs(off - po) >= 9 for px, po in placed[f]):
                    break
            placed[f].append((x, off))
            parts.append(f'<a href="{ctx.link(site.rkey(r))}"><title>{r["id"]} {esc(short_title(r["title"], 70))}, {esc(made_label(r))}: {esc(site.family_name(f))}</title>'
                         f'<circle class="mk w" cx="{x:.1f}" cy="{cy + off:.1f}" r="5"/></a>')
    parts.append("</svg>")

    lists = []
    for f in order:
        ids = [r["id"] for r in recs if f in r["tartar_referents_card"]]
        lists.append(f'<section class="section"><h2>{esc(site.family_name(f))} <span class="muted small">{len(ids)}</span></h2>{record_list(site, ctx, ids)}</section>')

    head = page_head("The vault", "Who counted as a Tartar?",
                     f"The same word named different peoples in different centuries. Each dot is one of {len(recs)} written sources, in the row of the people it meant.")
    banner = ('<p class="banner"><strong>A first pass.</strong> These readings come from catalogue notes, not yet from the passages themselves.</p>')
    body = (f'<div class="page">{head}{banner}<div class="figure" style="margin-top:18px"><div class="scroll">{"".join(parts)}</div>'
            f'<div class="fig-legend"><span><span class="sw w"></span>One written source</span>'
            f'<span class="muted">Before 1200 is squeezed to fit. Click a dot to open it.</span></div></div>'
            f'{"".join(lists)}</div>')
    return dict(title="What Tartar meant: Tartars and Tatars in the sources", description="Which peoples the word Tartar or Tatar named in each written source, plotted by date. Provisional, card-level readings.", body=body, nav="meanings")


# ------------------------------------------------ Lineage

def lineage_components(site):
    adj = collections.defaultdict(set)
    for e in site.lineage:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    seen, comps = set(), []
    for n in sorted(adj):
        if n in seen:
            continue
        stack, comp = [n], set()
        while stack:
            a = stack.pop()
            if a in comp:
                continue
            comp.add(a)
            stack.extend(adj[a] - comp)
        seen |= comp
        comps.append(comp)
    comps.sort(key=lambda c: min(site.rec[i]["date"]["made_start"] for i in c))
    return comps


def lineage_svg(site, ctx, comp, idx):
    nodes = sorted(comp, key=lambda i: sort_key(site.rec[i]))
    edges = [e for e in site.lineage if e["source"] in comp]
    ys = [site.rec[i]["date"]["made_start"] for i in nodes]
    y0, y1 = min(ys), max(ys)
    label_w = 150
    width = 1040
    left, right = label_w // 2 + 8, label_w // 2 + 8
    span = max(y1 - y0, 1)
    plot_w = min(width - left - right, max(260, span * 7))
    width = int(left + plot_w + right)

    def X(y):
        return left + (y - y0) / span * plot_w if y1 > y0 else left

    parents = collections.defaultdict(list)
    for e in edges:
        parents[e["target"]].append(e["source"])
    lane = {}
    occupied = collections.defaultdict(list)
    for n in nodes:
        x = X(site.rec[n]["date"]["made_start"])
        cand = lane[parents[n][0]] if parents[n] and parents[n][0] in lane else 0
        for d in range(0, 40):
            ln = cand + d
            if all(abs(x - ox) > label_w + 12 for ox in occupied[ln]):
                break
        lane[n] = ln
        occupied[ln].append(x)
    nlanes = max(lane.values()) + 1
    lane_h = 62
    height = 30 + nlanes * lane_h + 22

    def Y(n):
        return 30 + lane[n] * lane_h + 20

    mid = f"lin{idx}"
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Lineage diagram">',
             f'<defs><marker id="{mid}s" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead" d="M0 0L10 5L0 10z"/></marker>'
             f'<marker id="{mid}p" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead probable" d="M0 0L10 5L0 10z"/></marker></defs>']
    # year ticks
    stepv = 10 if span <= 60 else (25 if span <= 150 else (50 if span <= 400 else 100))
    for yv in range((y0 // stepv + 1) * stepv, y1 + 1, stepv):
        parts.append(f'<g class="axis"><line class="grid" x1="{X(yv):.1f}" x2="{X(yv):.1f}" y1="14" y2="{height - 22}"/><text class="yr" x="{X(yv):.1f}" y="{height - 6}" text-anchor="middle">{yv}</text></g>')
    for e in edges:
        a, b = e["source"], e["target"]
        ax, ay = X(site.rec[a]["date"]["made_start"]), Y(a)
        bx, by = X(site.rec[b]["date"]["made_start"]), Y(b)
        prob = e["certainty"] == "probable"
        if abs(bx - ax) < 4:
            dx = 36
            path = f"M{ax + 7:.1f} {ay:.1f}C{ax + dx:.1f} {ay:.1f} {bx + dx:.1f} {by:.1f} {bx + 8:.1f} {by:.1f}"
        else:
            sgn = 1 if bx > ax else -1
            ax2, bx2 = ax + 7 * sgn, bx - 8 * sgn
            mx = (ax2 + bx2) / 2
            path = f"M{ax2:.1f} {ay:.1f}C{mx:.1f} {ay:.1f} {mx:.1f} {by:.1f} {bx2:.1f} {by:.1f}"
        tip = f'{a} to {b}: {LINEAGE_TYPES.get(e["type"], e["type"])}, {e["certainty"]}. {e["basis"]}'
        marker = f' marker-end="url(#{mid}{"p" if prob else "s"})"' if e["type"] in DIRECTED else ""
        parts.append(f'<path class="lin-edge{" probable" if prob else ""}" d="{path}"{marker}><title>{esc(no_em(tip))}</title></path>')
    for n in nodes:
        r = site.rec[n]
        x, y = X(r["date"]["made_start"]), Y(n)
        lab = LINEAGE_SHORT.get(n) or short_creator(r["creator"], 22)
        parts.append(f'<a class="lin-node{" w" if r["kind"] == "written" else ""}" href="{ctx.link(site.rkey(r))}"><title>{esc(n)} {esc(short_title(r["title"], 90))}, {esc(made_label(r))}</title>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5"/>'
                     f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle">{esc(lab)} {esc(made_label(r))}</text>'
                     f'<text class="id" x="{x:.1f}" y="{y + 21:.1f}" text-anchor="middle">{n}</text></a>')
    parts.append("</svg>")
    return "".join(parts)


def lineage_svg_vertical(site, ctx, comp, idx):
    """Larger families: time runs down the page, one row per distinct year, in order (not to scale)."""
    nodes = sorted(comp, key=lambda i: sort_key(site.rec[i]))
    edges = [e for e in site.lineage if e["source"] in comp]
    years = sorted({site.rec[n]["date"]["made_start"] for n in nodes})
    row = {y: i for i, y in enumerate(years)}
    parents = collections.defaultdict(list)
    for e in edges:
        parents[e["target"]].append(e["source"])
    lane, used = {}, collections.defaultdict(set)
    for n in nodes:
        rw = row[site.rec[n]["date"]["made_start"]]
        cand = lane[parents[n][0]] if parents[n] and parents[n][0] in lane else 0
        for d in range(0, 40):
            opts = [cand + d, cand - d] if d else [cand]
            ok = [o for o in opts if o >= 0 and o not in used[rw]]
            if ok:
                ln = ok[0]
                break
        lane[n] = ln
        used[rw].add(ln)
    nl = max(lane.values()) + 1
    gutter, lane_w, row_h, top = 64, 205, 50, 22
    width = gutter + nl * lane_w + 10
    height = top + len(years) * row_h + 6

    def XY(n):
        return gutter + 14 + lane[n] * lane_w, top + row[site.rec[n]["date"]["made_start"]] * row_h + 10

    mid = f"lin{idx}"
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Lineage diagram, earliest at the top">',
             f'<defs><marker id="{mid}s" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead" d="M0 0L10 5L0 10z"/></marker>'
             f'<marker id="{mid}p" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead probable" d="M0 0L10 5L0 10z"/></marker></defs>']
    for y in years:
        yy = top + row[y] * row_h + 10
        parts.append(f'<g class="axis"><line class="grid" x1="{gutter - 6}" x2="{width - 6}" y1="{yy}" y2="{yy}" style="stroke:var(--rule-soft)"/>'
                     f'<text class="yr" x="{gutter - 12}" y="{yy + 4}" text-anchor="end">{year(y)}</text></g>')
    for e in edges:
        (ax, ay), (bx, by) = XY(e["source"]), XY(e["target"])
        prob = e["certainty"] == "probable"
        if abs(by - ay) < 2:
            sgn = 1 if bx > ax else -1
            path = f"M{ax + 7 * sgn:.1f} {ay:.1f}C{ax + 40 * sgn:.1f} {ay - 22:.1f} {bx - 40 * sgn:.1f} {by - 22:.1f} {bx - 8 * sgn:.1f} {by:.1f}"
        else:
            sgn = 1 if by > ay else -1
            my = (ay + by) / 2
            path = f"M{ax:.1f} {ay + 7 * sgn:.1f}C{ax:.1f} {my:.1f} {bx:.1f} {my:.1f} {bx:.1f} {by - 8 * sgn:.1f}"
        marker = f' marker-end="url(#{mid}{"p" if prob else "s"})"' if e["type"] in DIRECTED else ""
        tip = f'{e["source"]} to {e["target"]}: {LINEAGE_TYPES.get(e["type"], e["type"])}, {e["certainty"]}. {e["basis"]}'
        parts.append(f'<path class="lin-edge{" probable" if prob else ""}" d="{path}"{marker}><title>{esc(no_em(tip))}</title></path>')
    for n in nodes:
        r = site.rec[n]
        x, y = XY(n)
        lab = LINEAGE_SHORT.get(n) or short_creator(r["creator"], 22)
        parts.append(f'<a class="lin-node{" w" if r["kind"] == "written" else ""}" href="{ctx.link(site.rkey(r))}"><title>{esc(n)} {esc(short_title(r["title"], 90))}, {esc(made_label(r))}</title>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5"/>'
                     f'<text x="{x + 12:.1f}" y="{y + 1:.1f}">{esc(lab)}</text>'
                     f'<text class="id" x="{x + 12:.1f}" y="{y + 14:.1f}">{n} \u00b7 {esc(made_label(r))}</text></a>')
    parts.append("</svg>")
    return "".join(parts)


def page_lineage(site, ctx):
    comps = lineage_components(site)
    edges_all = site.lineage
    secs = []
    for i, comp in enumerate(comps):
        nodes = sorted(comp, key=lambda n: sort_key(site.rec[n]))
        repro = {e["target"] for e in edges_all if e["type"] == "reproduction"}
        y_min = site.rec[nodes[0]]["date"]["made_start"]
        first = site.rec[next((n for n in nodes if site.rec[n]["date"]["made_start"] == y_min and n not in repro), nodes[0])]
        last = site.rec[nodes[-1]]
        edges = [e for e in site.lineage if e["source"] in comp]
        name = LINEAGE_SHORT.get(first["id"]) or short_creator(first["creator"], 30)
        stated = sum(1 for e in edges if e["certainty"] == "stated")
        rows = "".join(
            f'<tr><td><a href="{ctx.link(site.rkey(e["source"]))}" class="rid">{e["source"]}</a></td>'
            f'<td><a href="{ctx.link(site.rkey(e["target"]))}" class="rid">{e["target"]}</a></td>'
            f'<td>{esc(LINEAGE_TYPES.get(e["type"], e["type"]))}</td><td><span class="edge-kind {e["certainty"]}">{e["certainty"]}</span></td><td>{linkify(site, ctx, e["basis"])}</td></tr>'
            for e in edges)
        secs.append(
            f'<section class="section" id="family-{i + 1}"><h2>From {esc(name)}, {esc(made_label(first))}</h2>'
            f'<p class="small muted">{len(nodes)} works, {esc(made_label(first))} to {esc(made_label(last))}</p>'
            f'<div class="figure"><div class="scroll">{lineage_svg_vertical(site, ctx, comp, i) if len(comp) > 6 else lineage_svg(site, ctx, comp, i)}</div></div>'
            f'<details><summary class="small">{"The " + str(len(edges)) + " links and the evidence for each" if len(edges) != 1 else "The link and its evidence"}</summary>'
            f'<div class="table-wrap" style="margin-top:8px"><table class="data"><thead><tr><th>From</th><th>To</th><th>Link</th><th>How sure</th><th>Why</th></tr></thead><tbody>{rows}</tbody></table></div></details></section>')
    n_prob = sum(1 for e in site.lineage if e["certainty"] == "probable")
    head = page_head("The vault", "Who copied whom",
                     f"Mapmakers copied, reissued and corrected one another. Here are {len(comps)} family trees. "
                     "An arrow runs from a map to the one made from it. A plain line joins works that share a plate, an atlas or a tradition.")
    legend = ('<div class="fig-legend" style="margin-bottom:6px"><span><span class="ln"></span>Stated outright</span>'
              f'<span><span class="ln dash"></span>Probable</span><span><span class="sw w"></span>Map</span>'
              '<span class="muted">Click a name to open it.</span></div>')
    return dict(title="Map lineage: who copied whom", description="Diagrams of which maps of Tartary copied, reissued or corrected which, from Jenkinson and Ortelius to the SDUK atlas.", body=f'<div class="page">{head}{legend}{"".join(secs)}</div>', nav="lineage")


# ------------------------------------------------ Explorer (home)

def explorer_data(site):
    trads = collections.Counter(tradition_label(r["tradition"]) for r in site.records)
    tlist = sorted(trads, key=lambda t: -trads[t])
    tindex = {t: i for i, t in enumerate(tlist)}
    recs = []
    for r in site.records:
        d = r["date"]
        recs.append([r["id"], 1 if r["kind"] == "map" else 0, d["made_start"], made_label(r),
                     EVIDENCE_ORDER.index(r["evidence_class"]), tindex[tradition_label(r["tradition"])],
                     short_title(no_em(r["title"]), 90), short_creator(no_em(r["creator"]), 40), r["places"]])
    places = []
    for p in site.places:
        g = basis_group(p["coord_basis"])
        places.append([p["id"], p["name"], g, p["lon"], p["lat"], len(site.psg_by_place.get(p["id"], []))])
    return {
        "records": recs, "places": places,
        "traditions": [[t, trads[t]] for t in tlist],
        "evidence": [[e, sum(1 for r in site.records if r["evidence_class"] == e)] for e in EVIDENCE_ORDER],
        "basis": {g: v[0] for g, v in BASIS.items()},
    }


def page_map(site, ctx):
    data = explorer_data(site)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    n_w = sum(1 for r in site.records if r["kind"] == "written")
    n_m = len(site.records) - n_w
    legend = "".join(f'<div>{basis_dot(g)}<span>{esc(BASIS[g][0])}</span></div>' for g in ["exact", "river", "capital", "approx", "anchor"])
    body = f'''<div class="explorer" data-module="explorer">
<script type="application/json">{js}</script>
<div class="mapwrap"><div id="ta-map" role="region" aria-label="Map of places named in the sources"></div>
<div class="map-note">Modern coastlines and rivers, Natural Earth. Aral Sea at its modern extent.</div></div>
<div class="side">
<div class="side-sec intro"><h1>Wander the map</h1>
<p>Click a place to read what was written about it.</p>
<div class="stats"><span><b data-stat="places">0</b>places</span><span><b data-stat="records">{len(site.records)}</b>books and maps</span></div></div>
<div class="side-sec place-panel" data-panel aria-live="polite"></div>
<div class="side-sec"><h2>Pick your years</h2>
<div class="range"><svg class="hist" viewBox="0 0 200 44" preserveAspectRatio="none" aria-hidden="true" data-hist></svg>
<div class="dual"><div class="track"></div><div class="fill" data-fill></div>
<input type="range" id="ex-lo" min="0" max="100" step="0.25" value="0" aria-label="Earliest date">
<input type="range" id="ex-hi" min="0" max="100" step="0.25" value="100" aria-label="Latest date"></div>
<div class="ticks" data-ticks></div>
<div class="readout" data-readout aria-live="polite"></div></div>
<label class="small" style="display:flex;gap:8px;align-items:center"><input type="checkbox" id="ex-undated" checked> Include the one undated map</label>
</div>
<div class="side-sec"><h2>Show</h2>
<div class="seg" role="group" aria-label="Kind of record"><button type="button" data-kind="all" aria-pressed="true">All</button><button type="button" data-kind="0" aria-pressed="false">Written</button><button type="button" data-kind="1" aria-pressed="false">Maps</button></div>
<details class="filters"><summary>How the author knew</summary><div class="checks" data-ev></div></details>
<details class="filters"><summary>Language</summary><div class="checks" data-tr></div></details>
</div>
<div class="side-sec"><h2>Map key</h2><div class="legend">{legend}</div>
<p class="small muted">Bigger dot, more sources. Dashed rings are rough positions. <a href="{ctx.link("method")}">How places were plotted</a>.</p></div>
</div></div>'''
    desc = f"A map of every place named in {n_w} historical texts and {n_m} maps about Tartary (Tartaria): who wrote about each one, when, and how they knew."
    return dict(title="Map of Tartary in the sources", description=desc, body=body, nav="map", modules=["explorer"], maplibre=True)


# ---------------------------------------------------------------- rides and the deck

RIDE_W = 1000.0
RIDE_MIN_RATIO = 0.52      # a route that runs due east still gets a map tall enough to read
# The five trails as suits: each wears a drawing cut from one of the maps.
SUITS = collections.OrderedDict([
    ("cities", "tents"), ("architecture", "khan"), ("customs", "rider"), ("names", "scholar"), ("outliers", "merfolk"),
])
# The three places in a spread, and the trails each draws from.
SPREAD = [("The place", ["cities", "architecture"]), ("The people", ["customs", "names"]), ("The marvel", ["outliers"])]


def clip_ring(ring, box):
    """Sutherland-Hodgman: a closed ring clipped to a lon/lat box."""
    x0, y0, x1, y1 = box
    def clip(pts, inside, cross):
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
        return out
    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))
    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)
    pts = [tuple(p[:2]) for p in ring]
    for inside, cross in [(lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                          (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))]:
        if not pts:
            break
        pts = clip(pts, inside, cross)
    return pts


class RideMap:
    """The sheet a journey is drawn on: a plain projection fitted to the stops, with the coast, lakes and rivers
    of the self-hosted basemap clipped to it."""
    _base = None

    def __init__(self, stops):
        lons, lats = [s["lon"] for s in stops], [s["lat"] for s in stops]
        lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
        pad = max(lon1 - lon0, 10) * 0.07
        lon0, lon1 = lon0 - pad, lon1 + pad
        lat0, lat1 = lat0 - pad * 0.8, lat1 + pad * 0.8
        self.kx = math.cos(math.radians((lat0 + lat1) / 2))
        w_deg = (lon1 - lon0) * self.kx
        if (lat1 - lat0) < w_deg * RIDE_MIN_RATIO:
            grow = (w_deg * RIDE_MIN_RATIO - (lat1 - lat0)) / 2
            lat0, lat1 = lat0 - grow, lat1 + grow
        self.lon0, self.lat1 = lon0, lat1
        self.s = RIDE_W / w_deg
        self.W, self.H = RIDE_W, (lat1 - lat0) * self.s
        m = 3.0
        self.box = (lon0 - m, lat0 - m, lon1 + m, lat1 + m)
        self.view = (lon0, lat0, lon1, lat1)

    def xy(self, lon, lat):
        return (lon - self.lon0) * self.kx * self.s, (self.lat1 - lat) * self.s

    @classmethod
    def base(cls):
        if cls._base is None:
            cls._base = {n: json.loads((STATIC / "basemap" / f"{n}.json").read_text()) for n in ("land", "lakes", "rivers")}
        return cls._base

    def _d(self, pts, close):
        out, last = [], None
        for lon, lat in pts:
            x, y = self.xy(lon, lat)
            if last is None or abs(x - last[0]) + abs(y - last[1]) > 0.9:
                out.append(f"{x:.1f} {y:.1f}")
                last = (x, y)
        if len(out) < (3 if close else 2):
            return ""
        return "M" + "L".join(out) + ("Z" if close else "")

    def _rings(self, geoms):
        x0, y0, x1, y1 = self.box
        parts = []
        for g in geoms:
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for ring in poly:
                    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
                    if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
                        continue
                    parts.append(self._d(clip_ring(ring, self.box), True))
        return "".join(parts)

    def land(self):
        return self._rings(self.base()["land"]["geometries"])

    def lakes(self):
        return self._rings([f["geometry"] for f in self.base()["lakes"]["features"] if f["geometry"]])

    def rivers(self):
        x0, y0, x1, y1 = self.box
        parts = []
        for f in self.base()["rivers"]["features"]:
            g = f["geometry"]
            if not g:
                continue
            lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            for line in lines:
                run = []
                for p in line:
                    if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                        run.append(p[:2])
                    else:
                        parts.append(self._d(run, False))
                        run = []
                parts.append(self._d(run, False))
        return "".join(parts)

    def graticule(self):
        lon0, lat0, lon1, lat1 = self.view
        out = []
        for lon in range(int(math.floor(lon0 / 10) * 10), int(lon1) + 10, 10):
            x, _ = self.xy(lon, 0)
            out.append(f"M{x:.1f} 0V{self.H:.1f}")
        for lat in range(int(math.floor(lat0 / 10) * 10), int(lat1) + 10, 10):
            _, y = self.xy(0, lat)
            out.append(f"M0 {y:.1f}H{self.W:.0f}")
        return "".join(out)

    def legs(self, stops):
        """One curve per leg, eased through the stops so the line bends like a road and not like a ruler."""
        P = [self.xy(s["lon"], s["lat"]) for s in stops]
        out = []
        for i in range(len(P) - 1):
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
            t = 0.16
            # keep the bend in proportion to the leg itself, so a short hop next to a long one does not loop
            d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            def lim(vx, vy):
                n = math.hypot(vx, vy)
                k = min(1.0, d * 0.45 / n) if n else 0
                return vx * k, vy * k
            ax, ay = lim((p2[0] - p0[0]) * t * 2, (p2[1] - p0[1]) * t * 2)
            bx, by = lim((p3[0] - p1[0]) * t * 2, (p3[1] - p1[1]) * t * 2)
            out.append(f"M{p1[0]:.1f} {p1[1]:.1f}C{p1[0] + ax:.1f} {p1[1] + ay:.1f} {p2[0] - bx:.1f} {p2[1] - by:.1f} {p2[0]:.1f} {p2[1]:.1f}")
        return out


def ride_counts(site, j):
    n_psg = sum(len([i for i in s["psg"] if i in site.psg]) for s in j["stops"])
    return len(j["stops"]), n_psg


def ride_thumb(site, ctx, j):
    """A small picture of the route for a card: the line over the same land shape the mini maps use."""
    pts = [mm_proj(s["lon"], s["lat"]) for s in j["stops"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    pad = max(w, h) * 0.12 + 6
    x0, y0, w, h = min(xs) - pad, min(ys) - pad, w + 2 * pad, h + 2 * pad
    if h < w * 0.5:
        y0 -= (w * 0.5 - h) / 2
        h = w * 0.5
    line = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    r = w / 110
    ends = (f'<circle class="end" cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="{r:.2f}"/>'
            f'<circle class="end far" cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="{r:.2f}"/>')
    return (f'<svg class="ride-thumb" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" aria-hidden="true" preserveAspectRatio="xMidYMid slice">'
            f'<use class="land" href="{ctx.land_href()}" width="{MM_W}" height="{MM_H}"/>'
            f'<path class="line" d="{line}" vector-effect="non-scaling-stroke"/>{ends}</svg>')


def ride_card(site, ctx, j):
    n_stops, n_psg = ride_counts(site, j)
    return (f'<a class="ridecard" href="{ctx.link("ride/" + j["key"])}">{ride_thumb(site, ctx, j)}'
            f'<span class="ridecard-body"><span class="ridecard-when">{esc(j["years"])}</span>'
            f'<span class="ridecard-t">{esc(j["title"])}</span>'
            f'<span class="ridecard-one">{esc(j["one_line"])}</span>'
            f'<span class="ridecard-n">{n_stops} stops · {plural(n_psg, "passage")} on the road</span></span></a>')


def rides_sorted(site):
    def first_year(j):
        m = re.search(r"\d{4}", j["years"])
        return int(m.group(0)) if m else 0
    return sorted(site.journeys, key=first_year)


def page_rides(site, ctx):
    js = rides_sorted(site)
    cards = "".join(ride_card(site, ctx, j) for j in js)
    head = page_head("Ride with a traveler", "Pick a road and ride it",
                     "Six travelers. Six roads. Their words at every stop.",
                     ornament=orn(site, ctx, "rider", "head"))
    body = f'<div class="page">{head}<div class="ridecards">{cards}</div></div>'
    return dict(title="Ride with a traveler", description="Follow six travelers across Tartary stop by stop, from Changchun in 1220 to John Bell in 1722, and read what each one wrote at each place.",
                body=body, nav="ride")


def page_ride(site, ctx, j):
    r = site.rec[j["rec"]]
    rm = RideMap(j["stops"])
    legs = rm.legs(j["stops"])
    n = len(j["stops"])
    svg = (f'<svg class="ride-svg" viewBox="0 0 {rm.W:.0f} {rm.H:.1f}" role="img" aria-label="Map of the route, from {esc(j["stops"][0]["name"])} to {esc(j["stops"][-1]["name"])}">'
           f'<defs><path id="ride-land" d="{rm.land()}" fill-rule="evenodd" vector-effect="non-scaling-stroke"/></defs>'
           f'<rect class="sea" width="{rm.W:.0f}" height="{rm.H:.1f}"/>'
           f'<path class="grat" d="{rm.graticule()}" vector-effect="non-scaling-stroke"/>'
           # the coast is drawn four times: three widening shore lines in the water, then the land over them
           + "".join(f'<use class="shore s{k}" href="#ride-land"/>' for k in (3, 2, 1))
           + '<use class="land" href="#ride-land"/>'
           f'<path class="lake" d="{rm.lakes()}" vector-effect="non-scaling-stroke"/>'
           f'<path class="river" d="{rm.rivers()}" vector-effect="non-scaling-stroke"/>'
           + "".join(f'<path class="leg" data-leg="{i}" d="{d}" vector-effect="non-scaling-stroke"/>' for i, d in enumerate(legs))
           + "</svg>")
    dots, items = [], []
    for i, s in enumerate(j["stops"]):
        x, y = rm.xy(s["lon"], s["lat"])
        px, py = x / rm.W * 100, y / rm.H * 100
        ps = [site.psg[p] for p in s["psg"] if p in site.psg]
        cls = ("exact" if s.get("exact", True) else "rough") + (" has" if ps else "")
        cls += (" al" if px < 16 else " ar" if px > 84 else "") + (" lo" if py < 18 else " hi" if py > 84 else "")
        dots.append(f'<a class="rdot {cls}" href="#stop-{i + 1}" data-go="{i}" style="left:{px:.2f}%;top:{py:.2f}%" '
                    f'aria-label="Stop {i + 1}: {esc(s["name"])}"><span>{esc(s["name"])}</span></a>')
        where = [x for x in [s.get("modern"), None if s.get("exact", True) else "rough position"] if x]
        modern = f'<p class="ride-modern">{esc(" · ".join(where))}</p>' if where else ""
        block = psg_block(site, ctx, ps, 2, theme_tag=True, source=False) if ps else ""
        more = ""
        pid = s.get("place_id")
        if pid in site.place and len(site.psg_by_place.get(pid, [])) > len(ps):
            more = (f'<p class="ride-more"><a href="{ctx.link("place/" + pid)}">What others wrote about {esc(site.place[pid]["name"])}</a></p>')
        items.append(
            f'<li class="ride-stop{"" if ps else " way"}" id="stop-{i + 1}" data-i="{i}" data-x="{px:.2f}" data-y="{py:.2f}" tabindex="-1">'
            f'<div class="ride-k"><span class="ride-num">{i + 1}</span><span class="ride-when">{esc(s["when"] or "")}</span></div>'
            f'<h2>{esc(s["name"])}</h2>{modern}<p class="ride-say">{esc(no_em(s["say"]))}</p>{block}{more}</li>')
    n_stops, n_psg = ride_counts(site, j)
    others = "".join(ride_card(site, ctx, o) for o in rides_sorted(site) if o["key"] != j["key"])
    tale = tale_link(ctx.link(site.rkey(r)), *tale_meta(site, j["rec"])) if j["rec"] in site.profiles else ""
    rider = site.orn.get("rider")
    rider_html = f'<span class="ride-rider" data-rider hidden>{cut(site, ctx, rider, "ornaments")}</span>' if rider else '<span class="ride-rider plain" data-rider hidden></span>'
    stage = (f'<div class="ride-stage" data-stage><div class="ride-sheet" style="aspect-ratio:{rm.W:.0f}/{rm.H:.1f}">{svg}'
             f'<div class="ride-dots">{"".join(dots)}</div>{rider_html}</div>'
             f'<div class="ride-bar"><button type="button" class="btn icon" data-prev aria-label="The stop before" disabled>←</button>'
             f'<p class="ride-pos" data-pos aria-live="polite">{n} stops</p>'
             f'<button type="button" class="btn icon" data-next aria-label="The next stop">→</button></div></div>')
    head = (f'<header class="ride-head"><div class="eyebrow"><a href="{ctx.link("ride")}">Ride with a traveler</a></div>'
            f'<h1>{esc(j["title"])}</h1><p class="ride-who">{esc(j["who"])} · {esc(j["years"])}</p>'
            f'<p class="lede">{esc(no_em(j["about"]))}</p>'
            f'<p class="hero-actions"><a class="btn primary" href="#stop-1" data-begin>Begin the ride</a>'
            f'<a class="btn" href="{ctx.link(site.rkey(r))}">Meet the witness</a></p></header>')
    def plain(d):
        # the working notes name passages by number; a reader does not need the numbers
        d = re.sub(r"\(W\d{3}-\d+\)\s*", "", d)
        d = re.sub(r"\(W\d{3}-\d+, ", "(", d)
        return re.sub(r"\s*\bW\d{3}-\d+\b(,| and)?", "", d)
    doubts = ""
    if j.get("doubts"):
        doubts = (f'<details class="ride-doubts"><summary>What is still uncertain ({len(j["doubts"])} notes)</summary>'
                  f'<ul>{"".join("<li>" + esc(no_em(plain(d))) + "</li>" for d in j["doubts"])}</ul></details>')
    end = (f'<div class="ride-end"><h2>The road ends here</h2>'
           f'<p class="ride-note"><strong>How sure is the line?</strong> {esc(no_em(j["route_note"]))} The line joins the stops. It is not the exact road.</p>'
           f'{doubts}{tale}</div>')
    body = (f'<div class="page ride" data-module="ride">{head}'
            f'<div class="ride-body">{stage}<ol class="ride-stops">{"".join(items)}</ol></div>{end}'
            f'{orn_rule(site, ctx, "compass-star")}'
            f'<section class="band"><div class="band-head"><h2>Ride with someone else</h2></div><div class="ridecards">{others}</div></section></div>')
    desc = f'{j["one_line"]} Follow the route stop by stop and read {plural(n_psg, "passage")} from the book at the places they describe.'
    return dict(title=f'{j["title"]}: {j["who"]}, {j["years"]}', description=desc, body=body, nav="ride", modules=["ride"])


def playing_back(site, ctx):
    """The back of a card: a mapmaker's lettering over a compass, inside ruled borders."""
    wheel = site.orn.get("compass-wheel") or site.orn.get("compass-star")
    label = next((c for c in site.labels if c.get("wordmark")), None)
    inner = (cut(site, ctx, label, "labels", "pc-back-name") if label else "") + (cut(site, ctx, wheel, "ornaments", "pc-back-orn") if wheel else "")
    return f'<span class="pc-back" aria-hidden="true"><span class="pc-back-in">{inner}</span></span>'


def deck_stack(site, ctx, n=3):
    return "".join(f'<span class="pc pc-s{i}">{playing_back(site, ctx)}</span>' for i in range(n))


def page_deck(site, ctx):
    suits = {}
    for t, key in SUITS.items():
        c = site.orn.get(key)
        if c:
            suits[t] = {"k": key, "w": c["size"][0], "h": c["size"][1], "l": THEMES[t]["label"]}
    data = {"suits": suits, "spread": [{"n": n, "t": ts} for n, ts in SPREAD], "site": CONFIG["base_url"].split("//")[1]}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    slots = "".join(
        f'<div class="spread-slot" data-slot="{i}"><p class="spread-k">{esc(n)}</p><div class="spread-card" data-card></div></div>'
        for i, (n, _) in enumerate(SPREAD))
    n_good = sum(1 for p in site.passages if p["strength"] == 3)
    head = page_head("The deck", "Fortune favours the curious",
                     "One place. One people. One marvel. What will you find?")
    body = (f'<div class="page deck" data-module="deck"><script type="application/json">{js}</script>{head}'
            f'<div class="deck-table"><button type="button" class="deck-stack" data-deal aria-label="Deal three cards">{deck_stack(site, ctx)}'
            f'<span class="deck-stack-k">Deal three</span></button>'
            f'<div class="spread" data-spread>{slots}</div><p class="deck-table-legend">T H E &nbsp; T A R T A R Y &nbsp; C O L L E C T I O N</p></div>'
            f'<p class="deck-acts"><button type="button" class="btn primary" data-deal>Deal three more</button>'
            f'<button type="button" class="btn" data-turn>Turn them all</button></p>'
            f'<div class="deck-read" data-read aria-live="polite"></div>'
            f'<noscript><p class="muted">The deck needs the page script. <a href="{ctx.link("passages")}">Read the passages</a> instead.</p></noscript></div>')
    return dict(title="The deck: draw three passages", description=f"Draw three passages about Tartary at random from {num(n_good)} quoted sources: one place, one people, one marvel. Each card links to its page.",
                body=body, nav="passages", modules=["deck"])


def rides_band(site, ctx):
    js = rides_sorted(site)
    if not js:
        return ""
    picks = [j for j in js if j["key"] in ("changchun", "rubruck", "ides")] or js[:3]
    return (f'<section class="band"><div class="band-head row"><div><h2>Ride with a traveler</h2>'
            f'<p>Six roads across the centuries.</p></div>'
            f'<a class="btn" href="{ctx.link("ride")}">See all {len(js)} rides</a></div>'
            f'<div class="ridecards">{"".join(ride_card(site, ctx, j) for j in picks)}</div></section>')


def deck_band(site, ctx):
    return (f'<section class="band deck-door"><a class="deck-door-a" href="{ctx.link("deck")}">'
            f'<span class="deck-door-stack" aria-hidden="true">{deck_stack(site, ctx)}</span>'
            f'<span class="deck-door-body"><span class="deck-door-t">Draw three from the deck</span>'
            f'<span class="deck-door-p">One place, one people, one marvel, dealt at random from the record.</span>'
            f'<span class="btn primary">Deal me in</span></span></a></section>')


# ------------------------------------------------ The time dial

DIAL_Y0, DIAL_Y1 = 1250, 1900
DIAL_BREAK = (1500, 0.15)       # the years before 1500 take the first part of the scale: few maps, long wait
DIAL_FIRST = "delisle-1706"     # the sheet shown when the page script does not run
DIAL_KINDS = {"land": "A country", "people": "A people", "sea": "A sea"}
DIAL_GAP = 0.027                # no two stops sit closer on the scale than this share of its length
DIAL_FAM = {"tartary": "t", "great": "t", "muscovite": "m", "independent": "i", "chinese": "c", "western": "c", "eastern": "c", "little": "l", "other": "o"}
DIAL_BASIS = {"border": "an engraved border line", "colour": "the colouring of this copy", "lettering": "none is drawn, so the outline is a reading of where the name sits",
              "sheet": "none is drawn; the whole sheet is titled as a map of it"}
DIAL_NOT_COUNTRIES = {"Siachen Glacier"}
DIAL_TODAY = {"Kyrgyzstan", "Tajikistan", "Turkmenistan", "Azerbaijan", "Georgia"}   # small countries named on the bare earth all the same


def dial_pos(y):
    """Where a year sits on the scale, from 0 to 1."""
    yb, fb = DIAL_BREAK
    if y <= yb:
        return (y - DIAL_Y0) / (yb - DIAL_Y0) * fb
    return fb + (y - yb) / (DIAL_Y1 - yb) * (1 - fb)


class DialSheet:
    """The shared sheet of the real earth that every old map on the dial is bent onto: an equidistant conic of
    Asia. The same arithmetic as generator/dial_tools.py, which draws the bent sheets."""
    R = 6371.0
    P1, P2, P0, L0 = math.radians(30), math.radians(60), math.radians(46), math.radians(88)
    N = (math.cos(P1) - math.cos(P2)) / (P2 - P1)
    G = math.cos(P1) / N + P1
    RHO0 = R * (G - P0)
    KM = (-5000.0, -2900.0, 5000.0, 3350.0)
    W = 1600
    K = (KM[2] - KM[0]) / W
    H = round((KM[3] - KM[1]) / K)

    @classmethod
    def xy(cls, lon, lat):
        if lon < -60:
            lon += 360
        rho = cls.R * (cls.G - math.radians(lat))
        th = cls.N * (math.radians(lon) - cls.L0)
        return (rho * math.sin(th) - cls.KM[0]) / cls.K, (cls.KM[3] - (cls.RHO0 - rho * math.cos(th))) / cls.K

    @classmethod
    def path(cls, rings, close):
        m = 260
        out = []
        for ring in rings:
            pts = [cls.xy(p[0], p[1]) for p in ring if p[1] > -35]
            if len(pts) < 2 or max(p[0] for p in pts) < -m or min(p[0] for p in pts) > cls.W + m or max(p[1] for p in pts) < -m or min(p[1] for p in pts) > cls.H + m:
                continue
            run, last = [], None
            for x, y in pts:
                if last is None or abs(x - last[0]) + abs(y - last[1]) > 1.1:
                    run.append(f"{x:.1f} {y:.1f}")
                    last = (x, y)
            if len(run) >= (3 if close else 2):
                out.append("M" + "L".join(run) + ("Z" if close else ""))
        return "".join(out)

    @classmethod
    def land(cls):
        rings = []
        for g in RideMap.base()["land"]["geometries"]:
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for ring in poly:
                    lons = [p[0] for p in ring]
                    if max(lons) < -25 and min(lons) > -168:      # the Americas are off this sheet
                        continue
                    rings.append(ring)
        return cls.path(rings, True)

    @classmethod
    def lakes(cls):
        rings = []
        for f in RideMap.base()["lakes"]["features"]:
            g = f["geometry"]
            if g:
                for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                    rings += poly
        return cls.path(rings, True)

    @classmethod
    def rivers(cls):
        lines = []
        for f in RideMap.base()["rivers"]["features"]:
            g = f["geometry"]
            if g:
                lines += g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        return cls.path(lines, False)

    @classmethod
    def countries(cls):
        """Today's borders as one path, and the names of the larger countries with where to set them."""
        fs = json.loads((STATIC / "basemap" / "countries.json").read_text())["features"]
        rings, names = [], []
        for f in fs:
            g = f["geometry"]
            for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                rings += poly
            p = f["properties"]
            x, y = cls.xy(*p["at"])
            if 50 < x < cls.W - 50 and 30 < y < cls.H - 30 and ((p["rank"] <= 3 and p["km2"] >= 120000) or p["name"] in DIAL_TODAY):
                names.append((p["name"], x, y))
        return cls.path(rings, True), names

    @classmethod
    def graticule(cls):
        out = []
        for lon in range(20, 181, 20):
            out.append("M" + "L".join("%.1f %.1f" % cls.xy(lon, lat) for lat in range(0, 89, 4)))
        for lat in range(10, 81, 10):
            out.append("M" + "L".join("%.1f %.1f" % cls.xy(lon, lat) for lon in range(0, 201, 4)))
        return "".join(out)


def dial_stops(site):
    d = site.dial or {}
    stops = [dict(s, early=True) for s in d.get("early", [])] + [m for m in d.get("maps", []) if not m.get("off") and m.get("drawn")]
    return sorted(stops, key=lambda s: s["year"])


def dial_scale(stops):
    """Where a year sits on the scale, from 0 to 1. The years run evenly (see dial_pos), except that stops crowded
    into a few years are eased apart, so every mark can be seen and pressed."""
    ys = [DIAL_Y0] + sorted({s["year"] for s in stops}) + [DIAL_Y1]
    lin = [dial_pos(y) for y in ys]
    gaps = [b - a for a, b in zip(lin, lin[1:])]
    mins = [min(g, DIAL_GAP) if k in (0, len(gaps) - 1) else DIAL_GAP for k, g in enumerate(gaps)]
    spare = sum(max(0.0, g - m) for g, m in zip(gaps, mins))
    k = max(0.0, 1 - sum(mins)) / spare if spare else 0.0
    at, p = [0.0], 0.0
    for g, m in zip(gaps, mins):
        p += m + max(0.0, g - m) * k
        at.append(p)
    at = [v / at[-1] for v in at]

    def pos(y):
        if y <= ys[0]:
            return 0.0
        for (y0, p0), (y1, p1) in zip(zip(ys, at), zip(ys[1:], at[1:])):
            if y <= y1:
                return p0 + (p1 - p0) * (y - y0) / (y1 - y0)
        return 1.0
    return pos


def dial_names(m, group):
    """The lettering on a sheet, one entry per name: a name set on two lines is one name with two outlines."""
    out = collections.OrderedDict()
    for lb in m.get(group, []):
        if not lb.get("frame"):
            continue
        e = out.setdefault(lb["reads"], {"reads": lb["reads"], "plain": lb.get("plain") or "", "kind": lb.get("kind", "land"),
                                         "family": lb.get("family") or "", "parts": []})
        e["parts"].append(lb)
    return list(out.values())


def dial_fam(e):
    """The colour class of a name: by family for a country, one class for peoples and seas."""
    if e.get("kind", "land") != "land":
        return "f-p"
    return "f-" + DIAL_FAM.get(e.get("family") or "tartary", "o")


def dial_lands(m):
    """The ground a sheet gives to each Tartary name, largest first, so a small land is drawn over a large one."""
    lands = [ln for ln in m.get("lands", []) if ln.get("frame") and len(ln["frame"]) > 2]
    return sorted(lands, key=lambda ln: -ln.get("km2", 0))


def dial_size(km2):
    def f(v, unit):
        return f"{v / 1e6:.1f} million {unit}" if v >= 950000 else f"{num(int(round(v, -3)))} {unit}"
    return f"{f(km2, 'sq km')} ({f(km2 * 0.386102, 'sq mi')})"


def dial_today(land):
    """Today's countries under a land, in plain words."""
    groups = collections.OrderedDict((k, []) for k in ("all of", "most of", "about half of", "part of", "a corner of"))
    for c in land.get("today", []):
        f = c["of_country"]
        if c["name"] in DIAL_NOT_COUNTRIES or (f < 0.04 and c["of_land"] < 0.05):
            continue
        k = "all of" if f >= 0.9 else "most of" if f >= 0.6 else "about half of" if f >= 0.4 else "part of" if f >= 0.12 else "a corner of"
        groups[k].append(c["name"])

    def join(v):
        return v[0] if len(v) == 1 else ", ".join(v[:-1]) + " and " + v[-1]
    return "; ".join(f"{k} {join(v)}" for k, v in groups.items() if v)


def split_words(text, n):
    """A name set on n lines: its words shared out between the lines as evenly as they go."""
    words = text.split()
    if n <= 1 or len(words) < n:
        return [text] * max(1, n)
    out, rest = [], words
    for left in range(n, 1, -1):
        target = sum(len(w) for w in rest) / left
        take, got = 1, len(rest[0])
        while take < len(rest) - (left - 1) and abs(got + len(rest[take]) - target) < abs(got - target):
            got += len(rest[take])
            take += 1
        out.append(" ".join(rest[:take]))
        rest = rest[take:]
    out.append(" ".join(rest))
    return out


def poly_d(pts):
    return "M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + "Z"


def line_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def dial_tags(entries, W, H):
    """A small flag for each Tartary name on a sheet, saying it in plain English, set where it covers no other flag."""
    placed, out = [], []
    for key, e, cls in entries:
        text = e["plain"] or e["reads"]
        w, h = len(text) * 10.1 + 20, 30
        spots = []
        for lb in e["parts"]:
            fr, mid = lb["frame"], lb.get("mid") or lb["frame"]
            half = math.hypot(fr[0][0] - fr[-1][0], fr[0][1] - fr[-1][1]) / 2 + 7
            (sx, sy), (ex, ey) = mid[0], mid[-1]
            spots += [(sx, sy - half - h), (sx, sy + half), (ex - w, ey - half - h), (ex - w, ey + half)]
        best = None
        for x, y in spots:
            x, y = min(max(4, x), W - w - 4), min(max(4, y), H - h - 4)
            hit = any(x < px + pw + 4 and px < x + w + 4 and y < py + ph + 4 and py < y + h + 4 for px, py, pw, ph in placed)
            if best is None:
                best = (x, y)
            if not hit:
                best = (x, y)
                break
        placed.append((best[0], best[1], w, h))
        out.append(f'<g class="dtag {cls}" data-n="{key}" transform="translate({best[0]:.0f} {best[1]:.0f})"><g class="dtag-in"><rect width="{w:.0f}" height="{h}" rx="4"/>'
                   f'<text x="10" y="21" textLength="{w - 20:.0f}" lengthAdjust="spacing">{esc(text)}</text></g></g>')
    return "".join(out)


def dial_land_paths(m, small=False):
    """A sheet's lands as outlines: solid where the sheet draws or colours a limit, dashed where the limit is only
    a reading of the lettering, thin where one land lies inside another."""
    out = []
    for k, ln in enumerate(dial_lands(m)):
        cls = f'dland {dial_fam(ln)}{" loose" if ln.get("sure") == "loose" else ""}{" in" if ln.get("inside") else ""}'
        d = poly_d(ln["frame"])
        if small:
            out.append(f'<path class="{cls}" d="{d}"/>')
        else:
            out.append(f'<path class="dland-c" data-n="l{k}" d="{d}"/><path class="{cls}" data-n="l{k}" d="{d}"><title>{esc(ln.get("plain") or ln["name"])}</title></path>')
    return "".join(out)


def dial_thumb(site, ctx):
    """A small still of the dial for the doors that lead to it."""
    S = DialSheet
    m = next((s for s in dial_stops(site) if s["key"] == DIAL_FIRST), None)
    return (f'<svg class="dial-thumb" viewBox="0 0 {S.W} {S.H}" aria-hidden="true"><rect class="sea" width="{S.W}" height="{S.H}"/>'
            f'<path class="land" d="{S.land()}"/>{dial_land_paths(m or {}, small=True)}</svg>')


def dial_band(site, ctx):
    stops = dial_stops(site)
    if not stops:
        return ""
    n = sum(1 for s in stops if not s.get("early"))
    wheel = site.orn.get("compass-wheel")
    return (f'<section class="band dial-door"><a class="dial-door-a" href="{ctx.link("dial")}">'
            f'<span class="dial-door-pic">{dial_thumb(site, ctx)}{cut(site, ctx, wheel, "ornaments", "dial-door-wheel") if wheel else ""}</span>'
            f'<span class="dial-door-body"><span class="dial-door-t">Turn the dial</span>'
            f'<span class="dial-door-p">{n} old maps laid on the real earth, from {min(s["year"] for s in stops if not s.get("early"))} to {stops[-1]["year"]}. '
            f'Watch the word Tartary arrive, swell, split and fade, and see on today\'s map what ground each mapmaker gave it.</span>'
            f'<span class="btn primary">Watch the name move</span></span></a></section>')


def page_dial(site, ctx):
    S = DialSheet
    stops = dial_stops(site)
    maps = [s for s in stops if not s.get("early")]
    first = next((i for i, s in enumerate(stops) if s["key"] == DIAL_FIRST), len(stops) - 1)
    at = dial_scale(stops)
    land = S.land()
    # today's countries, for the bare earth under a lifted sheet
    today, today_t = S.countries()
    base = (f'<svg class="dial-earth" viewBox="0 0 {S.W} {S.H}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<defs><path id="dial-land" d="{land}" fill-rule="evenodd"/></defs>'
            f'<rect class="sea" width="{S.W}" height="{S.H}"/><path class="grat" d="{S.graticule()}"/>'
            + "".join(f'<use class="shore s{k}" href="#dial-land"/>' for k in (3, 2, 1))
            + f'<use class="land" href="#dial-land"/><path class="lake" d="{S.lakes()}"/><path class="river" d="{S.rivers()}"/>'
            + f'<g class="today"><path d="{today}"/>'
            + "".join(f'<text x="{x:.0f}" y="{y:.0f}">{esc(name)}</text>' for name, x, y in today_t) + '</g></svg>')
    sheets, names, cards, ticks, data, grid = [], [], [], [], [], []
    for i, s in enumerate(stops):
        pos = at(s["year"])
        on = " on" if i == first else ""
        who = s["who"]
        ticks.append(f'<button type="button" class="dial-stop{" early" if s.get("early") else ""}{on}" data-go="{i}" style="left:{pos * 100:.2f}%" '
                     f'aria-label="{esc(s["when"])}: {esc(who)}, {esc(s["sheet"])}"><span>{s["year"]}</span></button>')
        rec = site.rec.get(s.get("rec") or "")
        links = []
        g = [f'<g class="dial-g{on}" data-i="{i}">']
        if s.get("early"):
            data.append({"y": s["year"], "p": round(pos, 4), "w": s["when"], "by": who, "sheet": s["sheet"]})
            j = next((j for j in site.journeys if j["key"] == s.get("ride")), None)
            if j:
                line = "M" + "L".join("%.1f %.1f" % S.xy(st["lon"], st["lat"]) for st in j["stops"])
                x0, y0 = S.xy(j["stops"][0]["lon"], j["stops"][0]["lat"])
                far = max(j["stops"], key=lambda st: st["lon"])
                x1, y1 = S.xy(far["lon"], far["lat"])
                g.append(f'<path class="dial-road" d="{line}"/><circle class="dial-town" cx="{x0:.0f}" cy="{y0:.0f}" r="7"/>'
                         f'<circle class="dial-town" cx="{x1:.0f}" cy="{y1:.0f}" r="7"/>'
                         f'<text class="dial-town-t" x="{x1 + 14:.0f}" y="{y1 + 6:.0f}">{esc(far["name"])}</text>')
                links.append(f'<a class="btn primary" href="{ctx.link("ride/" + j["key"])}">Ride his road</a>')
            if rec:
                links.append(f'<a class="btn" href="{ctx.link(site.rkey(rec))}">{"Meet the witness" if rec["kind"] == "written" else "Open this map"}</a>')
            lists = ""
            fit = '<p class="dial-fit">No sheet lies on the earth at this stop.</p>' if not j else '<p class="dial-fit">The line joins the stops of his journey. It is not the exact road.</p>'
            unsure = ""
        else:
            data.append({"y": s["year"], "p": round(pos, 4), "w": s["when"], "by": who, "sheet": s["sheet"], "k": s["key"]})
            sheets.append(f'<img class="dial-sheet{on}" data-i="{i}" alt="" {"src" if i == first else "data-src"}="{ctx.asset("dial/" + s["key"] + ".webp")}" '
                          f'width="{S.W}" height="{S.H}" decoding="async">')
            tart, also, lands = dial_names(s, "labels"), dial_names(s, "also"), dial_lands(s)
            # the ground the sheet gives each name, under everything else
            g.append(dial_land_paths(s))
            # where the lettering stands on the sheet: an outline round it, and the same words set in plain type for the bare earth
            letters, defs = [], []
            for pre, entries in (("t", tart), ("a", also)):
                for n_i, e in enumerate(entries):
                    cls = dial_fam(e) if pre == "t" else "also"
                    words = split_words(e["reads"], len(e["parts"]))
                    for p_i, lb in enumerate(e["parts"]):
                        d = poly_d(lb["frame"])
                        g.append(f'<path class="dn-c{" also" if pre == "a" else ""}" data-n="{pre}{n_i}" d="{d}"/><path class="dn {cls}" data-n="{pre}{n_i}" d="{d}"><title>{esc(e["reads"])}</title></path>')
                        mid = lb.get("mid") or []
                        if len(mid) > 1:
                            fr = lb["frame"]
                            ln, tall = line_len(mid), math.hypot(fr[0][0] - fr[-1][0], fr[0][1] - fr[-1][1])
                            size = min(tall * 0.78, 54.0, ln / max(1, len(words[p_i])) / 0.6)
                            if size < 11:                       # too small to read on the bare earth; the flag and the list say it
                                continue
                            pid = f'dm{i}{pre}{n_i}-{p_i}'
                            defs.append(f'<path id="{pid}" d="M{"L".join(f"{x:.0f} {y:.0f}" for x, y in mid)}"/>')
                            letters.append(f'<text class="dlt {cls}" data-n="{pre}{n_i}" style="font-size:{size:.0f}px" dy="0.34em">'
                                           f'<textPath href="#{pid}" textLength="{ln * 0.97:.0f}" lengthAdjust="spacing">{esc(words[p_i])}</textPath></text>')
            g.append(f'<defs>{"".join(defs)}</defs>{"".join(letters)}')
            g.append(dial_tags([(f"t{n_i}", e, dial_fam(e)) for n_i, e in enumerate(tart)], S.W, S.H))

            def chips(entries, pre, also_cls=""):
                return "".join(
                    f'<li><button type="button" class="dial-name {also_cls or dial_fam(e)} k-{e["kind"]}" data-n="{pre}{k}"><b>{esc(e["reads"])}</b>'
                    f'<span>{esc(e["plain"])}</span></button></li>' for k, e in enumerate(entries))
            if tart:
                head_t = f'Tartary lettered {plural(len(tart), "time").replace("1 time", "once")} on this sheet'
                lists = f'<h3>{head_t}</h3><ul class="dial-names">{chips(tart, "t")}</ul>'
                if not [e for e in tart if e["kind"] == "land"]:
                    lists = f'<h3>No country called Tartary on this sheet</h3><p class="small muted">The word is left in {plural(len(tart), "small name")}:</p><ul class="dial-names">{chips(tart, "t")}</ul>'
            else:
                lists = '<h3>Tartary is not lettered on this sheet</h3>'
            if lands:
                rows = []
                for k, ln in enumerate(lands):
                    inside = next((o for o in lands if o["name"] == ln.get("inside")), None)
                    under = dial_today(ln)
                    rows.append(
                        f'<li><button type="button" class="dial-name land {dial_fam(ln)}{" loose" if ln.get("sure") == "loose" else ""}" data-n="l{k}">'
                        f'<b>{esc(ln.get("plain") or ln["name"])}</b><span class="dl-size">About {dial_size(ln["km2"])} of today\'s land'
                        f'{", inside " + esc(inside.get("plain") or inside["name"]) if inside else ""}</span>'
                        + (f'<span>On today\'s map: {esc(under)}.</span>' if under else "")
                        + f'<span>Its limit on the sheet: {DIAL_BASIS.get(ln.get("basis"), DIAL_BASIS["lettering"])}.</span></button></li>')
                lists += (f'<h3>The ground this sheet gives the name</h3><ul class="dial-names lands">{"".join(rows)}</ul>')
            elif tart:
                lists += '<p class="small muted">No country on this sheet carries the name, so there is no outline to draw.</p>'
            if also:
                lists += f'<h3 class="quiet">Other big names in the same country</h3><ul class="dial-names">{chips(also, "a", "also")}</ul>'
            dr = s["drawn"]
            fit = (f'<p class="dial-fit">Laid on the earth by {dr["places"]} matched places. Left out one at a time, a place lands about '
                   f'{num(dr["median_km"])} km from where it belongs; the worst lands {num(dr["worst_km"])} km off. That is the mapmaker\'s error, kept on purpose.</p>')
            if s.get("item"):
                links.append(f'<a class="btn" href="{esc(s["item"])}" rel="noopener">The whole sheet at the Library of Congress</a>')
            if rec:
                links.append(f'<a class="btn" href="{ctx.link(site.rkey(rec))}">This map in the atlas</a>')
            notes = s.get("uncertain") or []
            unsure = ""
            if notes:
                unsure = (f'<details class="dial-doubts"><summary>What is uncertain ({plural(len(notes), "note")})</summary>'
                          f'<ul>{"".join("<li>" + esc(no_em(x)) + "</li>" for x in notes)}</ul></details>')
            # the same sheet as a small still, for the wall of outlines under the dial
            big = lands[0] if lands else None
            cap = (f'{esc(big.get("plain") or big["name"])}, {dial_size(big["km2"]).split(" (")[0]}'
                   + (f' and {len(lands) - 1} more' if len(lands) > 1 else "")) if big else "No country called Tartary"
            grid.append(f'<li><a class="dial-cell{"" if big else " none"}" href="#dial-{s["year"]}" data-go="{i}">'
                        f'<svg viewBox="0 0 {S.W} {S.H}" aria-hidden="true"><rect class="sea" width="{S.W}" height="{S.H}"/><use class="land" href="#dial-land"/>'
                        f'{dial_land_paths(s, small=True)}</svg>'
                        f'<span class="dial-cell-y mono">{esc(s["when"])}</span><span class="dial-cell-w">{esc(who)}</span><span class="dial-cell-c">{cap}</span></a></li>')
        g.append("</g>")
        names.append("".join(g))
        title = s.get("title")
        as_lettered = f'<p class="dial-title">{esc(short_title(title, 150))}</p>' if title and not s.get("early") else ""
        cards.append(
            f'<article class="dial-card{on}" data-i="{i}" id="dial-{s["year"]}"><div class="dial-card-main">'
            f'<p class="eyebrow"><span class="mono">{esc(s["when"])}</span> · {esc(who)} · {esc(s["sheet"])}</p>'
            f'<h2>{esc(s["head"])}</h2>{as_lettered}<p class="dial-says">{esc(no_em(s["says"]))}</p>'
            f'<p class="dial-links">{"".join(links)}</p>{fit}{unsure}</div>'
            f'<div class="dial-card-side">{lists}</div></article>')
    # the ruled scale under the sheet
    marks = []
    for y in range(DIAL_Y0, DIAL_Y1 + 1, 10):
        big = y % 100 == 0 or y == DIAL_Y0
        if y < DIAL_BREAK[0] and y % 50:
            continue
        marks.append(f'<i class="{("big e" if DIAL_Y0 < y < DIAL_BREAK[0] else "big") if big else ("mid" if y % 50 == 0 else "")}" style="left:{at(y) * 100:.2f}%">{f"<b>{y}</b>" if big else ""}</i>')
    wheel = site.orn.get("compass-wheel") or site.orn.get("compass-star")
    knob = cut(site, ctx, wheel, "ornaments", "dial-wheel") if wheel else ""
    cur = stops[first]
    js = json.dumps({"stops": data, "first": first}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    stage = (f'<div class="dial-stage" data-stage style="aspect-ratio:{S.W}/{S.H}">{base}'
             f'<div class="dial-sheets" data-sheets>{"".join(sheets)}</div>'
             f'<svg class="dial-over" viewBox="0 0 {S.W} {S.H}" preserveAspectRatio="xMidYMid slice" data-over>{"".join(names)}</svg>'
             f'<p class="dial-year" data-year aria-hidden="true">{cur["year"]}</p>'
             f'<p class="dial-tip" data-tip hidden></p></div>')
    scale = (f'<div class="dial-scale"><p class="dial-scale-label sr-only" id="dial-help">Drag the compass, choose a mark, or use the arrow keys.</p><div class="dial-track" data-track>'
             f'<div class="dial-rule" aria-hidden="true">{"".join(marks)}</div>{"".join(ticks)}'
             f'<div class="dial-knob" data-knob role="slider" tabindex="0" aria-label="Historical stop" aria-describedby="dial-help" aria-valuemin="1" aria-valuemax="{len(stops)}" '
             f'aria-valuenow="{first + 1}" aria-valuetext="{esc(cur["when"])}, {esc(cur["who"])}" style="left:{at(cur["year"]) * 100:.2f}%">{knob}</div></div>'
             f'<p class="dial-scale-note">Dates mark individual sources; transitions are crossfades.</p></div>')
    options = "".join(f'<option value="{i}"{" selected" if i == first else ""}>{esc(s["when"])} · {esc(s["who"])} · {esc(s["sheet"])}</option>' for i, s in enumerate(stops))
    console = (f'<aside class="dial-console" aria-label="Time dial controls">'
               f'<div class="dial-current" role="status" aria-live="polite" aria-atomic="true">'
               f'<p class="eyebrow" data-count>Stop {first + 1} of {len(stops)}</p>'
               f'<p class="dial-current-year" data-current-year>{esc(cur["when"])}</p>'
               f'<h2 data-current-maker>{esc(cur["who"])}</h2><p class="dial-current-sheet" data-current-sheet>{esc(cur["sheet"])}</p></div>'
               f'<label class="dial-select-label" for="dial-select">Choose a map or early account</label>'
               f'<select id="dial-select" data-select>{options}</select>'
               f'<div class="dial-bar"><button type="button" class="btn icon" data-prev aria-label="Previous stop">←</button>'
               f'<button type="button" class="btn primary" data-play aria-pressed="false">Let it run</button>'
               f'<button type="button" class="btn icon" data-next aria-label="Next stop">→</button></div>'
               f'<div class="dial-toggles"><button type="button" class="pill" data-lift aria-pressed="false">Lift the old sheet</button>'
               f'<button type="button" class="pill" data-ghost aria-pressed="false">Keep earlier outlines</button></div>'
               f'<p class="dial-view-state" data-view-state></p>'
               f'<p class="dial-transition" data-transition hidden>Turning between sources. No intervening map is shown.</p>'
               f'<p class="dial-load-state" data-load-state role="status" hidden></p></aside>')
    legend = ('<p class="dial-legend"><span><i class="sw t"></i>The word Tartary, where it is lettered</span>'
              '<span><i class="sw l"></i>The ground the sheet gives it, by a drawn or coloured limit</span>'
              '<span><i class="sw l loose"></i>The same, where no limit is drawn: a reading of the lettering</span>'
              '<span><i class="sw p"></i>Tartars, as a people or a sea</span>'
              '<span><i class="sw a"></i>Other big names</span><span class="muted">Press a name to find it. Lift the sheet to see the outlines on today\'s map.</span></p>')
    head = page_head("The many Tartarys in motion", "Turn the dial",
                     f"{len(maps)} maps. {maps[0]['year']} to {maps[-1]['year']}. A name in motion.",
                     ornament=orn(site, ctx, "compass-star", "head"))
    n_lands = sum(len(dial_lands(m)) for m in maps)
    wall = (f'<section class="dial-all"><h2>Every outline, side by side</h2>'
            f'<p>The ground each sheet gives to a country called Tartary, drawn on today\'s map. {len(maps)} sheets, {n_lands} outlines, and they do not agree. '
            f'Press one to turn the dial to it.</p><ol class="dial-grid">{"".join(grid)}</ol></section>')
    how = (f'<details class="section dial-how"><summary>Inside the instrument: sources &amp; method</summary>'
           f'<p>Each sheet is a Library of Congress picture of a printed map. On every one, between {min(m["drawn"]["places"] for m in maps)} and {max(m["drawn"]["places"] for m in maps)} '
           f'places were matched by an AI reader to where they really are: river mouths, capes, lakes and towns the mapmaker could have known from report. '
           f'The sheet was then bent, stiffly, so those places fall as near their true spots as the sheet allows. A stiff bend keeps the map looking like itself, '
           f'so its mistakes stay visible: an oval Caspian, a Siberia squeezed short, towns from Marco Polo set down by guess.</p>'
           f'<p>The boxes mark where the word is lettered, traced on each sheet and carried across with it. The larger outlines mark the ground the sheet gives to each '
           f'country called Tartary. Where the mapmaker engraved a border line, or the sheet is coloured country by country, the outline follows that and is drawn solid. '
           f'Where he drew no limit at all, the outline is a reading of how far the lettering reaches, carried to the nearest coast, river or neighbouring name, and is drawn dashed. '
           f'Hand colour was added copy by copy, so an outline that follows colour is true of this copy only. The sizes count only today\'s dry land under each outline, '
           f'and are as rough as the sheet: where a map rests on hearsay, the outline is only as good as the map.</p>'
           f'<p>Between two stops the dial fades one sheet into the next; nothing is known about the years in between, and where several maps crowd into a few years '
           f'the scale is eased apart so each can be reached. '
           f'No person has checked the matched places, the readings or the outlines yet. '
           f'<a href="{ctx.link("labels")}">The many Tartarys</a> counts every map and book in the atlas that uses each name, and '
           f'<a href="{ctx.link("method")}">How it was made</a> explains the rest.</p></details>')
    body = (f'<div class="page dial-page">{head}<div class="dial" data-module="dial"><script type="application/json">{js}</script>'
            f'<div class="dial-workbench"><div class="dial-map-panel">{stage}<p class="dial-pan-hint">Slide the map sideways to explore the whole sheet.</p>{scale}</div>{console}</div>'
            f'<p class="dial-reading-note">Read these as mapmakers’ claims. Solid outlines follow drawn or coloured limits; dashed outlines interpret the lettering. The readings and outlines await human review.</p>'
            f'{legend}<div class="dial-cards">{"".join(cards)}</div>{wall}</div>{how}</div>')
    desc = (f"Watch the word Tartary (Tartaria) move across {len(maps)} old maps laid on the real earth, from {maps[0]['year']} to {maps[-1]['year']}: "
            f"where each mapmaker lettered it, what ground he gave it on today's map, how it split into Muscovite, Independent and Chinese Tartary, and when it left the map.")
    return dict(title="Turn the dial: Tartary on the map, year by year", description=desc, body=body, nav="dial", modules=["dial"])


# ------------------------------------------------ About, Method, Corrections

def page_about(site, ctx):
    c = CONFIG
    pieces = "".join(
        f'<li><a href="{ctx.link(site.rkey(o["rec"]))}">{cut(site, ctx, o, "ornaments", label=o["what"])}'
        f'<span class="hand-by">{esc(cut_credit(site, o))}</span></a></li>' for o in site.orn.values())
    kit = f'<ul class="kit">{pieces}</ul>' if pieces else ""
    body = f'''<div class="page">{page_head("About", "About the atlas")}
<div class="prose">
<p>The Tartary Atlas gathers what the historical record says about Tartary: what the sources describe, where, when, and how each author came to know what they wrote. It covers {len(site.records)} written sources and maps in more than a dozen languages, from Old Turkic inscriptions and Mongol-era travel accounts to nineteenth-century atlases.</p>
<p>Tartary, printed as Tartaria on Latin maps, has lately become the subject of popular claims about a lost Tartarian Empire. The atlas is built so anyone can test a claim against the sources themselves.</p>
<h2>Who made it</h2>
<p>The atlas is a research project by {esc(c["researcher"])}, host of the <a href="{esc(c["podcast_url"])}" rel="noopener">{esc(c["podcast_name"])}</a>, where the research behind it is discussed. It was built with AI research assistance, and everything links back to its source so the work can be checked.</p>
<h2>Where to begin</h2>
<ul>
<li><a href="{ctx.link("passages")}">In their words</a>: {num(len(site.passages))} passages on cities, buildings, daily life, the name and strange tales, each with its quote and its page.</li>
<li><a href="{ctx.link("sources")}">Witnesses</a>: who wrote each source, how they knew, and what to watch out for.</li>
<li><a href="{ctx.link("maps")}">Map room</a>: {len(site.map_img)} old maps you can open and look into.</li>
<li><a href="{ctx.link("map")}">Wander the map</a>: click a place, read what was written about it.</li>
<li><a href="{ctx.link("archive")}">The vault</a>: the many Tartarys, who counted as a Tartar, who copied whom, and the full lists.</li>
<li><a href="{ctx.link("method")}">How it was made</a>: every label and limit, spelled out.</li>
</ul>
<h2>Spot a mistake?</h2>
<p>The atlas takes corrections and new sources in public. <a href="{ctx.link("corrections")}">Send one in</a>.</p>
<h2>The lettering and the ornaments</h2>
<p>The name at the top of every page is cut from one of the maps, and a different map lends its lettering on each visit. The small drawings between sections are cut from the maps too. Only the ink is kept, so each piece takes the colour of the page. Nothing here was drawn for the atlas.</p>
</div>{kit}</div>'''
    return dict(title="About the atlas", description="What The Tartary Atlas is, who made it, and how to use it.", body=body, nav="about")


def page_method(site, ctx):
    m = site.meta["counts"]
    ev_rows = "".join(f"<li><strong>{esc(k)}.</strong> {esc(v)} <span class=\"muted\">({sum(1 for r in site.records if r['evidence_class'] == k)} records)</span></li>" for k, v in EVIDENCE.items())
    basis_rows = "".join(f"<li>{basis_dot(g)} <strong>{esc(v[0])}.</strong> {esc(v[1])}</li>" for g, v in BASIS.items())
    prec_rows = "".join(f"<li><strong>{esc(v)}</strong> <span class=\"muted\">({esc(k)})</span></li>" for k, v in PRECISION.items() if not k.startswith("century (") )
    n_approx = sum(1 for p in site.places if basis_group(p["coord_basis"]) in ("approx", "anchor"))
    n_notes = sum(1 for r in site.records if r["date"].get("override"))
    chk = collections.Counter(p["check"] for p in site.passages)
    n_read, n_written, n_profile_only = reading_progress(site)
    n_tr = sum(1 for p in site.passages if p.get("translation"))
    basis_rows_p = "".join(f"<li>{basis_chip(k)} {esc(v[1])} <span class='muted'>({num(sum(1 for p in site.passages if p['basis'] == k))} passages)</span></li>" for k, v in PBASIS.items())
    passages_method = f'''<h2>The passages</h2>
<p>The passages are a reading layer on top of the catalogue. {n_read + n_profile_only} of the {n_written} written sources have a plain-words profile, and the {n_read} whose text the project holds were read for passages: the scanned pages that mention Tartars or Tartary were read with AI assistance, and the passages that say something specific were kept and sorted into five trails. The richest sources were read closely and the rest lightly, so the passages are a selection, never everything a source says. The other {n_profile_only} have a profile only, because their text is not held here or the stored scan could not be searched.</p>
<ul>
<li><strong>The quote</strong> is copied from the page it cites, in the original language, and kept to 70 words or fewer. Spelling is tidied only where the scan's machine-read text was broken (long s, split words, garbled letters).</li>
<li><strong>The translation</strong>, where the page is not in English, is a working translation made for this atlas ({num(n_tr)} passages). It is a guide to the original, which is always shown with it.</li>
<li><strong>The summary</strong> above each quote is the atlas's own plain-words account of what the page says.</li>
<li><strong>The page link</strong> opens the scan at the page quoted. Read the page before citing a passage.</li>
</ul>
<p>Each passage carries a label for how the author knew that one thing, which can differ from the source as a whole:</p>
<ul style="list-style:none;padding-left:0">{basis_rows_p}</ul>
<p><strong>Checking the quotes.</strong> Every quote was compared by machine with the stored text of the page it cites. {num(chk["page"])} of {num(len(site.passages))} match their page. {num(chk["image"])} were transcribed from the page image because the stored text of that scan is unreadable (blackletter, Fraktur and Arabic-script prints mostly), and each of those says so. {num(chk["partial"])} could not be confirmed automatically because the stored text is damaged, and each carries a note asking you to check the page. No passage has yet been checked line by line by a human editor.</p>'''
    body = f'''<div class="page">{page_head("The vault", "How it was made")}
<div class="prose">
<h2>Three layers of data</h2>
<ul>
<li><strong>The catalogue.</strong> {m["records"]} records: {m["written"]} written sources (IDs W001 to W303) and {m["maps"]} maps (M001 to M119), each with a card describing its date, places, peoples, access, and how its author knew. The catalogue was compiled from library, archive and scholarly catalogues in English, Latin, Italian, Spanish, Portuguese, French, Dutch, German, Russian, Persian, Arabic, Ottoman Turkish, Chagatai, Tatar, Chinese, Manchu, Mongolian, Tibetan and Japanese.</li>
<li><strong>The site data.</strong> Structured dates, a gazetteer of {m["places"]} places ({m["places_plotted"]} with a point), {m["peoples"]} peoples and polities, an evidence class for every record, {m["lineage_edges"]} map lineage links, and IIIF image routes for {m["maps_with_iiif"]} maps. Built {esc(site.meta["built"])}.</li>
<li><strong>The passages.</strong> {num(len(site.passages))} short extracts from {len(site.profiles)} of the written sources, sorted into five trails. See the next section.</li>
<li><strong>Passage attestations</strong> (in preparation). Every place a source names Tartary or a related term, with page, original wording and what it refers to. This layer will replace the provisional card-level readings on <a href="{ctx.link("meanings")}">What “Tartar” meant</a>.</li>
</ul>
{passages_method}
<h2>The rides</h2>
<p><a href="{ctx.link("ride")}">Ride with a traveler</a> sets {len(site.journeys)} journeys out stop by stop. Each route was written with AI assistance from the passages and the standard account of the journey, then checked a second time against the edition the atlas cites, and the dates follow that edition. A passage sits at a stop only when the traveler saw, heard or wrote it at or about that place on that journey. The rest of the source's passages stay on its own page. Camps that moved and places scholars still argue over are drawn as rough positions, and every ride ends with a list of what is still uncertain. The line joins the stops and is not the exact road. No route has yet been checked by a human editor.</p>
<h2>Dates</h2>
<p>Every record carries the date it was written or drawn, and a precision label saying how far to trust it. Written sources also carry the period they describe. A map may carry a later impression year, a modern facsimile year, or a content date when it prints much older geography, as a 1482 Ptolemy printing does. The map and the timelines use the date made.</p>
<ul>{prec_rows}</ul>
<p>{n_notes} records carry a dating note explaining a manual decision. One record, the Rossi “Marco Polo” sheet (M029), has no accepted date and is never plotted on a timeline.</p>
<h2>How places are plotted</h2>
<p>Each place carries a coordinate basis, and the map draws each basis differently so an approximate point never looks surveyed. {n_approx} points are editorial approximations or label positions.</p>
<ul style="list-style:none;padding-left:0">{basis_rows}</ul>
<p>The basemap shows modern coastlines, lakes and rivers from Natural Earth. The Aral Sea appears at its modern, shrunken extent. Historical regions are points only for now; outlines are a later job.</p>
<h2>How the author knew</h2>
<p>Every record is sorted by the evidence its card describes. The card's own wording travels with the class on each record page, so the sorting can be checked.</p>
<ul>{ev_rows}</ul>
<h2>Map lineage</h2>
<p>A lineage link is <strong>stated</strong> when a catalogue or the map itself names the source, and <strong>probable</strong> when the evidence is strong but indirect. Probable links are drawn dashed.</p>
<h2>What the atlas does not claim</h2>
<ul>
<li>A place or people appears on a record only when its catalogue card names it. A place the source discusses but the card does not name is missing.</li>
<li>Search the atlas for a name and find nothing, and that proves only that the catalogue has not recorded it.</li>
<li>The catalogue records what the sources say, where, and in what form. It draws no conclusion about Tartary beyond what each source shows.</li>
</ul>
</div></div>'''
    return dict(title="How it was made", description="How The Tartary Atlas dates sources, plots places, sorts evidence and traces map lineage.", body=body, nav="method")


def page_corrections(site, ctx):
    c = CONFIG
    items = []
    for k in site.corrections:
        srcs = "".join(f'<li><a href="{esc(s["url"])}" rel="noopener">{esc(s["title"])}</a></li>' for s in k.get("sources", []))
        items.append(
            f'<li class="panel" style="list-style:none"><div class="eyebrow">{esc(k["date"])} · {esc(k["id"])}</div>'
            f'<p><a href="{ctx.link(site.rkey(k["record"]))}">{esc(k["record"])}</a>: {esc(k["summary"])}</p>'
            f'<p class="small muted">Was: “{esc(k["find"])}”</p><p class="small muted">Now: “{esc(k["replace"])}”</p>'
            + (f'<ul class="note-list small">{srcs}</ul>' if srcs else "") + "</li>")
    log = f'<ol style="padding:0;display:grid;gap:12px">{"".join(items)}</ol>' if items else '<p class="muted">No corrections yet.</p>'
    body = f'''<div class="page">{page_head("The vault", "Spot a mistake?")}
<div class="prose">
<p>The atlas corrects itself in public. If a date, place, reading or link is wrong, or a source is missing, send it in and the fix will be logged below with its evidence.</p>
<h2>How to send a correction</h2>
<ul>
<li>Open an issue on the <a href="{esc(c["repo_url"])}/issues" rel="noopener">atlas repository</a>.</li>
<li>Give the atlas number (for example W122 or M081), what is wrong, and a link to a source that shows it.</li>
<li>To suggest a new source, give its title, date, and a link to a scan or catalogue entry.</li>
</ul>
<h2>Corrections made so far</h2>
</div>{log}</div>'''
    return dict(title="Corrections", description="How to correct The Tartary Atlas, and the public log of corrections made.", body=body, nav="corrections")


# ---------------------------------------------------------------- layout

TO_TOP = '<button type="button" class="totop" data-totop hidden><span aria-hidden="true">↑</span> Top</button>'


def wordmark(site, ctx):
    """The name in the header is set in lettering cut from the maps themselves, and the page script picks a
    different map's lettering on each visit (TA.wordmark). Without the cuts, or without script, it is plain type."""
    marks = [c for c in site.labels if c.get("wordmark")]
    if not marks:
        return f'<a class="wordmark" href="{ctx.link("")}"><span>The</span> Tartary Atlas</a>'
    first = marks[0]
    data = [{"k": c["key"], "r": c["reads"], "c": cut_credit(site, c), "m": c["rec"], "w": c["size"][0], "h": c["size"][1]} for c in marks]
    data_json = esc(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return (f'<div class="wm" data-wordmarks="{data_json}">'
            f'<a class="wordmark" href="{ctx.link("")}" aria-label="The Tartary Atlas, front page"><span aria-hidden="true">The</span>'
            f'<span class="wm-name" data-wm-name>{cut(site, ctx, first, "labels")}</span><span aria-hidden="true">Atlas</span></a>'
            f'<a class="wm-credit" data-wm-credit href="{ctx.link(site.rkey(first["rec"]))}">'
            f'lettered by {esc(cut_credit(site, first))}</a></div>')


def header(site, ctx, nav_key):
    return experience.header(ctx, nav_key)


def footer(site, ctx):
    c = CONFIG
    return (f'<footer class="site-footer">{orn(site, ctx, "compass-wheel", "foot")}<div class="inner"><span>The Tartary Atlas, a research project by {esc(c["researcher"])}</span>'
            f'<a href="{esc(c["podcast_url"])}" rel="noopener">Discussed on the {esc(c["podcast_name"])}</a>'
            f'<a href="{ctx.link("archive")}">The vault</a><a href="{ctx.link("method")}">How it was made</a><a href="{ctx.link("corrections")}">Spot a mistake?</a>'
            f'</div></footer>')


def full_title(pg):
    if pg.get("bare_title"):
        return pg["title"]
    return f'{pg["title"]} · {CONFIG["site_name"]}'


def static_page(site, key, pg):
    ctx = Ctx("static", key)
    title = full_title(pg)
    # Keep each redesigned page's markup and controls together in returning browsers.
    revision = "?v=cabinet-1"
    url = f'{CONFIG["base_url"]}/{key + "/" if key else ""}'
    head = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(pg["description"])}">',
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(pg["description"])}">',
        f'<meta property="og:type" content="website"><meta property="og:url" content="{url}"><meta property="og:site_name" content="{CONFIG["site_name"]}">',
        '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{CONFIG["fonts"]}">',
        f'<link rel="stylesheet" href="{ctx.asset("site.css")}{revision}">',
    ]
    if pg.get("maplibre"):
        head.append(f'<link rel="stylesheet" href="{ctx.asset("maplibre-gl.css")}">')
        head.append(f'<script src="{CONFIG["maplibre_js"]}" defer></script>')
    if pg.get("osd"):
        head.append(f'<script src="{CONFIG["osd_js"]}" defer></script>')
    if pg.get("homepage"):
        head.append(f'<link rel="stylesheet" href="{ctx.asset("home.css")}{revision}">')
    head.append(f'<link rel="stylesheet" href="{ctx.asset("cabinet.css")}{revision}">')
    if pg.get("storybook"):
        head.append(f'<link rel="stylesheet" href="{ctx.asset("storybook.css")}?v=storybook-5">')
        head.append(f'<script src="{ctx.asset("storybook.js")}?v=storybook-4" defer></script>')
    head.append('<script>document.documentElement.className += " js";</script>')
    if not pg.get("storybook"):
        head.append(f'<script src="{ctx.asset("site.js")}{revision}" defer></script>')
        head.append(f'<script src="{ctx.asset("cabinet.js")}{revision}" defer></script>')
    if pg.get("jsonld"):
        head.append('<script type="application/ld+json">' + json.dumps({k: v for k, v in pg["jsonld"].items() if v is not None}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    head.append("</head>")
    home_class = ' class="atlas-home cabinet"' if pg.get("homepage") else ' class="cabinet"'
    if pg.get("storybook"):
        body = f'<body data-root="{ctx.root}" class="cabinet storybook-home"><a class="skip" href="#main">Skip to the book</a><main id="main" tabindex="-1">{pg["body"]}</main>{storybook.footer(ctx)}</body></html>'
    else:
        body = f'<body data-root="{ctx.root}"{home_class}>{header(site, ctx, pg["nav"])}<main id="main" tabindex="-1">{pg["body"]}</main>{footer(site, ctx)}{TO_TOP}{experience.dialogs(ctx)}</body></html>'
    return "".join(head) + body


def all_pages(site, ctx_factory):
    """Yield (key, page dict) for every page. ctx_factory(key) builds the link context."""
    yield "", page_home(site, ctx_factory(""))
    yield "frontispiece", page_frontispiece(site, ctx_factory("frontispiece"))
    yield "passages", page_passages(site, ctx_factory("passages"))
    for t in THEMES:
        k = "passages/" + t
        yield k, page_passages(site, ctx_factory(k), t)
    for k, fn in [("maps", page_maps), ("map", page_map), ("sources", page_sources), ("archive", page_archive), ("records", page_records), ("places", page_places), ("peoples", page_peoples),
                  ("labels", page_labels), ("meanings", page_meanings), ("lineage", page_lineage),
                  ("about", page_about), ("method", page_method), ("corrections", page_corrections)]:
        yield k, fn(site, ctx_factory(k))
    yield "deck", page_deck(site, ctx_factory("deck"))
    if dial_stops(site):
        yield "dial", page_dial(site, ctx_factory("dial"))
    if site.journeys:
        yield "ride", page_rides(site, ctx_factory("ride"))
        for j in site.journeys:
            k = "ride/" + j["key"]
            yield k, page_ride(site, ctx_factory(k), j)
    for r in site.records:
        k = site.rkey(r)
        yield k, page_record(site, ctx_factory(k), r)
    for p in site.places:
        k = "place/" + p["id"]
        yield k, page_place(site, ctx_factory(k), p)
    for p in site.peoples:
        k = "peoples/" + p["id"]
        yield k, page_people(site, ctx_factory(k), p)


def write_static(site):
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    keys = []
    for key, pg in all_pages(site, lambda k: Ctx("static", k)):
        d = OUT / key if key else OUT
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(static_page(site, key, pg))
        keys.append(key)
    shutil.copy(STATIC / "css" / "site.css", OUT / "assets" / "site.css")
    shutil.copy(STATIC / "css" / "home.css", OUT / "assets" / "home.css")
    shutil.copy(STATIC / "textures" / "home-parchment.webp", OUT / "assets" / "home-parchment.webp")
    shutil.copy(STATIC / "js" / "site.js", OUT / "assets" / "site.js")
    shutil.copy(STATIC / "vendor" / "maplibre-gl.css", OUT / "assets" / "maplibre-gl.css")
    if (STATIC / "cuts").exists():
        shutil.copytree(STATIC / "cuts", OUT / "assets" / "cuts")
    if (STATIC / "dial").exists():
        shutil.copytree(STATIC / "dial", OUT / "assets" / "dial")
    shutil.copy(STATIC / "css" / "cabinet.css", OUT / "assets" / "cabinet.css")
    shutil.copy(STATIC / "js" / "cabinet.js", OUT / "assets" / "cabinet.js")
    shutil.copy(STATIC / "css" / "storybook.css", OUT / "assets" / "storybook.css")
    shutil.copy(STATIC / "js" / "storybook.js", OUT / "assets" / "storybook.js")
    shutil.copytree(STATIC / "storybook", OUT / "assets" / "storybook")
    shutil.copy(STATIC / "textures" / "scholars-desk.webp", OUT / "assets" / "scholars-desk.webp")
    (OUT / "assets" / "search-index.json").write_text(experience.search_index(site))
    write_basemap(OUT / "assets" / "basemap.json")
    write_passage_assets(site, OUT / "assets")
    (OUT / "assets" / "eurasia.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg">{build_land_svg()}</svg>')
    (OUT / ".nojekyll").write_text("")
    (OUT / "CNAME").write_text(CONFIG["base_url"].split("//")[1] + "\n")
    (OUT / "robots.txt").write_text(f'User-agent: *\nAllow: /\nSitemap: {CONFIG["base_url"]}/sitemap.xml\n')
    urls = "".join(f'<url><loc>{CONFIG["base_url"]}/{k + "/" if k else ""}</loc></url>' for k in keys)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    (OUT / "404.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Page not found · {CONFIG["site_name"]}</title><link rel="stylesheet" href="/assets/site.css"></head>'
        f'<body><main class="page lost">{orn(site, Ctx("static", ""), "merfolk").replace("./assets/", "/assets/")}'
        '<h1>Off the edge of the map</h1><p class="lede">That page is not in the atlas. <a href="/">Back to the front door</a>, or <a href="/passages/">read the passages</a>.</p></main></body></html>')
    return keys


def write_basemap(path):
    bm = {n: json.loads((STATIC / "basemap" / f"{n}.json").read_text()) for n in ("land", "lakes", "rivers")}
    path.write_text(json.dumps(bm, separators=(",", ":")))


def write_preview(site):
    if PREVIEW.exists():
        shutil.rmtree(PREVIEW)
    (PREVIEW / "assets").mkdir(parents=True)
    pages = {}
    for key, pg in all_pages(site, lambda k: Ctx("preview", k)):
        pages[key] = {"t": full_title(pg), "h": pg["body"], "n": nav_group(pg["nav"])}
    ctx = Ctx("preview", "")
    css = (STATIC / "vendor" / "maplibre-gl.css").read_text() + "\n" + (STATIC / "css" / "site.css").read_text().replace('url("home-parchment.webp")', 'url("assets/home-parchment.webp")')
    css += "\n" + (STATIC / "css" / "home.css").read_text().replace('url("home-parchment.webp")', 'url("assets/home-parchment.webp")')
    js = (STATIC / "js" / "site.js").read_text()
    pages_json = json.dumps(pages, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    doc = (f'<meta charset="utf-8"><title>Tartary Atlas Preview</title>\n'
           f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           f'<link rel="stylesheet" href="{CONFIG["fonts"]}">'
           f'<style>{css}</style>'
           f'<script src="{CONFIG["maplibre_js"]}"></script><script src="{CONFIG["osd_js"]}"></script>'
           f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">{build_land_svg()}</svg>'
           f'{header(site, ctx, "")}<main id="main" tabindex="-1"></main>{footer(site, ctx)}{TO_TOP}'
           f'<script type="application/json" id="ta-pages">{pages_json}</script>'
           f'<script>window.TA_PREVIEW=true;</script><script>{js}</script>')
    (PREVIEW / "index.html").write_text(doc)
    shutil.copy(STATIC / "textures" / "home-parchment.webp", PREVIEW / "assets" / "home-parchment.webp")
    # A Claude artifact cannot load pictures from other sites, so the preview carries its own copies.
    if (STATIC / "cuts").exists():
        shutil.copytree(STATIC / "cuts", PREVIEW / "assets" / "cuts")
    if (STATIC / "dial").exists():
        shutil.copytree(STATIC / "dial", PREVIEW / "assets" / "dial")
    front = ["front.jpg"] if site.front else []
    for sub, names in [("maps", [f"{rid}-{k}.jpg" for rid in site.map_img for k in MAP_PX]), ("pics", [f"{k}.jpg" for k in site.pics] + front)]:
        (PREVIEW / "assets" / sub).mkdir()
        for name in names:
            src = ROOT / "_cache" / sub / name
            if not src.exists():
                raise SystemExit(f"Missing picture {src.relative_to(ROOT)}. Run python3 generator/fetch_map_images.py")
            shutil.copy(src, PREVIEW / "assets" / sub / name)
    write_basemap(PREVIEW / "assets" / "basemap.json")
    write_passage_assets(site, PREVIEW / "assets")
    return len(pages)


def check_no_em_dash():
    bad = []
    for p in list(OUT.rglob("*.html")) + list(PREVIEW.rglob("*.html")):
        if EM_DASH in p.read_text():
            bad.append(str(p.relative_to(ROOT)))
    return bad


def main():
    site = Site()
    keys = write_static(site)
    print(f"static: {len(keys)} pages in docs/")
    if "--static" not in sys.argv:
        n = write_preview(site)
        size = (PREVIEW / "index.html").stat().st_size
        print(f"preview: {n} pages in preview/index.html ({size / 1e6:.1f} MB)")
    bad = check_no_em_dash()
    if bad:
        raise SystemExit(f"Em dash found in: {bad[:10]}")
    print("em dash check: clean")


if __name__ == "__main__":
    main()
