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
# 3c. the pills above a set of passages are buttons that filter it
w43 = (D/'w/W043/index.html').read_text()
check('data-module="pset"' in w43 and w43.count('class="pill" data-f=') >= 3 and 'data-copy' in w43, 'source page: trail pills are filter buttons, cards carry a copy button')
check(kz.count('data-th="') == kz.count('<article class="psg"'), 'every passage card says which trail it belongs to')
# 4. em dashes
em_titles = [str(f.relative_to(D)) for f in D.rglob('*.html') if '—' in re.search(r'<title>(.*?)</title>', f.read_text(), re.S).group(1)]
check(not em_titles, f'no em dash in any page title ({len(list(D.rglob("*.html")))} pages)')
em_any = [str(f) for f in list(D.rglob('*.html')) + [ROOT/'preview/index.html'] if '—' in f.read_text()]
check(not em_any, 'no em dash anywhere in the generated HTML')
# links resolve
missing = set()
for f in D.rglob('index.html'):
    for h in re.findall(r'href="(\.[^"#]*)"', f.read_text()):
        target = (f.parent / h).resolve()
        if h.endswith('/'): target = target / 'index.html'
        if not target.exists(): missing.add(str(h))
check(not missing, f'all internal links resolve ({list(missing)[:5]})')
print('ALL PASS' if ok else 'SOME FAILED')
