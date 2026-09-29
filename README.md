# The Tartary Atlas

An open explorer of what the historical record says about Tartary: 303 written sources and 119 maps, every place they name, when, and how each author knew. A research project by Chance Garton, discussed on the InnerVerse Podcast.

Planned address: `https://tartary.innerversepodcast.com`

## What is in this repository

| Path | What it holds |
|---|---|
| `data/` | The site data layer: `records.json`, `places.json`, `places.geojson`, `peoples.json`, `people_families.json`, `lineage.json`, `iiif.json`, `meta.json`. Copied from the private `tartary-corpus` repo (`site-data/data/`). Derived data, short card text and links only. |
| `data/corrections.json` | Published corrections applied at build time. Each one names the record, the field, the old and new wording, the reason and its sources. The Corrections page lists them. |
| `generator/build.py` | The site generator. Python 3, standard library only. |
| `generator/prepare_basemap.sh` | Rebuilds the self-hosted basemap from Natural Earth. |
| `static/` | Stylesheet, page script, MapLibre stylesheet, and the basemap GeoJSON. |
| `docs/` | The generated site, one HTML file per page. GitHub Pages serves this folder. |
| `preview/` | A single-file preview of the same pages (not committed). |

## Build

```
python3 generator/build.py            # writes docs/ and preview/
python3 generator/build.py --static   # docs/ only
```

The build fails if a correction no longer matches its record, and fails if an em dash appears in any page.

To refresh the data after the site data layer changes, copy `site-data/data/*.json` from `tartary-corpus` into `data/` and rebuild. Keep `data/corrections.json`.

Site-wide settings (name, address, repository link, researcher, podcast link) sit in `CONFIG` at the top of `generator/build.py`.

## Pages

* `/` the map explorer: MapLibre GL JS with a self-hosted Natural Earth basemap, a date range, and filters for kind, evidence class and language tradition.
* `/records/`, `/places/`, `/peoples/` browse pages.
* `/w/W122/`, `/m/M081/` one page per record: dates with precision, places and peoples, the "How we know" panel, access and IIIF links, map lineage.
* `/place/<id>/` and `/peoples/<id>/` every record naming the place or people, in date order.
* `/labels/` when each Tartary label (Tartary, Great, Little, Chinese, Independent, Muscovite, Eastern, Desert) appears.
* `/meanings/` what "Tartar" meant, source by source (card-level and provisional until the passage layer exists).
* `/lineage/` which maps copied, reissued or corrected which.
* `/about/`, `/method/`, `/corrections/`.

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
* Map images load from each holding library's IIIF server; nothing is copied here.
* Fonts: IM Fell English (Igino Marini), Public Sans, IBM Plex Mono, from Google Fonts.
