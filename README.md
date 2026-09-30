# The Tartary Atlas

An open explorer of what the historical record says about Tartary: 303 written sources and 119 maps, every place they name, when, and how each author knew, and (since 2026-09-30) quoted passages from the sources read so far, sorted into five trails. A research project by Chance Garton, discussed on the InnerVerse Podcast.

Planned address: `https://tartary.innerversepodcast.com`

## What is in this repository

| Path | What it holds |
|---|---|
| `data/` | The site data layer: `records.json`, `places.json`, `places.geojson`, `peoples.json`, `people_families.json`, `lineage.json`, `iiif.json`, `meta.json`. Copied from the private `tartary-corpus` repo (`site-data/data/`). Derived data, short card text and links only. |
| `data/passages.json` | Source profiles and themed passages, written by `generator/import_passages.py` from the corpus repo's `learn/extracts/` and `learn/quote_check.json`. |
| `data/passage_places.json` | Hand map from passage place names to gazetteer IDs, for names the gazetteer does not carry. |
| `data/corrections.json` | Published corrections applied at build time. Each one names the record, the field, the old and new wording, the reason and its sources. The Corrections page lists them. |
| `generator/build.py` | The site generator. Python 3, standard library only. |
| `data/pictures.json` | The named pictures on the front page and the trail pages: a detail of a catalogued map (record, IIIF region) or an image at a given address, each with its alt text and caption. |
| `data/map_images.json` | Pixel sizes of the map pictures, written by `generator/fetch_map_images.py`. |
| `generator/fetch_map_images.py` | Fetches a small and a large picture of every map with a working IIIF route, and the named pictures, into `_cache/` (not committed). Only the preview uses the copies. |
| `generator/prepare_basemap.sh` | Rebuilds the self-hosted basemap from Natural Earth. |
| `static/` | Stylesheet, page script, MapLibre stylesheet, and the basemap GeoJSON. |
| `docs/` | The generated site, one HTML file per page. GitHub Pages serves this folder. |
| `preview/` | A single-file preview of the same pages (not committed). |

## Build

```
python3 generator/fetch_map_images.py # once, and after data/iiif.json or data/pictures.json change: fills _cache/ for the preview
python3 generator/build.py            # writes docs/ and preview/
python3 generator/build.py --static   # docs/ only
```

The build fails if a correction no longer matches its record, and fails if an em dash appears in any page. Then run `python3 generator/check_site.py`, which checks that known records render, that place lists run in date order, that approximate points never look surveyed, and that every internal link resolves.

To refresh the passages after more sources are read, run `python3 learn/tools/verify_quotes.py` in `tartary-corpus` (it needs the cited text volumes checked out), then `python3 generator/import_passages.py /path/to/tartary-corpus --unmatched` here, add any worthwhile unmatched place names to `data/passage_places.json`, and rebuild.

To refresh the data after the site data layer changes, copy `site-data/data/*.json` from `tartary-corpus` into `data/` and rebuild. Keep `data/corrections.json`.

Site-wide settings (name, address, repository link, researcher, podcast link) sit in `CONFIG` at the top of `generator/build.py`.

## Pages

* `/` the front door: the question, one passage from the record beside it (first thing on the page, with a Draw another button), a period map, five question trails, a strip of old maps, twelve places, six witnesses, and the vault. No counts strip and no progress report. The passage is drawn at random on every visit from a pool of about a hundred (`FEATURE_PER_TRAIL`, `FEATURE_PER_SOURCE` in the generator), never the one seen last time; "Draw another" walks a fresh shuffle; Back returns to the passage that was showing. `FIRST_FEATURE` is what shows when the page script does not run.
* `/passages/` and `/passages/<trail>/` the passage explorer (cities, architecture, customs, names, outliers): search with the found words marked, how the author knew, century, order, shuffle, a count of what matches and a Clear filters button. Each menu shows how many passages every choice would give. Reads `assets/passages-<trail>.json`.
* `/sources/` every source that has been read, in plain words.
* `/maps/` the old maps: a picture gallery of every map with a working image route, by century, with a search box.
* `/map/` the places map: MapLibre GL JS with a self-hosted Natural Earth basemap, a date range, and filters for kind, evidence class and language tradition.
* `/archive/` the way in to the catalogue and research tools below.
* `/records/`, `/places/`, `/peoples/` browse pages.
* `/w/W122/`, `/m/M081/` one page per record: for a source that has been read, its plain-words profile and passages first; then dates with precision, places and peoples, the "How we know" panel, access and IIIF links, map lineage.
* `/place/<id>/` and `/peoples/<id>/` the passages about the place, then every record naming the place or people, in date order.
* `/labels/` when each Tartary label (Tartary, Great, Little, Chinese, Independent, Muscovite, Eastern, Desert) appears.
* `/meanings/` what "Tartar" meant, source by source (card-level and provisional until the passage layer exists).
* `/lineage/` which maps copied, reissued or corrected which.
* `/about/`, `/method/`, `/corrections/`.

Controls shared across pages (all in `static/js/site.js`):

* A set of passages on a source or place page (`psg_block` in the generator, `TA.modules.pset` in the script) has trail pills that filter it, an As chosen / Oldest first switch, and opens ten more at a time.
* Every passage card has a Copy quote button: the quote, who said it, the page and the link.
* Every passage card away from its own source page ends with a door into that source, "Explore this Tartaria tale": the plain title, the years, and how many passages wait there (`tale_link` in the generator, mirrored in `TA.card`). The passage data files carry `[title, passages, years]` per source for it.
* The label that says how the author knew ("Saw it", "Heard it") is a button on a card: pressing it spells the label out, for phones.
* Source pages open with "Read the N passages" and "Open the original book", and end with Keep exploring: the witness before, the witness after (by the years described) and Surprise me (`onward_section`, `TA.modules.lucky`). Map pages end with the maps drawn just before and after. The sources list has Surprise me too.
* A map picture opens a closer look in the page (`TA.zoom`): zoom with the buttons, the wheel or a tap, drag to move, Esc or Close to leave. The link to the full image at the library stays.
* A rounded, outlined pill is always something to press. Labels that only say something are flat tags (`span.chip`). The labels on the sources list and the catalogue table are buttons that filter the list.
* Coming back with Back or Forward puts the filters, the number of cards open and the scroll position back (`TA.mem`, `TA.restoring`).

Also written: `sitemap.xml`, `robots.txt`, `404.html`, `.nojekyll`.

## Going live

1. Squash the draft history if early drafts should stay out of view, then make the repository public (GitHub Pages on the free plan publishes only from public repositories).
2. Settings, Pages: deploy from branch `main`, folder `/docs`.
3. In GoDaddy DNS for innerversepodcast.com, add a CNAME record: host `tartary`, value `chance-garton.github.io`.
4. Settings, Pages: set the custom domain to `tartary.innerversepodcast.com`, then tick Enforce HTTPS once the certificate is issued.
5. Verify the domain in your GitHub account settings (profile Settings, Pages, Add a domain, not the repository settings) so no one else can claim the subdomain.

## Sources and credits

* Basemap: Natural Earth 1:50m land, lakes and rivers, public domain. The Aral Sea is shown at its modern extent.
* Map library: MapLibre GL JS 4.7.1 (BSD-3-Clause), loaded from cdnjs.
* Map images load from each holding library's IIIF server; nothing is copied into this repository or the static site. The private preview artifact carries its own small copies, because an artifact cannot load images from other sites. Check each library's terms before copying pictures anywhere public (David Rumsey: CC BY-NC-SA; Bodleian: CC BY-NC; the Vatican Library reserves rights).
* The vegetable lamb engraving is from Henry Lee, The Vegetable Lamb of Tartary (1887), via Wikimedia Commons, public domain.
* Fonts: Newsreader, Public Sans, IBM Plex Mono, and IM Fell English SC (Igino Marini) for the wordmark, from Google Fonts.

## Names the visitor sees

The navigation reads In their words (`/passages/`), Map room (`/maps/`), Wander the map (`/map/`), Witnesses (`/sources/`), The vault (`/archive/`), About. Inside the vault: The many Tartarys (`/labels/`), Who counted as a Tartar? (`/meanings/`), Who copied whom (`/lineage/`), Every book and map (`/records/`), Every place (`/places/`), Who's who (`/peoples/`), How it was made (`/method/`), Spot a mistake? (`/corrections/`). Addresses did not change. Visitor-facing copy avoids the project's working words (record, card, catalogue, IIIF, read for passages, profile only); How it was made is the one page that explains the machinery.
