#!/usr/bin/env python3
"""Import the themed passage extracts from the corpus repo into data/passages.json.

Run:  python3 generator/import_passages.py /path/to/tartary-corpus

Reads  <corpus>/learn/extracts/*.json   (source profiles and passages, written by the readers)
       <corpus>/learn/quote_check.json  (machine check of each quote against its cited page, optional)
       data/places.json, data/passage_places.json (hand map of passage place names to gazetteer IDs)
Writes data/passages.json: {"built", "profiles": {record id: profile}, "passages": [ ... ]}

A passage ID is the record ID plus its position in the reader's list, for example W001-03.
"""
import collections
import datetime
import glob
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
THEMES = ["cities", "architecture", "customs", "names", "outliers"]
BASIS = {"saw it": "saw", "heard it": "heard", "read it": "read", "legend or rumour": "legend",
         "official record": "record", "mixed": "mixed"}
STOP = {"river", "lake", "sea", "region", "steppe", "valley", "near", "the", "of", "and", "on", "in",
        "north", "south", "east", "west", "upper", "lower", "central", "great", "city", "town", "old", "new"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def year_of(when):
    """First year or century named in the free-text date, as an integer year, or None."""
    w = str(when or "")
    bce = "BCE" in w or "BC" in w.split()
    m = re.search(r"(?<!\d)(\d{3,4})(?!\d)", w)
    if m:
        y = int(m.group(1))
        return -y if bce else y
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th) century", w)
    if m:
        c = int(m.group(1))
        mid = (c - 1) * 100 + (20 if "early" in w or "first" in w else 80 if "late" in w else 50)
        return -((c - 1) * 100 + 50) if bce else mid
    return None


class PlaceMatcher:
    def __init__(self):
        places = json.loads((DATA / "places.json").read_text())
        self.ids = {p["id"] for p in places}
        self.idx = {}
        rank = {"settlement": 0}
        for p in sorted(places, key=lambda p: rank.get(p["type"], 1)):
            for n in [p["name"], p["id"].replace("-", " ")] + (p.get("aliases") or []):
                k = norm(n)
                if k and k not in STOP:
                    self.idx.setdefault(k, p["id"])
        hand = DATA / "passage_places.json"
        self.hand = {norm(k): v for k, v in json.loads(hand.read_text()).items()} if hand.exists() else {}
        for k, v in self.hand.items():
            for pid in v:
                if pid not in self.ids:
                    raise SystemExit(f"passage_places.json: unknown place id {pid} for {k}")

    def match(self, s):
        """Gazetteer IDs for a passage place string, most specific first. [] if none."""
        if not s:
            return []
        k = norm(s)
        if k in self.hand:
            return list(self.hand[k])
        if k in self.idx:
            return [self.idx[k]]
        out = []
        parts = [x for x in re.split(r"[,;()/]| near | and | on the | in the | between | of ", s) if x.strip()]
        for part in parts:
            pk = norm(part)
            if pk in self.hand:
                out += self.hand[pk]
            elif pk in self.idx:
                out.append(self.idx[pk])
            else:
                words = pk.split()
                for n in (3, 2, 1):
                    found = False
                    for i in range(len(words) - n + 1):
                        g = " ".join(words[i:i + n])
                        if g in self.hand:
                            out += self.hand[g]
                            found = True
                        elif g in self.idx and g not in STOP:
                            out.append(self.idx[g])
                            found = True
                    if found:
                        break
        seen, res = set(), []
        for pid in out:
            if pid not in seen:
                seen.add(pid)
                res.append(pid)
        return res[:3]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    corpus = pathlib.Path(sys.argv[1])
    check = {}
    cpath = corpus / "learn" / "quote_check.json"
    if cpath.exists():
        check = {c["id"]: c for c in json.loads(cpath.read_text())["passages"]}
    pm = PlaceMatcher()
    profiles, passages = {}, []
    unmatched = collections.Counter()
    for f in sorted(glob.glob(str(corpus / "learn" / "extracts" / "*.json"))):
        for r in json.loads(pathlib.Path(f).read_text())["records"]:
            rid = r["id"]
            if rid in profiles:
                raise SystemExit(f"{rid} appears in two extract files")
            profiles[rid] = {k: r[k] for k in ["plain_title", "one_line", "summary", "how_they_knew",
                                               "tartar_means", "why_read", "watch_out", "read_quality"]}
            for i, a in enumerate(r["accounts"]):
                pid = f"{rid}-{i + 1:02d}"
                if a["theme"] not in THEMES:
                    raise SystemExit(f"{pid}: unknown theme {a['theme']}")
                pl = pm.match(a.get("place"))
                if a.get("place") and not pl:
                    unmatched[a["place"]] += 1
                note = a.get("quote_note") or ""
                c = check.get(pid, {})
                if c.get("status") == "matched":
                    chk = "page"
                elif "image" in note.lower() or "transcrib" in note.lower():
                    chk = "image"
                elif c:
                    chk = "partial"
                else:
                    chk = "none"
                passages.append({
                    "id": pid, "rec": rid, "theme": a["theme"], "headline": a["headline"],
                    "place": a.get("place"), "place_ids": pl, "people": a.get("people"),
                    "when": str(a["when"]) if a.get("when") is not None else None, "year": year_of(a.get("when")),
                    "gloss": a["gloss"], "quote": a["quote"], "translation": a.get("translation"),
                    "quote_note": a.get("quote_note"), "speaker": a["speaker"],
                    "p": (str(a["p"]) if a.get("p") not in (None, "") else None), "url": a["page_url"],
                    "basis": BASIS[a["basis"]], "strength": a["strength"], "caution": a.get("caution"),
                    "tags": a.get("tags") or [], "check": chk,
                })
    out = {"built": datetime.date.today().isoformat(), "profiles": profiles, "passages": passages}
    txt = json.dumps(out, ensure_ascii=False, indent=0)
    for bad in ("—", "–"):
        if bad in txt:
            raise SystemExit("dash found in extracts")
    (DATA / "passages.json").write_text(txt)
    n = len(passages)
    print(f"{len(profiles)} profiles, {n} passages, {sum(1 for p in passages if p['place_ids'])} with a gazetteer place")
    print("quote check:", dict(collections.Counter(p["check"] for p in passages)))
    print("no year:", sum(1 for p in passages if p["year"] is None))
    if "--unmatched" in sys.argv:
        for k, v in unmatched.most_common():
            print(v, k)


if __name__ == "__main__":
    main()
