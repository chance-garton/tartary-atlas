# Homepage passage book · October 2, 2026

Request: make the homepage passage feel like a real dimensional ancient book and replace “Draw another” with “Turn the page.” Leave other passage locations for a later adaptation.

Built from main b6adaaa4b20876c27bb89745a00fe4932fc38259 on local branch design/homepage-passage-book. The existing step-3 dial release and its asset revisions are retained.

The homepage now has two vellum pages, leather boards, layered paper edges, a recessed binding, printed serif type and an initial capital. The source title leads the left page, followed by the printed attribution, date and an explicitly labeled editorial introduction. The passage title leads the right page above the exact quotation. Scan links, Copy quote, source navigation, evidence controls, original wording and cautions sit below the binding. All text on the pages uses book typography, with no interface buttons inside the printed spread. The turning right leaf exposes the next quotation, with the next source page on its reverse. Narrow screens retain a single-column book and turn the whole current passage. Reduced motion changes the content instantly. Source data and shared passage layouts are unchanged.

Validation completed: static build, all documented site checks, JavaScript syntax, and DOM behavior checks covering all 176 homepage passages for quote/translation/citation/caution preservation, rapid-click locking, inert decorative copies, animation completion, timeout completion, navigation cleanup, phone copy completeness, reduced motion, Back/Forward restoration and no-JavaScript markup. No other generated content pages are changed.

Chance approved the book materials and requested the typographic refinement, then explicitly authorized upload and live publication: “It can go live when you're done changing things.” This supersedes the initial upload approval block. The branch is based on the final time-dial release b6adaaa; the dial module, dial HTML, site-wide CSS, source data and all other generated content pages remain unchanged.

Browser review confirmed the source title precedes the introduction, page-turn completion, keyboard turning, layouts at 1280/768/390/320 px without horizontal overflow, and the Samarkand pin → Read below → matching passage flow. The evidence button expands its explanation. Reduced motion and all 176 passages were checked with the DOM harness. Visual review found and removed obsolete homepage card-order rules that had moved the title to the bottom of the left page. The responsive review is in review/homepage-book.html. Live publication and its release details are recorded in the running project handoff after deployment.

Local checkout: /workspace/scratch/0bf9217b47c7/tartary-atlas
Preview: /workspace/scratch/0bf9217b47c7/Tartary_Atlas_Homepage_Book_Preview.html

Future: adapt the accepted book language to other passage locations when requested. Dedicated mobile polish and Ask the Archive remain separate work.
