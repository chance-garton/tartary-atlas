"""An illustrated front door. Decorative art never stands in for source evidence."""
from html import escape


CHAPTERS = [
    dict(key="opening", tab="Opening", title="Grand Tartary", subtitle="An invitation to the unknown", art="frontispiece", caption="A world waiting between the leaves",
         paragraphs=["Beyond the familiar edge of old maps lies a name that once stretched across Asia: Tartary. Cities, caravan roads, distant courts, and extraordinary tales fill the pages left behind.",
                     "This Atlas gathers those maps and voices. Turn the leaves to choose your own way into their world."],
         link="Unfold the map", route="explore", note="Ortelius’s Tartary, 1570", alt="A manuscript-style painting of a caravan approaching a walled Central Asian city beneath distant mountains."),
    dict(key="words", tab="Words", title="Voices from afar", subtitle="The reading room", art="reading", caption="Let the witnesses tell their tales",
         paragraphs=["A traveler enters a strange city. An envoy is welcomed at court. A chronicler records a custom that astonishes him. Their words are still here, waiting to be read.",
                     "Explore passages about cities, buildings, daily life, names, and marvels. Every quotation leads back to its source."],
         link="Enter the reading room", route="passages", note="Stories in the witnesses’ own words", alt="A robed scholar reads an open manuscript in a medieval arched study."),
    dict(key="maps", tab="Maps", title="The painted world", subtitle="The map room", art="maps", caption="Every mapmaker saw a different world",
         paragraphs=["Mountains rise like little crowns. Rivers wander through kingdoms. A name stretches across the blank spaces. Each map offers a world as its maker imagined and understood it.",
                     "Wander through centuries of original maps. Look closely at their lettering, their borders, and the remarkable details hiding in the margins."],
         link="Step into the map room", route="maps", note="Original sheets, open to a closer look", alt="An illuminated manuscript scene of a cartographer’s table with a map, dividers, and an armillary sphere."),
    dict(key="journeys", tab="Journeys", title="Across the steppe", subtitle="Ride with a traveler", art="journeys", caption="A road is a story told one stop at a time",
         paragraphs=["Saddle a horse. Cross a river. Arrive at a city whose name you have only seen on parchment. Follow the roads of travelers who ventured into Tartary and wrote of what they found.",
                     "Six journeys unfold stop by stop, with the route beside you and the traveler’s words along the way."],
         link="Choose a journey", route="ride", note="Follow a witness into the distance", alt="A caravan of horsemen and Bactrian camels crosses the steppe toward a mountain pass."),
    dict(key="time", tab="Time", title="The turning ages", subtitle="The time dial", art="time", caption="Turn the centuries beneath your hand",
         paragraphs=["Tartary never sits still on the page. Through the centuries, mapmakers place the name differently, stretch its reach, and draw new boundaries around it.",
                     "Turn the dial to lay one historical sheet over another. Watch the maps change, lift a sheet, and follow the traces of earlier names."],
         link="Turn the time dial", route="dial", note="Many maps upon one shared earth", alt="A golden astrolabe, sun, crescent moon, and hourglass in the style of a manuscript illumination."),
    dict(key="chance", tab="Chance", title="A little serendipity", subtitle="The discovery deck", art="discovery", caption="You need not know what you are seeking",
         paragraphs=["Perhaps today brings a great city, an unfamiliar custom, or a tale strange enough to linger in your mind. Let the archive surprise you.",
                     "Draw a hand of illustrated cards. Turn one over to discover a passage, then follow its thread as far as curiosity carries you."],
         link="Draw from the deck", route="deck", note="A place, a people, a marvel", alt="A medieval sleeve reaches toward a fan of illustrated cards showing a city, a tent, a rider, a letter, and a botanical lamb."),
    dict(key="places", tab="Places", title="Where stories meet", subtitle="The living atlas", art="atlas", caption="Every place holds more than one story",
         paragraphs=["A river in one account becomes a crossing in another. A city welcomes travelers centuries apart. Place the witnesses side by side, and new paths begin to appear.",
                     "Explore the places named in the record. Follow a town, a region, or a people back to the sources that describe them."],
         link="Wander the living atlas", route="map", note="Find the stories gathered around a place", alt="A decorative manuscript landscape of connected rivers, walled towns, mountains, and tents."),
    dict(key="vault", tab="Vault", title="Deeper in the archive", subtitle="The scholar’s vault", art="archive", caption="For the curiosity that keeps you reading",
         paragraphs=["Every discovery has another door behind it. Meet the writers, trace the families of old maps, and seek the places and peoples scattered through their pages.",
                     "The vault opens the whole catalogue, along with the research notes and the questions that remain. There is always another thread to follow."],
         link="Open the scholar’s vault", route="archive", note="Books, maps, witnesses, and unfinished questions", alt="A vaulted medieval library with leather-bound books, scrolls, a chest, and an open manuscript on a lectern."),
]
PAPER = {"frontispiece": "#efd6ae", "reading": "#eed5aa", "maps": "#eed2a4", "journeys": "#ecd2a5",
         "time": "#f0d3a5", "atlas": "#f0d5ab", "archive": "#edd4af", "discovery": "#ecd3ad"}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def page(site, ctx):
    spreads, tabs = [], []
    for i, ch in enumerate(CHAPTERS):
        heading = "h1" if i == 0 else "h2"
        paragraphs = ''.join(f'<p>{escape(p)}</p>' for p in ch['paragraphs'])
        art = ctx.asset('storybook/' + ch['art'] + '-poster.webp')
        priority = 'fetchpriority="high"' if i == 0 else ''
        spreads.append(
            f'<section class="story-chapter" id="chapter-{ch["key"]}" data-chapter="{ch["key"]}" aria-label="{escape(ch["title"])}" style="--book-paper:{PAPER[ch["art"]]}">'
            f'<div class="story-page story-page-art"><span class="story-running">The Tartary Atlas</span>'
            f'<figure class="story-illumination"><div class="story-media"><img src="{art}" alt="{escape(ch["alt"])}" width="720" height="1080" '
            f'loading="{"eager" if i == 0 else "lazy"}" decoding="async" {priority}>'
            f'<video data-book-video data-src="{ctx.asset("storybook/" + ch["art"] + ".mp4")}" poster="{art}" '
            f'width="720" height="1080" muted loop playsinline preload="none" aria-hidden="true" tabindex="-1"></video></div>'
            f'<figcaption>{escape(ch["caption"])}</figcaption></figure>' 
            f'<span class="story-folio" aria-hidden="true">{2*i+1}</span></div>'
            f'<div class="story-page story-page-text"><span class="story-running">{escape(ch["subtitle"])}</span>'
            f'<div class="story-writing"><p class="story-chapter-number">Chapter {ROMAN[i]}</p>'
            f'<{heading} class="story-title">{escape(ch["title"])}</{heading}>'
            f'<div class="story-flourish" aria-hidden="true">❧</div>'
            f'<div class="story-prose">{paragraphs}</div>'
            f'<a class="story-inscription" href="{ctx.link(ch["route"])}"><span aria-hidden="true" class="story-manicule">☞</span> {escape(ch["link"])}</a>'
            f'<p class="story-link-note">{escape(ch["note"])}</p></div>'
            f'<span class="story-folio" aria-hidden="true">{2*i+2}</span></div></section>')
        tabs.append(f'<a href="#chapter-{ch["key"]}" class="story-tab" data-book-tab="{i}" aria-controls="chapter-{ch["key"]}"'
                    f' aria-label="Chapter {ROMAN[i]}: {escape(ch["title"])}"><span class="story-tab-number" aria-hidden="true">{ROMAN[i]}</span><span>{ch["tab"]}</span></a>')
    body = (
        '<div class="storybook-world"><div class="story-masthead"><a href="#chapter-opening" data-book-home>The Tartary Atlas</a>'
        '<span>A book of discoveries</span></div>'
        '<div class="story-scene"><div class="story-volume" data-storybook>'
        '<div class="story-cover" aria-hidden="true"><i></i><i></i><i></i><i></i></div>'
        '<div class="story-page-block" aria-hidden="true"></div>'
        '<nav class="story-tabs" aria-label="Book chapters">' + ''.join(tabs) + '</nav>'
        '<div class="story-spreads">' + ''.join(spreads) + '</div>'
        '<div class="story-spine" aria-hidden="true"></div>'
        '<div class="story-turner" aria-hidden="true" hidden><div class="story-turner-front"></div><div class="story-turner-back"></div></div>'
        '<nav class="story-page-turns" aria-label="Turn the pages" hidden><button type="button" data-book-prev aria-label="Previous page"><span aria-hidden="true">☜</span> Previous leaf</button>'
        '<button type="button" data-book-next aria-label="Turn the page">Turn the page <span aria-hidden="true">☞</span></button></nav>'
        '<div class="story-ribbon" aria-hidden="true"></div></div></div>'
        '<div class="story-colophon"><span data-book-position>Chapter I of VIII</span><span class="story-hint">Turn a leaf, or choose a ribbon.</span>'
        '<button type="button" class="story-motion" data-book-motion hidden>Pause illustrations</button>'
        f'<a href="{ctx.link("about")}">A work by Chance Garton</a></div>'
        '<p class="sr-only" role="status" aria-live="polite" aria-atomic="true" data-book-status></p></div>'
    )
    return dict(title="Grand Tartary · The Tartary Atlas", description="Open an illustrated book of discoveries. Explore Tartary through historical maps, travelers’ journeys, and the words of the witnesses.",
                body=body, nav="", modules=[], bare_title=True, storybook=True)


def footer(ctx):
    return (f'<footer class="story-footer"><a href="{ctx.link("method")}">About the research</a><span aria-hidden="true">❦</span>'
            f'<a href="{ctx.link("corrections")}">Notes &amp; corrections</a></footer>')
