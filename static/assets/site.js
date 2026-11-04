// Gufino site script v1.0.0
(function () {
  // mobile menu
  var btn = document.querySelector('.menu-btn'), nav = document.getElementById('nav');
  if (btn && nav) btn.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  // gallery thumbnails
  document.querySelectorAll('.gallery').forEach(function (g) {
    var main = g.querySelector('.gallery-main img');
    g.querySelectorAll('.thumb').forEach(function (t) {
      t.addEventListener('click', function () {
        main.src = t.dataset.src;
        g.querySelectorAll('.thumb').forEach(function (x) { x.classList.remove('on'); });
        t.classList.add('on');
      });
    });
  });

  // color variants: swap gallery + Amazon link
  var swatches = document.querySelectorAll('.swatch');
  var buy = document.getElementById('buy');
  function pick(slug, updateUrl) {
    var found = false;
    document.querySelectorAll('.gallery').forEach(function (g) {
      var on = g.dataset.variant === slug;
      g.hidden = !on;
      if (on) { found = true; if (buy) buy.href = 'https://www.amazon.com/dp/' + g.dataset.asin; }
    });
    if (!found) return;
    swatches.forEach(function (s) {
      var on = s.dataset.variant === slug;
      s.classList.toggle('on', on);
      s.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if (updateUrl && history.replaceState) {
      var u = new URL(location.href); u.searchParams.set('color', slug); history.replaceState(null, '', u);
    }
  }
  swatches.forEach(function (s) { s.addEventListener('click', function () { pick(s.dataset.variant, true); }); });
  var c = new URLSearchParams(location.search).get('color');
  if (c && swatches.length) pick(c, false);
})();
