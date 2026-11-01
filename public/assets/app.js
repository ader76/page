(function () {
  'use strict';
  var T = window.I18N, LANGS = ['fr', 'en', 'ar'];
  var cur = 'fr';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var t = function (k) { return (T[cur] && T[cur][k]) || T.fr[k] || ''; };

  function detect() {
    var q = new URLSearchParams(location.search).get('lang');
    if (LANGS.indexOf(q) > -1) return q;
    try { var s = localStorage.getItem('lang'); if (LANGS.indexOf(s) > -1) return s; } catch (e) {}
    var n = (navigator.language || 'fr').slice(0, 2).toLowerCase();
    return LANGS.indexOf(n) > -1 ? n : 'fr';
  }

  function apply(l) {
    cur = l;
    var h = document.documentElement;
    h.lang = l; h.dir = l === 'ar' ? 'rtl' : 'ltr';
    try { localStorage.setItem('lang', l); } catch (e) {}
    document.title = t('meta.title');
    var d = $('meta[name=description]'); if (d) d.content = t('meta.desc');
    var og = $('meta[property="og:title"]'); if (og) og.content = t('meta.title');
    $$('[data-i18n]').forEach(function (el) { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-aria]').forEach(function (el) { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
    $$('[data-i18n-alt]').forEach(function (el) { el.alt = t(el.dataset.i18nAlt); });
    $$('#galleryGrid .g').forEach(function (b) { b.setAttribute('aria-label', t('g.' + b.dataset.k)); $('img', b).alt = t('g.' + b.dataset.k); });
    $$('.proj').forEach(function (p) { $('img', p).alt = $('h3', p).textContent; });
    $$('.lang button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.lang === l); });
    $('#ytBtn').setAttribute('aria-label', t('vid.yt'));
    var wa = 'https://wa.me/212661247505?text=' + encodeURIComponent(t('con.wamsg'));
    $('#waBtn').href = wa; $('#waFloat').href = wa;
    syncSound();
  }

  /* language switch */
  $$('.lang button').forEach(function (b) { b.addEventListener('click', function () { apply(b.dataset.lang); }); });

  /* header + menu */
  var hdr = $('.site-header'), nav = $('#nav'), burger = $('#burger');
  function onScroll() { hdr.classList.toggle('solid', window.scrollY > 40); }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
  burger.addEventListener('click', function () {
    var o = nav.classList.toggle('open'); burger.setAttribute('aria-expanded', o);
  });
  $$('a', nav).forEach(function (a) { a.addEventListener('click', function () { nav.classList.remove('open'); burger.setAttribute('aria-expanded', 'false'); }); });

  /* video sound toggle */
  var film = $('#film'), soundBtn = $('#sound');
  function syncSound() { soundBtn.textContent = film.muted ? t('vid.sound') : t('vid.mute'); }
  soundBtn.addEventListener('click', function () {
    film.muted = !film.muted;
    if (!film.muted) { film.volume = 1; film.play().catch(function () {}); }
    syncSound();
  });
  film.addEventListener('volumechange', syncSound);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { film.play().catch(function () {}); } else { film.pause(); } });
    }, { threshold: .25 }).observe(film);
  }

  /* YouTube: load only on click */
  $('#ytBtn').addEventListener('click', function () {
    var box = $('#yt'), f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + box.dataset.id + '?autoplay=1&rel=0';
    f.title = t('vid.ytTitle');
    f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    f.allowFullscreen = true;
    box.replaceChildren(f);
    film.pause();
  });

  /* lightbox */
  var lb = $('#lb'), lbImg = $('#lbImg'), lbCap = $('#lbCap');
  var items = $$('#galleryGrid .g'), idx = 0;
  function show(i) {
    idx = (i + items.length) % items.length;
    var b = items[idx];
    lbImg.src = $('img', b).src; lbImg.alt = t('g.' + b.dataset.k); lbCap.textContent = t('g.' + b.dataset.k);
  }
  items.forEach(function (b, i) { b.addEventListener('click', function () { show(i); lb.showModal(); }); });
  $('#lbClose').addEventListener('click', function () { lb.close(); });
  $('#lbPrev').addEventListener('click', function () { show(idx - 1); });
  $('#lbNext').addEventListener('click', function () { show(idx + 1); });
  lb.addEventListener('click', function (e) { if (e.target === lb) lb.close(); });
  document.addEventListener('keydown', function (e) {
    if (!lb.open) return;
    if (e.key === 'ArrowLeft') show(idx - 1);
    if (e.key === 'ArrowRight') show(idx + 1);
  });

  /* reveal on scroll */
  var rv = $$('.section .wrap > *, .facts-grid > div');
  rv.forEach(function (el) { el.classList.add('rv'); });
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0, rootMargin: '0px 0px -4% 0px' });
    rv.forEach(function (el) { io.observe(el); });
  } else { rv.forEach(function (el) { el.classList.add('in'); }); }

  $('#year').textContent = new Date().getFullYear();
  apply(detect());
})();
