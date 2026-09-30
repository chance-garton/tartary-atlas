/* The Tartary Atlas: page behaviour.
   Every interactive block is marked data-module="name" and initialised by TA.init().
   In the static site each page runs TA.init(document). In the single-file preview,
   a small hash router swaps page bodies in and runs TA.init on the new content. */
(function () {
  'use strict';
  var TA = window.TA = window.TA || {};
  var PREVIEW = !!window.TA_PREVIEW;
  TA.modules = {};
  TA.cleanups = [];

  function rootPrefix() { return (document.body && document.body.getAttribute('data-root')) || './'; }
  TA.href = function (key) {
    if (PREVIEW) return '#' + (key ? key.replace('/', '-') : 'home');
    return rootPrefix() + (key ? key + '/' : '');
  };
  TA.asset = function (name) { return PREVIEW ? 'assets/' + name : rootPrefix() + 'assets/' + name; };
  TA.init = function (root) {
    root.querySelectorAll('[data-module]').forEach(function (el) {
      var m = TA.modules[el.getAttribute('data-module')];
      if (m && !el.__ta) { el.__ta = true; try { m(el); } catch (e) { console.error('[TA]', e); } }
    });
  };
  TA.destroy = function () { TA.cleanups.splice(0).forEach(function (f) { try { f(); } catch (e) { /* ignore */ } }); };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function onTheme(cb) {
    var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    var h = function () { setTimeout(cb, 0); };
    if (mq && mq.addEventListener) mq.addEventListener('change', h);
    var mo = new MutationObserver(h);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
    return function () { if (mq && mq.removeEventListener) mq.removeEventListener('change', h); mo.disconnect(); };
  }
  function yearText(y) { return y < 0 ? (-y) + ' BCE' : String(y); }
  function numText(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function arr(list) { return Array.prototype.slice.call(list); }
  function searchWords(input) { return input.value.trim().toLowerCase().split(/\s+/).filter(Boolean); }

  /* ------------------------------------------------------------ memory
     What the reader set on a page (filters, how far they had read) is kept for the visit,
     and put back only when they return with Back or Forward. */
  var memStore = {};
  TA.restoring = false;
  function memKey(k) { return 'ta:' + (PREVIEW ? location.hash : location.pathname) + ':' + k; }
  TA.mem = {
    get: function (k) {
      var key = memKey(k);
      if (Object.prototype.hasOwnProperty.call(memStore, key)) return memStore[key];
      try { var v = window.sessionStorage.getItem(key); return v == null ? undefined : JSON.parse(v); } catch (e) { return undefined; }
    },
    set: function (k, v) {
      var key = memKey(k);
      memStore[key] = v;
      try { window.sessionStorage.setItem(key, JSON.stringify(v)); } catch (e) { /* private window, or storage is off */ }
    }
  };
  // Lists that draw after their data arrives call TA.rescroll() so a returning reader lands where they were.
  var pendingY = null;
  TA.rescroll = function () { if (pendingY != null) window.scrollTo(0, pendingY); };
  function holdScroll(y) {
    pendingY = y;
    window.scrollTo(0, y);
    setTimeout(function () { pendingY = null; }, 4000);
  }
  ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) {
    window.addEventListener(ev, function () { pendingY = null; }, { passive: true });
  });
  var scrollTimer = null;
  window.addEventListener('scroll', function () {
    toTop();
    if (scrollTimer) return;
    scrollTimer = setTimeout(function () { scrollTimer = null; TA.mem.set('y', Math.round(window.scrollY)); }, 150);
  }, { passive: true });

  /* ------------------------------------------------------------ small things on every page */
  function reduced() { return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
  function toTop() {
    var b = document.querySelector('[data-totop]');
    if (b) b.hidden = window.scrollY < window.innerHeight * 1.5;
  }
  // On a narrow screen the navigation scrolls sideways; bring the current page's entry into view.
  function navReveal() {
    var nav = document.querySelector('.site-nav'), cur = nav && nav.querySelector('[aria-current]');
    if (cur && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = cur.offsetLeft - (nav.clientWidth - cur.offsetWidth) / 2;
  }
  function copyText(t) {
    var legacy = function () {
      return new Promise(function (res, rej) {
        var ta = document.createElement('textarea');
        ta.value = t;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
        document.body.appendChild(ta);
        ta.select();
        var ok = false;
        try { ok = document.execCommand('copy'); } catch (e) { /* not allowed here */ }
        ta.remove();
        if (ok) res(); else rej();
      });
    };
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).catch(legacy);
    return legacy();
  }
  // The quote with who said it, the page and the link: ready to paste into notes or a slide.
  TA.citation = function (card) {
    var bq = card.querySelector('blockquote'), orig = bq.querySelector('.orig');
    var link = card.querySelector('.psg-links a'), who = card.querySelector('.who');
    var page = (link.textContent.match(/\(p\. (.+)\)/) || [])[1];
    var out = '“' + bq.querySelector('p').textContent.trim() + '”';
    if (orig) out += '\n(Working translation. Original: “' + orig.textContent.trim() + '”)';
    out += '\n' + (who ? who.textContent.trim() : '') + (page ? ', p. ' + page : '') + '\n' + link.href;
    return out;
  };
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('[data-copy], [data-totop], [data-basis], [data-zoom]') : null;
    if (!t) return;
    if (t.hasAttribute('data-zoom')) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;      // a new tab still goes to the library
      if (TA.zoom(t)) e.preventDefault();
      return;
    }
    if (t.hasAttribute('data-basis')) {
      // "Saw it", "Heard it": pressing the label spells it out, since a phone has no hover.
      var foot = t.closest('.psg-foot'), tip = foot && foot.nextElementSibling;
      if (tip && tip.classList.contains('basis-tip')) { tip.remove(); t.setAttribute('aria-expanded', 'false'); return; }
      tip = document.createElement('p');
      tip.className = 'basis-tip';
      tip.textContent = t.getAttribute('title');
      foot.parentNode.insertBefore(tip, foot.nextSibling);
      t.setAttribute('aria-expanded', 'true');
      return;
    }
    if (t.hasAttribute('data-totop')) {
      window.scrollTo({ top: 0, behavior: reduced() ? 'auto' : 'smooth' });
      var m = document.getElementById('main');
      if (m) m.focus({ preventScroll: true });
      return;
    }
    var card = t.closest('.psg');
    if (!card) return;
    var done = function (msg) {
      t.textContent = msg;
      clearTimeout(t.__t);
      t.__t = setTimeout(function () { t.textContent = 'Copy quote'; }, 1800);
    };
    copyText(TA.citation(card)).then(function () { done('Copied'); }, function () { done('Could not copy here'); });
  });

  /* ------------------------------------------------------------ passages */
  var THEMES = [['cities', 'Cities'], ['architecture', 'Buildings'], ['customs', 'Daily life'], ['names', 'The name'], ['outliers', 'Strange tales']];
  var THEME_LABEL = {};
  THEMES.forEach(function (t) { THEME_LABEL[t[0]] = t[1]; });
  var BASIS = {
    saw: ['Saw it', 'The author describes something they saw themselves.'],
    heard: ['Heard it', 'The author was told this by someone else.'],
    read: ['Read it', 'The author took this from an earlier book or document.'],
    legend: ['Legend or rumour', 'A legend, a rumour, or a tale the author repeats.'],
    record: ['Official record', 'An official document or a record made at the time.'],
    mixed: ['Mixed', 'Part seen, part heard or read.']
  };
  // Each data file names its sources once: [plain title, passages from it, the years it describes].
  TA.srcMeta = function (p, src) {
    var m = src[p.r] || [];
    p.sr = m[0] || ''; p.sn = m[1] || 0; p.sw = m[2] || '';
  };
  var themeCache = {};
  // Load one trail's passages (cached). Resolves to an array; each passage keeps its source title in .sr.
  TA.loadTheme = function (t) {
    if (!themeCache[t]) {
      themeCache[t] = fetch(TA.asset('passages-' + t + '.json')).then(function (r) {
        if (!r.ok) throw new Error('passages ' + r.status);
        return r.json();
      }).then(function (d) {
        d.p.forEach(function (p) { TA.srcMeta(p, d.src); });
        return d.p;
      });
      themeCache[t].catch(function () { delete themeCache[t]; });
    }
    return themeCache[t];
  };
  TA.loadThemes = function (list) {
    return Promise.all(list.map(TA.loadTheme)).then(function (parts) { return [].concat.apply([], parts); });
  };
  // One passage card. Mirrors psg_card in generator/build.py; keep the two in step.
  TA.card = function (p, o) {
    o = o || {};
    var meta = '';
    if (o.theme !== false) meta += '<a class="ttag" href="' + TA.href('passages/' + p.th) + '">' + esc(THEME_LABEL[p.th]) + '</a>';
    if (p.pl) meta += p.pi ? '<a href="' + TA.href('place/' + p.pi) + '">' + esc(p.pl) + '</a>' : '<span>' + esc(p.pl) + '</span>';
    if (p.w) meta += '<span>' + esc(p.w) + '</span>';
    var quote = p.t
      ? '<blockquote><p>' + esc(p.t) + '</p><p class="q-tag">Working translation</p><details><summary>Original wording</summary><p class="orig" dir="auto">' + esc(p.q) + '</p></details></blockquote>'
      : '<blockquote><p dir="auto">' + esc(p.q) + '</p></blockquote>';
    var notes = '';
    if (p.c) notes += '<p>' + esc(p.c) + '</p>';
    if (p.n) notes += '<p>' + esc(p.n) + '</p>';
    if (notes) notes = '<details class="psg-notes"><summary>' + (p.c ? 'Keep in mind' : 'A note on this quote') + '</summary>' + notes + '</details>';
    var b = BASIS[p.b] || [p.b, ''];
    var links = '<a href="' + esc(p.u) + '" rel="noopener">See the original page' + (p.p ? ' (p. ' + esc(p.p) + ')' : '') + '</a>';
    links += '<button type="button" class="psg-copy" data-copy>Copy quote</button>';
    var tale = '';
    if (o.source !== false) {
      tale = '<a class="psg-tale" href="' + TA.href('w/' + p.r) + '"><span class="psg-tale-k">Explore this Tartaria tale</span>' +
        '<span class="psg-tale-t">' + esc(p.sr) + '</span><span class="psg-tale-n">' + esc(p.sw) + ' · ' + numText(p.sn) + ' passage' + (p.sn === 1 ? '' : 's') + '</span></a>';
    }
    return '<article class="psg' + (o.cls ? ' ' + o.cls : '') + '" id="p-' + esc(p.i) + '" data-th="' + esc(p.th) + '" data-b="' + esc(p.b) + '" data-y="' + (p.y == null ? '' : p.y) + '">' +
      '<div class="psg-meta">' + meta + '</div><h3>' + esc(p.h) + '</h3><p class="gloss">' + esc(p.g) + '</p>' + quote +
      '<div class="psg-foot"><button type="button" class="basis ' + esc(p.b) + '" data-basis aria-expanded="false" title="' + esc(b[1]) + '">' + esc(b[0]) + '</button><span class="who">' + esc(p.s) + '</span></div>' +
      (p.pe ? '<p class="psg-people"><span>About</span> ' + esc(p.pe) + '</p>' : '') +
      notes + tale + '<div class="psg-links">' + links + '</div></article>';
  };
  function bestOrder(a, b) { return (b.st - a.st) || (a.x - b.x) || (a.i < b.i ? -1 : 1); }
  function shuffled(list) {
    var a = list.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  // Mark the words the reader searched for, in the text they can see.
  TA.mark = function (root, words) {
    words = words.filter(function (w) { return w.length > 1; });
    if (!words.length) return;
    var re = new RegExp(words.map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|'), 'gi');
    arr(root.querySelectorAll('.psg h3, .psg .gloss, .psg blockquote p:not(.q-tag), .psg-meta > *, .psg .who, .psg-people')).forEach(function (n) {
      var walker = document.createTreeWalker(n, NodeFilter.SHOW_TEXT), nodes = [], t;
      while ((t = walker.nextNode())) nodes.push(t);
      nodes.forEach(function (node) {
        var text = node.nodeValue, frag = document.createDocumentFragment(), last = 0, m;
        re.lastIndex = 0;
        while ((m = re.exec(text))) {
          frag.appendChild(document.createTextNode(text.slice(last, m.index)));
          var mk = document.createElement('mark');
          mk.textContent = m[0];
          frag.appendChild(mk);
          last = m.index + m[0].length;
        }
        if (!last) return;
        frag.appendChild(document.createTextNode(text.slice(last)));
        node.parentNode.replaceChild(frag, node);
      });
    });
  };
  function pressed(btns, on) { btns.forEach(function (x) { x.setAttribute('aria-pressed', x === on ? 'true' : 'false'); }); }
  // "37 of 2,029" with a Clear filters button, shared by every filtered list.
  function countUI(el, n, filtering) {
    var cnt = el.querySelector('[data-count]'), of = el.querySelector('[data-of]'), clear = el.querySelector('[data-clear]');
    if (cnt) cnt.textContent = numText(n);
    if (of) of.hidden = !filtering;
    if (clear) clear.hidden = !filtering;
    var empty = el.querySelector('[data-empty]');
    if (empty) empty.hidden = n > 0;
  }

  /* The passage explorer on /passages/ and each trail page. */
  TA.modules.pexplore = function (el) {
    var theme = el.getAttribute('data-trail');
    var q = el.querySelector('#px-q'), bs = el.querySelector('#px-b'), wh = el.querySelector('#px-w'), od = el.querySelector('#px-o');
    var list = el.querySelector('[data-list]'), nf = el.querySelector('[data-nf]'), det = el.querySelector('[data-filters]');
    var moreBtn = el.querySelector('[data-more]'), moreRow = moreBtn.parentNode;
    var STEP = 10, shown = STEP, all = null, cur = [], order = null, failed = false;
    arr(el.querySelectorAll('#px-b option, #px-w option')).forEach(function (o) { o.setAttribute('data-l', o.textContent); });
    // On a phone the filters fold away so the passages start on the first screen.
    if (det && window.matchMedia) {
      var mq = window.matchMedia('(max-width: 960px)');
      var fold = function () { det.open = !mq.matches; };
      fold();
      if (mq.addEventListener) { mq.addEventListener('change', fold); TA.cleanups.push(function () { mq.removeEventListener('change', fold); }); }
    }
    var saved = TA.restoring ? TA.mem.get('px') : null;
    if (saved) {
      q.value = saved.q || ''; bs.value = saved.b || ''; wh.value = saved.w || ''; od.value = saved.o || 'best';
      shown = saved.n || STEP;
      if (det && (saved.b || saved.w)) det.open = true;
    }
    function save() { TA.mem.set('px', { q: q.value, b: bs.value, w: wh.value, o: od.value, n: shown }); }
    function century(p) { return p.y == null ? null : (p.y < 1200 ? 0 : Math.floor(p.y / 100) * 100); }
    function match() {
      var words = searchWords(q), b = bs.value, c = wh.value === '' ? null : +wh.value;
      var nb = {}, nw = {}, nbAll = 0, nwAll = 0;
      cur = [];
      all.forEach(function (p) {
        if (words.length) {
          if (!p.hay) p.hay = [p.h, p.g, p.pl, p.pe, p.w, p.s, p.sr, p.tg, p.t, p.q].join(' ').toLowerCase();
          if (!words.every(function (w) { return p.hay.indexOf(w) >= 0; })) return;
        }
        var cen = century(p), okB = !b || p.b === b, okW = c === null || cen === c;
        if (okW) { nb[p.b] = (nb[p.b] || 0) + 1; nbAll++; }
        if (okB) { if (cen !== null) nw[cen] = (nw[cen] || 0) + 1; nwAll++; }
        if (okB && okW) cur.push(p);
      });
      // Each menu says how many passages every choice would give, with the other filters as they are.
      arr(bs.options).forEach(function (o) { o.textContent = o.getAttribute('data-l') + ' (' + numText(o.value ? (nb[o.value] || 0) : nbAll) + ')'; });
      arr(wh.options).forEach(function (o) { o.textContent = o.getAttribute('data-l') + ' (' + numText(o.value === '' ? nwAll : (nw[+o.value] || 0)) + ')'; });
      if (order) {
        var pos = {};
        order.forEach(function (id, i) { pos[id] = i; });
        cur.sort(function (a, b) { return pos[a.i] - pos[b.i]; });
      } else if (od.value === 'old' || od.value === 'new') {
        var s = od.value === 'old' ? 1 : -1;
        cur.sort(function (a, b) {
          if (a.y == null || b.y == null) return (a.y == null) - (b.y == null) || bestOrder(a, b);
          return s * (a.y - b.y) || bestOrder(a, b);
        });
      } else cur.sort(bestOrder);
    }
    function draw() {
      var words = searchWords(q), picked = (bs.value ? 1 : 0) + (wh.value !== '' ? 1 : 0);
      countUI(el, cur.length, words.length > 0 || picked > 0);
      if (nf) nf.textContent = picked ? picked + ' on' : '';
      list.innerHTML = cur.length
        ? cur.slice(0, shown).map(function (p) { return TA.card(p, { theme: !theme }); }).join('')
        : '<p class="muted">No passage matches. Try a shorter word, or <button type="button" class="linkbtn" data-clear>clear the filters</button>.</p>';
      TA.mark(list, words);
      var left = cur.length - shown;
      moreRow.hidden = left <= 0;
      moreBtn.textContent = 'Show ' + Math.min(STEP, left) + ' more';
    }
    function refresh(keep) {
      if (failed || !all) return;       // while the data is loading, refresh runs again when it lands
      if (!keep) shown = STEP;
      match(); draw(); save();
    }
    var ready = TA.loadThemes(theme ? [theme] : THEMES.map(function (t) { return t[0]; })).then(function (ps) {
      all = ps.slice();
      refresh(true);
      TA.rescroll();
    }).catch(function () {
      failed = true;
      moreRow.hidden = true;
      el.querySelector('.filterbar').insertAdjacentHTML('afterend',
        '<p class="banner">Search is off for the moment: the full list could not load. Here are the first passages.</p>');
    });
    [q, bs, wh].forEach(function (x) { x.addEventListener('input', function () { refresh(); }); });
    od.addEventListener('input', function () { order = null; refresh(); });
    el.querySelector('[data-shuffle]').addEventListener('click', function () {
      ready.then(function () {
        if (!all) return;
        order = shuffled(all).map(function (p) { return p.i; });
        refresh();
      });
    });
    el.addEventListener('click', function (e) {
      if (!e.target.closest('[data-clear]')) return;
      q.value = ''; bs.value = ''; wh.value = '';
      refresh();
      q.focus();
    });
    moreBtn.addEventListener('click', function () { shown += STEP; ready.then(function () { refresh(true); }); });
  };

  /* A set of passages on a source page or a place page: trail pills that filter it, an order switch,
     and the rest of the set a few at a time. The static site has every card in the page already;
     the single-file preview names them by ID and the cards are drawn here. */
  TA.modules.pset = function (el) {
    var list = el.querySelector('[data-list]'), bar = el.querySelector('[data-bar]'), cnt = el.querySelector('[data-count]');
    var moreRow = el.querySelector('[data-more-row]'), moreBtn = el.querySelector('[data-more]'), allBtn = el.querySelector('[data-all]');
    var pills = arr(el.querySelectorAll('[data-f]')), ords = arr(el.querySelectorAll('[data-ord]'));
    var first = +(el.getAttribute('data-first') || 4), STEP = 10;
    var cards = [], f = '', ord = 'best', shown = first;
    var slot = arr(document.querySelectorAll('[data-module="pset"]')).indexOf(el);
    function save() { TA.mem.set('ps' + slot, { f: f, o: ord, n: shown }); }
    function draw() {
      var m = cards.filter(function (c) { return !f || c.getAttribute('data-th') === f; });
      if (ord === 'old') {
        m.sort(function (a, b) {
          var ya = a.getAttribute('data-y'), yb = b.getAttribute('data-y');
          if (ya === '' || yb === '') return (ya === '') - (yb === '') || a.__i - b.__i;
          return (ya - yb) || a.__i - b.__i;
        });
      }
      cards.forEach(function (c) { c.hidden = true; });
      m.forEach(function (c, i) { c.hidden = i >= shown; list.appendChild(c); });
      var left = m.length - shown;
      moreRow.hidden = left <= 0;
      if (left > 0) {
        moreBtn.textContent = 'Show ' + Math.min(STEP, left) + ' more';
        allBtn.hidden = left <= STEP;
        allBtn.textContent = 'Show all ' + m.length;
        cnt.textContent = 'Showing ' + shown + ' of ' + m.length + (f ? ' in ' + THEME_LABEL[f] : '');
      }
      cnt.hidden = left <= 0;
      save();
    }
    function adopt() {
      var more = el.querySelector('details.more');
      if (more) {
        arr(more.querySelectorAll('.psg')).forEach(function (c) { list.appendChild(c); });
        more.parentNode.removeChild(more);
      }
      cards = arr(list.querySelectorAll('.psg'));
      cards.forEach(function (c, i) { c.__i = i; });
      if (bar) bar.hidden = false;
      var saved = TA.restoring ? TA.mem.get('ps' + slot) : null;
      if (saved) {
        f = saved.f || ''; ord = saved.o || 'best'; shown = saved.n || first;
        pressed(pills, pills.filter(function (b) { return b.getAttribute('data-f') === f; })[0]);
        pressed(ords, ords.filter(function (b) { return b.getAttribute('data-ord') === ord; })[0]);
      }
      draw();
      TA.rescroll();
    }
    pills.forEach(function (b) {
      b.addEventListener('click', function () {
        f = b.getAttribute('data-f');
        pressed(pills, b);
        shown = f ? STEP : first;      // a chosen trail opens wider than the first glance
        draw();
      });
    });
    ords.forEach(function (b) {
      b.addEventListener('click', function () { ord = b.getAttribute('data-ord'); pressed(ords, b); draw(); });
    });
    moreBtn.addEventListener('click', function () { shown += STEP; draw(); });
    allBtn.addEventListener('click', function () { shown = cards.length; draw(); });

    var ids = (el.getAttribute('data-ids') || '').split(',').filter(Boolean);
    if (!ids.length) { adopt(); return; }
    var opts = el.getAttribute('data-opts') || '11';
    var o = { theme: opts.charAt(0) === '1', source: opts.charAt(1) === '1' };
    var want = {};
    ids.forEach(function (id) { want[id] = true; });
    TA.loadThemes(THEMES.map(function (t) { return t[0]; })).then(function (ps) {
      var by = {};
      ps.forEach(function (p) { if (want[p.i]) by[p.i] = p; });
      list.innerHTML = ids.map(function (id) { return by[id] ? TA.card(by[id], o) : ''; }).join('');
      adopt();
    }).catch(function () {
      list.innerHTML = '<p class="banner">The passages could not load here. Try again in a moment.</p>';
    });
  };

  /* The name in the header, set in lettering cut from the maps. One map lends its hand for the whole visit;
     the next visit draws another, never the one seen last time. */
  TA.wordmark = function () {
    var box = document.querySelector('[data-wordmarks]');
    if (!box) return;
    var name = box.querySelector('[data-wm-name]'), credit = box.querySelector('[data-wm-credit]');
    var list = [];
    try { list = JSON.parse(box.getAttribute('data-wordmarks')); } catch (e) { /* keep the lettering already there */ }
    if (!list.length) { name.setAttribute('data-set', ''); return; }
    var KEY = 'ta:wordmark', now = null, last = null;
    try { now = window.sessionStorage.getItem(KEY); } catch (e) { /* storage is off: a new hand on every page */ }
    var pick = list.filter(function (c) { return c.k === now; })[0];
    if (!pick) {
      try { last = window.localStorage.getItem(KEY); } catch (e) { /* as above */ }
      var pool = list.filter(function (c) { return c.k !== last; });
      if (!pool.length) pool = list;
      pick = pool[Math.floor(Math.random() * pool.length)];
      try { window.sessionStorage.setItem(KEY, pick.k); window.localStorage.setItem(KEY, pick.k); } catch (e) { /* as above */ }
    }
    var cut = name.querySelector('.cut');
    var src = 'url(' + TA.asset('cuts/labels/' + pick.k + '.png') + ')';
    cut.style.webkitMaskImage = src;
    cut.style.maskImage = src;
    cut.style.aspectRatio = pick.w + ' / ' + pick.h;
    name.setAttribute('data-set', '');
    if (credit) { credit.textContent = 'lettered by ' + pick.c; credit.setAttribute('href', TA.href('m/' + pick.m)); }
  };

  /* The front door: Ortelius's map with the passage beside it. A different passage opens on every visit,
     "Draw another" takes the next from a fresh shuffle, and a reader who comes Back finds the passage they left.
     When the passage is about a place Ortelius lettered, the map travels there. A dot on the map is a place the
     sources wrote about; a diamond is something the mapmaker wrote on the sheet. Without the map viewer the
     still picture stays and the passages work as before. */
  TA.modules.feature = function (el) {
    var D = JSON.parse(el.querySelector('script[type="application/json"]').textContent);
    var slot = el.querySelector('[data-slot]'), btn = el.querySelector('[data-next]'), at = el.querySelector('[data-at]');
    var LAST = 'ta:feature-last', queue = [], cur = null, curPin = null;
    var M = D.map, pinById = {};
    if (M) M.pins.forEach(function (pin) { pinById[pin.i] = pin; });
    D.p.forEach(function (p) { TA.srcMeta(p, D.src); });
    function lastSeen() { try { return window.localStorage.getItem(LAST); } catch (e) { return null; } }
    function draw(p, moved) {
      cur = p.i;
      slot.innerHTML = TA.card(p, { cls: 'big' });
      slot.setAttribute('data-ready', '');
      TA.mem.set('feature', p.i);
      try { window.localStorage.setItem(LAST, p.i); } catch (e) { /* storage is off: still random, may repeat */ }
      if (moved && !reduced()) {
        var card = slot.firstChild;
        card.classList.add('dealt');
        setTimeout(function () { card.classList.remove('dealt'); }, 400);
      }
      curPin = p.pn && pinById[p.pn] ? p.pn : null;
      if (at) {
        if (curPin) {
          at.innerHTML = 'On the map: <em>' + esc(pinById[curPin].m) + '</em>';
          at.hidden = false;
        } else at.hidden = true;
      }
      travel(!moved);
    }
    function next() {
      if (!queue.length) {
        queue = shuffled(D.p);
        // never the passage on show, nor the one this reader saw last time
        var avoid = cur || lastSeen();
        if (queue.length > 1 && queue[0].i === avoid) queue.push(queue.shift());
      }
      return queue.shift();
    }

    /* ---- the map */
    var stage = el.querySelector('[data-stage]'), viewer = null, open = false, roaming = false, marks = {};
    var slip = el.querySelector('[data-slip]');
    function pt(x, y) { return new window.OpenSeadragon.Point(x, y * M.ar); }
    function travel(now) {
      if (!open) return;
      var vp = viewer.viewport, still = !!now || reduced();
      Object.keys(marks).forEach(function (k) { marks[k].classList.toggle('on', k === curPin); });
      if (!curPin) {
        vp.zoomTo(vp.getHomeZoom(), null, still);
        vp.panTo(pt(0.42, 0.4), still);
        vp.applyConstraints(still);
        return;
      }
      var pin = pinById[curPin], size = viewer.container.getBoundingClientRect();
      var wide = size.width > 900 && !roaming;
      var zoom = Math.max(vp.getHomeZoom(), Math.min(vp.getMaxZoom(), M.w / (size.width * (size.width > 700 ? 1.5 : 2.7))));
      // on a wide screen the passage card covers the lower right, so the place is held left of centre and high
      var dx = wide ? 0.16 : 0, dy = roaming ? 0 : 0.1;
      vp.zoomTo(zoom, null, still);
      vp.panTo(new window.OpenSeadragon.Point(pin.x + dx / zoom, pin.y * M.ar + dy * (size.height / size.width) / zoom), still);
      vp.applyConstraints(still);
    }
    function closeSlip() { if (slip) { slip.hidden = true; slip.innerHTML = ''; } }
    function openSlip(html) {
      slip.innerHTML = '<button type="button" class="slip-x" data-slip-x aria-label="Close this note">×</button>' + html;
      slip.hidden = false;
    }
    function fromPin(id) {
      var here = D.p.filter(function (p) { return p.pn === id && p.i !== cur; });
      if (!here.length) here = D.p.filter(function (p) { return p.pn === id; });
      return here.length ? here[Math.floor(Math.random() * here.length)] : null;
    }
    function pickPin(pin) {
      closeSlip();
      if (roaming) {
        openSlip('<p class="slip-k">' + (pin.k === 'town' ? 'A town' : 'A name') + ' on the map</p><h3><em>' + esc(pin.m) + '</em></h3>' +
          '<p>' + esc(pin.n) + '. ' + numText(pin.c) + ' passage' + (pin.c === 1 ? '' : 's') + ' in the atlas.</p>' +
          '<p class="slip-go"><button type="button" class="btn primary" data-read="' + esc(pin.i) + '">Read one</button>' +
          '<a class="btn" href="' + TA.href('place/' + pin.i) + '">Open ' + esc(pin.n) + '</a></p>');
        curPin = pin.i;
        Object.keys(marks).forEach(function (k) { marks[k].classList.toggle('on', k === curPin); });
        return;
      }
      var p = fromPin(pin.i);
      if (p) draw(p, true);
    }
    function pickSight(s) {
      openSlip('<p class="slip-k">Written on the map</p><h3>' + esc(s.t) + '</h3><p>' + esc(s.w) + '</p>' +
        (s.l ? '<p class="orig" lang="la">' + esc(s.l) + '</p><p class="slip-note">The Latin as read from the sheet. It may be partial.</p>' : ''));
    }
    function mark(cls, label, x, y, fn) {
      var OSD = window.OpenSeadragon, b = document.createElement('button');
      b.type = 'button';
      b.className = 'fpin ' + cls;
      b.setAttribute('aria-label', label);
      b.innerHTML = '<span>' + esc(label) + '</span>';
      // The viewer reads the pointer itself, so a press on a mark is caught by a tracker of its own.
      var tr = new OSD.MouseTracker({ element: b, clickHandler: function (e) { if (e.quick !== false) fn(); } });
      b.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); } });
      viewer.addOverlay({ element: b, location: pt(x, y), placement: OSD.Placement.CENTER, checkResize: false });
      TA.cleanups.push(function () { tr.destroy(); });
      return b;
    }
    function setRoam(on) {
      roaming = on;
      stage.classList.toggle('roam', on);
      document.documentElement.classList.toggle('roaming', on);
      var t = viewer.gestureSettingsTouch, m = viewer.gestureSettingsMouse, p = viewer.gestureSettingsPen;
      m.scrollToZoom = on;
      [t, p].forEach(function (g) { g.dragToPan = on; g.pinchToZoom = on; g.flickEnabled = on; });
      viewer.canvas.style.touchAction = on ? 'none' : 'pan-y';
      stage.querySelector('[data-roam]').hidden = on;
      stage.querySelector('[data-close]').hidden = !on;
      closeSlip();
      setTimeout(function () { viewer.forceResize(); travel(true); }, 60);
      if (on) stage.querySelector('[data-close]').focus();
    }
    function startMap() {
      var OSD = window.OpenSeadragon;
      if (!M || !OSD || !stage) return;
      var quiet = { dragToPan: false, pinchToZoom: false, flickEnabled: false, clickToZoom: false, dblClickToZoom: false, scrollToZoom: false };
      viewer = OSD({
        element: stage.querySelector('[data-osd]'),
        tileSources: M.tiled ? M.src : { type: 'image', url: M.src },
        showNavigationControl: false, homeFillsViewer: true, visibilityRatio: 1, constrainDuringPan: true,
        minZoomImageRatio: 1, maxZoomPixelRatio: 2, animationTime: 1.6, springStiffness: 6.5, minScrollDeltaTime: 0,
        gestureSettingsMouse: { scrollToZoom: false, clickToZoom: false, dblClickToZoom: true },
        gestureSettingsTouch: quiet, gestureSettingsPen: JSON.parse(JSON.stringify(quiet))
      });
      viewer.addHandler('open', function () {
        open = true;
        viewer.canvas.style.touchAction = 'pan-y';
        M.pins.forEach(function (pin) {
          marks[pin.i] = mark(pin.k === 'town' ? 'town' : 'name', pin.n + ', lettered ' + pin.m, pin.x, pin.y, function () { pickPin(pin); });
        });
        M.sights.forEach(function (s) { mark('sight', s.t, s.x, s.y, function () { pickSight(s); }); });
        stage.querySelector('[data-tools]').hidden = false;
        var how = el.querySelector('[data-how]');
        if (how) how.hidden = false;
        travel(true);
        var still = stage.querySelector('[data-still]');
        var lift = function () { if (still) still.classList.add('gone'); };
        viewer.addOnceHandler('tile-drawn', function () { setTimeout(lift, 120); });
        setTimeout(lift, 2500);
      });
      // The wheel scrolls the page past the map, and zooms the map only while roaming.
      viewer.addHandler('canvas-scroll', function (e) { e.preventDefault = roaming; });
      viewer.addHandler('open-failed', function () { try { viewer.destroy(); } catch (e) { /* the still picture stays */ } viewer = null; });
      stage.addEventListener('click', function (e) {
        var b = e.target.closest ? e.target.closest('button') : null;
        if (!b || !viewer) return;
        var vp = viewer.viewport;
        if (b.hasAttribute('data-zoom-in')) { vp.zoomBy(1.6); vp.applyConstraints(); }
        else if (b.hasAttribute('data-zoom-out')) { vp.zoomBy(1 / 1.6); vp.applyConstraints(); }
        else if (b.hasAttribute('data-roam')) setRoam(true);
        else if (b.hasAttribute('data-close')) setRoam(false);
        else if (b.hasAttribute('data-slip-x')) closeSlip();
        else if (b.hasAttribute('data-read')) {
          var p = fromPin(b.getAttribute('data-read'));
          setRoam(false);
          if (p) { draw(p, true); slot.scrollIntoView({ block: 'center', behavior: reduced() ? 'auto' : 'smooth' }); }
        }
      });
      var key = function (e) { if (e.key === 'Escape') { if (slip && !slip.hidden) closeSlip(); else if (roaming) setRoam(false); } };
      document.addEventListener('keydown', key);
      TA.cleanups.push(function () {
        document.removeEventListener('keydown', key);
        document.documentElement.classList.remove('roaming');
        open = false;
        try { if (viewer) viewer.destroy(); } catch (e) { /* already gone */ }
      });
    }
    try { startMap(); } catch (e) { console.error('[TA] front map', e); }

    if (!D.p.length) { slot.setAttribute('data-ready', ''); return; }
    var back = TA.restoring ? TA.mem.get('feature') : null;
    var kept = back && D.p.filter(function (p) { return p.i === back; })[0];
    draw(kept || next());
    btn.addEventListener('click', function () { closeSlip(); draw(next(), true); });
  };

  /* "Surprise me": open one source at random. */
  TA.modules.lucky = function (el) {
    var pool = (el.getAttribute('data-pool') || '').split(',').filter(Boolean);
    var here = (PREVIEW ? location.hash : location.pathname).match(/W\d{3}/);
    if (here) pool = pool.filter(function (id) { return id !== here[0]; });
    el.addEventListener('click', function () {
      if (pool.length) location.href = TA.href('w/' + pool[Math.floor(Math.random() * pool.length)]);
    });
  };

  /* A closer look at a map picture, without leaving the page: fit to the screen, then zoom and drag. */
  TA.zoom = function (a) {
    var src = a.getAttribute('data-zoom');
    if (!src || !window.HTMLDialogElement) return false;
    var dlg = document.createElement('dialog');
    dlg.className = 'zoom';
    dlg.setAttribute('aria-label', 'A closer look: ' + (a.getAttribute('data-zoom-title') || 'map'));
    dlg.innerHTML = '<div class="zoom-bar"><span class="zoom-title">' + esc(a.getAttribute('data-zoom-title') || '') + '</span>' +
      '<span class="zoom-tools"><button type="button" data-z="out" aria-label="Zoom out">−</button>' +
      '<button type="button" data-z="in" aria-label="Zoom in">+</button>' +
      '<a href="' + esc(a.getAttribute('href')) + '" rel="noopener">Full image at the library</a>' +
      '<button type="button" data-z="close">Close</button></span></div>' +
      '<div class="zoom-pan"><img alt="' + esc((a.querySelector('img') || a).getAttribute('alt') || '') + '" src="' + esc(src) + '" draggable="false"></div>';
    document.body.appendChild(dlg);
    var pan = dlg.querySelector('.zoom-pan'), img = pan.querySelector('img');
    var k = 1, MAX = 4, fitW = 0, started = false, centred = false;
    function fit() {
      var nw = img.naturalWidth || 1400, nh = img.naturalHeight || 1000;
      fitW = Math.min(pan.clientWidth, pan.clientHeight * nw / nh);
      // a wide map on an upright phone would open as a thin strip, so it opens filling most of the height
      if (!started) { started = true; k = Math.min(2.5, Math.max(1, pan.clientHeight * 0.8 / (fitW * nh / nw))); if (k < 1.15) k = 1; }
      apply();
      if (k > 1 && !centred) { centred = true; pan.scrollLeft = (pan.scrollWidth - pan.clientWidth) / 2; pan.scrollTop = (pan.scrollHeight - pan.clientHeight) / 2; }
    }
    function apply(cx, cy) {
      // keep the point under the pointer (or the centre) where it is while the picture grows
      var r = img.getBoundingClientRect(), pr = pan.getBoundingClientRect();
      if (cx == null) { cx = pr.left + pr.width / 2; cy = pr.top + pr.height / 2; }
      var fx = r.width ? (cx - r.left) / r.width : 0.5, fy = r.height ? (cy - r.top) / r.height : 0.5;
      img.style.width = Math.round(fitW * k) + 'px';
      var r2 = img.getBoundingClientRect();
      pan.scrollLeft += (r2.left + fx * r2.width) - cx;
      pan.scrollTop += (r2.top + fy * r2.height) - cy;
      pan.classList.toggle('zoomed', k > 1);
      dlg.querySelector('[data-z="out"]').disabled = k <= 1;
      dlg.querySelector('[data-z="in"]').disabled = k >= MAX;
    }
    function step(d, cx, cy) { k = Math.max(1, Math.min(MAX, +(k * (d > 0 ? 1.5 : 1 / 1.5)).toFixed(3))); if (k < 1.05) k = 1; apply(cx, cy); }
    if (img.complete) setTimeout(fit, 0); else img.addEventListener('load', fit);
    window.addEventListener('resize', fit);
    dlg.addEventListener('click', function (e) {
      var b = e.target.closest('[data-z]');
      if (b) {
        var z = b.getAttribute('data-z');
        if (z === 'close') dlg.close(); else step(z === 'in' ? 1 : -1);
      } else if (e.target === dlg || e.target === pan) dlg.close();
    });
    pan.addEventListener('wheel', function (e) { e.preventDefault(); step(e.deltaY < 0 ? 1 : -1, e.clientX, e.clientY); }, { passive: false });
    // drag to move; a press without a drag zooms in (or back out at the limit)
    var drag = null;
    img.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'touch') return;          // fingers scroll the picture natively
      drag = { x: e.clientX, y: e.clientY, l: pan.scrollLeft, t: pan.scrollTop, moved: false };
      img.setPointerCapture(e.pointerId);
    });
    img.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      pan.scrollLeft = drag.l - dx; pan.scrollTop = drag.t - dy;
    });
    img.addEventListener('pointerup', function (e) {
      var d = drag; drag = null;
      if (d && !d.moved) { if (k >= MAX) { k = 1; apply(); } else step(1, e.clientX, e.clientY); }
    });
    // a tap on a touch screen: zoom in where the finger was
    img.addEventListener('touchend', function (e) {
      if (e.changedTouches.length !== 1 || img.__moved) { img.__moved = false; return; }
      var t = e.changedTouches[0];
      if (k >= MAX) { k = 1; apply(); } else step(1, t.clientX, t.clientY);
    });
    img.addEventListener('touchmove', function () { img.__moved = true; }, { passive: true });
    dlg.addEventListener('close', function () {
      window.removeEventListener('resize', fit);
      dlg.remove();
      a.focus({ preventScroll: true });
    });
    dlg.showModal();
    return true;
  };

  /* The gallery of old maps: century buttons and a search box. */
  TA.modules.gallery = function (el) {
    var q = el.querySelector('#gl-q');
    var cards = arr(el.querySelectorAll('[data-grid] > a'));
    var btns = arr(el.querySelectorAll('[data-era]'));
    var lo = null, hi = null;
    function upd() {
      var words = searchWords(q), n = 0;
      cards.forEach(function (a) {
        var y = a.getAttribute('data-y');
        var inEra = (lo === null && hi === null) || (y !== '' && (lo === null || +y >= lo) && (hi === null || +y <= hi));
        var ok = inEra && words.every(function (w) { return a.getAttribute('data-h').indexOf(w) >= 0; });
        a.hidden = !ok;
        if (ok) n++;
      });
      countUI(el, n, words.length > 0 || lo !== null || hi !== null);
    }
    function era(b) {
      pressed(btns, b);
      var l = b.getAttribute('data-lo'), h = b.getAttribute('data-hi');
      lo = l ? +l : null; hi = h ? +h : null;
      upd();
    }
    btns.forEach(function (b) { b.addEventListener('click', function () { era(b); }); });
    q.addEventListener('input', upd);
    el.querySelector('[data-clear]').addEventListener('click', function () { q.value = ''; era(btns[0]); });
  };

  /* The list of sources that have been read. */
  TA.modules.slist = function (el) {
    var q = el.querySelector('#sl-q'), hk = el.querySelector('#sl-hk'), od = el.querySelector('#sl-o');
    var box = el.querySelector('[data-rows]'), allBtn = el.querySelector('[data-all]');
    var rows = arr(box.children);
    var LIMIT = 30, showAll = false;
    var saved = TA.restoring ? TA.mem.get('sl') : null;
    if (saved) { q.value = saved.q || ''; hk.value = saved.hk || ''; od.value = saved.o || 'n'; showAll = !!saved.all; }
    function upd() {
      var words = searchWords(q);
      var key = od.value;
      var sorted = rows.slice().sort(function (a, b) {
        if (key === 'n') return (+b.getAttribute('data-n')) - (+a.getAttribute('data-n'));
        var ya = a.getAttribute('data-y'), yb = b.getAttribute('data-y');
        if (ya === '' || yb === '') return (ya === '') - (yb === '');
        return key === 'old' ? ya - yb : yb - ya;
      });
      var n = 0, filtering = words.length > 0 || !!hk.value;
      sorted.forEach(function (li) {
        var ok = (!hk.value || li.getAttribute('data-hk') === hk.value) &&
          words.every(function (w) { return li.getAttribute('data-h').indexOf(w) >= 0; });
        if (ok) n++;
        li.hidden = !ok || (!showAll && !filtering && n > LIMIT);
        var chip = li.querySelector('[data-set]');
        if (chip) chip.setAttribute('aria-pressed', hk.value && chip.getAttribute('data-set') === hk.value ? 'true' : 'false');
        box.appendChild(li);
      });
      countUI(el, n, filtering);
      allBtn.parentNode.hidden = showAll || filtering || n <= LIMIT;
      TA.mem.set('sl', { q: q.value, hk: hk.value, o: od.value, all: showAll });
    }
    [q, hk, od].forEach(function (x) { x.addEventListener('input', upd); });
    allBtn.addEventListener('click', function () { showAll = true; upd(); });
    // The label on a row is a shortcut to the same filter; a second click lets go of it.
    box.addEventListener('click', function (e) {
      var chip = e.target.closest('[data-set]');
      if (!chip) return;
      var v = chip.getAttribute('data-set');
      hk.value = hk.value === v ? '' : v;
      upd();
    });
    el.querySelector('[data-clear]').addEventListener('click', function () { q.value = ''; hk.value = ''; upd(); q.focus(); });
    if (saved) { upd(); TA.rescroll(); }
  };

  /* ------------------------------------------------------------ explorer */
  TA.modules.explorer = function (el) {
    var D = JSON.parse(el.querySelector('script[type="application/json"]').textContent);
    var R = D.records.map(function (a) {
      return { id: a[0], m: a[1], s: a[2], d: a[3], ev: a[4], tr: a[5], t: a[6], c: a[7], p: a[8] };
    });
    var P = {};
    D.places.forEach(function (a) { P[a[0]] = { id: a[0], n: a[1], b: a[2], lon: a[3], lat: a[4], psg: a[5] || 0, count: 0 }; });
    var st = {
      kind: 'all', lo: 0, hi: 100, undated: true, sel: null,
      ev: D.evidence.map(function () { return true; }),
      tr: D.traditions.map(function () { return true; })
    };

    // Piecewise date scale: antiquity to 1250 is compressed, 1250 to 1900 is linear.
    var K = [[0, -500], [10, 1000], [22, 1250], [100, 1900]];
    function toYear(v) {
      for (var i = 1; i < K.length; i++) if (v <= K[i][0]) {
        var a = K[i - 1], b = K[i];
        return a[1] + (v - a[0]) / (b[0] - a[0]) * (b[1] - a[1]);
      }
      return 1900;
    }
    function toSlider(y) {
      for (var i = 1; i < K.length; i++) if (y <= K[i][1]) {
        var a = K[i - 1], b = K[i];
        return a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0]);
      }
      return 100;
    }
    function sliderYear(v) { var y = toYear(v); return v < 22 ? Math.round(y / 10) * 10 : Math.round(y); }
    function passOther(r) {
      if (st.kind !== 'all' && String(r.m) !== st.kind) return false;
      return st.ev[r.ev] && st.tr[r.tr];
    }
    function passDate(r) {
      if (r.s == null) return st.undated;
      var lo = st.lo <= 0 ? -Infinity : sliderYear(st.lo);
      var hi = st.hi >= 100 ? Infinity : sliderYear(st.hi);
      return r.s >= lo && r.s <= hi;
    }
    function recHref(r) { return TA.href((r.m ? 'm/' : 'w/') + r.id); }

    // ---- controls
    var lo = el.querySelector('#ex-lo'), hi = el.querySelector('#ex-hi');
    var fill = el.querySelector('[data-fill]'), readout = el.querySelector('[data-readout]');
    var hist = el.querySelector('[data-hist]'), ticks = el.querySelector('[data-ticks]');
    [[-500, '500 BCE'], [1250, '1250'], [1400, '1400'], [1550, '1550'], [1700, '1700'], [1900, '1900']].forEach(function (t, i, arr) {
      var s = document.createElement('span');
      s.textContent = t[1];
      s.style.left = toSlider(t[0]) + '%';
      if (i === 0) s.style.transform = 'none';
      if (i === arr.length - 1) s.style.transform = 'translateX(-100%)';
      ticks.appendChild(s);
    });
    function onRange(e) {
      var a = +lo.value, b = +hi.value;
      if (a > b - 1) { if (e && e.target === lo) { a = b - 1; lo.value = a; } else { b = a + 1; hi.value = b; } }
      st.lo = a; st.hi = b;
      update();
    }
    lo.addEventListener('input', onRange);
    hi.addEventListener('input', onRange);
    el.querySelector('#ex-undated').addEventListener('change', function (e) { st.undated = e.target.checked; update(); });
    el.querySelectorAll('[data-kind]').forEach(function (b) {
      b.addEventListener('click', function () {
        st.kind = b.getAttribute('data-kind');
        el.querySelectorAll('[data-kind]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        update();
      });
    });
    function checks(box, list, arr, prefix) {
      box.innerHTML = list.map(function (it, i) {
        return '<label for="' + prefix + i + '"><span class="l"><input type="checkbox" id="' + prefix + i + '" data-i="' + i + '" checked>' +
          esc(it[0]) + '</span><span class="n">' + it[1] + '</span></label>';
      }).join('');
      box.addEventListener('change', function (e) {
        var i = +e.target.getAttribute('data-i');
        arr[i] = e.target.checked;
        update();
      });
    }
    checks(el.querySelector('[data-ev]'), D.evidence, st.ev, 'ex-ev');
    checks(el.querySelector('[data-tr]'), D.traditions, st.tr, 'ex-tr');

    // ---- map
    var map = null, popup = null, markers = [];
    var mapEl = el.querySelector('#ta-map');
    var POINT_LAYERS = ['approx', 'river', 'capital', 'exact'];
    function fc() {
      return {
        type: 'FeatureCollection',
        features: Object.keys(P).filter(function (k) {
          var p = P[k]; return p.lon != null && p.b !== 'anchor' && p.b !== 'none';
        }).map(function (k) {
          var p = P[k];
          return { type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon, p.lat] }, properties: { id: p.id, n: p.count, b: p.b, name: p.n } };
        })
      };
    }
    var Rexp = ['+', 2.5, ['*', 1.8, ['sqrt', ['get', 'n']]]];
    function rad(extra) {
      var r = extra ? ['+', Rexp, extra] : Rexp;
      return ['interpolate', ['linear'], ['zoom'], 1, ['*', 0.8, r], 4, r, 7, ['*', 1.5, r]];
    }
    function paintAll() {
      if (!map || !map.getLayer('exact')) return;
      var c = {
        water: cssVar('--map-water'), land: cssVar('--map-land'), coast: cssVar('--map-coast'), river: cssVar('--map-river'),
        pt: cssVar('--map-point'), rpt: cssVar('--map-river-point'), cap: cssVar('--map-capital'),
        approx: cssVar('--map-approx'), halo: cssVar('--map-halo'), ink: cssVar('--ink')
      };
      map.setPaintProperty('bg', 'background-color', c.water);
      if (map.getLayer('land')) {
        map.setPaintProperty('land', 'fill-color', c.land);
        map.setPaintProperty('coast', 'line-color', c.coast);
        map.setPaintProperty('lakes', 'fill-color', c.water);
        map.setPaintProperty('lakes-line', 'line-color', c.coast);
        map.setPaintProperty('rivers', 'line-color', c.river);
      }
      map.setPaintProperty('approx-halo', 'circle-color', c.approx);
      map.setPaintProperty('approx', 'circle-stroke-color', c.approx);
      map.setPaintProperty('river', 'circle-color', c.rpt);
      map.setPaintProperty('river', 'circle-stroke-color', c.halo);
      map.setPaintProperty('capital-ring', 'circle-stroke-color', c.cap);
      map.setPaintProperty('capital', 'circle-color', c.cap);
      map.setPaintProperty('capital', 'circle-stroke-color', c.halo);
      map.setPaintProperty('exact', 'circle-color', c.pt);
      map.setPaintProperty('exact', 'circle-stroke-color', c.halo);
      map.setPaintProperty('sel', 'circle-stroke-color', c.ink);
    }
    function on(b) { return ['all', ['==', ['get', 'b'], b], ['>', ['get', 'n'], 0]]; }
    function initMap() {
      if (!window.maplibregl) {
        mapEl.innerHTML = '<div class="map-fallback">The map could not load here. Try <a href="' + TA.href('places') + '">every place</a> or <a href="' + TA.href('records') + '">every book and map</a> ' +
          'instead.</div>';
        return;
      }
      try {
        map = new maplibregl.Map({
          container: mapEl,
          style: { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': cssVar('--map-water') } }] },
          bounds: [[22, 18], [148, 72]], fitBoundsOptions: { padding: 16 },
          minZoom: 0.8, maxZoom: 9, attributionControl: false, dragRotate: false, pitchWithRotate: false
        });
      } catch (e) {
        mapEl.innerHTML = '<div class="map-fallback">This browser could not start the map. ' +
          '<a href="' + TA.href('places') + '">See every place as a list</a>.</div>';
        return;
      }
      map.touchZoomRotate.disableRotation();
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
      map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: 'Basemap: Natural Earth' }), 'bottom-right');
      TA.cleanups.push(function () { markers.forEach(function (m) { m.remove(); }); map.remove(); map = null; });
      TA.cleanups.push(onTheme(paintAll));
      map.on('load', function () {
        map.addSource('places', { type: 'geojson', data: fc() });
        map.addLayer({ id: 'approx-halo', type: 'circle', source: 'places', filter: on('approx'),
          paint: { 'circle-radius': rad(7), 'circle-opacity': 0.11, 'circle-blur': 0.5, 'circle-color': '#a8304a' } });
        map.addLayer({ id: 'approx', type: 'circle', source: 'places', filter: on('approx'),
          paint: { 'circle-radius': rad(0), 'circle-opacity': 0, 'circle-stroke-width': 1.6, 'circle-stroke-color': '#a8304a' } });
        map.addLayer({ id: 'river', type: 'circle', source: 'places', filter: on('river'),
          layout: { 'circle-sort-key': ['-', 0, ['get', 'n']] },
          paint: { 'circle-radius': rad(0), 'circle-color': '#5f9c95', 'circle-stroke-width': 1, 'circle-stroke-color': '#fff' } });
        map.addLayer({ id: 'capital-ring', type: 'circle', source: 'places', filter: on('capital'),
          paint: { 'circle-radius': rad(3.5), 'circle-opacity': 0, 'circle-stroke-width': 1.2, 'circle-stroke-color': '#1a2327' } });
        map.addLayer({ id: 'capital', type: 'circle', source: 'places', filter: on('capital'),
          paint: { 'circle-radius': rad(0), 'circle-color': '#1a2327', 'circle-stroke-width': 1.5, 'circle-stroke-color': '#fff' } });
        map.addLayer({ id: 'exact', type: 'circle', source: 'places', filter: on('exact'),
          layout: { 'circle-sort-key': ['-', 0, ['get', 'n']] },
          paint: { 'circle-radius': rad(0), 'circle-color': '#1d6a63', 'circle-stroke-width': 1.2, 'circle-stroke-color': '#fff' } });
        map.addLayer({ id: 'sel', type: 'circle', source: 'places', filter: ['==', ['get', 'id'], ''],
          paint: { 'circle-radius': rad(5), 'circle-opacity': 0, 'circle-stroke-width': 2.2, 'circle-stroke-color': '#000' } });
        paintAll();
        fetch(TA.asset('basemap.json')).then(function (r) { return r.json(); }).then(function (bm) {
          if (!map) return;
          map.addSource('land', { type: 'geojson', data: bm.land });
          map.addSource('lakes', { type: 'geojson', data: bm.lakes });
          map.addSource('rivers', { type: 'geojson', data: bm.rivers });
          map.addLayer({ id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': '#eee' } }, 'approx-halo');
          map.addLayer({ id: 'lakes', type: 'fill', source: 'lakes', paint: { 'fill-color': '#ccc' } }, 'approx-halo');
          map.addLayer({ id: 'rivers', type: 'line', source: 'rivers', paint: { 'line-color': '#9bc', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.5, 6, 1.6] } }, 'approx-halo');
          map.addLayer({ id: 'lakes-line', type: 'line', source: 'lakes', paint: { 'line-color': '#999', 'line-width': 0.5 } }, 'approx-halo');
          map.addLayer({ id: 'coast', type: 'line', source: 'land', paint: { 'line-color': '#999', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.4, 6, 1] } }, 'approx-halo');
          paintAll();
        }).catch(function () { /* the points still render on plain water */ });

        popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, maxWidth: '260px' });
        POINT_LAYERS.forEach(function (id) {
          map.on('mousemove', id, function (e) {
            map.getCanvas().style.cursor = 'pointer';
            var f = e.features[0].properties;
            popup.setLngLat(e.lngLat).setHTML('<strong>' + esc(f.name) + '</strong><br>' + f.n + ' source' + (f.n === 1 ? '' : 's') +
              ' · ' + esc(D.basis[f.b]).toLowerCase()).addTo(map);
          });
          map.on('mouseleave', id, function () { map.getCanvas().style.cursor = ''; popup.remove(); });
          map.on('click', id, function (e) { select(e.features[0].properties.id); });
        });
        Object.keys(P).forEach(function (k) {
          var p = P[k];
          if (p.b !== 'anchor' || p.lon == null) return;
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'map-label';
          b.setAttribute('aria-label', p.n + ', map label position');
          b.addEventListener('click', function (ev) { ev.stopPropagation(); select(p.id); });
          p.el = b;
          markers.push(new maplibregl.Marker({ element: b }).setLngLat([p.lon, p.lat]).addTo(map));
        });
        var sizeLabels = function () {
          var z = map.getZoom();
          var fs = Math.max(10, Math.min(17, 8 + z * 2.4));
          // On a narrow map the Tartary labels pile up at the opening zoom, so they wait until the reader zooms in.
          var crowded = mapEl.clientWidth < 620 && z < 2.2;
          markers.forEach(function (m) { var e = m.getElement(); e.style.fontSize = fs + 'px'; e.style.visibility = crowded ? 'hidden' : ''; });
        };
        map.on('zoom', sizeLabels);
        sizeLabels();
        update();
      });
    }

    function select(id) {
      st.sel = id;
      if (map && map.getLayer('sel')) map.setFilter('sel', ['==', ['get', 'id'], id || '']);
      renderPanel();
      if (window.matchMedia && window.matchMedia('(max-width: 900px)').matches) {
        var pn = el.querySelector('[data-panel]');
        if (pn && id) pn.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    // ---- recompute
    var shown = [];
    function update() {
      Object.keys(P).forEach(function (k) { P[k].count = 0; });
      shown = [];
      var bins = new Array(50).fill(0), binsOn = new Array(50).fill(false);
      R.forEach(function (r) {
        if (!passOther(r)) return;
        if (r.s != null) { var bi = Math.min(49, Math.max(0, Math.floor(toSlider(r.s) / 2))); bins[bi]++; }
        if (!passDate(r)) return;
        shown.push(r);
        r.p.forEach(function (pid) { if (P[pid]) P[pid].count++; });
      });
      // readout and fill
      fill.style.left = st.lo + '%';
      fill.style.right = (100 - st.hi) + '%';
      var a = st.lo <= 0 ? 'the earliest' : yearText(sliderYear(st.lo));
      var b = st.hi >= 100 ? 'the latest' : yearText(sliderYear(st.hi));
      readout.textContent = (st.lo <= 0 && st.hi >= 100) ? 'All dates' : 'From ' + a + ' to ' + b;
      // histogram
      var mx = Math.max.apply(null, bins) || 1;
      hist.innerHTML = bins.map(function (n, i) {
        var h = n ? Math.max(1.5, n / mx * 42) : 0;
        var inR = (i * 2 + 1) >= st.lo && (i * 2 + 1) <= st.hi;
        return '<rect x="' + (i * 4 + 0.3) + '" y="' + (44 - h) + '" width="3.4" height="' + h + '"' + (inR ? ' class="on"' : '') + '></rect>';
      }).join('');
      // stats
      var plotted = 0;
      Object.keys(P).forEach(function (k) { var p = P[k]; if (p.count && p.lon != null && p.b !== 'none') plotted++; });
      var sr = el.querySelector('[data-stat="records"]'), sp = el.querySelector('[data-stat="places"]');
      if (sr) sr.textContent = shown.length;
      if (sp) sp.textContent = plotted;
      if (map && map.getSource('places')) map.getSource('places').setData(fc());
      Object.keys(P).forEach(function (k) {
        var p = P[k];
        if (!p.el) return;
        p.el.innerHTML = esc(p.n) + '<small>' + p.count + '</small>';
        p.el.classList.toggle('dim', !p.count);
      });
      renderPanel();
    }

    function recItem(r) {
      return '<li><div class="yr">' + esc(r.d) + '</div><div class="body"><a class="t" href="' + recHref(r) + '">' + esc(r.t) + '</a>' +
        '<div class="meta"><span class="kind' + (r.m ? ' m' : '') + '">' + (r.m ? 'M' : 'W') + '</span><span>' + esc(r.c) + '</span>' +
        '<span class="rid">' + r.id + '</span></div></div></li>';
    }
    function renderPanel() {
      var pn = el.querySelector('[data-panel]');
      if (!pn) return;
      if (st.sel && P[st.sel]) {
        var p = P[st.sel];
        var recs = shown.filter(function (r) { return r.p.indexOf(p.id) >= 0; });
        recs.sort(function (a, b) { return (a.s == null) - (b.s == null) || (a.s - b.s) || (a.id < b.id ? -1 : 1); });
        pn.innerHTML = '<div class="eyebrow"><span class="basis-dot ' + p.b + '"></span> ' + esc(D.basis[p.b] || '') + '</div>' +
          '<h2>' + esc(p.n) + '</h2>' +
          (p.psg ? '<p><a class="btn primary" href="' + TA.href('place/' + p.id) + '">Read ' + p.psg + ' passage' + (p.psg === 1 ? '' : 's') + ' about ' + esc(p.n) + '</a></p>' : '') +
          '<p class="small muted">Named in ' + recs.length + ' book' + (recs.length === 1 ? '' : 's') + ' and maps. ' +
          '<a href="' + TA.href('place/' + p.id) + '">See everything about ' + esc(p.n) + '</a></p>' +
          (recs.length ? '<ol class="rlist">' + recs.map(recItem).join('') + '</ol>' : '<p class="muted">Nothing in these years. Widen the dates.</p>') +
          '<p><button type="button" class="chip" data-clear>Pick another place</button></p>';
        pn.querySelector('[data-clear]').addEventListener('click', function () { select(null); });
        return;
      }
      var ranked = Object.keys(P).map(function (k) { return P[k]; })
        .filter(function (p) { return p.count && p.b !== 'none' && p.lon != null; })
        .sort(function (a, b) { return b.count - a.count; }).slice(0, 12);
      var nopoint = Object.keys(P).map(function (k) { return P[k]; })
        .filter(function (p) { return p.count && p.b === 'none'; })
        .sort(function (a, b) { return b.count - a.count; }).slice(0, 10);
      pn.innerHTML = '<h2 style="font-family:var(--font-body);font-size:var(--step-0);font-weight:650">Try one of these</h2>' +
        '<ul class="tags">' + ranked.map(function (p) {
          return '<li><button type="button" class="chip" data-sel="' + esc(p.id) + '"><span class="basis-dot ' + p.b + '"></span>' + esc(p.n) +
            ' <span class="mono muted">' + p.count + '</span></button></li>';
        }).join('') + '</ul>' +
        (nopoint.length ? '<div class="nopoint"><p>Too big for one dot:</p><ul>' + nopoint.map(function (p) {
          return '<li><a href="' + TA.href('place/' + p.id) + '"><span class="chip"><span class="basis-dot none"></span>' + esc(p.n) +
            ' <span class="mono muted">' + p.count + '</span></span></a></li>';
        }).join('') + '</ul><p class="small muted" style="margin-top:6px">Tartary and Great Tartary changed shape from map to map. ' +
          '<a href="' + TA.href('labels') + '">See the many Tartarys</a>.</p></div>' : '');
      pn.querySelectorAll('[data-sel]').forEach(function (b) {
        b.addEventListener('click', function () {
          var p = P[b.getAttribute('data-sel')];
          select(p.id);
          if (map && p.lon != null) map.easeTo({ center: [p.lon, p.lat], duration: 600 });
        });
      });
    }

    update();
    initMap();
  };

  /* ------------------------------------------------------------ labels timeline */
  TA.modules.labels = function (el) {
    var svg = el.querySelector('svg');
    var inp = el.querySelector('#lab-y'), out = el.querySelector('[data-out]');
    var y0 = +svg.getAttribute('data-y0'), y1 = +svg.getAttribute('data-y1');
    var left = +svg.getAttribute('data-left'), pw = +svg.getAttribute('data-plotw');
    var cursor = svg.querySelector('[data-cursor]'), win = svg.querySelector('[data-window]');
    var marks = Array.prototype.slice.call(svg.querySelectorAll('a[data-y]'));
    var list = el.querySelector('[data-window-list]');
    var W = 25;
    function X(y) { return left + (Math.max(y0, Math.min(y1, y)) - y0) / (y1 - y0) * pw; }
    function upd() {
      var y = +inp.value;
      out.textContent = y;
      cursor.style.display = '';
      cursor.setAttribute('x1', X(y)); cursor.setAttribute('x2', X(y));
      win.setAttribute('x', X(y - W)); win.setAttribute('width', X(y + W) - X(y - W));
      var groups = [], byLabel = {};
      marks.forEach(function (a) {
        var yy = +a.getAttribute('data-y');
        var inW = Math.abs(yy - y) <= W;
        a.classList.toggle('dim', !inW);
        if (!inW) return;
        var lid = a.getAttribute('data-label');
        if (!byLabel[lid]) { byLabel[lid] = { name: a.getAttribute('data-lname'), items: [] }; groups.push(byLabel[lid]); }
        byLabel[lid].items.push('<a href="' + a.getAttribute('href') + '">' + esc(a.querySelector('title').textContent) + '</a>');
      });
      list.innerHTML = '<h2>In use from ' + (y - W) + ' to ' + (y + W) + '</h2>' +
        (groups.length ? groups.map(function (g) {
          return '<div style="display:grid;gap:4px"><div class="eyebrow">' + esc(g.name) + ' · ' + g.items.length + '</div>' +
            '<ul class="note-list">' + g.items.map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ul></div>';
        }).join('') : '<p class="muted">No Tartary on the maps in these years.</p>');
    }
    inp.addEventListener('input', upd);
    upd();
  };

  /* ------------------------------------------------------------ records table */
  TA.modules.rtable = function (el) {
    var q = el.querySelector('#rt-q'), k = el.querySelector('#rt-k'), ev = el.querySelector('#rt-ev');
    var body = el.querySelector('tbody');
    var rows = arr(body.querySelectorAll('tr'));
    var saved = TA.restoring ? TA.mem.get('rt') : null;
    if (saved) { q.value = saved.q || ''; k.value = saved.k || ''; ev.value = saved.ev || ''; }
    function upd() {
      var words = searchWords(q), n = 0;
      rows.forEach(function (tr) {
        var ok = (!k.value || tr.getAttribute('data-k') === k.value) &&
          (!ev.value || tr.getAttribute('data-ev') === ev.value) &&
          words.every(function (w) { return tr.getAttribute('data-h').indexOf(w) >= 0; });
        tr.hidden = !ok;
        var chip = tr.querySelector('[data-set]');
        if (chip) chip.setAttribute('aria-pressed', ev.value && chip.getAttribute('data-set') === ev.value ? 'true' : 'false');
        if (ok) n++;
      });
      countUI(el, n, words.length > 0 || !!k.value || !!ev.value);
      el.querySelector('.table-wrap').hidden = n === 0;
      TA.mem.set('rt', { q: q.value, k: k.value, ev: ev.value });
    }
    [q, k, ev].forEach(function (x) { x.addEventListener('input', upd); });
    body.addEventListener('click', function (e) {
      var chip = e.target.closest('[data-set]');
      if (!chip) return;
      var v = chip.getAttribute('data-set');
      ev.value = ev.value === v ? '' : v;
      upd();
    });
    el.querySelector('[data-clear]').addEventListener('click', function () { q.value = ''; k.value = ''; ev.value = ''; upd(); q.focus(); });
    if (saved) { upd(); TA.rescroll(); }
  };

  /* ------------------------------------------------------------ start */
  if (PREVIEW) {
    var pages = JSON.parse(document.getElementById('ta-pages').textContent);
    var main = document.getElementById('main');
    var byHash = {};
    Object.keys(pages).forEach(function (k) { byHash[k ? k.replace('/', '-') : 'home'] = k; });
    var isPage = function (h) { return Object.prototype.hasOwnProperty.call(byHash, h); };
    var seq = 0, started = false;
    var show = function () {
      var h = decodeURIComponent(location.hash.slice(1));
      var pg = pages[isPage(h) ? byHash[h] : ''];
      // An entry already stamped is one the reader is coming back to; a fresh one gets its stamp now.
      var st = null;
      try { st = history.state; } catch (e) { /* history is closed to this frame */ }
      TA.restoring = !!(st && st.ta);
      if (!TA.restoring) { try { history.replaceState({ ta: ++seq }, ''); } catch (e) { /* carry on without */ } }
      TA.destroy();
      main.innerHTML = pg.h;
      document.title = pg.t;
      document.querySelectorAll('.site-nav a').forEach(function (a) {
        if (a.getAttribute('data-nav') === pg.n) a.setAttribute('aria-current', 'page');
        else a.removeAttribute('aria-current');
      });
      navReveal();
      TA.init(main);
      if (TA.restoring) holdScroll(TA.mem.get('y') || 0);
      else { pendingY = null; window.scrollTo(0, 0); }
      if (started) main.focus({ preventScroll: true });
      started = true;
      toTop();
    };
    // A link to a spot on the page (the skip link) must not be read as a page address.
    document.addEventListener('click', function (e) {
      var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      var h = decodeURIComponent(a.getAttribute('href').slice(1));
      var target = !isPage(h) && document.getElementById(h);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView();
      target.focus({ preventScroll: true });
    });
    try { history.scrollRestoration = 'manual'; } catch (e) { /* the page still works; Back may land at the top */ }
    window.addEventListener('hashchange', show);
    TA.wordmark();
    show();
  } else {
    var start = function () {
      try {
        var nav = performance.getEntriesByType('navigation')[0];
        TA.restoring = !!nav && nav.type === 'back_forward';
      } catch (e) { /* older browsers: nothing to restore */ }
      if (TA.restoring && TA.mem.get('y')) holdScroll(TA.mem.get('y'));
      navReveal();
      TA.wordmark();
      TA.init(document);
      toTop();
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
  }
})();
