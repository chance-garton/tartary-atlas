# Homepage parchment study

Stage 1 only, prepared October 2, 2026. Awaiting Chance's design review. Do not merge or deploy until approved.

The opening gives visitors four routes into the collection before the map. The Ortelius sheet opens in full, with its existing place pins and mapmaker's notes. A new Whole map control restores that view. Selecting a place offers a short note with a Read below button, so the passage beneath the map is discoverable.

The featured passage uses a homepage-only manuscript treatment: the quotation, author and original-page citation remain visible; editorial context expands on request. Cautions, original wording, evidence labels, and links into the source remain available. The page explicitly distinguishes the map from independent written sources.

`static/css/home.css` is loaded only by the static homepage, scoped under `.atlas-home`. The legacy single-file preview embeds it and toggles that class as routes change. No shared passage-card markup or site-wide stylesheet has changed. All 944 other generated content pages are byte-identical to the starting commit. The time dial and private corpus have not been changed.

## Validation

- `python3 generator/build.py --static`: 945 content pages generated.
- `python3 generator/check_site.py`: all checks pass, including 2,029 passages, 28 homepage places, 11 map notes, six journeys, 26 dial maps and internal links.
- `node --check static/js/site.js`: passed.
- Browser: homepage and map-room navigation; full-screen entry and Escape; zoom and whole-map reset; Samarkand pin, matching passage and Read below; Draw another; expanding editorial context.
- Responsive review at desktop, 768 px, 390 px and 320 px. The original wide lettering strip was constrained to prevent overflow at the smallest size.
- JavaScript-disabled review preserves a still map, featured quote and original citation; unavailable map controls stay hidden.
- Reduced motion: CSS animation and transitions disabled; OpenSeadragon animations set to zero when the preference is active. This preference was reviewed in code, not emulated in the browser.
- The documented static-only checker previously tried to read a nonexistent legacy preview. It now checks that optional file only when present.

The full legacy single-file build was not run: it requires an uncommitted cache of all map images. The review uses the actual static output and its existing library image services. The `review/` harness is outside the deployed `docs/` folder and allows switching widths and disabling JavaScript.

## Decorative asset

`static/textures/home-parchment.webp` (102,656 bytes) is a generated decorative material, not historical evidence. Created with the built-in image-generation tool; converted to WebP for delivery. Original maps, scans, ornaments and lettering were not regenerated.

Prompt: Use case: photorealistic-natural. Asset type: seamless decorative background material for a historical atlas website. Generate a square, flat overhead macro scan of warm ivory antique vellum parchment, subtle irregular natural fibers, softly mottled cream and pale flax tones, tiny sparse flecks, restrained age and slight handmade undulation. Entire frame is uninterrupted paper, uniformly softly lit. Very low contrast, suitable underneath dark readable typography. Authentic tactile archival material, refined not grungy, warm ivory rather than orange. Seamless tileable edges. No writing, no symbols, no objects, no borders, no torn edges, no vignette, no watermarks. This is only a blank paper material; no historical evidence or map is to be depicted.

## Next action

Collect Chance's feedback on the homepage materials, opening copy, map framing and manuscript excerpt. Revise this stage before merging. Shared passage-card redesign, dial usability, dedicated mobile polish and Ask the Archive remain queued.
