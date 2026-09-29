#!/usr/bin/env python3
"""Build The Tartary Atlas.

Reads the site data layer in data/*.json and writes:
  docs/      the static site, one HTML file per page (GitHub Pages serves this folder)
  preview/   a single-file preview of the same pages, for a private Claude artifact

Run:  python3 generator/build.py            (both outputs)
      python3 generator/build.py --static   (docs/ only)
"""
import collections
import html
import json
import math
import pathlib
import re
import shutil
import sys

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
    "fonts": "https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&family=IBM+Plex+Mono:wght@400;500;600&family=Public+Sans:wght@400..700&display=swap",
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
    "not stated": "The catalogue card does not say how the author knew.",
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
    "unspecified": "Not specified on the card",
}

FAMILY_EXTRA = {
    "unspecified": "Not specified on the card",
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
    ("derived", "in"): "this record derives from it",
    ("derived", "out"): "derives from this record",
    ("reproduction", "in"): "this record reproduces it",
    ("reproduction", "out"): "reproduces this record",
    ("corrected-by", "in"): "this record corrects it",
    ("corrected-by", "out"): "corrects this record",
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
    ("", "Map"), ("records", "Records"), ("places", "Places"), ("peoples", "Peoples"),
    ("labels", "Tartary labels"), ("meanings", "What “Tartar” meant"),
    ("lineage", "Map lineage"), ("about", "About"), ("method", "Method"),
]

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
        corr_path = DATA / "corrections.json"
        self.corrections = json.loads(corr_path.read_text()) if corr_path.exists() else []
        self.apply_corrections()

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
            return "#" + (key.replace("/", "-") if key else "map")
        return self.root + (key + "/" if key else "")

    def asset(self, name):
        if self.mode == "preview":
            return "assets/" + name
        return self.root + "assets/" + name

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
        cap = f'<p class="minimap-cap">{n} plotted place{"s" if n != 1 else ""}. Modern coastlines. Dashed rings are approximate.' + ((f" {missing} further point lies off this frame." if missing == 1 else f" {missing} further points lie off this frame.") if missing else "") + "</p>"
    return (f'<figure style="margin:0"><svg class="minimap" viewBox="0 0 {MM_W} {MM_H}" role="img" aria-label="Map of the places named">'
            f'<use class="land" href="{ctx.land_href()}" width="{MM_W}" height="{MM_H}"/>{body}</svg>{cap}</figure>')


# ---------------------------------------------------------------- shared fragments

def kind_badge(r):
    if r["kind"] == "map":
        return '<span class="kind m" title="Map">M</span>'
    return '<span class="kind" title="Written source">W</span>'


def ev_chip(ev):
    cls = {"claimed or disputed": " ev-claimed", "firsthand": " ev-firsthand"}.get(ev, "")
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


def page_head(eyebrow, title, lede=None, extra=""):
    lede_html = f'<p class="lede">{lede}</p>' if lede else ""
    return f'<header class="page-head"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1>{lede_html}{extra}</header>'


# ---------------------------------------------------------------- pages

def page_record(site, ctx, r):
    d = r["date"]
    is_map = r["kind"] == "map"
    kind_word = "Map" if is_map else "Written source"
    lang = (r["language"] or "").split(" (")[0]
    if len(lang) > 34:
        lang = lang[:34].rsplit(" ", 1)[0] + "…"
    eyebrow = " · ".join(esc(x) for x in [kind_word, lang, tradition_label(r["tradition"])] if x)
    title_html = esc(smart(no_em(r["title"])))
    extra = ""
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
        corr_note = f'<p class="small muted">This record carries a published correction. See <a href="{ctx.link("corrections")}">Corrections</a>.</p>'
    how = (f'<section class="panel how{" claimed" if ev == "claimed or disputed" else ""}" aria-labelledby="how-{r["id"]}">'
           f'<h2 id="how-{r["id"]}">How we know</h2>'
           f'<p>{ev_chip(ev)} {esc(EVIDENCE.get(ev, ""))}</p>'
           + (f'<div><div class="eyebrow">Card wording</div><p>{linkify(site, ctx, r["evidence_text"])}</p></div>' if (r.get("evidence_text") or "").strip() else '<p class="small muted">The card gives no wording on how the author knew.</p>')
           + (f'<div><div class="eyebrow">Cautions</div><ul class="note-list">{caut_html}</ul></div>' if caut_html else "")
           + corr_note + '</section>')

    sections = [how]
    if r.get("research_value"):
        sections.append(f'<section class="section"><h2>Why it matters</h2><p class="prose">{linkify(site, ctx, r["research_value"])}</p></section>')

    if r["tartar_referents_card"]:
        items = "".join(f'<li><span class="chip">{esc(site.family_name(f))}</span></li>' for f in r["tartar_referents_card"])
        sections.append(
            f'<section class="section"><h2>What “Tartar” means here</h2>'
            f'<p class="small muted"><span class="chip prov">provisional</span> Read from the catalogue card, not yet from tagged passages. '
            f'See <a href="{ctx.link("meanings")}">what the word meant</a>.</p><ul class="tags">{items}</ul></section>')

    # places
    if r["places"]:
        tags = []
        for pid in r["places"]:
            p = site.place.get(pid)
            if not p:
                continue
            g = basis_group(p["coord_basis"])
            tags.append(f'<li><a href="{ctx.link("place/" + pid)}"><span class="chip" title="{esc(BASIS[g][0])}">{basis_dot(g)}{esc(p["name"])}</span></a></li>')
        card = f'<p class="small muted">Card wording: {linkify(site, ctx, r["regions_text"])}</p>' if r.get("regions_text") else ""
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
        card = f'<p class="small muted">Card wording: {linkify(site, ctx, r["peoples_text"])}</p>' if r.get("peoples_text") else ""
        sections.append(f'<section class="section"><h2>Peoples named</h2>{"".join(rows)}{card}</section>')

    if is_map or site.edges_by.get(r["id"]):
        sections.append(lineage_section(site, ctx, r))

    # aside
    aside = []
    thumb = thumbnail(site, r)
    if thumb:
        aside.append(thumb)
    facts = [("Record", f'<span class="mono">{r["id"]}</span>'), ("Kind", esc(r["type"] or kind_word))]
    if r.get("language"):
        facts.append(("Language", esc(r["language"])))
    if d["made_start"] is not None:
        facts.append(("Made" if is_map else "Written", f'<strong>{esc(made_label(r))}</strong> <span class="muted small">({esc(prec_label(d["made_precision"]))})</span>'))
    else:
        facts.append(("Made", f'<strong>Undated</strong> <span class="muted small">({esc(prec_label(d["made_precision"]))})</span>'))
    if d.get("made_text"):
        facts.append(("Card date", linkify(site, ctx, d["made_text"])))
    if d.get("subject_start") is not None:
        facts.append(("Period described", esc(span_label(d["subject_start"], d["subject_end"], d["subject_precision"])) + (f'<br><span class="small muted">{linkify(site, ctx, d["subject_text"])}</span>' if d.get("subject_text") else "")))
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
    if r.get("access_status"):
        acc.append(f'<p class="small muted">{linkify(site, ctx, r["access_status"])}</p>')
    if is_map:
        routes = site.iiif.get(r["id"], [])
        if routes:
            li = []
            for e in routes:
                st = e["status"]
                ok = st == "ok"
                st_txt = "verified" if ok else ("not yet confirmed" if st.startswith("pattern") else "did not answer when checked")
                li.append(f'<li><a href="{esc(e["url"])}" rel="noopener">IIIF {esc(e["kind"])}</a> <span class="small muted">{st_txt}</span></li>')
            acc.append(f'<div><div class="eyebrow">IIIF</div><ul class="note-list" style="padding-left:1em">{"".join(li)}</ul></div>')
        else:
            acc.append('<p class="small muted">No IIIF route found yet.</p>')
    aside.append(f'<div class="panel"><h2>Access</h2>{"".join(acc)}</div>')

    mm = minimap(site, ctx, r["places"])
    if mm:
        aside.append(mm)
    aside.append(f'<p class="small"><a href="{ctx.link("corrections")}">Report a correction to {r["id"]}</a></p>')

    body = (f'<div class="page"><nav class="small muted" aria-label="Breadcrumb"><a href="{ctx.link("records")}">Records</a> / <span class="mono">{r["id"]}</span></nav>'
            f'{head}<div class="record-grid"><div style="display:grid;gap:28px">{"".join(sections)}</div>'
            f'<aside style="display:grid;gap:18px">{"".join(aside)}</aside></div></div>')

    title = f'{smart(short_title(no_em(r["title"]), 60))} ({made_label(r)}) · {r["id"]}'
    desc = first_sentence(no_em(r.get("research_value") or r["title"]))
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
    return dict(title=title, description=desc, body=body, nav="records", jsonld=jsonld)


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
            f'<div class="cap">Image served by {esc(host)} through IIIF.</div></a>')


def lineage_section(site, ctx, r):
    edges = site.edges_by.get(r["id"], [])
    if not edges:
        return (f'<section class="section"><h2>Map lineage</h2><p class="muted">No lineage links recorded for this map yet. '
                f'See <a href="{ctx.link("lineage")}">all lineage links</a>.</p></section>')
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
    return (f'<section class="section"><h2>Map lineage</h2>{"".join(parts)}'
            f'<p class="small"><a href="{ctx.link("lineage")}">See the full lineage diagrams</a></p></section>')


def page_place(site, ctx, p):
    g = basis_group(p["coord_basis"])
    eyebrow = " · ".join(["Place", esc(p["type"].replace("-", " "))])
    lede = esc(p["note"]) if p.get("note") else None
    head = page_head(eyebrow, esc(p["name"]), lede)
    n = len(p["records"])
    main = [f'<section class="section" style="margin-top:0"><h2>{n} record{"s" if n != 1 else ""} name this place, in date order</h2>{record_list(site, ctx, p["records"])}</section>']
    if p["id"] in LABEL_IDS:
        main.insert(0, f'<p class="banner"><strong>A label, not a location.</strong> Its extent changed from map to map. '
                       f'See when each Tartary label was in use on the <a href="{ctx.link("labels")}">Tartary labels timeline</a>.</p>')
    facts = []
    if p["lat"] is not None:
        facts.append(("Point", f'<span class="mono">{coord_text(p["lat"], p["lon"])}</span>'))
    facts.append(("Basis", f'{basis_dot(g)} {esc(BASIS[g][0])}<br><span class="small muted">{esc(BASIS[g][1])}</span>'))
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
        facts.append(("Forms on the cards", esc("; ".join(shown)) + more))
    aside = [f'<dl class="facts">{"".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)}</dl>']
    mm = minimap(site, ctx, [p["id"]], caption=False)
    if mm:
        aside.insert(0, mm)
    body = (f'<div class="page"><nav class="small muted" aria-label="Breadcrumb"><a href="{ctx.link("places")}">Places</a> / {esc(p["name"])}</nav>'
            f'{head}<div class="record-grid"><div>{"".join(main)}</div><aside style="display:grid;gap:18px">{"".join(aside)}</aside></div></div>')
    desc = f'{p["name"]}: {n} historical source{"s" if n != 1 else ""} and maps that name it, in date order, with how each author knew.'
    jsonld = {"@context": "https://schema.org", "@type": "Place", "name": p["name"], "url": f'{CONFIG["base_url"]}/place/{p["id"]}/'}
    if p["lat"] is not None and g in ("exact", "river", "capital"):
        jsonld["geo"] = {"@type": "GeoCoordinates", "latitude": p["lat"], "longitude": p["lon"]}
    if p.get("wikidata"):
        jsonld["sameAs"] = f'https://www.wikidata.org/wiki/{p["wikidata"]}'
    return dict(title=f'{p["name"]} in the sources', description=desc, body=body, nav="places", jsonld=jsonld)


def page_people(site, ctx, p):
    ids = site.people_records.get(p["id"], [])
    head = page_head("People · " + esc(site.family_name(p["family"])), esc(p["name"]),
                     f'{len(ids)} record{"s" if len(ids) != 1 else ""} name this people or polity.')
    aliases = sorted(set(a for a in p.get("aliases", []) if len(a) < 60))
    aside = ""
    if aliases:
        aside = f'<dl class="facts"><dt>Forms on the cards</dt><dd>{esc("; ".join(aliases[:40]))}</dd></dl>'
    fam = [q for q in site.peoples if q["family"] == p["family"] and q["id"] != p["id"]]
    if fam:
        aside += ('<div style="display:grid;gap:6px"><div class="eyebrow">Same family</div><ul class="tags">'
                  + "".join(f'<li><a href="{ctx.link("peoples/" + q["id"])}"><span class="chip">{esc(q["name"])}</span></a></li>' for q in fam)
                  + "</ul></div>")
    body = (f'<div class="page"><nav class="small muted" aria-label="Breadcrumb"><a href="{ctx.link("peoples")}">Peoples</a> / {esc(p["name"])}</nav>'
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
            f'<td>{ev_chip(r["evidence_class"])}</td><td class="rid">{r["id"]}</td></tr>')
    ev_opts = "".join(f'<option value="{esc(e)}">{esc(e)}</option>' for e in EVIDENCE_ORDER)
    counts = collections.Counter(r["kind"] for r in site.records)
    head = page_head("Catalogue", "Records",
                     f'{counts["written"]} written sources and {counts["map"]} maps, from antiquity to the 1870s, each with its date, its places and how its author knew.')
    body = (f'<div class="page">{head}<div data-module="rtable">'
            f'<div class="filterbar"><label for="rt-q">Find<input type="search" id="rt-q" placeholder="Witsen, Tobolsk, Tartaria, W122…"></label>'
            f'<label for="rt-k">Kind<select id="rt-k"><option value="">All</option><option value="written">Written sources</option><option value="map">Maps</option></select></label>'
            f'<label for="rt-ev">How the author knew<select id="rt-ev"><option value="">Any</option>{ev_opts}</select></label>'
            f'<p class="small muted" aria-live="polite"><span data-count>{len(site.records)}</span> shown</p></div>'
            f'<div class="table-wrap"><table class="data"><thead><tr><th class="num">Date</th><th>Kind</th><th>Title and creator</th><th>Evidence</th><th>ID</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div></div>')
    return dict(title="Records", description="All 422 written sources and maps in the Tartary Atlas, in date order, searchable by name, place and ID.", body=body, nav="records", modules=["rtable"])


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
    head = page_head("Gazetteer", "Places",
                     f'{len(site.places)} places named in the records. The dot beside each name says how its map point was chosen. The number is how many records name it.')
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
    head = page_head("Vocabulary", "Peoples and polities",
                     f'{len(site.peoples)} peoples and polities named in the records, in {len(site.families)} families. The number is how many records name each one.')
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
        forms_html = f'<p class="small muted">Forms on the cards: {esc("; ".join(forms[:14]))}</p>' if forms else ""
        lists.append(f'<section class="section"><h2><a href="{ctx.link("place/" + p["id"])}">{esc(p["name"])}</a> <span class="muted small">{len(recs)} records</span></h2>{forms_html}{record_list(site, ctx, [r["id"] for r in recs])}</section>')

    def first_map(lid, last=False):
        ms = sorted((r for r in rows_by[lid] if r["kind"] == "map" and r["date"]["made_start"] is not None), key=sort_key)
        r = ms[-1] if last else ms[0]
        return f'<a href="{ctx.link(site.rkey(r))}">{r["date"]["made_start"]}</a>'
    rows_by = {p["id"]: recs for p, recs in rows}
    lede = (f"In these records, Tartaria first appears on a map in {first_map('tartary')} and last in {first_map('tartary', True)}. "
            f"Great Tartary reaches the maps in {first_map('great-tartary')}. Chinese Tartary follows in {first_map('chinese-tartary')}, "
            f"Muscovite Tartary in {first_map('muscovite-tartary')}, Independent Tartary in {first_map('independent-tartary')} "
            f"and Little Tartary in {first_map('little-tartary')}. Each label named a region whose borders moved from map to map, "
            "so the atlas shows them on a timeline and never as a single dot on the map.")
    head = page_head("Labels on maps", "When each Tartary label was in use", lede)
    mid = 1700
    body = (f'<div class="page">{head}<div data-module="labels">'
            f'<div class="figure"><div class="slider-row"><label for="lab-y" class="small">Show the labels in use around</label>'
            f'<input type="range" id="lab-y" min="{y0}" max="{y1}" step="5" value="{mid}"><output for="lab-y" data-out>{mid}</output>'
            f'<span class="small muted">within 25 years either side</span></div>'
            f'<div class="scroll">{"".join(parts)}</div>'
            f'<div class="fig-legend"><span><span class="sw"></span>Map</span><span><span class="sw w"></span>Written source</span>'
            f'<span class="muted">Each mark is one record. Click a mark to open it.</span></div></div>'
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

    head = page_head("The word in use", "What “Tartar” meant, source by source",
                     f"The same word named different peoples in different centuries. This chart places {len(recs)} written sources by the date they were written, "
                     "in a row for each group their catalogue card says the word pointed to. A source whose card names two groups appears in both rows, joined by a thin line.")
    banner = ('<p class="banner"><strong>Provisional.</strong> These readings come from each catalogue card, not yet from the passages themselves. '
              'The next data layer tags every passage where a source uses the word, and will replace this chart.</p>')
    body = (f'<div class="page">{head}{banner}<div class="figure" style="margin-top:18px"><div class="scroll">{"".join(parts)}</div>'
            f'<div class="fig-legend"><span><span class="sw w"></span>One written source</span>'
            f'<span class="muted">The shaded band before 1200 uses a compressed scale. Click a dot to open the record.</span></div></div>'
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
            f'<p class="small muted">{len(nodes)} records, {len(edges)} link{"s" if len(edges) != 1 else ""} ({stated} stated), {esc(made_label(first))} to {esc(made_label(last))}</p>'
            f'<div class="figure"><div class="scroll">{lineage_svg_vertical(site, ctx, comp, i) if len(comp) > 6 else lineage_svg(site, ctx, comp, i)}</div></div>'
            f'<details><summary class="small">{"The " + str(len(edges)) + " links and the evidence for each" if len(edges) != 1 else "The link and its evidence"}</summary>'
            f'<div class="table-wrap" style="margin-top:8px"><table class="data"><thead><tr><th>From</th><th>To</th><th>Link</th><th>Certainty</th><th>Basis</th></tr></thead><tbody>{rows}</tbody></table></div></details></section>')
    n_prob = sum(1 for e in site.lineage if e["certainty"] == "probable")
    head = page_head("Copying and correction", "Map lineage",
                     f"Mapmakers copied, reissued and corrected one another. These diagrams trace {len(site.lineage)} recorded links between "
                     f"{len(set(e['source'] for e in site.lineage) | set(e['target'] for e in site.lineage))} records, in {len(comps)} families. "
                     "Time runs left to right in the small families and top to bottom in the three large ones. An arrow points from a source to the map derived from, reproducing or correcting it. "
                     "A line without an arrow joins works that share a plate, an atlas, a text or a tradition.")
    legend = ('<div class="fig-legend" style="margin-bottom:6px"><span><span class="ln"></span>Stated in the catalogue</span>'
              f'<span><span class="ln dash"></span>Probable ({n_prob} links)</span><span><span class="sw w"></span>Map</span>'
              '<span class="muted">Hover a line for its basis. Click a node to open the record.</span></div>')
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
        places.append([p["id"], p["name"], g, p["lon"], p["lat"]])
    return {
        "records": recs, "places": places,
        "traditions": [[t, trads[t]] for t in tlist],
        "evidence": [[e, sum(1 for r in site.records if r["evidence_class"] == e)] for e in EVIDENCE_ORDER],
        "basis": {g: v[0] for g, v in BASIS.items()},
    }


def page_home(site, ctx):
    data = explorer_data(site)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    n_w = sum(1 for r in site.records if r["kind"] == "written")
    n_m = len(site.records) - n_w
    legend = "".join(f'<div>{basis_dot(g)}<span>{esc(BASIS[g][0])}</span></div>' for g in ["exact", "river", "capital", "approx", "anchor"])
    body = f'''<div class="explorer" data-module="explorer">
<script type="application/json">{js}</script>
<div class="mapwrap"><div id="map" role="region" aria-label="Map of places named in the sources"></div>
<div class="map-note">Modern coastlines and rivers, Natural Earth. Aral Sea at its modern extent.</div></div>
<div class="side">
<div class="side-sec intro"><h1>The Tartary Atlas</h1>
<p>Every place named in {n_w} written sources and {n_m} maps about Tartary, from the Mongol conquests to the nineteenth century. Pick a date range, then click a place to see who wrote about it, when, and how they knew.</p>
<div class="stats"><span><b data-stat="records">{len(site.records)}</b>records shown</span><span><b data-stat="places">0</b>places plotted</span></div></div>
<div class="side-sec"><h2>Dates</h2>
<div class="range"><svg class="hist" viewBox="0 0 200 44" preserveAspectRatio="none" aria-hidden="true" data-hist></svg>
<div class="dual"><div class="track"></div><div class="fill" data-fill></div>
<input type="range" id="ex-lo" min="0" max="100" step="0.25" value="0" aria-label="Earliest date">
<input type="range" id="ex-hi" min="0" max="100" step="0.25" value="100" aria-label="Latest date"></div>
<div class="ticks" data-ticks></div>
<div class="readout" data-readout aria-live="polite"></div></div>
<label class="small" style="display:flex;gap:8px;align-items:center"><input type="checkbox" id="ex-undated" checked> Include the undated record (M029)</label>
</div>
<div class="side-sec"><h2>Show</h2>
<div class="seg" role="group" aria-label="Kind of record"><button type="button" data-kind="all" aria-pressed="true">All</button><button type="button" data-kind="0" aria-pressed="false">Written</button><button type="button" data-kind="1" aria-pressed="false">Maps</button></div>
<details class="filters"><summary>How the author knew</summary><div class="checks" data-ev></div></details>
<details class="filters"><summary>Language tradition</summary><div class="checks" data-tr></div></details>
</div>
<div class="side-sec place-panel" data-panel aria-live="polite"></div>
<div class="side-sec"><h2>Map key</h2><div class="legend">{legend}</div>
<p class="small muted">Dot size follows the number of records. Hollow dashed rings mark editorial approximations for regions with no single location. <a href="{ctx.link("method")}">How places were plotted</a>.</p></div>
</div></div>'''
    desc = f"An open atlas of Tartary (Tartaria) in {n_w} historical texts and {n_m} maps: every place named, when, and how each author knew."
    return dict(title="The Tartary Atlas: Tartary and Tartaria in the historical record", description=desc, body=body, nav="", modules=["explorer"], maplibre=True, bare_title=True)


# ------------------------------------------------ About, Method, Corrections

def page_about(site, ctx):
    c = CONFIG
    body = f'''<div class="page">{page_head("About", "About the atlas")}
<div class="prose">
<p>The Tartary Atlas gathers what the historical record says about Tartary: which sources name it, where, when, and how each author came to know what they wrote. It covers {len(site.records)} written sources and maps in more than a dozen languages, from Old Turkic inscriptions and Mongol-era travel accounts to nineteenth-century atlases.</p>
<p>Tartary, printed as Tartaria on Latin maps, has lately become the subject of popular claims about a lost Tartarian Empire. The atlas is built so anyone can test a claim against the sources themselves. Each record page shows the source's date and how precise that date is, the places and peoples it names, whether its author saw them or compiled from others, and a link to the source.</p>
<h2>Who made it</h2>
<p>The atlas is a research project by {esc(c["researcher"])}, host of the <a href="{esc(c["podcast_url"])}" rel="noopener">{esc(c["podcast_name"])}</a>, where the research behind it is discussed. The catalogue, the gazetteer and the site were built with AI research assistance, and every record links back to its source so the work can be checked.</p>
<h2>How to use it</h2>
<ul>
<li><a href="{ctx.link("")}">The map</a> plots every place the sources name. Narrow the dates, then click a place.</li>
<li><a href="{ctx.link("labels")}">Tartary labels</a> shows when Great, Little, Chinese, Independent and Muscovite Tartary appear.</li>
<li><a href="{ctx.link("meanings")}">What “Tartar” meant</a> shows which peoples the word pointed to, source by source.</li>
<li><a href="{ctx.link("lineage")}">Map lineage</a> traces which maps copied which.</li>
<li><a href="{ctx.link("method")}">Method</a> explains every label and limit in the data.</li>
</ul>
<h2>Corrections and new sources</h2>
<p>The atlas takes corrections and source suggestions in public. See <a href="{ctx.link("corrections")}">Corrections</a>.</p>
</div></div>'''
    return dict(title="About the atlas", description="What The Tartary Atlas is, who made it, and how to use it.", body=body, nav="about")


def page_method(site, ctx):
    m = site.meta["counts"]
    ev_rows = "".join(f"<li><strong>{esc(k)}.</strong> {esc(v)} <span class=\"muted\">({sum(1 for r in site.records if r['evidence_class'] == k)} records)</span></li>" for k, v in EVIDENCE.items())
    basis_rows = "".join(f"<li>{basis_dot(g)} <strong>{esc(v[0])}.</strong> {esc(v[1])}</li>" for g, v in BASIS.items())
    prec_rows = "".join(f"<li><strong>{esc(v)}</strong> <span class=\"muted\">({esc(k)})</span></li>" for k, v in PRECISION.items() if not k.startswith("century (") )
    n_approx = sum(1 for p in site.places if basis_group(p["coord_basis"]) in ("approx", "anchor"))
    n_notes = sum(1 for r in site.records if r["date"].get("override"))
    body = f'''<div class="page">{page_head("Method", "How the atlas is built")}
<div class="prose">
<h2>Three layers of data</h2>
<ul>
<li><strong>The catalogue.</strong> {m["records"]} records: {m["written"]} written sources (IDs W001 to W303) and {m["maps"]} maps (M001 to M119), each with a card describing its date, places, peoples, access, and how its author knew. The catalogue was compiled from library, archive and scholarly catalogues in English, Latin, Italian, Spanish, Portuguese, French, Dutch, German, Russian, Persian, Arabic, Ottoman Turkish, Chagatai, Tatar, Chinese, Manchu, Mongolian, Tibetan and Japanese.</li>
<li><strong>The site data.</strong> Structured dates, a gazetteer of {m["places"]} places ({m["places_plotted"]} with a point), {m["peoples"]} peoples and polities, an evidence class for every record, {m["lineage_edges"]} map lineage links, and IIIF image routes for {m["maps_with_iiif"]} maps. Built {esc(site.meta["built"])}.</li>
<li><strong>Passage attestations</strong> (in preparation). Every place a source names Tartary or a related term, with page, original wording and what it refers to. This layer will replace the provisional card-level readings on <a href="{ctx.link("meanings")}">What “Tartar” meant</a>.</li>
</ul>
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
    return dict(title="Method", description="How The Tartary Atlas dates sources, plots places, sorts evidence and traces map lineage.", body=body, nav="method")


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
    body = f'''<div class="page">{page_head("Corrections", "Corrections and new sources")}
<div class="prose">
<p>The atlas corrects itself in public. If a date, place, reading or link is wrong, or a source is missing, send it in and the fix will be logged below with its evidence.</p>
<h2>How to send a correction</h2>
<ul>
<li>Open an issue on the <a href="{esc(c["repo_url"])}/issues" rel="noopener">atlas repository</a>.</li>
<li>Give the record ID (for example W122 or M081), what is wrong, and a link to a source that shows it.</li>
<li>To suggest a new source, give its title, date, and a link to a scan or catalogue entry.</li>
</ul>
<h2>Corrections log</h2>
</div>{log}</div>'''
    return dict(title="Corrections", description="How to correct The Tartary Atlas, and the public log of corrections made.", body=body, nav="corrections")


# ---------------------------------------------------------------- layout

def header(ctx, nav_key):
    cur = ' aria-current="page"'
    items = "".join(
        f'<a href="{ctx.link(k)}" data-nav="{k}"{cur if k == nav_key else ""}>{esc(label)}</a>' for k, label in NAV)
    return (f'<a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="bar">'
            f'<a class="wordmark" href="{ctx.link("")}"><span>The</span> Tartary Atlas</a>'
            f'<nav class="site-nav" aria-label="Main">{items}</nav></div></header>')


def footer(site, ctx):
    c = CONFIG
    return (f'<footer class="site-footer"><div class="inner"><span>The Tartary Atlas, a research project by {esc(c["researcher"])}</span>'
            f'<a href="{esc(c["podcast_url"])}" rel="noopener">Discussed on the {esc(c["podcast_name"])}</a>'
            f'<a href="{ctx.link("method")}">Method</a><a href="{ctx.link("corrections")}">Corrections</a>'
            f'<span>Data built {esc(site.meta["built"])}</span></div></footer>')


def full_title(pg):
    if pg.get("bare_title"):
        return pg["title"]
    return f'{pg["title"]} · {CONFIG["site_name"]}'


def static_page(site, key, pg):
    ctx = Ctx("static", key)
    title = full_title(pg)
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
        f'<link rel="stylesheet" href="{ctx.asset("site.css")}">',
    ]
    if pg.get("maplibre"):
        head.append(f'<link rel="stylesheet" href="{ctx.asset("maplibre-gl.css")}">')
        head.append(f'<script src="{CONFIG["maplibre_js"]}" defer></script>')
    head.append(f'<script src="{ctx.asset("site.js")}" defer></script>')
    if pg.get("jsonld"):
        head.append('<script type="application/ld+json">' + json.dumps({k: v for k, v in pg["jsonld"].items() if v is not None}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    head.append("</head>")
    body = f'<body data-root="{ctx.root}">{header(ctx, pg["nav"])}<main id="main">{pg["body"]}</main>{footer(site, ctx)}</body></html>'
    return "".join(head) + body


def all_pages(site, ctx_factory):
    """Yield (key, page dict) for every page. ctx_factory(key) builds the link context."""
    yield "", page_home(site, ctx_factory(""))
    for k, fn in [("records", page_records), ("places", page_places), ("peoples", page_peoples),
                  ("labels", page_labels), ("meanings", page_meanings), ("lineage", page_lineage),
                  ("about", page_about), ("method", page_method), ("corrections", page_corrections)]:
        yield k, fn(site, ctx_factory(k))
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
    shutil.copy(STATIC / "js" / "site.js", OUT / "assets" / "site.js")
    shutil.copy(STATIC / "vendor" / "maplibre-gl.css", OUT / "assets" / "maplibre-gl.css")
    write_basemap(OUT / "assets" / "basemap.json")
    (OUT / "assets" / "eurasia.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg">{build_land_svg()}</svg>')
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text(f'User-agent: *\nAllow: /\nSitemap: {CONFIG["base_url"]}/sitemap.xml\n')
    urls = "".join(f'<url><loc>{CONFIG["base_url"]}/{k + "/" if k else ""}</loc></url>' for k in keys)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    (OUT / "404.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Page not found · {CONFIG["site_name"]}</title><link rel="stylesheet" href="/assets/site.css"></head>'
        '<body><main class="page"><h1>Page not found</h1><p class="lede">That address is not in the atlas. <a href="/">Go to the map</a> or <a href="/records/">browse the records</a>.</p></main></body></html>')
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
        pages[key] = {"t": full_title(pg), "h": pg["body"], "n": pg["nav"]}
    ctx = Ctx("preview", "")
    css = (STATIC / "vendor" / "maplibre-gl.css").read_text() + "\n" + (STATIC / "css" / "site.css").read_text()
    js = (STATIC / "js" / "site.js").read_text()
    pages_json = json.dumps(pages, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    doc = (f'<meta charset="utf-8"><title>Tartary Atlas Preview</title>\n'
           f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           f'<link rel="stylesheet" href="{CONFIG["fonts"]}">'
           f'<style>{css}</style>'
           f'<script src="{CONFIG["maplibre_js"]}"></script>'
           f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">{build_land_svg()}</svg>'
           f'{header(ctx, "")}<main id="main"></main>{footer(site, ctx)}'
           f'<script type="application/json" id="ta-pages">{pages_json}</script>'
           f'<script>window.TA_PREVIEW=true;</script><script>{js}</script>')
    (PREVIEW / "index.html").write_text(doc)
    write_basemap(PREVIEW / "assets" / "basemap.json")
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
