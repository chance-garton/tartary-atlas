# Grand Tartary storybook landing page

October 3, 2026. Implements Chance’s request for an open medieval storybook as the Atlas landing page.

## Experience

Eight spreads pair a manuscript-style illustration with a short chapter and an ink inscription linking to a feature. Side ribbons jump to the opening, words, maps, journeys, time, chance, places, and vault. CSS constructs the leather boards, gilt corners, page block, gutter, and ribbon bookmark. Desktop page turns show front and back faces; smaller screens use stacked leaves and a short transition. Keyboard arrows, Home/End, swipe, chapter deep links, and browser history are supported. Reduced motion removes the animation; no-script mode shows the complete book.

The prior interactive homepage is preserved at `/frontispiece/`, reached by “Unfold the first map.” Its original map, pinned places, map notes, random passage book, trails, and deeper navigation remain. All other feature routes and source material are unchanged. The requested removal of the name-lettering section remains in place.

## Validation

- Static build: 946 content pages; all site checks pass.
- `review/storybook-checks.cjs`: no-script access, all eight illustrations and entrances, reduced motion, side tabs, keyboard boundaries, history, forward/back leaf faces, cleanup, unique IDs, mid-turn history, mobile swipe.
- `review/cabinet-checks.cjs`: all 2,029 quotations, translations, attribution, context, citations and cautions; collection, reading desk, search, deep links, time dial, discovery deck, and the relocated original passage book.
- Browser review: desktop at 1280 px, tablet at 768 px, and phones at 390/320 px. No horizontal overflow, including the 305 px content width produced by the narrowest frame. Checked chapter tabs, page turns, disabled last-page control, illustration rendering, and all eight chapters with JavaScript disabled. The first review exposed page-width crowding of the ribbon labels; explicit page width and extra side allowance corrected it. Image-edge masking makes the paintings sit on the parchment. A retained inner-page script expected a reading dialog on the landing page; the landing now loads only its own script. Cold chapter images are decoded before turning the leaf.

Reduced motion and touch swipe were exercised in DOM integration checks; physical touch hardware and OS-level reduced-motion emulation were not used. The artwork is served locally with the site; fonts remain an external dependency. The existing repository README was deliberately left unchanged.

## Artwork and prompts

Built-in image generation was used, one generation per illustration. Images are decorative modern work, not historical source imagery. Production assets are `static/storybook/{frontispiece,reading,maps,journeys,time,discovery,atlas,archive}.webp`, copied by the generator to `docs/assets/storybook/`. Each is optimized to 800 × 1200; approximately 2.4 MB for the complete set. The opening and neighboring chapter are loaded first, with later illustrations loaded as needed.

Each exact prompt consisted of this shared specification followed by the corresponding scene below:

> Use case: illustration-story. Asset: a single full-page illustration for the LEFT leaf of a premium medieval Grand Tartary storybook website. Portrait 2:3 format. Hand-painted illuminated manuscript miniature, delicate sepia pen outlines, egg tempera, finely hatched texture, restrained lapis and faded teal, ochre, burnished gold and small oxblood accents. Warm pale ivory parchment ground (#eee0be), not dark or stained. Flat medieval perspective and exquisite miniature detail, grown-up and museum-book quality. One coherent central scene contained within a fine irregular gold-and-ink architectural arch with tiny vine flourishes, with generous parchment margins on all four sides. No page title, no words, no readable text, no numbers, no UI, no physical book mockup, no photograph. Edges should melt softly into clean pale ivory parchment. This is clearly a modern decorative illustration inspired by manuscripts, not a purported historical document. Scene: 

### frontispiece

An immense storybook landscape of Grand Tartary: a walled Central Asian oasis city with turquoise cupolas, tiled gateways, distant mountain passes, and a small camel caravan arriving across the steppe. A sense of opening a wondrous historical travel book.

### reading

A medieval scholar in a deep oxblood robe reading an open manuscript at a wooden writing desk in a pointed-arch alcove; several handwritten books, a quill and ink, a small candle, and a distant Central Asian city visible through the arch.

### maps

A medieval cartographer's table viewed at a graceful oblique angle: a richly drawn rolled-out old map with miniature mountains and towns, brass dividers, a compass rose and one armillary sphere, beneath an arched window.

### journeys

A small caravan of riders on horseback and laden Bactrian camels winds across ochre steppe into a high blue mountain pass, with a felt tent and a fortified town in the distance. Spacious, lyrical medieval travel narrative.

### time

A magnificent medieval brass astrolabe surrounded by a sun and a crescent moon, fine stars, a sand hourglass, and flowing ribbons of parchment. The brass astrolabe is large and central; its rings imply the passage of centuries. Allegorical manuscript illumination, not a technical diagram.

### discovery

Five beautiful illustrated miniature parchment cards laid in an overlapping fan on a scholar's table: a walled city, a yurt, a horseman, an ornate letter T, and a curious botanical lamb. A hand in a medieval sleeve gently turns one card. Playful mystery, refined illuminated medieval manuscript.

### atlas

A lyrical bird's-eye medieval painted landscape: a river connects walled towns, a blue lake, mountain ranges, felt tents and a distant caravan. A small decorative compass rose in a corner. The landscape is a storybook illustration, not an accurate map.

### archive

A medieval vaulted library and archive with warm old stone arches, shelves of leather-bound manuscripts, a wooden chest containing scrolls, an open book on a lectern and soft gold light falling through a narrow window. Rich discovery and quiet mystery.
