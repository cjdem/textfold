// The page's moving parts, besides the lettering (ascii.js): the download for this computer, the clips that play when
// they are in view, and the copy buttons. With reduced motion the clips wait for a click.
(() => {
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const roots = [...document.querySelectorAll('[data-root]')];

  // ── the download for this computer: the Windows app here, the Python package for anything else ──
  const ua = navigator.userAgent;
  const os = /Windows NT/.test(ua) ? 'win' : 'py';
  function pick(id) {
    for (const root of roots) {
      const c = JSON.parse(root.querySelector('script.cta-conf').textContent)[id];
      root.querySelectorAll('.card').forEach((card) => card.classList.toggle('is-you', card.dataset.os === id));
      if (!c) continue;
      const a = root.querySelector('[data-cta]');
      a.href = c.href;
      a.querySelector('[data-cta-t]').textContent = c.t;
      a.querySelector('[data-cta-s]').textContent = c.s;
    }
  }
  pick(os);

  // ── the clips: loaded and played when they come into view, paused when they leave ──
  const clips = [...document.querySelectorAll('.clips video')];
  if (still) clips.forEach((v) => { v.controls = true; v.preload = 'none'; v.src = v.dataset.src; });
  else if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => es.forEach(({ target: v, isIntersecting }) => {
      if (isIntersecting) { if (!v.getAttribute('src')) v.src = v.dataset.src; v.play().catch(() => {}); } else v.pause();
    }), { threshold: 0.35 });
    clips.forEach((v) => io.observe(v));
  } else clips.forEach((v) => { v.src = v.dataset.src; v.autoplay = true; });

  // ── copy ──
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-copy]');
    if (!b || !navigator.clipboard || !navigator.clipboard.writeText) return;
    const was = b.textContent;
    navigator.clipboard.writeText(b.dataset.copy).then(() => { b.textContent = b.dataset.done; setTimeout(() => { b.textContent = was; }, 1600); }, () => {});
  });
})();
