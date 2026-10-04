/* Run with jsdom in NODE_PATH. Verify the map note -> exact book passage contract. */
const {JSDOM, VirtualConsole} = require('jsdom');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const wait = ms => new Promise(r => setTimeout(r, ms));
async function setup(reduced = false, mapAvailable = true) {
  const errors = [], calls = {}, trackers = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push(e.message));
  const dom = new JSDOM(fs.readFileSync(root + '/docs/frontispiece/index.html', 'utf8'), {
    url: 'https://tartary.innerversepodcast.com/frontispiece/', runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc
  });
  const w = dom.window, d = w.document;
  w.matchMedia = q => ({matches: q.includes('reduced-motion') && reduced, addEventListener(){}, removeEventListener(){}});
  w.scrollTo = () => {};
  w.Element.prototype.scrollIntoView = function(options){calls.scroll = {id:this.id, options}};
  Object.defineProperty(w.performance, 'getEntriesByType', {value: () => [{type:'navigate'}]});
  if (mapAvailable) {
    w.OpenSeadragon = function(options) {
      const handlers = {};
      const viewer = {container: options.element, canvas: options.element, gestureSettingsMouse: options.gestureSettingsMouse,
        viewport: {goHome(){calls.home = (calls.home || 0) + 1}, getHomeZoom(){return 1}, getMaxZoom(){return 10}, zoomTo(){}, panTo(){}, applyConstraints(){}, zoomBy(v){calls.zoom = v}},
        addHandler(name, cb){handlers[name] = cb; if(name === 'open') w.setTimeout(cb, 0)},
        addOnceHandler(name, cb){if(name === 'tile-drawn') cb()},
        addOverlay({element}){options.element.appendChild(element)}, forceResize(){}, destroy(){}
      }; return viewer;
    };
    w.OpenSeadragon.Point = function(x,y){this.x=x;this.y=y};
    w.OpenSeadragon.Placement = {CENTER:'center'};
    w.OpenSeadragon.MouseTracker = function(o){trackers.push(o);this.destroy=()=>{}};
  }
  await wait(0);
  w.eval(fs.readFileSync(root + '/static/js/site.js', 'utf8'));
  await wait(30);
  return {dom,w,d,errors,calls,trackers};
}
(async()=>{
  let {dom,w,d,errors,calls,trackers} = await setup();
  const raw = JSON.parse(d.querySelector('[data-module="feature"] > script').textContent);
  assert.equal(d.querySelectorAll('.fpin').length, raw.map.pins.length + raw.map.sights.length);
  const before = d.querySelector('[data-slot] .psg').id;
  const mark = d.querySelector('.fpin.town');
  mark.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
  assert.equal(d.querySelector('[data-slot] .psg').id, before, 'opening a note must not silently change the book');
  const heading = d.querySelector('[data-slip] h3').textContent;
  assert.equal(d.activeElement, d.querySelector('[data-slip]'));
  d.querySelector('[data-read]').click();
  assert.equal(d.querySelector('.book-passage-title').textContent, heading, 'Read below must load the exact passage offered in the note');
  assert.equal(calls.scroll.id, 'front-passage');
  assert.equal(d.activeElement.id, 'front-passage');
  assert.equal(d.querySelector('[data-slip]').hidden, true);
  d.querySelector('[data-next]').click();
  assert.ok(d.querySelector('.book-turn-leaf'));
  assert.equal(d.querySelector('.book-turn-leaf').hasAttribute('inert'), true);
  console.log('PASS keyboard marker -> note -> exact book passage; focus, scrolling and page turn');
  d.querySelector('[data-roam]').click();
  assert.ok(d.querySelector('.scroll-workspace.is-roaming'));
  assert.ok(d.documentElement.classList.contains('roaming'));
  trackers.find(t => t.element === mark).clickHandler({quick:true});
  const fullHeading = d.querySelector('[data-slip] h3').textContent;
  d.querySelector('[data-read]').click();
  assert.equal(d.querySelector('.book-passage-title').textContent, fullHeading);
  assert.equal(d.querySelector('.scroll-workspace.is-roaming'), null);
  assert.equal(d.documentElement.classList.contains('roaming'), false);
  d.querySelector('[data-roam]').click();
  d.querySelector('.scroll-read').click();
  assert.equal(d.documentElement.classList.contains('roaming'), false);
  assert.equal(calls.scroll.id, 'front-passage');
  console.log('PASS fullscreen notes and Open the book both return to the reading volume');
  const sight = d.querySelector('.fpin.sight');
  sight.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
  assert.equal(d.querySelector('[data-slip] h3').textContent, raw.map.sights[0].t);
  assert.equal(d.querySelector('[data-read]'), null);
  if(raw.map.sights[0].l) assert.equal(d.querySelector('[data-slip] .orig').textContent, raw.map.sights[0].l);
  d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape'}));
  assert.equal(d.querySelector('[data-slip]').hidden,true);
  assert.equal(d.activeElement,sight);
  d.querySelector('[data-zoom-in]').click(); assert.equal(calls.zoom,1.6);
  d.querySelector('[data-home]').click(); assert.ok(calls.home > 0);
  assert.deepEqual(errors,[]);
  console.log('PASS original map notes/Latin, Escape focus, zoom and whole-map reset');
  dom.window.close();
  ({dom,w,d,errors} = await setup(true));
  assert.equal(d.querySelector('.is-unfurling'),null);
  d.querySelector('[data-next]').click(); assert.equal(d.querySelector('.book-turn-leaf'),null);
  assert.deepEqual(errors,[]);dom.window.close();
  ({dom,w,d,errors} = await setup(true,false));
  assert.ok(d.querySelector('[data-still] img'));
  assert.equal(d.querySelector('[data-tools]').hidden,true);
  assert.ok(d.querySelector('[data-slot] blockquote'));
  const id=d.querySelector('[data-slot] .psg').id;d.querySelector('[data-next]').click();assert.notEqual(d.querySelector('[data-slot] .psg').id,id);
  assert.deepEqual(errors,[]);dom.window.close();
  console.log('PASS reduced motion and map-unavailable reading fallback');
})().catch(e=>{console.error(e);process.exit(1)});
