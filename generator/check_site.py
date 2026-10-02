#!/usr/bin/env python3
"""Checks the built site: five known records render, place lists are in date order,
approximate points never look surveyed, no em dashes, and every internal link resolves.
Run after generator/build.py:  python3 generator/check_site.py"""
import json, re, pathlib, html
ROOT = pathlib.Path(__file__).resolve().parent.parent; D = ROOT/'docs'
R = {r['id']: r for r in json.load(open(ROOT/'data/records.json'))}
P = {p['id']: p for p in json.load(open(ROOT/'data/places.json'))}
ok = True
def check(cond, msg):
    global ok
    print(('PASS ' if cond else 'FAIL ') + msg); ok &= cond
# 1. five known records
for rid, expect in [('W122', '1692'), ('M081', '1562'), ('M004', '1570'), ('W118', '1228–1252'), ('M029', 'Undated')]:
    k = ('w/' if R[rid]['kind'] == 'written' else 'm/') + rid
    t = (D/k/'index.html').read_text()
    title = re.search(r'<title>(.*?)</title>', t).group(1)
    check(expect in t and 'How we know' in t and R[rid]['primary_access'] in html.unescape(t), f'{rid} renders ({html.unescape(title)[:70]})')
m029 = (D/'m/M029/index.html').read_text()
check('<strong>Undated</strong>' in m029, 'M029 shows as undated')
lab = (D/'labels/index.html').read_text() + (D/'meanings/index.html').read_text()
check('data-y="None"' not in lab, 'no undated marks on timelines')
# 2. date order
def sk(r):
    d = r['date']; return (1, 0, 0) if d['made_start'] is None else (0, d['made_start'], d['made_end'] or d['made_start'])
for pid in ['tobolsk', 'kazan', 'beijing']:
    t = (D/'place'/pid/'index.html').read_text()
    ids = re.findall(r'<span class="rid">([WM]\d{3})</span></div></div></li>', t)
    keys = [sk(R[i]) for i in ids]
    check(len(ids) == len(P[pid]['records']) and keys == sorted(keys), f'{pid}: {len(ids)} records in date order: ' + ', '.join(f"{i} {R[i]['date']['made_start']}" for i in ids))
# 3. approximate points never styled as surveyed
bad = []
for pid, p in P.items():
    b = p['coord_basis']
    if p['lat'] is None: continue
    t = (D/'place'/pid/'index.html').read_text()
    svg = re.search(r'<svg class="minimap".*?</svg>', t, re.S)
    if not svg: continue
    svg = svg.group(0)
    if b in ('approx', 'centroid'):
        if 'class="approx"' not in svg or 'class="pt' in svg: bad.append(pid)
    elif b == 'anchor':
        if 'class="anchor"' not in svg or 'class="pt' in svg: bad.append(pid)
    else:
        if 'class="approx"' in svg: bad.append(pid)
check(not bad, f'mini maps: approximate and anchor points never drawn as surveyed dots ({len(bad)} bad {bad[:5]})')
home = (D/'map/index.html').read_text()
data = json.loads(html.unescape(re.search(r'<script type="application/json">(.*?)</script>', home, re.S).group(1)).replace('<\\/', '</'))
grp = {a[0]: a[2] for a in data['places']}
wrong = [pid for pid, p in P.items() if p['coord_basis'] in ('approx', 'centroid', 'anchor') and grp[pid] not in ('approx', 'anchor')]
check(not wrong, f'explorer: every approximate or anchor place is in an approximate style group ({wrong[:5]})')
# 3b. passages: every passage is on its source page, its trail file and its place pages
PS = json.load(open(ROOT/'data/passages.json'))
psg = PS['passages']
lost = [p['id'] for p in psg if f'id="p-{p["id"]}"' not in (D/'w'/p['rec']/'index.html').read_text()]
check(not lost, f'{len(psg)} passages each appear on their source page ({lost[:5]})')
n_files = sum(len(json.load(open(D/'assets'/f'passages-{t}.json'))['p']) for t in ['cities', 'architecture', 'customs', 'names', 'outliers'])
check(n_files == len(psg), f'trail data files hold all {len(psg)} passages ({n_files})')
bad_url = [p['id'] for p in psg if not p['url'].startswith('https://')]
check(not bad_url, f'every passage links to a page ({bad_url[:5]})')
kz = (D/'place/kazan/index.html').read_text()
check(kz.count('<article class="psg"') == sum(1 for p in psg if 'kazan' in p['place_ids']), 'kazan place page carries every Kazan passage')
front = (D/'index.html').read_text()
check('Follow a question' in front and front.count('class="trail"') == 5 and 'data-module="feature"' in front, 'front page has the five trails and a featured passage')
check(0 < front.index('One passage from the record') < front.index('Follow a question') and 'What has been read' not in front, 'front page: the passage comes first, above the trails, with no progress report')
# 3c. the pills above a set of passages are buttons that filter it
w43 = (D/'w/W043/index.html').read_text()
check('data-module="pset"' in w43 and w43.count('class="pill" data-f=') >= 3 and 'data-copy' in w43, 'source page: trail pills are filter buttons, cards carry a copy button')
check(kz.count('data-th="') == kz.count('<article class="psg"'), 'every passage card says which trail it belongs to')
# 3d. the ways onward: the door from a passage into its source, a random front page passage, no dead ends
check(kz.count('class="psg-tale"') == kz.count('<article class="psg"') and 'About this source' not in kz, 'place page: every passage card opens onto its source with the Explore door')
check('class="psg-tale"' not in w43 and 'Keep exploring' in w43 and 'data-module="lucky"' in w43, 'source page: no door to itself, and it ends with the witness before, the witness after and Surprise me')
feat = json.loads(re.search(r'data-module="feature"><script type="application/json">(.*?)</script>', front, re.S).group(1).replace('<\\/', '</'))
per = {}
for q in feat['p']: per[(q['th'], q['r'])] = per.get((q['th'], q['r']), 0) + 1
check(len(feat['p']) >= 60 and max(per.values()) <= 2 and all(q['r'] in feat['src'] for q in feat['p']), f"front page draws its passage from a pool of {len(feat['p'])}, at most two per source in a trail")
m81 = (D/'m/M081/index.html').read_text()
check('data-zoom="' in m81 and 'Keep exploring' in m81, 'map page: the picture opens a closer look, and the page ends with the neighbouring maps')
check(kz.count('data-basis') == kz.count('<article class="psg"'), 'every passage card has a pressable label for how the author knew')
# 3e. the front door map, the lettering in the header and the ornaments
fmap = feat.get('map') or {}
pin_ids = {q['i'] for q in fmap.get('pins', [])}
check(len(pin_ids) >= 20 and all(q['i'] in P for q in fmap['pins']) and all(0 < q['x'] < 1 and 0 < q['y'] < 1 for q in fmap['pins'] + fmap['sights']),
      f"front map: {len(pin_ids)} pinned places, all in the gazetteer and all on the sheet, and {len(fmap.get('sights', []))} notes")
check(all(q['pn'] in pin_ids for q in feat['p'] if 'pn' in q) and all(any(q.get('pn') == i for q in feat['p']) for i in pin_ids), 'front map: every pin has a passage to show, and every placed passage has its pin')
check('data-osd' in front and 'openseadragon' in front and 'class="front-still"' in front, 'front page: the map viewer is loaded and the still picture stands in until it is')
cuts = json.load(open(ROOT/'data/cuts.json'))
gone = [c['key'] for c in cuts['labels'] if not (D/'assets/cuts/labels'/(c['key'] + '.png')).exists()] + [c['key'] for c in cuts['ornaments'] if not (D/'assets/cuts/ornaments'/(c['key'] + '.png')).exists()]
check(not gone, f"every cut in data/cuts.json has its picture in the site ({gone[:5]})")
check('data-wordmarks=' in w43 and 'mask-image:url(../../assets/cuts/labels/' in w43, 'header: the name is set in lettering cut from a map, addressed from the page')
check(front.count('class="orn-rule"') >= 4 and 'One name, many hands' in front, 'front page: the many hands strip and the ornament rules are there')
# 3f. the rides and the deck
J = json.load(open(ROOT/'data/journeys.json'))['journeys']
PID = {p['id']: p for p in psg}
bad = []
for j in J:
    t = (D/'ride'/j['key']/'index.html').read_text()
    ids = [i for s in j['stops'] for i in s['psg']]
    if t.count('<li class="ride-stop') != len(j['stops']) or t.count('class="leg"') != len(j['stops']) - 1 or t.count('class="rdot ') != len(j['stops']): bad.append(j['key'] + ': stops')
    if any(i not in PID or PID[i]['rec'] != j['rec'] or f'id="p-{i}"' not in t for i in ids) or len(ids) != len(set(ids)): bad.append(j['key'] + ': passages')
    if set(ids) | {x['id'] for x in j['left_out']} != {p['id'] for p in psg if p['rec'] == j['rec']}: bad.append(j['key'] + ': a passage is neither on the road nor left out')
    if any(not (-10 <= s['lon'] <= 150 and 20 <= s['lat'] <= 70) for s in j['stops']): bad.append(j['key'] + ': a stop is off the sheet')
    if '–' in json.dumps(j, ensure_ascii=False) or '—' in json.dumps(j, ensure_ascii=False): bad.append(j['key'] + ': dash')
    if 'Ride the route' not in (D/'w'/j['rec']/'index.html').read_text(): bad.append(j['key'] + ': no way in from the source page')
check(len(J) >= 6 and not bad, f'rides: {len(J)} journeys, every stop drawn, every passage of the source either on the road or left out with a reason ({bad[:4]})')
rides = (D/'ride/index.html').read_text()
check(rides.count('class="ridecard"') == len(J) and front.count('class="ridecard"') == 3 and 'Ride with a traveler' in front, 'rides: the list shows them all and the front page offers three')
deck = (D/'deck/index.html').read_text()
dd = json.loads(re.search(r'data-module="deck"><script type="application/json">(.*?)</script>', deck, re.S).group(1))
check(len(dd['spread']) == 3 and deck.count('data-card') == 3 and set(dd['suits']) == {'cities', 'architecture', 'customs', 'names', 'outliers'}
      and all((D/'assets/cuts/ornaments'/(v['k'] + '.png')).exists() for v in dd['suits'].values()), 'deck: three places in the spread and a suit drawing for each of the five trails')
check('class="deck-door-a"' in front and 'draw three from the deck' in (D/'passages/index.html').read_text(), 'deck: a door on the front page and on the passages page')
# 3g. the time dial
DL = json.load(open(ROOT/'data/dial.json'))
dl = (D/'dial/index.html').read_text()
on = [m for m in DL['maps'] if not m.get('off')]
dj = json.loads(re.search(r'data-module="dial"><script type="application/json">(.*?)</script>', dl, re.S).group(1))
bad = [m['key'] for m in on if not (D/'assets/dial'/(m['key'] + '.webp')).exists() or 'loc.gov' not in m['iiif'] or len([p for p in m['points'] if not p.get('skip')]) < 25
       or any(not (0 <= x <= 1600 and 0 <= y <= 1000) for lb in m['labels'] for x, y in lb['mid'])]
check(len(on) >= 12 and not bad and len(dj['stops']) == len(on) + len(DL['early']) and dl.count('<article class="dial-card') == len(dj['stops']),
      f"dial: {len(on)} maps, each a Library of Congress sheet with 25 or more matched places, its bent picture in the site and its Tartary lettering on the sheet ({bad[:4]})")
check([s['y'] for s in dj['stops']] == sorted(s['y'] for s in dj['stops']) and all(0 <= s['p'] <= 1 for s in dj['stops']) and dl.count('class="dial-stop') == len(dj['stops']), 'dial: the stops run in date order along the scale')
check('—' not in json.dumps(DL, ensure_ascii=False) and '–' not in json.dumps([[m['says'], m.get('uncertain'), m['head']] for m in DL['maps']] + DL['early'], ensure_ascii=False), 'dial: no dash in the words a visitor reads')
lands = [(m['key'], ln) for m in on for ln in m.get('lands', [])]
badl = [k for k, ln in lands if len(ln.get('frame') or []) < 3 or ln.get('basis') not in ('border', 'colour', 'lettering', 'sheet') or ln.get('sure') not in ('firm', 'fair', 'loose')
        or not ln.get('km2') or (ln.get('inside') and ln['inside'] not in [o['name'] for kk, o in lands if kk == k])]
check(len(lands) >= 40 and not badl and all('lands' in m for m in on) and dl.count('class="dland-c"') == len(lands) and dl.count('<a class="dial-cell') == len(on),
      f"dial: {len(lands)} outlines, each carried onto the earth, measured, with how its limit was found, drawn on the dial and on the wall of outlines ({badl[:4]})")
ps = [s_['p'] for s_ in dj['stops']]
check(min(b - a for a, b in zip(ps, ps[1:])) > 0.02 and 'class="today"' in dl and 'Keep earlier outlines' in dl, "dial: no two stops crowd each other on the scale; today's countries lie under the sheet")
check('class="dial-door-a"' in front and 'Turn the dial' in (D/'maps/index.html').read_text() and 'Turn the dial' in (D/'labels/index.html').read_text() and 'Turn the dial' in (D/'archive/index.html').read_text(),
      'dial: doors on the front page, the map room, the many Tartarys and the vault')
# 4. em dashes
em_titles = [str(f.relative_to(D)) for f in D.rglob('*.html') if '—' in re.search(r'<title>(.*?)</title>', f.read_text(), re.S).group(1)]
check(not em_titles, f'no em dash in any page title ({len(list(D.rglob("*.html")))} pages)')
html_outputs = list(D.rglob('*.html'))
if (ROOT/'preview/index.html').exists():
    html_outputs.append(ROOT/'preview/index.html')
em_any = [str(f) for f in html_outputs if '—' in f.read_text()]
check(not em_any, 'no em dash anywhere in the generated HTML')
# links resolve
missing = set()
for f in D.rglob('index.html'):
    for h in re.findall(r'href="(\.[^"#]*)"', f.read_text()):
        path = h.split('?', 1)[0]
        target = (f.parent / path).resolve()
        if path.endswith('/'): target = target / 'index.html'
        if not target.exists(): missing.add(str(h))
check(not missing, f'all internal links resolve ({list(missing)[:5]})')
print('ALL PASS' if ok else 'SOME FAILED')
