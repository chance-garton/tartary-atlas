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
    if (PREVIEW) return '#' + (key ? key.replace('/', '-') : 'map');
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

  /* ------------------------------------------------------------ explorer */
  TA.modules.explorer = function (el) {
    var D = JSON.parse(el.querySelector('script[type="application/json"]').textContent);
    var R = D.records.map(function (a) {
      return { id: a[0], m: a[1], s: a[2], d: a[3], ev: a[4], tr: a[5], t: a[6], c: a[7], p: a[8] };
    });
    var P = {};
    D.places.forEach(function (a) { P[a[0]] = { id: a[0], n: a[1], b: a[2], lon: a[3], lat: a[4], count: 0 }; });
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
    var mapEl = el.querySelector('#map');
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
        mapEl.innerHTML = '<div class="map-fallback">The interactive map could not load here. Every place and record is still listed on the ' +
          '<a href="' + TA.href('places') + '">Places</a> and <a href="' + TA.href('records') + '">Records</a> pages.</div>';
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
        mapEl.innerHTML = '<div class="map-fallback">This browser could not start the map (it needs WebGL). The ' +
          '<a href="' + TA.href('places') + '">Places</a> page lists every place.</div>';
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
            popup.setLngLat(e.lngLat).setHTML('<strong>' + esc(f.name) + '</strong><br>' + f.n + ' record' + (f.n === 1 ? '' : 's') +
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
          markers.forEach(function (m) { m.getElement().style.fontSize = fs + 'px'; });
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
          '<p class="small muted">' + recs.length + ' record' + (recs.length === 1 ? '' : 's') + ' in this selection, in date order. ' +
          '<a href="' + TA.href('place/' + p.id) + '">Open the place page</a></p>' +
          (recs.length ? '<ol class="rlist">' + recs.map(recItem).join('') + '</ol>' : '<p class="muted">No records match the current filters.</p>') +
          '<p><button type="button" class="chip" data-clear>Clear selection</button></p>';
        pn.querySelector('[data-clear]').addEventListener('click', function () { select(null); });
        return;
      }
      var ranked = Object.keys(P).map(function (k) { return P[k]; })
        .filter(function (p) { return p.count && p.b !== 'none' && p.lon != null; })
        .sort(function (a, b) { return b.count - a.count; }).slice(0, 12);
      var nopoint = Object.keys(P).map(function (k) { return P[k]; })
        .filter(function (p) { return p.count && p.b === 'none'; })
        .sort(function (a, b) { return b.count - a.count; }).slice(0, 10);
      pn.innerHTML = '<h2 style="font-family:var(--font-body);font-size:var(--step-0);font-weight:650">Most named in this selection</h2>' +
        '<ul class="tags">' + ranked.map(function (p) {
          return '<li><button type="button" class="chip" data-sel="' + esc(p.id) + '"><span class="basis-dot ' + p.b + '"></span>' + esc(p.n) +
            ' <span class="mono muted">' + p.count + '</span></button></li>';
        }).join('') + '</ul>' +
        (nopoint.length ? '<div class="nopoint"><p>Named, but deliberately not plotted:</p><ul>' + nopoint.map(function (p) {
          return '<li><a href="' + TA.href('place/' + p.id) + '"><span class="chip"><span class="basis-dot none"></span>' + esc(p.n) +
            ' <span class="mono muted">' + p.count + '</span></span></a></li>';
        }).join('') + '</ul><p class="small muted" style="margin-top:6px">Tartary and Great Tartary changed shape from map to map. ' +
          '<a href="' + TA.href('labels') + '">See when each Tartary label was in use</a>.</p></div>' : '');
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
        }).join('') : '<p class="muted">No record carries a Tartary label in these years.</p>');
    }
    inp.addEventListener('input', upd);
    upd();
  };

  /* ------------------------------------------------------------ records table */
  TA.modules.rtable = function (el) {
    var q = el.querySelector('#rt-q'), k = el.querySelector('#rt-k'), ev = el.querySelector('#rt-ev');
    var cnt = el.querySelector('[data-count]');
    var rows = Array.prototype.slice.call(el.querySelectorAll('tbody tr'));
    function upd() {
      var words = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      var n = 0;
      rows.forEach(function (tr) {
        var ok = (!k.value || tr.getAttribute('data-k') === k.value) &&
          (!ev.value || tr.getAttribute('data-ev') === ev.value) &&
          words.every(function (w) { return tr.getAttribute('data-h').indexOf(w) >= 0; });
        tr.hidden = !ok;
        if (ok) n++;
      });
      cnt.textContent = n;
    }
    [q, k, ev].forEach(function (x) { x.addEventListener('input', upd); });
  };

  /* ------------------------------------------------------------ start */
  if (PREVIEW) {
    var pages = JSON.parse(document.getElementById('ta-pages').textContent);
    var main = document.getElementById('main');
    var keyFromHash = function () {
      var h = decodeURIComponent(location.hash.slice(1));
      if (!h || h === 'map') return '';
      var m = h.match(/^(w|m|place|peoples)-(.+)$/);
      return m ? m[1] + '/' + m[2] : h;
    };
    var show = function () {
      var key = keyFromHash();
      var pg = pages[key];
      if (!pg) { key = ''; pg = pages['']; }
      TA.destroy();
      main.innerHTML = pg.h;
      document.title = pg.t;
      document.querySelectorAll('.site-nav a').forEach(function (a) {
        if (a.getAttribute('data-nav') === pg.n) a.setAttribute('aria-current', 'page');
        else a.removeAttribute('aria-current');
      });
      TA.init(main);
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', show);
    show();
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { TA.init(document); });
  } else {
    TA.init(document);
  }
})();
