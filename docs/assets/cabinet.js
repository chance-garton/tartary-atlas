/* Progressive enhancements for the scholar's cabinet. No network writes. */
(function () {
  'use strict';
  function start() {
    var TA = window.TA;
    if (!TA) return;
    var $ = function (s, el) { return (el || document).querySelector(s); };
    var $$ = function (s, el) { return Array.from((el || document).querySelectorAll(s)); };
    var reduced = function () { return matchMedia('(prefers-reduced-motion: reduce)').matches; };
    var base = new URL(TA.href(''), location.href);
    var icon = function (name) {
      var d = name === 'save' ? '<path d="M6 3h12v18l-6-4-6 4V3Z"/>' : name === 'close' ? '<path d="m6 6 12 12M18 6 6 18"/>' : '<path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v14c-4-1-6 0-9 2-3-2-5-3-9-2V4Z"/>';
      return '<svg class="atlas-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
    };
    function node(tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text != null) n.textContent = text;
      return n;
    }
    function text(s, el) { var n = $(s, el); return n ? n.textContent.trim() : ''; }
    function destination(path) {
      var u = new URL(path, base);
      return u.origin === base.origin && u.pathname.indexOf(base.pathname) === 0 ? u.href : base.href;
    }
    var toastTimer;
    function toast(message) {
      var box = $('.atlas-toast');
      if (!box) return;
      box.textContent = message; box.hidden = false;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(function () { box.hidden = true; }, 3300);
    }

    /* The menu is a native disclosure and is useful before any script runs. */
    var menu = $('.atlas-menu');
    document.addEventListener('click', function (e) { if (menu && !menu.contains(e.target)) menu.open = false; });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu && menu.open) { menu.open = false; $('summary', menu).focus(); }
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.target.closest('input, textarea, select, [contenteditable="true"]') && !$('dialog[open]')) {
        e.preventDefault(); openSearch();
      }
    });
    $$('[data-close-dialog]').forEach(function (button) { button.addEventListener('click', function () { button.closest('dialog').close(); }); });
    $$('dialog.atlas-dialog').forEach(function (dialog) {
      dialog.addEventListener('click', function (e) {
        var r = dialog.getBoundingClientRect();
        if (e.target === dialog && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) dialog.close();
      });
    });
    function show(dialog) {
      if (!dialog || typeof dialog.showModal !== 'function') return false;
      if (menu) menu.open = false;
      if (!dialog.open) dialog.showModal();
      return true;
    }

    /* Search lazily downloads only the public catalogue index. */
    var searchDialog = $('#atlas-search'), searchInput = $('#global-search');
    var index = null, pending = null, querySerial = 0, searchTimer;
    function loadIndex() {
      if (index) return Promise.resolve(index);
      if (pending) return pending;
      pending = fetch(TA.asset('search-index.json')).then(function (r) { if (!r.ok) throw new Error('index unavailable'); return r.json(); }).then(function (data) {
        index = data; pending = null; return data;
      }).catch(function (e) { pending = null; throw e; });
      return pending;
    }
    function resultLink(item) {
      var a = node('a', 'search-result');
      a.href = destination(item.u);
      a.append(node('small', '', item.k), node('strong', '', item.t));
      if (item.d) a.append(node('span', '', item.d));
      return a;
    }
    function runSearch() {
      var query = searchInput.value.trim(), serial = ++querySerial;
      var box = $('[data-search-results]'), status = $('[data-search-status]');
      box.replaceChildren();
      if (!query) { status.textContent = 'Search books, maps, peoples, and places.'; return; }
      var passage = {t: 'Search passages for “' + query + '”', k: 'In their own words', d: 'Search the full text of the archive', u: 'passages/?q=' + encodeURIComponent(query)};
      box.append(resultLink(passage));
      status.textContent = 'Searching the catalogue…';
      loadIndex().then(function (items) {
        if (serial !== querySerial) return;
        var terms = query.toLowerCase().split(/\s+/);
        var matches = items.filter(function (it) { return terms.every(function (term) { return [it.t, it.d, it.x || ''].join(' ').toLowerCase().includes(term); }); });
        matches.sort(function (a, b) { return Number(b.t.toLowerCase().includes(query.toLowerCase())) - Number(a.t.toLowerCase().includes(query.toLowerCase())); });
        matches.slice(0, 14).forEach(function (it) { box.append(resultLink(it)); });
        status.textContent = matches.length ? matches.length + ' catalogue matches' + (matches.length > 14 ? ' · showing the first 14' : '') : 'No catalogue matches. Try the full passage search.';
      }).catch(function () { if (serial === querySerial) status.textContent = 'The catalogue could not load. Passage search is still available below.'; });
    }
    function openSearch() { if (show(searchDialog)) { searchInput.focus(); if (searchInput.value) runSearch(); } }
    $$('[data-open-search]').forEach(function (button) { button.hidden = false; button.addEventListener('click', openSearch); });
    if (searchInput) searchInput.addEventListener('input', function () { clearTimeout(searchTimer); searchTimer = setTimeout(runSearch, 130); });

    /* A local collection. Store stable source links, not HTML or private data. */
    var KEY = 'ta:collection:v1', saved = [], durable = true;
    try {
      var raw = JSON.parse(localStorage.getItem(KEY) || '[]');
      if (Array.isArray(raw)) saved = raw.filter(function (it) { return it && typeof it.id === 'string' && typeof it.u === 'string' && typeof it.t === 'string' && /^[a-z]+\//.test(it.u); }).slice(0, 500);
    } catch (e) { durable = false; }
    function savedItem(id) { return saved.find(function (it) { return it.id === id; }); }
    function writeSaved() {
      try { localStorage.setItem(KEY, JSON.stringify(saved)); durable = true; } catch (e) { durable = false; }
      syncSaved();
    }
    function syncSaved() {
      $$('[data-saved-count]').forEach(function (n) { n.textContent = saved.length; });
      $$('[data-save-id]').forEach(function (b) {
        var active = !!savedItem(b.dataset.saveId);
        b.setAttribute('aria-pressed', String(active));
        b.innerHTML = icon('save') + '<span>' + (active ? 'Collected' : 'Collect') + '</span>';
        b.title = active ? 'Remove from your collection' : 'Save to your collection';
      });
    }
    function renderSaved() {
      var list = $('[data-saved-list]');
      list.replaceChildren();
      if (!saved.length) {
        var empty = node('div', 'collection-empty'); empty.innerHTML = icon('save');
        empty.append(node('h3', '', 'Your cabinet awaits.'), node('p', '', 'Collect a passage, book, or map as you explore. Your discoveries will be waiting here.'));
        list.append(empty); return;
      }
      saved.slice().reverse().forEach(function (it) {
        var row = node('div', 'collection-item'), remove = node('button', 'cabinet-tool');
        remove.type = 'button'; remove.innerHTML = icon('close'); remove.setAttribute('aria-label', 'Remove ' + it.t + ' from collection');
        remove.addEventListener('click', function () { saved = saved.filter(function (s) { return s.id !== it.id; }); writeSaved(); renderSaved(); });
        row.append(resultLink(it), remove); list.append(row);
      });
    }
    $$('[data-open-saved]').forEach(function (button) {
      button.hidden = false;
      button.addEventListener('click', function () { renderSaved(); show($('#atlas-saved')); });
    });
    function collect(item) {
      var exists = savedItem(item.id);
      if (exists) saved = saved.filter(function (s) { return s.id !== item.id; });
      else {
        if (saved.length >= 500) { toast('Your collection is full. Remove a discovery to make room.'); return; }
        saved.push(item);
      }
      writeSaved();
      toast(exists ? 'Removed from your collection' : durable ? 'Added to your collection' : 'Collected for this visit. Browser storage is unavailable.');
    }
    function passageItem(card) {
      var id = card.dataset.passageId || card.id;
      var record = (id.match(/W\d+/) || [])[0];
      if (!record) return null;
      return { id: id, t: text('.reader-right h3', card) || text('.book-passage-title, h3', card), k: 'Passage', d: text('.who', card), u: 'w/' + record + '/#' + id };
    }
    function addPassageTools(root) {
      var cards = root.matches && root.matches('.psg') ? [root] : $$('.psg', root);
      cards.forEach(function (card) {
        if (card.closest('dialog') || card.dataset.cabinetReady || card.closest('[inert]')) return;
        var links = $('.psg-links', card);
        if (!links) return;
        card.dataset.cabinetReady = 'true';
        var item = passageItem(card);
        if (item) {
          var save = node('button', 'passage-action'); save.type = 'button'; save.dataset.saveId = item.id;
          links.append(save);
        }
        if (!card.classList.contains('book-entry')) {
          var read = node('button', 'passage-action'); read.type = 'button'; read.dataset.openReader = '';
          read.innerHTML = icon('book') + '<span>Read at the desk</span>'; links.append(read);
        }
      });
      syncSaved();
    }
    addPassageTools($('#main'));
    var observer = new MutationObserver(function (changes) {
      changes.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType === 1 && (n.matches('.psg') || n.querySelector('.psg'))) addPassageTools(n); }); });
    });
    observer.observe($('#main'), { childList: true, subtree: true });
    document.addEventListener('click', function (e) {
      var button = e.target.closest('[data-save-id]');
      if (!button) return;
      var card = button.closest('.psg'), item = card ? passageItem(card) : button._item;
      if (item) collect(item);
    });
    var pageMatch = location.pathname.match(/\/(w|m|place|peoples)\/([^/]+)\/?$/);
    if (pageMatch) {
      var head = $('.page-head');
      if (head) {
        var pageItem = {id: 'page:' + pageMatch[1] + '/' + pageMatch[2], t: text('h1', head), k: {w:'Book',m:'Map',place:'Place',peoples:'People'}[pageMatch[1]], d: '', u: pageMatch[1] + '/' + pageMatch[2] + '/'};
        var pageButton = node('button', 'passage-action'); pageButton.type = 'button'; pageButton.dataset.saveId = pageItem.id; pageButton._item = pageItem; head.append(pageButton);
      }
    }
    syncSaved();
    window.addEventListener('storage', function (e) {
      if (e.key !== KEY) return;
      try { var data = JSON.parse(e.newValue || '[]'); if (Array.isArray(data)) { saved = data.filter(function (it) { return it && typeof it.id === 'string' && typeof it.u === 'string' && typeof it.t === 'string'; }).slice(0, 500); syncSaved(); if ($('#atlas-saved').open) renderSaved(); } } catch (_) { /* keep current collection */ }
    });

    /* A reading desk, built from the current exact passage DOM and its sources. */
    var reader = $('#atlas-reader'), readerCards = [], readerIndex = 0;
    reader.insertBefore($('.reader-nav', reader), $('[data-reader-body]', reader));
    function copy(el) {
      if (!el) return null;
      var c = el.cloneNode(true); c.removeAttribute('id');
      $$('[id]', c).forEach(function (n) { n.removeAttribute('id'); });
      return c;
    }
    function readCard(turn) {
      var original = readerCards[readerIndex];
      if (!original) return;
      var article = node('article', 'psg reader-document'); article.dataset.passageId = original.id;
      var spread = node('div', 'reader-spread'), left = node('div', 'reader-left'), right = node('div', 'reader-right');
      left.append(node('p', 'reader-running', 'The Tartary Atlas'));
      var sourceTitle = text('.psg-tale-t', original) || text('h1') || 'From the archive';
      left.append(node('h3', '', sourceTitle));
      var who = copy($('.who', original)); if (who) left.append(who);
      var context = $('.psg-context', original);
      if (context) { var introduction = node('section', 'reader-introduction'); introduction.append(node('h4', '', 'Editor’s introduction')); var gloss = copy($('.gloss', context)); if (gloss) introduction.append(gloss); left.append(introduction); }
      right.append(node('p', 'reader-running', 'In their own words'));
      var title = copy($('h3', original)), quote = copy($('blockquote', original));
      var originalWording = quote && copy($('details', quote));
      if (originalWording) $('details', quote).remove();
      if (title) right.append(title); if (quote) right.append(quote);
      right.append(node('p', 'reader-mobile-byline', text('.who', original)));
      spread.append(left, right); article.append(spread);
      var apparatus = node('div', 'reader-apparatus');
      ['.psg-meta', '.psg-foot', '.psg-links', '.psg-people', '.psg-notes', '.psg-tale'].forEach(function (selector) {
        var c = copy($(selector, original));
        if (c) { $$('[data-open-reader]', c).forEach(function (b) { b.remove(); }); apparatus.append(c); }
      });
      if (originalWording) apparatus.append(originalWording);
      article.append(apparatus);
      $('[data-reader-body]').replaceChildren(article);
      $('[data-reader-prev]').disabled = readerIndex === 0;
      $('[data-reader-next]').disabled = readerIndex >= readerCards.length - 1;
      $('[data-reader-count]').textContent = 'Leaf ' + (readerIndex + 1) + ' of ' + readerCards.length;
      if (turn && !reduced()) right.classList.add('turning');
      reader.scrollTop = 0; syncSaved();
    }
    function openReader(card) {
      var scope = card.closest('.psg-list') || $('#main');
      readerCards = $$('.psg:not(.book-entry)', scope).filter(function (c) { return !c.hidden && !c.closest('details:not([open])'); });
      if (!readerCards.includes(card)) readerCards = [card];
      readerIndex = readerCards.indexOf(card); readCard(false); show(reader);
    }
    document.addEventListener('click', function (e) { var b = e.target.closest('[data-open-reader]'); if (b) openReader(b.closest('.psg')); });
    $$('[data-read-first]').forEach(function (button) { button.hidden = false; button.addEventListener('click', function () { var c = $('.px-main .psg:not([hidden])'); if (c) openReader(c); else toast('No passages match your search.'); }); });
    $('[data-reader-prev]').addEventListener('click', function () { if (readerIndex > 0) { readerIndex--; readCard(true); } });
    $('[data-reader-next]').addEventListener('click', function () { if (readerIndex < readerCards.length - 1) { readerIndex++; readCard(true); } });
    reader.addEventListener('keydown', function (e) {
      if (e.target.closest('input, textarea, select')) return;
      if (e.key === 'ArrowRight' && readerIndex < readerCards.length - 1) { e.preventDefault(); readerIndex++; readCard(true); }
      if (e.key === 'ArrowLeft' && readerIndex > 0) { e.preventDefault(); readerIndex--; readCard(true); }
    });

    /* Physical depth, only on fine pointers. Nothing moves autonomously. */
    $$('[data-tilt]').forEach(function (el) {
      el.addEventListener('pointermove', function (e) {
        if (e.pointerType !== 'mouse' || reduced()) return;
        var r = el.getBoundingClientRect();
        el.style.setProperty('--tilt-y', ((e.clientX - r.left) / r.width * 8 - 4).toFixed(1) + 'deg');
        el.style.setProperty('--tilt-x', (4 - (e.clientY - r.top) / r.height * 8).toFixed(1) + 'deg');
      });
      el.addEventListener('pointerleave', function () { el.style.removeProperty('--tilt-x'); el.style.removeProperty('--tilt-y'); });
    });

    /* Rotary input reuses the established dial state machine and map evidence. */
    var dial = $('[data-module="dial"]');
    if (dial) {
      var select = $('[data-select]', dial), oldKnob = $('[data-knob]', dial), current = $('.dial-current', dial);
      var wheel = node('div', 'chronometer');
      wheel.tabIndex = 0; wheel.setAttribute('role', 'slider'); wheel.setAttribute('aria-label', 'Turn the time dial');
      wheel.setAttribute('aria-valuemin', '1'); wheel.setAttribute('aria-valuemax', String(select.options.length));
      wheel.innerHTML = '<i aria-hidden="true"></i><span class="chrono-value" aria-hidden="true"><span></span><small>TURN THROUGH TIME</small></span>';
      current.before(wheel);
      function syncWheel() {
        var i = Number(select.value);
        wheel.style.setProperty('--angle', (-135 + 270 * i / (select.options.length - 1)) + 'deg');
        wheel.setAttribute('aria-valuenow', String(i + 1)); wheel.setAttribute('aria-valuetext', select.options[i].textContent);
        $('.chrono-value > span', wheel).textContent = $('[data-current-year]', dial).textContent;
      }
      function choose(i) {
        i = Math.max(0, Math.min(select.options.length - 1, i));
        select.value = String(i); select.dispatchEvent(new Event('change', {bubbles: true}));
      }
      var dialObserver = new MutationObserver(syncWheel);
      dialObserver.observe(oldKnob, {attributes: true, attributeFilter: ['aria-valuenow']});
      var drag = false;
      function rotate(e) {
        var r = wheel.getBoundingClientRect(), a = Math.atan2(e.clientY - r.top - r.height / 2, e.clientX - r.left - r.width / 2) * 180 / Math.PI + 90;
        if (a > 180) a -= 360;
        choose(Math.round((Math.max(-135, Math.min(135, a)) + 135) / 270 * (select.options.length - 1)));
      }
      wheel.addEventListener('pointerdown', function (e) { if (e.button !== 0) return; drag = true; wheel.setPointerCapture(e.pointerId); wheel.focus(); rotate(e); });
      wheel.addEventListener('pointermove', function (e) { if (drag) rotate(e); });
      ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (event) { wheel.addEventListener(event, function () { drag = false; }); });
      wheel.addEventListener('keydown', function (e) {
        var i = Number(select.value), n = select.options.length;
        if (e.key === 'Home') i = 0; else if (e.key === 'End') i = n - 1;
        else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') i++;
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') i--;
        else if (e.key === 'PageUp') i += 5; else if (e.key === 'PageDown') i -= 5; else return;
        e.preventDefault(); choose(i);
      });
      syncWheel();
    }

    /* An itinerary control complements scrolling and the existing map pins. */
    var journey = $('[data-module="ride"]');
    if (journey) {
      var stops = $$('.ride-stop', journey), stage = $('.ride-stage', journey), dots = $$('.rdot', journey);
      var itinerary = node('select', 'journey-itinerary'); itinerary.setAttribute('aria-label', 'Choose a journey stop');
      stops.forEach(function (stop, i) { var option = node('option', '', (i + 1) + '. ' + text('h2', stop)); option.value = i; itinerary.append(option); });
      itinerary.addEventListener('change', function () { if (dots[Number(itinerary.value)]) dots[Number(itinerary.value)].click(); });
      var progress = node('div', 'journey-progress'); progress.setAttribute('aria-hidden', 'true'); progress.append(node('i'));
      stage.append(itinerary, progress);
      function syncJourney() {
        var i = stops.findIndex(function (stop) { return stop.classList.contains('on'); });
        if (i >= 0) itinerary.value = i;
        progress.style.setProperty('--progress', Math.max(0, (i + 1) / stops.length * 100) + '%');
      }
      var routeObserver = new MutationObserver(syncJourney);
      stops.forEach(function (stop) { routeObserver.observe(stop, {attributes: true, attributeFilter: ['class']}); }); syncJourney();
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
