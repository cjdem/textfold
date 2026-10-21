// The page's moving parts, besides the lettering (ascii.js): the download for this computer and the copy buttons.
(() => {
  const roots = [...document.querySelectorAll('[data-root]')];

  // ── the Windows app; the Python package runs on Windows too ──
  const ua = navigator.userAgent;
  const os = /Windows NT/.test(ua) ? 'win' : null;
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
  if (os) pick(os);

  // ── copy ──
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-copy]');
    if (!b || !navigator.clipboard || !navigator.clipboard.writeText) return;
    const was = b.textContent;
    navigator.clipboard.writeText(b.dataset.copy).then(() => { b.textContent = b.dataset.done; setTimeout(() => { b.textContent = was; }, 1600); }, () => {});
  });
})();
