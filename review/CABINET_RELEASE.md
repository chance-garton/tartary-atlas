# The scholar’s cabinet

A broad creative overhaul requested by Chance Garton on October 2, 2026. This supersedes the earlier page-by-page scope restrictions. Based on main `64ba28ff7a9eba42b9fbefe3f6ff229719ef7088`, including the approved homepage book and time-dial improvements. Production publication remains a separate approval from this review branch.

## Experience

- A dark walnut map table, dimensional original Ortelius sheet, antique serif typography, burnished brass and oxblood leather.
- A compact header and native Explore menu connecting all six primary features, with witnesses, the vault and project information one level below.
- Six constructed CSS objects: a bound volume, folded map, itinerary, brass instruments and a fanned card deck. Fine-pointer tilt responds to the visitor; reduced-motion disables it.
- A shorter homepage. The map, six entrances, open anthology and thematic trails remain prominent; additional archive material is still available in a disclosure.
- Quotation-first passage cards with editorial context on demand. All cautions remain expanded by default.
- A shared reading desk, with exact quoted text and source metadata, printed introductions, separate research controls, keyboard leaf navigation, and quotation-first phone pages.
- Search across books, maps, places, people, aliases and dates. Full passage text is handled by the existing passage search.
- A persistent collection in local browser storage, with explicit remove controls and stable source links. No account, telemetry, or server write. A storage failure falls back to the current visit and says so.
- A draggable and keyboard-accessible brass rotary control tied to the existing time-dial source selector. The existing map alignment, date precision, interpretive distinctions, overlays and playback are preserved.
- Framed gallery maps; an itinerary selector and progress line for journeys; large swipeable cards on phones.

## Decorative asset

Path: `static/textures/scholars-desk.webp` (also copied to `docs/assets/`). Built-in image generator; the 1536 × 1024 output was converted to WebP, about 170 KB. It is decoration, never evidence. Exact generation prompt:

> Use case: stylized-concept. Asset type: decorative background for a premium interactive historical atlas website, not historical evidence. Create a cinematic tactile late-medieval scholar's desk seen from directly overhead, wide landscape 3:2 composition. Very dark weathered walnut tabletop occupies nearly the entire frame, near-black warm umber with nuanced visible fine wood grain, patinated brass dividers and the corner of a deeply worn oxblood leather folio at the far lower left edge, the tiniest corner of an unlettered rolled parchment at the far upper right edge, a small pooled warm candle glow spilling in from the far top left. The broad central 80 percent must be empty, uninterrupted dark walnut where real map content will later be overlaid. Restrained luxurious museum photography, physically realistic surface texture, deep cinematic soft shadows, burnished honey highlights, genuine material detail, subtle vignette. No readable text, no writing, no maps, no globe, no symbols, no magical effects, no people, no UI. This is a quiet beautiful background material, never busy. Full bleed.

All 3D objects and interactions use CSS transforms and DOM controls. There is no new 3D engine, model service, or WebGL dependency. Original source maps remain unmodified.

## Verification

- Static generator builds 945 content pages, plus the existing 404 page.
- All site checks pass, including internal links, dates, all 2,029 source passages, map pins, journey stops, and 26 historical dial maps.
- Integration checks compare every dynamically rendered passage against its exact quote/translation, editorial context, author, scan URL, and caution state.
- Reader citations match the originating card; printed pages have no interactive controls; IDs remain unique; previous/next and collection actions work.
- Saved collections persist across page visits. Deep links reveal passages beyond the initial set. Query parameters populate and filter the passage explorer.
- Rotary keyboard navigation reaches the first and last of all 29 stops, synchronized with the established selector. Deck dealing, reveal, reading, and collection controls pass.
- Homepage page turning still uses inert decorative leaves, rapid-click protection, and reduced-motion support.
- Browser review covers desktop, tablet and 390/320 px frames, navigation, reading desk, card reveal, global search, and major feature layouts. A narrow-gallery overflow was found and fixed. Screenshots and final review links are attached to the pull request when available.
- JavaScript syntax and git whitespace checks pass. `data/`, `static/dial/`, `static/cuts/`, source image URLs and the private corpus are unchanged.
- Final browser confirmation: the map gallery and expanded menu fit a 305 px content viewport; phone reading opens with the quotation before the introduction; the rotary End key selects 1894, stop 29 of 29. Section and saved-passage links allow for the sticky header.

Review screenshots: `cabinet-desktop-1790978931347.jpg` and `cabinet-rooms-1790978963492.jpg` in this directory.

Limits: reduced motion is verified with simulated media preferences in the integration checks and CSS inspection, not an OS setting in the cloud browser. The responsive harness uses an iframe; actual touch hardware has not been tested. Historical image services and fonts retain their existing external dependencies. Saved collections are browser-local, not synchronized across devices.
