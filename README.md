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
| `data/cuts.json` | The lettering and ornaments cut from the maps: map, box in full-resolution pixels, reading, mapmaker and year. `wordmark: true` puts a label in the header rotation. |
| `data/front_map.json` | The front door: places and mapmaker's notes pinned on Ortelius's map (M047), in full-resolution pixels. |
| `data/journeys.json` | The routes for Ride with a traveler: per journey, the stops in the order travelled (name, modern place, point, whether the point is rough, date, a plain line on what happens there, the passages that belong there), the passages left out and why, and a list of doubts. Written 2026-09-30 and checked against the cited editions. |
| `generator/fetch_cuts.py` | Fetches each cut from the Library of Congress, removes the paper and keeps the ink (`static/cuts/`, committed), and fetches the preview's large copy of the front map (`_cache/pics/front.jpg`). Needs Pillow, numpy and OpenCV. |
| `data/dial.json` | The time dial: for each old map, its Library of Congress picture, the places matched between the sheet and the real earth, every lettering of Tartary on it (and the other big names beside it), plain words on how the sheet uses the name, and what is uncertain. `early` holds the stops before any sheet can be laid on the earth; `off: true` keeps a map on record but off the dial. Matched and read by AI readers on 2026-09-30; no person has checked it. |
| `generator/dial_tools.py` | Bends each map in `data/dial.json` onto one shared sheet of the real earth (`static/dial/*.webp`, committed) and carries the lettering outlines across. `view` shows a piece of a sheet with a pixel grid, `check` fits one map and draws two check pictures, `build` does them all. Needs Pillow, numpy, scipy and OpenCV. |
| `static/` | Stylesheet, page script, MapLibre stylesheet, the basemap GeoJSON, and `cuts/` (the ink-only lettering and ornaments). |
| `docs/` | The generated site, one HTML file per page. GitHub Pages serves this folder. |
| `preview/` | A single-file preview of the same pages (not committed). |

## Build

```
python3 generator/fetch_map_images.py # once, and after data/iiif.json or data/pictures.json change: fills _cache/ for the preview
python3 generator/fetch_cuts.py       # only after data/cuts.json changes, or once in a fresh clone for the preview's front map
python3 generator/dial_tools.py build # only after data/dial.json changes: bends the dial's maps into static/dial/
python3 generator/build.py            # writes docs/ and preview/
python3 generator/build.py --static   # docs/ only
```

The build fails if a correction no longer matches its record, and fails if an em dash appears in any page. Then run `python3 generator/check_site.py`, which checks that known records render, that place lists run in date order, that approximate points never look surveyed, and that every internal link resolves.

To refresh the passages after more sources are read, run `python3 learn/tools/verify_quotes.py` in `tartary-corpus` (it needs the cited text volumes checked out), then `python3 generator/import_passages.py /path/to/tartary-corpus --unmatched` here, add any worthwhile unmatched place names to `data/passage_places.json`, and rebuild.

To refresh the data after the site data layer changes, copy `site-data/data/*.json` from `tartary-corpus` into `data/` and rebuild. Keep `data/corrections.json`.

Site-wide settings (name, address, repository link, researcher, podcast link) sit in `CONFIG` at the top of `generator/build.py`.

## Pages

* `/` the front door: Ortelius's map of Tartary across the whole page (OpenSeadragon 4.1.0 from cdnjs; the static site reads the Library of Congress tiles, the preview its own copy). Places he lettered that the sources write about are pinned on it (a dot for a town, a ring for a wider name); a diamond is a note the mapmaker wrote on the sheet and opens a slip with plain words and the Latin. The question sits on the map like a cartouche and "One passage from the record" rises from its lower edge. The passage is drawn at random on every visit (`FEATURE_PER_TRAIL`, `FEATURE_PER_SOURCE`, plus `FRONT_PER_PIN` passages for every pin); when it is about a pinned place the map travels there. Pressing a pin draws a passage from that place. The map can be dragged and pinched where it sits; "Roam the map" gives it the whole window, and only there does the wheel zoom, so the page still scrolls past the map. Without the viewer the still picture stays and the passages work as before. Below: One name, many hands (the lettering strip), five question trails, the door to the deck, a strip of old maps, three rides, six witnesses and the vault, with an ornament set into the rule between each.
* `/passages/` and `/passages/<trail>/` the passage explorer (cities, architecture, customs, names, outliers): search with the found words marked, how the author knew, century, order, shuffle, a count of what matches and a Clear filters button. Each menu shows how many passages every choice would give. Reads `assets/passages-<trail>.json`.
* `/deck/` the deck: three cards dealt from the strength 3 passages, one place (Cities, Buildings), one people (Daily life, The name), one marvel (Strange tales). Each trail is a suit with an ornament cut from the maps (`SUITS`, `SPREAD` in the generator). A card turns when pressed and its passage is set out in full below, where it can be saved as a picture (drawn on a canvas, 1080 by 1512). Back brings the same hand. Script: `TA.modules.deck`.
* `/ride/` and `/ride/<key>/` ride with a traveler: six journeys from `data/journeys.json`. The map is drawn at build time from the self-hosted basemap, fitted to the stops (`RideMap`). The stops scroll past it; the stop under the reader's eye is the current one, the line draws itself to it and a rider cut from Delisle's map travels along it. The arrows and the dots on the map go to a stop too. Rough positions are dotted. Each ride ends with what is still uncertain. Without script the whole line is drawn. Script: `TA.modules.ride`.
* `/dial/` the time dial: thirteen Library of Congress maps from 1516 to 1894, each bent onto one shared sheet of the real earth (an equidistant conic of Asia), with three earlier stops that have no sheet (Rubruck's road, the Hereford map, the Borgia map). The wheel on the ruled scale is the dial: dragging it fades each sheet into the next and letting go settles on the nearest map; the arrows, the marks on the scale, the arrow keys and "Let it run" do the same. Every lettering of Tartary is outlined on the sheet (carmine for a country, dashed gold for a people or a sea, blue for the other big names) and listed under it; pressing a name picks it out. "Lift the old sheet" shows the outlines on the bare earth and "Keep earlier names" leaves the earlier maps' outlines on as ghosts. The bend is stiff on purpose, so a sheet keeps its own shape and its errors show; each card says how many places hold it and how far off a place lands when left out. Without script every stop is listed in order under Delisle's sheet. Script: `TA.modules.dial`; generator: `DialSheet`, `page_dial`, `dial_band`.
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
* The name in the header is lettering cut from one of the maps (`wordmark` in the generator, `TA.wordmark` in the script). One map lends its hand for a whole visit; the next visit draws another. The line under it names the mapmaker and links to the map.
* A cut (`cut`, `orn`, `orn_rule` in the generator; `.cut` in the stylesheet) is a picture of ink alone, painted in the text colour through a CSS mask, so it works on both themes. The picture's address is written in the element's own style, because an address inside a stylesheet variable is read from the stylesheet's folder.
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
* The bent sheets in `static/dial/` are made from Library of Congress pictures only (the same terms as the cuts below; five of the thirteen maps are not in the catalogue and are linked to their Library of Congress pages instead).
* The lettering and ornaments in `static/cuts/` are cut from Library of Congress pictures only, which the Library offers without known restrictions for these maps; confirm each item's rights statement before going public. The About page credits every piece.
* Map viewer on the front page: OpenSeadragon 4.1.0 (BSD-3-Clause), loaded from cdnjs.
* Map images load from each holding library's IIIF server; apart from the cuts above, nothing is copied into this repository or the static site. The private preview artifact carries its own small copies, because an artifact cannot load images from other sites. Check each library's terms before copying pictures anywhere public (David Rumsey: CC BY-NC-SA; Bodleian: CC BY-NC; the Vatican Library reserves rights).
* The vegetable lamb engraving is from Henry Lee, The Vegetable Lamb of Tartary (1887), via Wikimedia Commons, public domain.
* Fonts: Newsreader, Public Sans, IBM Plex Mono, and IM Fell English SC (Igino Marini) for the wordmark, from Google Fonts.

## Names the visitor sees

The navigation reads In their words (`/passages/`), Map room (`/maps/`), Wander the map (`/map/`), Witnesses (`/sources/`), The vault (`/archive/`), About. Inside the vault: The many Tartarys (`/labels/`), Who counted as a Tartar? (`/meanings/`), Who copied whom (`/lineage/`), Every book and map (`/records/`), Every place (`/places/`), Who's who (`/peoples/`), How it was made (`/method/`), Spot a mistake? (`/corrections/`). Addresses did not change. Visitor-facing copy avoids the project's working words (record, card, catalogue, IIIF, read for passages, profile only); How it was made is the one page that explains the machinery.
