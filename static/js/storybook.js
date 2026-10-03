/* Progressive enhancement: the unenhanced document remains a complete book. */
(function () {
  'use strict';
  var book = document.querySelector('[data-storybook]');
  if (!book) return;
  var chapters = Array.from(book.querySelectorAll('[data-chapter]'));
  var tabs = Array.from(book.querySelectorAll('[data-book-tab]'));
  var turns = book.querySelector('.story-page-turns');
  var previous = book.querySelector('[data-book-prev]');
  var next = book.querySelector('[data-book-next]');
  var leaf = book.querySelector('.story-turner');
  var position = document.querySelector('[data-book-position]');
  var status = document.querySelector('[data-book-status]');
  var current = 0, busy = false, animation = null, pending = null;
  var romans = ['I','II','III','IV','V','VI','VII','VIII'];
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  var narrow = window.matchMedia('(max-width: 700px)');
  var motion = document.querySelector('[data-book-motion]');
  var paused = reduced.matches, inView = true;
  var videos = chapters.map(function (chapter) { return chapter.querySelector('[data-book-video]'); });
  function syncMotion() {
    videos.forEach(function (video, i) {
      var playing = i === current && !busy && !paused && inView && !document.hidden;
      if (!playing) { video.pause(); return; }
      if (!video.getAttribute('src')) video.src = video.dataset.src;
      video.muted = true;
      var play = video.play();
      if (play) play.catch(function () { /* The poster remains when autoplay is unavailable. */ });
    });
    motion.textContent = paused ? 'Play illustrations' : 'Pause illustrations';
    motion.setAttribute('aria-pressed', String(paused));
  }
  videos.forEach(function (video) {
    video.addEventListener('playing', function () { video.classList.add('is-playing'); });
    video.addEventListener('error', function () { video.classList.remove('is-playing'); });
  });
  motion.hidden = false;
  motion.addEventListener('click', function () { paused = !paused; syncMotion(); });
  document.addEventListener('visibilitychange', syncMotion);
  if (reduced.addEventListener) reduced.addEventListener('change', function () { paused = reduced.matches; syncMotion(); });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) { inView = entries[0].isIntersecting; syncMotion(); }).observe(book);
  }
  function fromHash() { return chapters.findIndex(function (chapter) { return '#' + chapter.id === location.hash; }); }
  function remember(index, push) {
    var hash = '#' + chapters[index].id;
    if (location.hash !== hash) {
      try { history[push ? 'pushState' : 'replaceState'](null, '', hash); } catch (_) { /* A sandbox can disallow history. */ }
    }
  }
  function warm(index) {
    var chapter = chapters[index];
    if (!chapter) return;
    var img = chapter.querySelector('img');
    if (img) img.loading = 'eager';
  }
  function markChapter(index) {
    tabs.forEach(function (tab, i) {
      if (i === index) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
    });
  }
  function render(index, announce) {
    chapters.forEach(function (chapter, i) { chapter.hidden = i !== index; });
    markChapter(index);
    previous.disabled = index === 0;
    next.disabled = index === chapters.length - 1;
    position.textContent = 'Chapter ' + romans[index] + ' of ' + romans[chapters.length - 1];
    if (announce) status.textContent = 'Chapter ' + romans[index] + ': ' + chapters[index].getAttribute('aria-label');
    warm(index); warm(index + 1); warm(index - 1);
    syncMotion();
  }
  function copyPage(page) {
    var copy = page.cloneNode(true);
    copy.removeAttribute('id');
    copy.style.setProperty('--book-paper', getComputedStyle(page).getPropertyValue('--book-paper'));
    /* Freeze the exact visible frame on the turning leaf, never clone a decoder. */
    var originals = page.querySelectorAll('video');
    copy.querySelectorAll('video').forEach(function (video, i) {
      var source = originals[i];
      if (source.readyState >= 2 && source.classList.contains('is-playing')) {
        var canvas = document.createElement('canvas');
        canvas.width = source.videoWidth; canvas.height = source.videoHeight;
        try { canvas.getContext('2d').drawImage(source, 0, 0); video.replaceWith(canvas); }
        catch (_) { video.remove(); }
      } else video.remove();
    });
    copy.querySelectorAll('[id]').forEach(function (n) { n.removeAttribute('id'); });
    copy.querySelectorAll('a,button').forEach(function (n) { n.tabIndex = -1; });
    return copy;
  }
  function go(index, options) {
    options = options || {};
    if (index < 0 || index >= chapters.length) return;
    if (busy) { pending = {index:index, options:options}; return; }
    if (index === current) return;
    var old = current, forward = index > old;
    var oldChapter = chapters[old], target = chapters[index];
    var focused = document.activeElement;
    var movingFocus = oldChapter.contains(focused);
    current = index; busy = true;
    syncMotion();
    book.setAttribute('aria-busy', 'true');
    if (!options.history) remember(index, true);
    warm(index);
    function finish() {
      if (!busy) return;
      busy = false;
      book.removeAttribute('aria-busy');
      if (animation) { animation.cancel(); animation = null; }
      leaf.hidden = true;
      leaf.querySelector('.story-turner-front').replaceChildren();
      leaf.querySelector('.story-turner-back').replaceChildren();
      oldChapter.querySelectorAll('.story-page').forEach(function (page) { page.style.visibility = ''; });
      target.querySelectorAll('.story-page').forEach(function (page) { page.style.visibility = ''; });
      chapters.forEach(function (chapter) { chapter.style.position = ''; chapter.style.inset = ''; chapter.style.zIndex = ''; });
      render(index, true);
      if (movingFocus) tabs[index].focus({preventScroll:true});
      if (focused === next && next.disabled) previous.focus({preventScroll:true});
      if (focused === previous && previous.disabled) next.focus({preventScroll:true});
      if (narrow.matches && book.getBoundingClientRect().top < -100) {
        book.scrollIntoView({behavior: reduced.matches ? 'auto' : 'smooth', block:'start'});
      }
      if (pending) { var queued = pending; pending = null; go(queued.index, queued.options); }
    }
    function turn() {
    markChapter(index);
    if (reduced.matches || typeof leaf.animate !== 'function') { finish(); return; }
    if (narrow.matches) {
      render(index, false);
      animation = target.animate([{opacity:.25,transform:'translateX('+(forward ? 12 : -12)+'px)'},{opacity:1,transform:'translateX(0)'}], {duration:300,easing:'ease-out'});
    } else {
      var leftOld = oldChapter.querySelector('.story-page-art');
      var rightOld = oldChapter.querySelector('.story-page-text');
      var leftNew = target.querySelector('.story-page-art');
      var rightNew = target.querySelector('.story-page-text');
      leaf.querySelector('.story-turner-front').replaceChildren(copyPage(forward ? rightOld : rightNew));
      leaf.querySelector('.story-turner-back').replaceChildren(copyPage(forward ? leftNew : leftOld));
      leaf.inert = true;
      target.hidden = false;
      target.style.position = 'absolute'; target.style.inset = '0';
      /* Earlier chapters precede the old spread in DOM order. Give the revealed
         sheet its own layer so reverse turns cannot leave the old art on top. */
      oldChapter.style.zIndex = '0'; target.style.zIndex = '1';
      (forward ? leftNew : rightNew).style.visibility = 'hidden';
      leaf.hidden = false;
      animation = leaf.animate([
        {transform:'rotateY('+(forward ? 0 : -180)+'deg)'},
        {transform:'rotateY('+(forward ? -82 : -98)+'deg)',offset:.48},
        {transform:'rotateY('+(forward ? -180 : 0)+'deg)'}
      ], {duration:1000,easing:'cubic-bezier(.35,.05,.25,1)',fill:'forwards'});
    }
    animation.finished.then(finish).catch(finish);
    }
    var picture = target.querySelector('img');
    if (picture && !picture.complete && typeof picture.decode === 'function') {
      status.textContent = 'Opening ' + target.getAttribute('aria-label') + '…';
      picture.decode().catch(function () {}).then(turn);
    } else turn();
  }
  book.classList.add('book-ready');
  turns.hidden = false;
  current = Math.max(0, fromHash());
  render(current, false);
  previous.addEventListener('click', function () { go(current - 1); });
  next.addEventListener('click', function () { go(current + 1); });
  /* Hover/focus stay local to the index. render() warms adjacent pages and
     go() loads a selected chapter before turning its leaf. */
  tabs.forEach(function (tab, i) {
    tab.addEventListener('click', function (event) { event.preventDefault(); go(i); });
  });
  document.querySelector('[data-book-home]').addEventListener('click', function (event) { event.preventDefault(); go(0); });
  book.addEventListener('keydown', function (event) {
    if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest('input,textarea,select')) return;
    var index = current;
    if (event.key === 'ArrowRight') index++;
    else if (event.key === 'ArrowLeft') index--;
    else if (event.key === 'Home') index = 0;
    else if (event.key === 'End') index = chapters.length - 1;
    else return;
    event.preventDefault(); go(index);
  });
  var touchStart = null;
  book.addEventListener('touchstart', function (event) {
    if (event.touches.length !== 1 || event.target.closest('a,button')) { touchStart = null; return; }
    var t = event.touches[0]; touchStart = {x:t.clientX,y:t.clientY};
  }, {passive:true});
  book.addEventListener('touchend', function (event) {
    if (!touchStart || !event.changedTouches.length) return;
    var t = event.changedTouches[0], dx = t.clientX-touchStart.x, dy = t.clientY-touchStart.y;
    touchStart = null;
    if (Math.abs(dx) > 65 && Math.abs(dx) > Math.abs(dy)*1.8) go(current + (dx < 0 ? 1 : -1));
  }, {passive:true});
  book.addEventListener('touchcancel', function () { touchStart = null; }, {passive:true});
  window.addEventListener('popstate', function () { var index = fromHash(); go(index < 0 ? 0 : index, {history:true}); });
  window.addEventListener('hashchange', function () { var index = fromHash(); if (index >= 0) go(index, {history:true}); });
  /* The old homepage’s map and passage permalinks still reach the preserved feature. */
  if (/^#(front-passage|p-W\d+-\d+)$/.test(location.hash)) {
    var legacy = chapters[0].querySelector('.story-inscription');
    if (legacy) location.replace(legacy.href + location.hash);
  }
})();
