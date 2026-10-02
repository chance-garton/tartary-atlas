"""Presentation helpers for the Atlas cabinet. Evidence stays in build.py/data/."""
import html
import json


def icon(name):
    paths = {
        "compass": '<circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5L16 8Z"/>',
        "book": '<path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v14c-4-1-6 0-9 2-3-2-5-3-9-2V4Z"/>',
        "map": '<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2V5Zm6-2v16m6-14v16"/>',
        "route": '<circle cx="5" cy="18" r="2"/><circle cx="19" cy="5" r="2"/><path d="M7 18h9a4 4 0 0 0 0-8H8a3 3 0 0 1 0-6h9"/>',
        "time": '<circle cx="12" cy="13" r="9"/><path d="M12 7v6l4 2M9 1h6M12 1v3"/>',
        "cards": '<path d="m4 6 11-3 5 16-11 3L4 6Z"/><path d="M4 16H2V1h12M10 11l3-2 2 3-3 2-2-3Z"/>',
        "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
        "save": '<path d="M6 3h12v18l-6-4-6 4V3Z"/>',
        "close": '<path d="m6 6 12 12M18 6 6 18"/>',
        "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
        "vault": '<path d="M3 5h18v16H3V5Zm-1 0 10-4 10 4M7 9v8m5-8v8m5-8v8"/>',
    }
    return f'<svg class="atlas-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths.get(name, paths["compass"])}</svg>'


ROOMS = [
    ("passages", "book", "The reading room", "Words across centuries", "I"),
    ("maps", "map", "The map room", "The world in many hands", "II"),
    ("ride", "route", "The journeys", "Six roads into Tartary", "III"),
    ("dial", "time", "The time dial", "Watch the name move", "IV"),
    ("deck", "cards", "The discovery deck", "Leave a little to chance", "V"),
    ("map", "compass", "The living atlas", "Every place, every witness", "VI"),
]


def object_art(kind):
    # Constructed CSS objects, deliberately separate from source imagery.
    if kind == "book":
        return '<span class="obj-book"><i></i><b>ANTHOLOGIA</b><small>TARTARIA</small></span>'
    if kind == "map":
        return '<span class="obj-map"><i></i><b>❦</b></span>'
    if kind in ("compass", "time"):
        return f'<span class="obj-astrolabe"><i></i><b>{icon("compass" if kind == "compass" else "time")}</b><em></em></span>'
    if kind == "cards":
        return '<span class="obj-cards"><i>✦</i><i>✦</i><i>✦</i></span>'
    return '<span class="obj-route"><i></i><b>✦</b><em></em></span>'


def room_cards(ctx, compact=False):
    cards = []
    for key, kind, title, detail, number in ROOMS:
        art = icon(kind) if compact else f'<span class="room-object" aria-hidden="true">{object_art(kind)}</span>'
        cards.append(f'<a class="room-door room-{kind}" href="{ctx.link(key)}" data-tilt>'
                     f'<span class="room-number" aria-hidden="true">{number}</span>{art}'
                     f'<span class="room-name">{title}</span><span class="room-note">{detail}</span>'
                     f'<span class="room-enter" aria-hidden="true">{icon("arrow")}</span></a>')
    return f'<div class="room-grid{" compact" if compact else ""}">{"".join(cards)}</div>'


def header(ctx, nav_key):
    quick = [("passages", "Read"), ("maps", "Maps"), ("ride", "Journeys"), ("dial", "Time")]
    links = ''.join(f'<a href="{ctx.link(k)}" data-nav="{k}"' + (' aria-current="page"' if nav_key == k else '') + f'>{t}</a>' for k, t in quick)
    index_links = ''.join(f'<a href="{ctx.link(k)}">{t}</a>' for k, t in [("sources", "Witnesses"), ("archive", "The vault"), ("about", "About the Atlas")])
    return (f'<a class="skip" href="#main">Skip to content</a><header class="site-header cabinet-header"><div class="bar">'
            f'<a class="atlas-brand" href="{ctx.link("")}" aria-label="The Tartary Atlas, front page"><span class="brand-seal">{icon("compass")}</span>'
            f'<span><b>Tartary</b><small>ATLAS OF THE HISTORICAL RECORD</small></span></a>'
            f'<nav class="site-nav" aria-label="Main">{links}</nav>'
            f'<div class="cabinet-actions"><button class="cabinet-tool" type="button" data-open-search hidden aria-label="Search the Atlas">{icon("search")}<span>Search</span></button>'
            f'<button class="cabinet-tool" type="button" data-open-saved hidden aria-label="Open your collection">{icon("save")}<span>Collection</span><small data-saved-count>0</small></button>'
            f'<details class="atlas-menu"><summary>{icon("compass")}<span>Explore</span></summary>'
            f'<nav class="cabinet-menu" aria-label="Explore the Atlas"><div class="menu-heading"><span class="eyebrow">Choose your next discovery</span></div>'
            f'{room_cards(ctx, True)}<div class="menu-index">{index_links}</div></nav></details></div></div></header>')


def dialogs(ctx):
    close = f'<button type="button" class="cabinet-tool dialog-close" data-close-dialog aria-label="Close">{icon("close")}</button>'
    return (f'<dialog class="atlas-dialog" id="atlas-search" aria-labelledby="search-title"><div class="dialog-head"><h2 id="search-title">Seek in the Atlas</h2>{close}</div>'
            f'<label class="global-search-label" for="global-search">A name, a place, a mapmaker</label>'
            f'<div class="global-search-box">{icon("search")}<input type="search" id="global-search" placeholder="Samarkand, Rubruck, 1706…" autocomplete="off"></div>'
            f'<p class="search-status" data-search-status role="status">Search books, maps, peoples, and places.</p><div class="search-results" data-search-results></div></dialog>'
            f'<dialog class="atlas-dialog" id="atlas-saved" aria-labelledby="saved-title"><div class="dialog-head"><div><span class="eyebrow">Your discoveries</span><h2 id="saved-title">The collection</h2></div>{close}</div>'
            f'<p class="collection-note">Kept in this browser.</p><div data-saved-list></div></dialog>'
            f'<dialog class="atlas-dialog reader-dialog" id="atlas-reader" aria-labelledby="reader-label"><div class="dialog-head"><h2 id="reader-label">The reading desk</h2>{close}</div>'
            f'<div data-reader-body></div><div class="reader-nav"><button class="btn" type="button" data-reader-prev>← Previous leaf</button><span data-reader-count role="status"></span>'
            f'<button class="btn primary" type="button" data-reader-next>Next leaf →</button></div></dialog>'
            f'<div class="atlas-toast" role="status" aria-live="polite" hidden></div>')


def home_rooms(ctx):
    return f'<section class="cabinet-rooms" id="explore"><div class="cabinet-section-head"><p class="eyebrow">Six ways into the record</p><h2>Choose your discovery.</h2></div>{room_cards(ctx)}</section>'


def search_index(site):
    items = []
    for r in site.records:
        profile = site.profiles.get(r["id"], {})
        items.append(dict(t=profile.get("plain_title") or r["title"], k="Map" if r["kind"] == "map" else "Book",
                          d=r["creator"] or "", u=site.rkey(r) + "/", x=r["title"] + " " + r["id"]))
    for p in site.places:
        items.append(dict(t=p["name"], k="Place", d=p.get("type", ""), u="place/" + p["id"] + "/"))
    for p in site.peoples:
        items.append(dict(t=p["name"], k="People", d="", u="peoples/" + p["id"] + "/"))
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))
