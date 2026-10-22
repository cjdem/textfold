// The app around the reader: the sidebar of papers, the landing form, settings, and generation jobs.
// On a reader page it exposes window.DRApp so the reader's language menu can generate a language.
(() => {
  'use strict';
  const I18N = window.DR_I18N;
  const bootEl = document.getElementById('boot');
  const BOOT = bootEl ? JSON.parse(bootEl.textContent) : {};
  const readerEl = document.getElementById('paper-data');
  const PAPER = readerEl ? JSON.parse(readerEl.textContent).meta : null;   // the paper open in the reader, if any
  const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { /* private window */ } } };
  const SHORT = { en: 'EN', zh: '中' };
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const h = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const api = (path, body) => fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(async (r) => { const d = await r.json(); if (!r.ok) throw new Error(d.error || r.statusText); return d; });

  // the reader's language (settings; else the browser's): the interface speaks it, papers are read and made in it, and a
  // switch of a paper's language is a switch of it (reader.js)
  const UI_KEY = 'pf-ui-lang';
  let uiLang = [store.get(UI_KEY), I18N.guess()].find((l) => l && I18N.NATIVE[l]) || 'en';
  function setUiLang(code) {
    if (!I18N.NATIVE[code]) return;
    uiLang = code;
    store.set(UI_KEY, code);
    renderSidebar();
    if (landing) renderLanding();
    if (window.__reader && window.__reader.setUi) window.__reader.setUi(code);
    document.dispatchEvent(new Event('tf-lang'));   // (what else speaks it: the app's update)
  }
  let papers = BOOT.papers || [];
  let folders = BOOT.folders || { folders: [], of: {} };   // the reader's folders, and which document is in which (folders.py)
  let sbQuery = '';        // the sidebar's search, as typed
  let editing = null;      // a folder's name being written: 'new', or the folder's id
  let dragging = null;     // the document being dragged to a folder
  let moving = null;       // the document a new folder is being named for (its menu's New folder…)
  let menu = null;         // a folder's or a document's menu, while it is open
  let stale = false;       // the list as polled while a menu was open: drawn when it closes
  const FOLDED = 'textfold.folded';   // the folders shut, kept for next time
  const SORT = 'textfold.sort';       // the list's order: 'kind' (the default), 'added' (when it came in) or 'opened' (last)
  const folded = new Set((store.get(FOLDED) || '').split(' ').filter(Boolean));
  let jobs = BOOT.jobs || [];
  let modelName = BOOT.model || '';       // the model generations use, as the settings name it
  let askName = BOOT.askName || '';       // the one questions are answered with, when it is another
  const t = () => I18N.t(uiLang);
  // an item picked in the Zotero library: on the landing it is read there; from a paper's page it goes there to be (?zotero=)
  let pickItem = (item, title) => { location.href = `/?zotero=${encodeURIComponent(item)}&t=${encodeURIComponent(title)}`; };

  // ── sidebar ──────────────────────────────────────────────────────────
  const side = document.getElementById('sidebar');
  const MARK = '<svg viewBox="0 0 20 20" aria-hidden="true"><rect class="m1" x="2" y="3" width="16" height="2.4" rx="1.2"/><rect class="m2" x="2" y="8.8" width="11" height="2.4" rx="1.2"/><rect class="m3" x="2" y="14.6" width="5" height="2.4" rx="1.2"/></svg>';
  const BOOKS = '<svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 3.5h3v13H4z"/><path d="M8.5 3.5h3v13h-3z"/><path d="M13 4.2l2.8-.7 2.6 12.3-2.8.7z"/></svg>';
  const LIST = '<svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2.5" y="3.5" width="15" height="13" rx="2.5"/><path d="M7.5 3.5v13"/></svg>';
  const FOLDER = '<svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M2.5 5.5a1.5 1.5 0 0 1 1.5-1.5h3.6l1.8 2H16a1.5 1.5 0 0 1 1.5 1.5v7A1.5 1.5 0 0 1 16 16H4a1.5 1.5 0 0 1-1.5-1.5z"/></svg>';
  const FOLDER_NEW = '<svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 5.5a1.5 1.5 0 0 1 1.5-1.5h3.6l1.8 2H16a1.5 1.5 0 0 1 1.5 1.5v7A1.5 1.5 0 0 1 16 16H4a1.5 1.5 0 0 1-1.5-1.5z"/><path d="M10 8.5v5M7.5 11h5"/></svg>';
  const CHEV = '<svg class="sb-chev" viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6l4 4-4 4"/></svg>';
  // a paper opens in the reader's language, else the one last read in, else its first
  const pick = (p) => [uiLang, store.get('dr-lang')].find((l) => l && p.langs.includes(l)) || p.langs[0] || 'en';
  const modelLabel = () => {   // and the one for questions, when it is another
    if (!askName) return modelName;
    const head = modelName.split(' · ')[0], short = askName.startsWith(`${head} · `) ? askName.slice(head.length + 3) : askName;
    return `${modelName} · ${t().sb_ask_with.replace('{m}', short)}`;
  };
  const live = (j) => j.status === 'queued' || j.status === 'running';
  function jobFor(pid) { return jobs.find((j) => j.pid === pid && live(j) && j.kind !== 'card'); }   // (a reading card's draft has its own progress in card.js)
  function pct(j) { return j.total ? Math.round((100 * j.done) / j.total) : (j.stage === 'done' ? 100 : 6); }
  // where a job is: its stage and count, or that it is stopping
  const stageOf = (j, T) => {
    const st = j.stage === 'convert' && j.file && !/\.pdf$/i.test(j.file) ? 'convert-file' : j.stage;   // a Word file, a picture
    return j.stopping ? T.stopping : `${T.stages[st] || (T.pstages || {})[st] || st}${j.total ? ` ${j.done}/${j.total}` : ''}`;
  };
  const stopBtn = (j, T) => `<button type="button" class="sb-stop" data-stop="${j.id}" title="${esc(T.stop)}" aria-label="${esc(T.stop)}"${j.stopping ? ' disabled' : ''}><i></i></button>`;
  const progress = (j, T) => `<span class="sb-prog"><i style="width:${pct(j)}%"></i></span><span class="sb-stage">${esc(stageOf(j, T))}${j.lang ? ` · ${esc(I18N.NATIVE[j.lang])}` : ''}</span>`;
  const jobName = (j, T) => j.title || j.pid;
  let lastSidebar = '';
  function renderSidebar() {
    stale = false;
    const T = t();
    const listed = new Set(papers.map((p) => p.id));
    const pending = jobs.filter((j) => !listed.has(j.pid) && live(j));
    const item = (p) => {
      const j = jobFor(p.id);
      const title = (p.titles && p.titles[uiLang]) || p.title;
      const langs = p.langs.map((l) => `<span${l === uiLang ? ' class="on"' : ''}>${SHORT[l] || l}</span>`).join('');
      const active = PAPER && PAPER.id === p.id;
      const unfinished = !j && !p.langs.length;   // stopped (or failed) before its first language: a click goes on with it
      return `<div class="sb-row" data-pid="${p.id}" data-q="${esc(hay(p))}"><a class="sb-item${active ? ' active' : ''}${unfinished ? ' unfinished' : ''}" href="${unfinished ? '#' : `/p/${p.id}?lang=${pick(p)}`}"${unfinished ? ` data-resume="${p.id}"` : ''} title="${esc(p.title)}">
        <span class="sb-t">${esc(title)}</span><span class="sb-m"><span class="sb-id">${p.id}</span><span class="sb-langs">${langs}</span></span>
        ${j ? progress(j, T) : unfinished ? `<span class="sb-stage">${esc(T.unfinished)}</span>` : ''}</a>` +
        (j ? stopBtn(j, T) : `<button type="button" class="sb-del" data-del="${p.id}" title="${esc(T.del_paper)}" aria-label="${esc(T.del_paper)}">×</button>`) + '</div>';
    };
    // papers, Wikipedia articles, GitHub READMEs and documents of one's own, each under its name when there is more than one kind
    // (a file read from a Zotero item is among the papers: Zotero says what it is)
    const kindOf = (p) => (p.zotero ? 'paper' : /^wiki-/.test(p.id) ? 'wiki' : /^gh-/.test(p.id) ? 'gh' : /^web-/.test(p.id) ? 'web' : /^(md|pdf|doc)-/.test(p.id) ? 'doc' : 'paper');
    // by kind, or by when each came in or was last opened (one never opened: when it came in), newest first, in
    // folders too; by kind, in the server's order (the latest layer first)
    const order = sortOrder(), when = (p) => (order === 'opened' ? p.opened || p.added : p.added) || p.updated;
    const docs = order === 'kind' ? papers : [...papers].sort((a, b) => when(b) - when(a));
    // the reader's folders first (one level; a document in one at most), then the documents in none
    const fs = folders.folders, loose = docs.filter((p) => !folders.of[p.id]);
    const today = new Date().setHours(0, 0, 0, 0);
    const since = (p) => { const at = when(p) * 1000; return at >= today ? 0 : Date.now() - at < 7 * 864e5 ? 1 : Date.now() - at < 30 * 864e5 ? 2 : 3; };
    const groups = (order !== 'kind' ? [[0, T.d_today], [1, T.d_week], [2, T.d_month], [3, T.d_older]].map(([k, name]) => [name, loose.filter((p) => since(p) === k)])
      : [['paper', T.papers], ['wiki', T.g_wiki], ['gh', 'GitHub'], ['web', T.g_web], ['doc', T.g_docs]].map(([k, name]) => [name, loose.filter((p) => kindOf(p) === k)]))
      .filter(([, ps]) => ps.length);
    const named = (value) => `<input class="sb-fname-in" value="${esc(value)}" placeholder="${esc(T.f_name)}" aria-label="${esc(T.f_name)}" maxlength="80" spellcheck="false">`;
    const folder = (f) => {
      const ps = docs.filter((p) => folders.of[p.id] === f.id), shut = folded.has(f.id);
      const head = editing === f.id ? named(f.name)
        : `<button type="button" class="sb-fhead" aria-expanded="${!shut}">${CHEV}${FOLDER}<span class="sb-fname">${esc(f.name)}</span><span class="sb-fn">${ps.length}</span></button>` +
          `<button type="button" class="sb-fmenu" aria-label="${esc(T.f_actions)}" title="${esc(T.f_actions)}">⋯</button>`;
      return `<div class="sb-folder${shut ? ' shut' : ''}" data-folder="${f.id}"><div class="sb-frow">${head}</div>` +
        `<div class="sb-fitems">${ps.map(item).join('') || `<div class="sb-fempty">${esc(T.f_empty)}</div>`}</div></div>`;
    };
    const kinds = groups.length > 1 || fs.length
      ? groups.map(([name, ps]) => `<div class="sb-group">${esc(name)}</div>${ps.map(item).join('')}`).join('')
      : loose.map(item).join('');
    const listed_ = papers.length || fs.length || editing
      ? (editing === 'new' ? `<div class="sb-folder"><div class="sb-frow">${named('')}</div></div>` : '') + fs.map(folder).join('') +
        (fs.length ? `<div class="sb-out">${esc(T.f_out)}</div>` : '') + `<div class="sb-loose">${kinds}</div><div class="sb-nomatch" hidden>${esc(T.sb_nomatch)}</div>`
      : '';
    const pend = (j) => `<div class="sb-row" data-q="${esc(fold(`${jobName(j, T)} ${j.pid}`))}"><div class="sb-item pending"><span class="sb-t">${esc(jobName(j, T))}</span>` +
      `<span class="sb-m"><span class="sb-id">${j.pid}</span></span>${progress(j, T)}</div>${stopBtn(j, T)}</div>`;
    const html = `
      <div class="sb-head"><a class="sb-brand" href="/">${MARK}<span>TextFold</span></a>
        <button type="button" class="sb-toggle" aria-label="${esc(T.collapse)}" title="${esc(T.collapse)}">‹</button></div>
      <div class="sb-rail">
        <a class="rail-btn rail-home" href="/" title="${esc(T.home)}">${MARK}</a>
        <button type="button" class="rail-btn rail-open" title="${esc(T.expand)}">${LIST}</button>
        <a class="rail-btn" href="/" title="${esc(T.new_paper)}">＋</a>
        <button type="button" class="rail-btn rail-settings" title="${esc(T.settings)}">⚙</button>
        ${window.TFTutorial && PAPER ? `<button type="button" class="rail-btn rail-help" title="${esc(T.tut_open)}">?</button>` : ''}
      </div>
      <div class="sb-find"><input type="search" class="sb-q" value="${esc(sbQuery)}" placeholder="${esc(T.sb_search)}" aria-label="${esc(T.sb_search)}" autocomplete="off" spellcheck="false">` +
        `<button type="button" class="sb-newf" title="${esc(T.f_new)}" aria-label="${esc(T.f_new)}">${FOLDER_NEW}</button></div>
      <div class="sb-order" role="radiogroup" aria-label="${esc(T.sort_label)}">${['kind', 'added', 'opened'].map((o) =>
        `<button type="button" role="radio" aria-checked="${o === order}" data-sort="${o}" title="${esc(T[`sort_${o}`])}">${esc(T[`by_${o}`])}</button>`).join('')}</div>
      ${groups.length > 1 || fs.length ? '' : `<div class="sb-label">${esc(groups.length ? groups[0][0] : T.papers)}</div>`}
      <nav class="sb-list">${pending.map(pend).join('')}${listed_ || (pending.length ? '' : `<div class="sb-empty">${esc(T.empty)}</div>`)}</nav>
      <div class="sb-foot"><button type="button" class="sb-zotero">${BOOKS}${esc(T.z_lib)}</button><button type="button" class="sb-settings">⚙ ${esc(T.settings)}</button>${window.TFTutorial && PAPER ? `<button type="button" class="sb-help">? ${esc(T.tut_open)}</button>` : ''}<div class="sb-model">${esc(modelLabel())}</div></div>
      <div class="sb-resize" role="separator" aria-orientation="vertical" tabindex="0" title="${esc(T.sb_resize)}" aria-label="${esc(T.sb_resize)}"></div>`;
    // polled every second while something generates: drawn again only when it changed, and where it was scrolled to
    const busy = jobs.some(live);
    if (dragging) return;   // (drawn again after the drop: the row being dragged stays where the drag began)
    if (html === lastSidebar) { side.querySelector('.rail-open').classList.toggle('busy', busy); return; }
    const scrolled = side.querySelector('.sb-list') ? side.querySelector('.sb-list').scrollTop : 0;
    const act = document.activeElement, typing = act && side.contains(act) && act.matches('.sb-q, .sb-fname-in')
      ? { sel: act.matches('.sb-q') ? '.sb-q' : '.sb-fname-in', value: act.value, a: act.selectionStart, b: act.selectionEnd } : null;
    closeMenu();
    side.innerHTML = html;
    lastSidebar = html;
    side.querySelector('.sb-list').scrollTop = scrolled;
    const field = typing && side.querySelector(typing.sel);
    if (field) { field.value = typing.value; field.focus(); try { field.setSelectionRange(typing.a, typing.b); } catch { /* (a search field) */ } }
    applySearch();
    side.querySelector('.sb-toggle').onclick = () => setCollapsed(true);
    side.querySelector('.rail-open').onclick = () => setCollapsed(false);
    side.querySelectorAll('.sb-settings, .rail-settings').forEach((b) => { b.onclick = openSettings; });
    side.querySelector('.sb-zotero').onclick = () => openLibrary();
    side.querySelectorAll('.sb-help, .rail-help').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); window.TFTutorial.open(uiLang); }; });
    side.querySelectorAll('.sb-del').forEach((b) => { b.onclick = (e) => { e.preventDefault(); e.stopPropagation(); deletePaper(b.dataset.del); }; });
    side.querySelectorAll('.sb-stop').forEach((b) => { b.onclick = (e) => { e.preventDefault(); e.stopPropagation(); stopJob(b.dataset.stop); }; });
    side.querySelectorAll('[data-resume]').forEach((a) => { a.onclick = (e) => { e.preventDefault(); resume(a.dataset.resume); }; });
    // folded to a rail (over a paper): a dot on the list button while something generates
    side.querySelector('.rail-open').classList.toggle('busy', busy);
  }
  // a job stopped from anywhere (the sidebar, the landing's card, the toast over a paper): what is written stays cached
  async function stopJob(id) {
    try {
      const j = await api('/api/jobs/stop', { id });
      jobs = [...jobs.filter((x) => x.id !== id), j];
      const cb = watchers.get(id);
      if (cb) cb(j);
    } catch { /* finished meanwhile */ }
    renderSidebar(); startPolling();
  }
  // an unfinished paper goes on in the language it was last asked for (else the reader's), in the background
  function resume(pid) {
    const last = [...jobs].reverse().find((j) => j.pid === pid && j.kind !== 'card');
    const lang = (last && last.lang) || uiLang;
    submit(pid, lang, false, () => {}).catch(() => {});
  }
  // a paper off the list, after a prompt that says what goes with it; the server moves its folder to papers/.trash
  async function deletePaper(pid) {
    const T = t(), p = papers.find((x) => x.id === pid);
    if (!p) return;
    const title = (p.titles && p.titles[uiLang]) || p.title;
    if (!confirm(T.del_confirm.replace('{title}', title).replace('{n}', p.notes || 0))) return;
    try { papers = await api('/api/papers/delete', { paper: pid }); }
    catch (err) { alert(err.message === 'busy' ? T.del_busy : err.message); return; }
    if (PAPER && PAPER.id === pid) { location.href = '/'; return; }
    renderSidebar();
  }
  function setCollapsed(c) {
    side.classList.toggle('collapsed', c);
    document.documentElement.classList.toggle('sb-open', !c);
    if (!PAPER) store.set('dr-sidebar', c ? '1' : '0');
  }
  // over a paper the sidebar folds to a rail and opens over the page; on the landing it stays open beside the form
  if (PAPER) {
    side.classList.add('collapsed');
    // (by where the click was when it happened: what it hit may be drawn anew by then, a folder shut, an order picked)
    document.addEventListener('click', (e) => { if (!side.classList.contains('collapsed') && !e.composedPath().includes(side)) setCollapsed(true); });
  } else if (store.get('dr-sidebar') === '1' || innerWidth < 720) setCollapsed(true);
  else document.documentElement.classList.add('sb-open');

  // its width, dragged at its edge (or with the arrow keys there) and kept for next time; a double-click goes back to the default
  const SBW = 'textfold.sbw';
  let sbw = +store.get(SBW) || 0;
  function setWidth(w) {
    sbw = Math.round(Math.min(Math.max(280, Math.min(640, innerWidth - 360)), Math.max(220, w)));
    document.documentElement.style.setProperty('--sb', `${sbw}px`);
  }
  if (sbw) setWidth(sbw);
  addEventListener('resize', () => { if (+store.get(SBW)) setWidth(+store.get(SBW)); });
  side.addEventListener('pointerdown', (e) => {
    const grip = e.target.closest('.sb-resize');
    if (!grip || e.button !== 0) return;
    e.preventDefault();
    grip.setPointerCapture(e.pointerId);
    document.documentElement.classList.add('sb-resizing');
    const move = (ev) => setWidth(ev.clientX);
    const up = () => {
      grip.removeEventListener('pointermove', move); grip.removeEventListener('pointerup', up); grip.removeEventListener('pointercancel', up);
      document.documentElement.classList.remove('sb-resizing');
      store.set(SBW, String(sbw));
    };
    grip.addEventListener('pointermove', move); grip.addEventListener('pointerup', up); grip.addEventListener('pointercancel', up);
  });
  side.addEventListener('dblclick', (e) => {
    if (!e.target.closest('.sb-resize')) return;
    sbw = 0; store.set(SBW, '');
    document.documentElement.style.removeProperty('--sb');
  });
  side.addEventListener('keydown', (e) => {
    if (!e.target.closest('.sb-resize') || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
    e.preventDefault();
    setWidth((sbw || side.getBoundingClientRect().width) + (e.key === 'ArrowLeft' ? -16 : 16));
    store.set(SBW, String(sbw));
  });

  // ── the library's search and folders ────────────────────────────────
  // a search narrows the list as it is typed: every word, in a title (any language's), an author or an id, accents aside
  function fold(s) { return String(s || '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase(); }
  function hay(p) { return fold([p.title, ...Object.values(p.titles || {}), ...(p.authors || []), p.id].join(' ')); }
  function applySearch() {
    const list = side.querySelector('.sb-list');
    if (!list) return;
    const words = fold(sbQuery).split(/\s+/).filter(Boolean), on = words.length > 0;
    let any = false;
    list.querySelectorAll('.sb-row').forEach((r) => { const ok = !on || words.every((w) => (r.dataset.q || '').includes(w)); r.hidden = !ok; any = any || ok; });
    list.querySelectorAll('.sb-folder[data-folder]').forEach((f) => {
      const n = f.querySelectorAll('.sb-row:not([hidden])').length;
      f.hidden = on && !n;
      f.classList.toggle('found', on && n > 0);   // (open while it shows what was found)
    });
    list.querySelectorAll('.sb-group').forEach((g) => {   // a kind's heading, while one of its own shows
      let n = g.nextElementSibling, shows = false;
      for (; n && !n.classList.contains('sb-group'); n = n.nextElementSibling) if (n.matches('.sb-row:not([hidden])')) shows = true;
      g.hidden = on && !shows;
    });
    list.classList.toggle('searching', on);
    const none = list.querySelector('.sb-nomatch');
    if (none) none.hidden = !on || any;
  }
  function openSearch() {
    if (side.classList.contains('collapsed')) setCollapsed(false);
    const q = side.querySelector('.sb-q');
    if (q) { q.focus(); q.select(); }
  }
  // Ctrl+K, or / outside a field: the search
  addEventListener('keydown', (e) => {
    const typing = e.target.closest && e.target.closest('input, textarea, select, [contenteditable]');
    const k = e.key === 'k' && (e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey;
    if (!k && !(e.key === '/' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey)) return;
    if (document.querySelector('dialog[open]')) return;
    e.preventDefault();
    openSearch();
  });
  side.addEventListener('input', (e) => {
    if (!e.target.matches('.sb-q')) return;
    sbQuery = e.target.value;
    applySearch();
  });
  side.addEventListener('keydown', (e) => {
    if (e.target.matches('.sb-q')) {
      if (e.key === 'Escape') {   // the words out, then the field
        e.preventDefault(); e.stopPropagation();
        if (e.target.value) { e.target.value = ''; sbQuery = ''; applySearch(); } else e.target.blur();
      } else if (e.key === 'Enter' || e.key === 'ArrowDown') {   // the first found: opened, or the arrows go on from it
        const first = side.querySelector('.sb-list .sb-row:not([hidden]) .sb-item');
        if (!first) return;
        e.preventDefault();
        if (e.key === 'Enter') first.click(); else first.focus();
      }
    } else if (e.target.matches('.sb-fname-in')) {
      if (e.key === 'Enter') { e.preventDefault(); saveName(e.target.value); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); editing = null; moving = null; renderSidebar(); }
    } else if (e.target.matches('.sb-list .sb-item') && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      const all = [...side.querySelectorAll('.sb-list .sb-row:not([hidden]) .sb-item')].filter((a) => a.offsetParent);
      const n = all.indexOf(e.target) + (e.key === 'ArrowDown' ? 1 : -1);
      e.preventDefault();
      if (n >= 0 && n < all.length) all[n].focus(); else if (n < 0) side.querySelector('.sb-q').focus();
    }
  });
  side.addEventListener('focusout', (e) => {   // a name left: kept when it has one
    if (e.target.matches('.sb-fname-in') && editing !== null) saveName(e.target.value);
  });
  function editName(id, pid = null) {
    editing = id; moving = pid;
    renderSidebar();
    const f = side.querySelector('.sb-fname-in');
    if (f) { f.focus(); f.select(); }
  }
  async function saveName(value) {
    const id = editing, name = value.trim(), papers = moving ? [moving] : [];
    editing = null; moving = null;
    if (name && id) {
      try { folders = await api('/api/folders', id === 'new' ? { op: 'new', name, papers } : { op: 'rename', id, name }); }
      catch (err) { alert(err.message); }
    }
    renderSidebar();
  }
  async function moveTo(pid, folder) {
    try { folders = await api('/api/folders', { op: 'move', papers: [pid], folder }); }
    catch (err) { alert(err.message); }
    renderSidebar();
  }
  async function deleteFolder(id) {
    const T = t(), f = folders.folders.find((x) => x.id === id);
    if (!f || !confirm(T.f_del_confirm.replace('{name}', f.name))) return;
    try { folders = await api('/api/folders', { op: 'delete', id }); }
    catch (err) { alert(err.message); }
    renderSidebar();
  }
  function sortOrder() { const o = store.get(SORT); return ['added', 'opened'].includes(o) ? o : 'kind'; }
  // a folder's actions, in a small menu by its ⋯ (or at a right click on its name)
  function closeMenu() {
    if (!menu) return;
    menu.remove(); menu = null;
    side.querySelectorAll('.menu-on').forEach((x) => x.classList.remove('menu-on'));
    if (stale) renderSidebar();
  }
  function folderMenu(btn, id, at) {
    const T = t();
    showMenu(btn, `<button type="button" role="menuitem" data-act="rename">${esc(T.f_rename)}</button>` +
      `<button type="button" role="menuitem" class="danger" data-act="delete">${esc(T.f_delete)}</button>`,
    (a) => { if (a.dataset.act === 'rename') editName(id); else deleteFolder(id); }, at);
  }
  // a document's, at a right click on it: into a folder (however far down the list it is), out of its own, into a new
  // one named there, or deleted
  function docMenu(btn, pid, at) {
    const T = t(), here = folders.of[pid] || null;
    const fs = folders.folders.map((f) => `<button type="button" role="menuitemradio" aria-checked="${f.id === here}" data-to="${f.id}">` +
      `${FOLDER}<span class="sb-mname">${esc(f.name)}</span></button>`).join('');
    showMenu(btn, (fs ? `<div class="sb-mlabel">${esc(T.f_move_to)}</div>${fs}` : '') +
      (here ? `<button type="button" role="menuitem" data-to="">${esc(T.f_take_out)}</button>` : '') +
      `<button type="button" role="menuitem" data-act="new">${FOLDER_NEW}<span class="sb-mname">${esc(T.f_new)}…</span></button>` +
      `<div class="sb-msep" role="separator"></div><button type="button" role="menuitem" class="danger" data-act="delete">${esc(T.del_paper)}</button>`,
    (a) => {
      if (a.dataset.act === 'new') editName('new', pid);
      else if (a.dataset.act === 'delete') deletePaper(pid);
      else if ((a.dataset.to || null) !== here) moveTo(pid, a.dataset.to || null);
    }, at);
  }
  // under its button at the sidebar's right, or where the right click was (kept inside the sidebar); a pick closes it
  function showMenu(btn, items, pick, at) {
    closeMenu();
    menu = document.createElement('div');
    menu.className = 'sb-menu';
    menu.setAttribute('role', 'menu');
    menu.innerHTML = items;
    side.append(menu);
    btn.classList.add('menu-on');   // (the row it is for stays marked while it is open)
    const r = btn.getBoundingClientRect(), s = side.getBoundingClientRect();
    if (at) {
      menu.style.left = `${Math.max(8, Math.min(at.x - s.left, s.width - menu.offsetWidth - 8))}px`;
      menu.style.top = `${Math.max(8, Math.min(at.y - s.top, s.height - menu.offsetHeight - 8))}px`;
    } else {
      menu.style.top = `${Math.min(r.bottom - s.top + 4, s.height - menu.offsetHeight - 8)}px`;
      menu.style.right = `${Math.max(8, s.right - r.right)}px`;
    }
    menu.onclick = (e) => {
      const a = e.target.closest('button');
      if (!a) return;
      closeMenu();
      pick(a);
    };
    menu.onkeydown = (e) => {
      const all = [...menu.querySelectorAll('button')], n = all.indexOf(document.activeElement);
      if (e.key === 'Escape') { e.stopPropagation(); closeMenu(); if (btn.isConnected) btn.focus(); }
      else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); all[(n + (e.key === 'ArrowDown' ? 1 : all.length - 1)) % all.length].focus(); }
    };
    (menu.querySelector('[aria-checked="true"]') || menu.querySelector('button')).focus();
  }
  document.addEventListener('click', (e) => { if (menu && !menu.contains(e.target) && !e.target.closest('.sb-fmenu')) closeMenu(); });
  side.addEventListener('contextmenu', (e) => {
    const row = e.target.closest('.sb-row[data-pid]'), head = !row && e.target.closest('.sb-folder[data-folder] > .sb-frow');
    if (!row && !(head && head.querySelector('.sb-fmenu'))) { closeMenu(); return; }   // (a name being written: the field's own)
    e.preventDefault();
    const at = e.clientX || e.clientY ? { x: e.clientX, y: e.clientY } : null;   // (none from the keyboard: by the row)
    if (row) docMenu(row.querySelector('.sb-item'), row.dataset.pid, at);
    else folderMenu(head.querySelector('.sb-fmenu'), head.parentElement.dataset.folder, at);
  });
  document.addEventListener('contextmenu', (e) => { if (menu && !side.contains(e.target)) closeMenu(); });
  side.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.matches('.sb-newf')) editName('new');
    else if (b.matches('.sb-order [data-sort]')) { store.set(SORT, b.dataset.sort); renderSidebar(); }
    else if (b.matches('.sb-fhead')) {   // shut, or open again
      const id = b.closest('.sb-folder').dataset.folder;
      if (folded.has(id)) folded.delete(id); else folded.add(id);
      store.set(FOLDED, [...folded].join(' '));
      renderSidebar();
    } else if (b.matches('.sb-fmenu')) {
      e.stopPropagation();
      if (menu) closeMenu(); else folderMenu(b, b.closest('.sb-folder').dataset.folder);
    }
  });
  // a document dragged into a folder (onto its name, or into it), or out of any (onto the rest of the list)
  const dropOn = (e) => e.target.closest && (e.target.closest('.sb-folder[data-folder]') || e.target.closest('.sb-out, .sb-loose'));
  // held near the list's top or bottom (or over the search above it), the list scrolls, the faster the nearer its edge:
  // a document far down reaches the folders at the top
  const EDGE = 48;
  let edgeStep = 0, edgeAt = 0, edgeRaf = 0;
  function edgeScroll(e) {
    const list = side.querySelector('.sb-list'), r = list.getBoundingClientRect();
    const up = r.top + EDGE - e.clientY, down = e.clientY - (r.bottom - EDGE);
    edgeStep = up > 0 ? -Math.ceil(14 * Math.min(1, up / EDGE)) : down > 0 ? Math.ceil(14 * Math.min(1, down / EDGE)) : 0;
    edgeAt = performance.now();
    if (!edgeStep || edgeRaf) return;
    const step = () => {   // (until the drag ends, leaves the sidebar or stops near the edge)
      if (!dragging || !edgeStep || performance.now() - edgeAt > 700) { edgeRaf = 0; return; }
      list.scrollTop += edgeStep;
      edgeRaf = requestAnimationFrame(step);
    };
    edgeRaf = requestAnimationFrame(step);
  }
  side.addEventListener('dragstart', (e) => {
    const row = e.target.closest && e.target.closest('.sb-row[data-pid]');
    if (!row) return;
    dragging = row.dataset.pid;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/x-textfold-paper', dragging);
    side.classList.add('dragging');
    side.classList.toggle('from-folder', !!folders.of[dragging]);
  });
  side.addEventListener('dragend', () => {
    dragging = null; edgeStep = 0;
    side.classList.remove('dragging', 'from-folder');
    side.querySelectorAll('.drop').forEach((x) => x.classList.remove('drop'));
  });
  side.addEventListener('dragover', (e) => {
    if (dragging) edgeScroll(e);
    const at = dragging && dropOn(e);
    side.querySelectorAll('.drop').forEach((x) => { if (x !== at) x.classList.remove('drop'); });
    if (!at) return;
    const to = at.matches('.sb-folder') ? at.dataset.folder : null;
    if ((folders.of[dragging] || null) === to) return;   // (where it is already)
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    at.classList.add('drop');
  });
  side.addEventListener('dragleave', (e) => {
    if (!side.contains(e.relatedTarget)) edgeStep = 0;
    const at = dropOn(e);
    if (at && !at.contains(e.relatedTarget)) at.classList.remove('drop');
  });
  side.addEventListener('drop', (e) => {
    const at = dragging && dropOn(e);
    if (!at) return;
    e.preventDefault();
    const pid = dragging, to = at.matches('.sb-folder') ? at.dataset.folder : null;
    dragging = null;
    if ((folders.of[pid] || null) !== to) moveTo(pid, to);
  });

  // ── jobs ─────────────────────────────────────────────────────────────
  const watchers = new Map();   // job id -> callback(job)
  let polling = null;
  async function poll() {
    polling = null;
    try {
      const before = new Map(jobs.map((j) => [j.id, j.status]));
      jobs = await api('/api/jobs');
      let finished = false;
      for (const j of jobs) {
        const cb = watchers.get(j.id);
        if (cb) cb(j);
        if (before.get(j.id) !== j.status && (j.status === 'done' || j.status === 'error' || j.status === 'stopped')) finished = true;
      }
      if (finished) papers = await api('/api/papers');
      if (menu) stale = true; else renderSidebar();   // (a menu stays open while a job goes on)
    } catch { /* the server restarted; try again */ }
    if (jobs.some(live) || watchers.size) polling = setTimeout(poll, 1200);
  }
  function startPolling() { if (!polling) polling = setTimeout(poll, 400); }
  function watch(job, onUpdate) {
    watchers.set(job.id, (j) => { onUpdate(j); if (!live(j)) watchers.delete(j.id); });
    jobs = [...jobs.filter((j) => j.id !== job.id), job];
    renderSidebar(); onUpdate(job); startPolling();
    return job;
  }
  async function submit(paper, lang, force, onUpdate) {
    return watch(await api('/api/generate', { paper, lang, force: !!force }), onUpdate);
  }
  // A file to the server: a PDF always through MinerU; a Word file, an e-book or a picture through its local reader or
  // MinerU.
  async function uploadFile(file, lang) {
    const r = await fetch('/api/files', { method: 'POST', body: file, headers: { 'Content-Type': file.type || 'application/octet-stream',
      'X-Name': encodeURIComponent(file.name), 'X-Lang': lang } });
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || r.statusText);
    return d;
  }
  const isPdf = (file) => /\.pdf$/i.test(file.name) || file.type === 'application/pdf';
  // What the picker and drop zone take. OFD and TIFF are absent: their only reader was the removed local engine and
  // MinerU's API does not take them.
  const ENGINE_EXT = ['pdf', 'docx', 'pptx', 'xlsx', 'epub', 'html', 'htm', 'mhtml', 'mht',
    'csv', 'tsv', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'jp2'];
  // not offered in the picker, but uploaded so the server answers: a PDF renamed .odt still opens as a PDF
  const LEGACY_EXT = ['doc', 'ppt', 'xls', 'rtf', 'odt', 'ods', 'odp'];
  const TEXT_EXT = ['md', 'markdown', 'mdown', 'txt'];
  const extOf = (name) => ((/\.([a-z0-9]+)$/i.exec(name || '') || [])[1] || '').toLowerCase();
  const forEngine = (file) => isPdf(file) || ENGINE_EXT.includes(extOf(file.name)) || LEGACY_EXT.includes(extOf(file.name));
  const isText = (file) => TEXT_EXT.includes(extOf(file.name));
  // The server names a file it reads by its bytes (pdfdoc.pid_of: sha256, first 16 hex, pdf- for a PDF): read here, so
  // a file already in the library, or sent twice in one batch, is not uploaded (the server would queue another job for
  // it). Empty when the browser has no SubtleCrypto: the upload goes on and the server's own dedupe decides.
  async function filePid(file) {
    if (!(window.crypto && window.crypto.subtle)) return '';
    try {
      const buf = await file.arrayBuffer();
      const hex = [...new Uint8Array(await window.crypto.subtle.digest('SHA-256', buf))]
        .map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
      // (the bytes decide, as on the server: take_file routes on `%PDF-`, and only an accepted file's name matters)
      return (new TextDecoder().decode(buf.slice(0, 5)) === '%PDF-' ? 'pdf-' : 'doc-') + hex;
    } catch { return ''; }
  }
  // Several files at once (dropped, or chosen together): each goes to the server in turn, one upload at a time, and its
  // job waits in the server's queues, which read the files and write their levels one after another (the sidebar shows
  // each, with its stop). Files given while others are still going up wait for them. Says what came of them: how many
  // were taken, which need a MinerU key, why any was not, and any job that fails or is stopped later. The page stays
  // where it is. step(k, file) says which file is going up; done(got) is called after the uploads and each time a job
  // ends.
  let adding = Promise.resolve();
  let queued = 0;   // (batches sent or waiting: a new one says it is waiting only when this is not 0)
  function addFiles(files, lang, step, done, again = false) {
    queued++;
    const run = adding.then(async () => {
      const MAX = 50;
      const got = { taken: 0, pdfs: 0, mineru: [], skipped: [], failed: [], stopped: [], retry: [], pids: new Set(), jobIds: new Map() };
      files = [...files];
      if (files.length > MAX) {
        for (const f of files.slice(MAX)) got.skipped.push([f.name, t().fl_too_many]);
        files = files.slice(0, MAX);
      }
      // (the library once up front: a file already in it is skipped before it is uploaded, and the list is fresh even
      // on a page opened long ago; after that the sidebar's own poll keeps it current)
      try { papers = await api('/api/papers'); } catch { /* the list it has */ }
      const watchJob = (job, name, file) => {
        if (!job || !job.id) return;
        let ended = false;
        watch(job, (j) => {   // (the sidebar has it meanwhile; this only says how it ended)
          if (live(j) || ended) return;
          ended = true;
          if (j.status === 'error') {
            if (j.error === 'needs-mineru-key') got.mineru.push(name);   // (a picture, whose conversion asked for it)
            else {
              got.failed.push([name, errText(j.error)]);
              // (readable: the file was read and only its levels failed — its paper stays, with Continue in the sidebar;
              // a conversion that left no paper is the one to choose again)
              if (file && !j.readable) got.retry.push(file);
            }
          } else if (j.status === 'stopped') got.stopped.push(name);
          done(got);
        });
      };
      for (const [k, file] of files.entries()) {
        step(k, file);
        const why = forEngine(file)
          ? (file.size > 100 * 1024 * 1024 ? (isPdf(file) ? t().pdf_large : t().file_large) : '')
          : isText(file)
            ? (file.size > 12_000_000 ? t().fl_md_large : (!modelName ? t().fl_no_model : ''))
            : t().md_only;
        if (why) { got.skipped.push([file.name, why]); continue; }
        try {
          let pid = '', job = null;
          if (forEngine(file)) {
            const known = await filePid(file);
            if (known && (got.pids.has(known) || papers.some((p) => p.id === known))) {
              got.skipped.push([file.name, t().fl_duplicate]); continue;
            }
            const seen = new Set(jobs.map((j) => j.id));   // (before this upload: a job the page already knew is not ours to stop)
            const d = await uploadFile(file, lang);
            pid = d.paper || (d.job && d.job.pid) || '';
            job = d.job || null;
            if (pid && (got.pids.has(pid) || papers.some((p) => p.id === pid))) {
              got.skipped.push([file.name, t().fl_duplicate]);
              // (the server queues a job for a paper it has; a repeated file must not leave one, so stop the one just
              // queued — a job this page already knew, another tab's or this batch's first copy, is left alone)
              if (job && job.id && !seen.has(job.id) && job.id !== got.jobIds.get(pid)) await stopJob(job.id);
              continue;
            }
            if (pid) got.pids.add(pid);
            if (isPdf(file)) got.pdfs++;
          } else {
            const r = await api('/api/import', { name: file.name, text: await file.text() });
            pid = r.paper;
            // (the import stores the same text and title under the same paper as before: no new paper. In a batch, the
            // paper being there means the file is already added, and no job is started; on a retry it may be there
            // because the import succeeded and the job did not, so the job is what is asked for.)
            if (got.pids.has(pid) || (!again && papers.some((p) => p.id === pid))) {
              got.skipped.push([file.name, t().fl_duplicate]); continue;
            }
            got.pids.add(pid);
            job = await submit(pid, lang, false, () => {});
          }
          got.taken++;
          if (pid) got.jobIds.set(pid, job && job.id);
          watchJob(job, file.name, file);
        } catch (x) {
          if (x.message === 'needs-mineru-key') { got.mineru.push(file.name); if (isPdf(file)) got.pdfs++; continue; }
          got.skipped.push([file.name, x.message === 'too-large' && !forEngine(file) ? t().fl_md_large : errText(x.message)]);
          // (the summary offers again what may pass on a second try — a busy server, a network error, a temporary
          // failure; a file the server refused for what is in it would only fail the same way)
          if (!['legacy-format', 'bad-file', 'not-pdf', 'too-large', 'not-supported', 'not-markdown', 'empty'].includes(x.message))
            got.retry.push(file);
        }
      }
      return got;
    });
    adding = run.catch(() => {}).finally(() => { queued--; });
    return run.then((got) => { done(got); return got; });
  }
  // what came of them, as lines: a heading, the lines under it, the files not taken (name: why, a few at most)
  function filesSaid(got, m, T) {
    const lines = [];
    if (got.taken) lines.push(modelName ? T.fl_queue : T.fl_read);
    if (got.mineru.length) lines.push(T.fl_mineru.replace('{n}', got.mineru.length));
    if (got.pdfs) lines.push(T.mineru_limits);
    const not = got.skipped.slice(0, 6).map(([name, why]) => `${name}: ${why}`);
    if (got.skipped.length > 6) not.push('…');
    return [T.fl_added.replace('{n}', got.taken).replace('{m}', m), lines, not];
  }
  // OpenRouter's consent page. In the browser: this tab goes there and comes back with the key. Inside the app: the
  // system browser (where the reader is signed in) goes there, and the app waits for the key, then offers the models.
  async function connectOpenRouter(back) {
    const desktop = !!window.desktop;
    const r = await api('/api/openrouter/start', { back, desktop });
    if (!desktop) { location.href = r.url; return; }
    window.desktop.openExternal(r.url);
    for (let k = 0; k < 150; k++) {   // five minutes for a person in another window
      await new Promise((res) => setTimeout(res, 2000));
      if ((await api('/api/openrouter/minted')).minted) { openSettings({ minted: true }); return; }
    }
  }
  const errText = (msg) => (msg === 'no-html' ? t().no_html : msg === 'bad-ref' ? t().bad_ref : msg === 'no-model' ? t().no_model
    : msg === 'not-markdown' || msg === 'empty' || msg === 'not-supported' ? t().md_only : msg === 'legacy-format' ? t().legacy_format
    : msg === 'no-fulltext' ? t().no_fulltext
    : msg === 'no-readme' ? t().no_readme : msg === 'github-limit' ? t().github_limit : msg === 'needs-mineru-key' ? t().mineru_needed
    : msg === 'bad-mineru-key' ? t().mineru_bad_key : msg === 'bad-mineru-url' ? t().mineru_bad_url : msg === 'busy' ? t().busy : msg === 'not-pdf' ? t().not_pdf : msg === 'too-large' ? t().pdf_large
    : msg === 'bad-file' ? t().file_bad : msg === 'no-file' ? t().no_file : msg === 'not-running' ? t().z_off : msg === 'api-off' ? t().z_api_off
    : msg === 'web-notext' ? t().web_notext : msg === 'web-pdf' ? t().web_pdf : msg === 'web-blocked' ? t().web_blocked : msg);

  // the corner where the page says what is under way, one above the other: a generation, the app's update. Each toast
  // is a small card: a sign at the left, what happens beside it, then its line, its progress or its buttons below.
  const toasts = h('div', 'toasts'); document.body.append(toasts);
  const SIGN = {
    done: '<path d="M5.5 10.5l3 3 6-6.5"/>',
    down: '<path d="M10 4.5v8.5M6.5 9.5l3.5 3.5 3.5-3.5M5.5 16h9"/>',
    restart: '<path d="M15.5 10a5.5 5.5 0 1 1-1.7-4M14.5 3.5v3h-3"/>',
    warn: '<path d="M10 6.5V11M10 13.8v.2"/><circle cx="10" cy="10" r="7"/>',
    out: '<path d="M8.5 5.5h-3v9h9v-3M11.5 4.5h4v4M15.5 4.5l-6 6"/>',
    x: '<path d="M6 6l8 8M14 6l-8 8"/>',
  };
  const svg = (k) => `<svg viewBox="0 0 20 20" aria-hidden="true">${SIGN[k]}</svg>`;
  const sign = (k, tone) => `<span class="g-ico${tone ? ` ${tone}` : ''}">${k === 'mark' ? MARK : svg(k)}</span>`;
  const shut = (label) => `<button type="button" class="g-x" aria-label="${esc(label)}" title="${esc(label)}">${svg('x')}</button>`;

  // ── the app's own updates (desktop-mygo): a newer release, downloaded and installed when the reader says ──
  if (window.desktop && window.desktop.onUpdate) {
    const D = window.desktop, box = h('div', 'gen-toast upd-toast');
    let last = null, fade = 0;
    box.hidden = true; toasts.append(box);
    const SAID = { latest: 'up_latest', 'check-failed': 'up_check_failed', dev: 'up_dev', disabled: 'up_disabled' };   // answers to a check by hand
    const show = (s) => {
      last = s;
      clearTimeout(fade);
      const T = t(), v = (x) => esc(x.replace('{v}', (s && s.version) || ''));
      box.hidden = !s || s.dismissed || !['updated', 'available', 'downloading', 'ready', 'failed', ...Object.keys(SAID)].includes(s.kind);
      if (box.hidden) return;
      const x = shut(T.close);
      const go = (label, primary) => `<span class="g-acts"><button type="button" class="g-go${primary ? ' primary' : ''}">${esc(label)}</button></span>`;
      const link = (href, label) => `<span class="g-acts"><a class="g-go" href="${esc(href)}" target="_blank" rel="noopener">${esc(label)}${svg('out')}</a></span>`;
      box.innerHTML = SAID[s.kind] ? `${sign(s.kind === 'latest' ? 'done' : 'warn', s.kind === 'latest' ? 'ok' : 'warn')}<b>${esc(T[SAID[s.kind]])}</b>${x}`
        : s.kind === 'updated' ? `${sign('done', 'ok')}<b>${v(T.up_done)}</b>${x}${link(s.notes, T.up_whatsnew)}`
        : s.kind === 'available' ? `${sign('down')}<b>${v(T.up_new)}</b>${x}${go(T.up_get, true)}`
        : s.kind === 'downloading' ? `${sign('down')}<b>${esc(T.up_getting.replace('{p}', s.percent || 0))}</b><span class="sb-prog"><i style="width:${Math.max(3, s.percent || 0)}%"></i></span>`
        : s.kind === 'ready' ? `${sign('restart')}<b>${v(T.up_ready)}</b>${x}${go(T.up_restart, true)}`
        : `${sign('warn', 'warn')}<b>${esc(T.up_failed)}</b>${x}${go(T.up_retry)}`;
      if (s.transient) fade = setTimeout(() => { box.hidden = true; }, 6000);
      const close = box.querySelector('.g-x');
      if (close) close.onclick = () => { box.hidden = true; if (!s.transient) D.dismissUpdate(); };
      const b = box.querySelector('button.g-go');
      if (b) b.onclick = () => { b.disabled = true; if (s.kind === 'ready') D.installUpdate(); else D.downloadUpdate(); };
    };
    D.onUpdate(show);
    D.updateState().then(show).catch(() => {});
    document.addEventListener('tf-lang', () => show(last));
  }

  // ── on a reader page: generate a language, or regenerate the current one ──
  if (PAPER) {
    const toast = h('div', 'gen-toast'); toast.hidden = true; toasts.append(toast);
    // (a batch's summary, kept apart from a generation's toast: the two can be up at once, and neither rewrites the other)
    const fileToast = h('div', 'gen-toast'); fileToast.hidden = true; toasts.append(fileToast);
    // a Markdown file dropped on a paper's page: stored, then generated from the landing (?start=)
    let over = 0;
    const hasFile = (e) => [...((e.dataTransfer && e.dataTransfer.types) || [])].includes('Files');
    const say = (msg, ms) => {   // (ms: a message that goes by itself, which says what went wrong)
      toast.hidden = false;
      toast.innerHTML = `${ms ? sign('warn', 'warn') : sign(msg === t().drop_md ? 'down' : 'mark')}<b>${esc(msg)}</b>`;
      if (ms) setTimeout(() => { toast.hidden = true; }, ms);
    };
    document.addEventListener('dragenter', (e) => { if (hasFile(e)) { over++; say(t().drop_md); } });
    document.addEventListener('dragleave', () => { if (--over <= 0) { over = 0; if (toast.textContent === t().drop_md) toast.hidden = true; } });
    document.addEventListener('dragover', (e) => { if (hasFile(e)) e.preventDefault(); });
    // several dropped here: they go in from this page, which stays open, and the toast says what came of them. A newer
    // batch takes the toast over, and a closed one stays closed, so a job ending later cannot raise it again.
    let batch = 0;
    async function dropFiles(files, again = false) {
      const T = t(), lang = (window.__reader && window.__reader.lang) || uiLang, mine = ++batch;
      let closed = false;
      const draw = (got) => {
        if (closed || mine !== batch) return;
        const [head, lines, not] = filesSaid(got, files.length, T);
        const acts = (got.retry.length ? `<button type="button" class="g-go primary g-retry">${esc(T.fl_retry)}</button>` : '') +
          (got.mineru.length ? `<button type="button" class="g-go${got.retry.length ? '' : ' primary'} g-mineru">${esc(T.mineru_settings)}</button>` : '');
        fileToast.hidden = false;
        fileToast.innerHTML = `${got.taken ? sign('mark') : sign('warn', 'warn')}<b>${esc(head)}</b>${shut(T.close)}` +
          lines.map((l) => `<span class="g-note">${esc(l)}</span>`).join('') +
          (not.length ? `<span class="g-note">${esc(T.fl_skipped)}<br>${not.map(esc).join('<br>')}</span>` : '') +
          (got.failed.length ? `<span class="g-note">${esc(T.fl_failed)}<br>${got.failed.slice(0, 6).map(([n, why]) => esc(`${n}: ${why}`)).join('<br>')}</span>` : '') +
          (got.stopped.length ? `<span class="g-note">${esc(T.fl_stopped)} ${esc(got.stopped.slice(0, 6).join(', '))}</span>` : '') +
          (acts ? `<span class="g-acts">${acts}</span>` : '');
        fileToast.querySelector('.g-x').onclick = () => { closed = true; fileToast.hidden = true; };
        const r = fileToast.querySelector('.g-retry');
        if (r) r.onclick = () => { closed = true; fileToast.hidden = true; dropFiles(got.retry.slice(), true); };
        const m = fileToast.querySelector('.g-mineru');
        if (m) m.onclick = () => { closed = true; fileToast.hidden = true; openSettings({ mineru: true }); };
      };
      const step = (k, file) => {
        if (closed || mine !== batch) return;
        fileToast.hidden = false;
        fileToast.innerHTML = `${sign('down')}<b>${esc(T.fl_adding.replace('{k}', k + 1).replace('{n}', files.length))}</b>` +
          `<span class="g-stage">${esc(file.name)}</span><span class="sb-prog"><i style="width:${Math.round((100 * k) / files.length) + 4}%"></i></span>`;
      };
      // (an earlier batch still uploading: say this one is waiting; otherwise say which file is about to go up, while
      // the library is read, rather than leave an earlier summary or a blank toast)
      if (queued) {
        fileToast.hidden = false;
        fileToast.innerHTML = `${sign('down')}<b>${esc(T.fl_waiting)}</b>`;
      } else step(0, files[0]);
      await addFiles(files, lang, step, draw, again);
    }
    document.addEventListener('drop', async (e) => {
      if (!e.dataTransfer.files.length) return;
      e.preventDefault(); over = 0;
      if (e.dataTransfer.files.length > 1) { dropFiles([...e.dataTransfer.files]); return; }
      const file = e.dataTransfer.files[0];
      if (forEngine(file)) {
        say(isPdf(file) ? t().pdf_reading : t().file_reading);
        try {
          const d = await uploadFile(file, uiLang);
          if (d.paper) { location.href = `/p/${d.paper}?lang=${encodeURIComponent(d.job.lang)}`; return; }   // read already
          location.href = `/?${new URLSearchParams({ t: file.name, follow: d.job.id })}`;
        } catch (x) { say(errText(x.message), 4000); }
        return;
      }
      if (!isText(file)) { say(t().md_only, 4000); return; }
      if (file.size > 12_000_000) { say(t().fl_md_large, 4000); return; }   // (the import's own limit)
      try {
        const r = await api('/api/import', { name: file.name, text: await file.text() });
        location.href = `/?start=${encodeURIComponent(r.paper)}&t=${encodeURIComponent(r.title)}`;
      } catch (x) { say(x.message === 'too-large' ? t().fl_md_large : errText(x.message), 4000); }
    });
    // a generation of this paper in the toast: its stage and a stop button; done, the page again, at the paragraph being
    // read (the reader picks it up from sessionStorage). `note` says why the page is here before its levels are.
    function toastFor(lang, note) {
      const T = t(), name = I18N.NATIVE[lang];
      toast.hidden = false;
      toast.innerHTML = `${sign('mark')}<b>${esc(T.generating)} · ${esc(name)}</b><span class="g-stage">${esc(T.stages.queued)}</span>` +
        `<span class="sb-prog"><i style="width:4%"></i></span>${note ? `<span class="g-note">${esc(note)}</span>` : ''}`;
      const closable = (head, line, bad) => {
        toast.innerHTML = `${bad ? sign('warn', 'warn') : sign('mark')}<b>${esc(head)} · ${esc(name)}</b>${shut(t().close)}${line ? `<span class="g-stage">${esc(line)}</span>` : ''}`;
        toast.querySelector('.g-x').onclick = () => { toast.hidden = true; };
      };
      const update = (j) => {
        const T2 = t();
        if (j.status === 'error') { closable(T2.failed, errText(j.error), true); return; }
        if (j.status === 'stopped') { closable(T2.stopped, ''); return; }
        // (anything may have used this toast since — a drag hint, another generation's end: draw the generation's own
        // parts again, and show it, rather than dereference a missing stage or progress bar on the next poll)
        if (!toast.querySelector('.g-stage') || !toast.querySelector('.sb-prog i')) {
          toast.hidden = false;
          toast.innerHTML = `${sign('mark')}<b>${esc(T2.generating)} · ${esc(name)}</b><span class="g-stage"></span>` +
            `<span class="sb-prog"><i style="width:4%"></i></span>`;
        }
        if (!toast.querySelector('.g-stop')) {
          toast.insertAdjacentHTML('beforeend', `<button type="button" class="g-stop">${esc(T2.stop)}</button>`);
          toast.querySelector('.g-stop').onclick = () => stopJob(j.id);
        }
        toast.querySelector('.g-stage').textContent = stageOf(j, T2);
        toast.querySelector('.g-stop').disabled = !!j.stopping;
        toast.querySelector('.sb-prog i').style.width = `${pct(j)}%`;
        if (j.status === 'done') reopen(j.lang);
      };
      update.fail = (e) => closable(t().failed, errText(e.message), true);
      return update;
    }
    function reopen(lang) {
      const r = document.getElementById('doc').getBoundingClientRect(), R = window.__reader;
      let u = null;
      for (const f of [0.3, 0.36, 0.42, 0.24]) {   // the reading line, or near it when it falls between paragraphs
        const at = document.elementFromPoint(r.left + Math.min(r.width / 2, 320), innerHeight * f);
        u = at && at.closest('.u[data-u]');
        if (u) break;
      }
      try { if (u) sessionStorage.setItem('pf-keep', JSON.stringify({ pid: PAPER.id, uid: u.dataset.u, top: u.getBoundingClientRect().top, level: R && R.level })); } catch { /* private window */ }
      if (R && lang !== R.lang && I18N.NATIVE[lang]) store.set(UI_KEY, lang);   // a language just made: the interface goes with it
      location.href = `/p/${PAPER.id}?lang=${encodeURIComponent(lang)}`;
    }
    const src = PAPER.source || {};
    if ((src.kind === 'pdf' && src.tier !== 'accurate') || (src.kind === 'file' && src.tier === 'fast')) {
      const acc = h('button', 'cmpbtn accbtn');
      acc.type = 'button';
      acc.textContent = t().convert_acc;
      acc.title = `${t().conv_fast_note} ${t().tier_accurate}`;
      const bar = document.querySelector('.topbar .cmpbtn') || document.querySelector('.topbar .langpick');
      if (bar) bar.before(acc);
      acc.onclick = async () => {
        const T = t();
        if (!confirm(`${T.convert_acc}? ${T.tier_accurate}.`)) return;
        acc.disabled = true;
        const lang = (window.__reader && window.__reader.lang) || 'en', update = toastFor(lang);
        try { watch(await api('/api/convert', { paper: PAPER.id, tier: 'accurate', lang }), update); }
        catch (x) { update.fail(x); acc.disabled = false; }
      };
    }
    // A translation stored with paragraphs it has none for (PAPER.gaps: a call that failed, a paragraph the model left
    // out; or made before TextFold asked for them again): they are asked for as it is opened, with the model in use, the
    // rest kept. Once a visit for as many as there are, so one that will not translate is not asked for at every
    // opening; the language menu asks again (asked).
    function fillGaps(lang, asked) {
      const n = (PAPER.gaps || {})[lang], key = `tf-gaps:${PAPER.id}:${lang}`;
      if (!n || jobFor(PAPER.id) || !modelName) return;
      let tried = null;
      try { tried = sessionStorage.getItem(key); } catch { /* private window */ }
      if (!asked && tried === String(n)) return;
      try { sessionStorage.setItem(key, String(n)); } catch { /* private window */ }
      const update = toastFor(lang, t().gaps_filling.replace('{n}', n));
      submit(PAPER.id, lang, false, update).catch(update.fail);
    }
    window.DRApp = {
      onLang(lang, ui) {   // (ui: the reader's language, which a switch of the paper's moves)
        if (ui && ui !== uiLang && I18N.NATIVE[ui]) uiLang = ui;
        renderSidebar();
        fillGaps(lang);
      },
      generate(lang, force) {
        const T = t(), name = I18N.NATIVE[lang];
        if (force && !confirm(`${T.regen} · ${name}?`)) return;
        const update = toastFor(lang);
        submit(PAPER.id, lang, force, update).catch(update.fail);
      },
      fill(lang) {
        if (!modelName) { say(t().no_model); return; }
        fillGaps(lang, true);
      },
    };
    const modelsIn = api('/api/models').then((d) => { modelName = d.selectedName || ''; askName = d.askName || ''; renderSidebar(); }).catch(() => {});
    api('/api/papers').then((p) => { papers = p; renderSidebar(); }).catch(() => {});
    api('/api/folders').then((f) => { folders = f; renderSidebar(); }).catch(() => {});
    api('/api/jobs').then((j) => {
      jobs = j;
      renderSidebar();
      // a generation of this paper under way (the landing opens a paper as soon as it can be read): followed here
      const mine = jobFor(PAPER.id);
      if (mine) {
        const update = toastFor(mine.lang, t().read_first);
        watchers.set(mine.id, (x) => { update(x); if (!live(x)) watchers.delete(x.id); });
        update(mine);
      } else modelsIn.then(() => fillGaps((window.__reader && window.__reader.lang) || new URLSearchParams(location.search).get('lang') || 'en'));
      if (j.some(live)) startPolling();
    }).catch(() => {});
  }

  // ── the landing ──────────────────────────────────────────────────────
  const landing = document.getElementById('landing');
  function renderLanding() {
    const T = t();
    document.documentElement.lang = I18N.htmlLang(uiLang);
    document.getElementById('h-tagline').textContent = T.hero;
    document.getElementById('ref').placeholder = T.placeholder;
    document.getElementById('ref').setAttribute('aria-label', T.placeholder);
    document.getElementById('l-lang').textContent = T.read_in;
    document.getElementById('lang').value = uiLang;
    const ui = document.getElementById('ui-lang');
    ui.value = uiLang;
    document.getElementById('ui-lang-box').title = T.language;
    ui.setAttribute('aria-label', T.language);
    document.getElementById('go-t').textContent = T.generate;
    document.getElementById('sources').textContent = T.sources;
    document.getElementById('sources').title = T.sources_tip;
    document.getElementById('dropzone-t').textContent = T.drop_zone;
    document.getElementById('dropzone-k').textContent = T.drop_types;
    document.getElementById('zlib-open-t').textContent = T.z_lib;
    document.getElementById('ui-help-t').textContent = T.tut_open;
    document.getElementById('ui-help').title = T.tut_open;
    document.getElementById('open-settings').textContent = T.settings;
    document.getElementById('model-label').textContent = modelLabel();
    renderConnect();
  }
  // No model yet: the ways in, on the landing itself. OpenRouter's one-click
  // authorisation (free models), or the settings.
  function renderConnect() {
    const box = document.getElementById('connect');
    if (!box) return;
    box.hidden = !!modelName;
    if (box.hidden) return;
    const T = t();
    box.innerHTML = `<div class="cn-t">${esc(T.cn_title)}</div><p>${esc(T.cn_sub)}</p><div class="cn-ways">` +
      `<button type="button" class="primary cn-or">${esc(T.cn_or)}</button>` +
      `</div><button type="button" class="linkbtn cn-more">${esc(T.cn_more)}</button>`;
    box.querySelector('.cn-or').onclick = async (e) => { e.target.disabled = true; await connectOpenRouter('/'); e.target.disabled = false; };
    box.querySelector('.cn-more').onclick = () => openSettings({ add: true });
  }
  if (landing) {
    const sel = document.getElementById('lang');
    for (const code of I18N.CODES) sel.append(Object.assign(h('option'), { value: code, textContent: I18N.NATIVE[code] }));
    sel.value = uiLang;
    // the language, top right, and the one to read in, beside the bar: one language, so either moves both
    const ui = document.getElementById('ui-lang');
    for (const code of I18N.CODES) ui.append(Object.assign(h('option'), { value: code, textContent: I18N.NATIVE[code] }));
    ui.value = uiLang;
    sel.onchange = () => setUiLang(sel.value);
    ui.onchange = () => setUiLang(ui.value);
    document.getElementById('open-settings').onclick = openSettings;
    const help = document.getElementById('ui-help');
    if (window.TFTutorial) help.onclick = () => window.TFTutorial.open(uiLang); else help.hidden = true;
    const form = document.getElementById('newform'), err = document.getElementById('err'), card = document.getElementById('jobcard');
    const fail = (msg) => { err.textContent = msg; err.hidden = false; };
    // a paper (an arXiv link, or a document just opened) into the job card, then into the reader
    let latest = null;   // the paper the card shows: started last. One started before keeps going in the sidebar.
    function onCard(label, mine, note) {
      const cb = (j) => {
        if (latest !== mine) return;
        const T = t(), name = esc(label || jobName(j, T)), in_ = j.lang ? ` · ${esc(I18N.NATIVE[j.lang])}` : '';
        if (j.status === 'moved' && j.next) { watchers.set(j.next, cb); startPolling(); return; }   // (an arXiv paper without HTML: its PDF converts)
        if (j.status === 'error') { card.innerHTML = `<div class="jc-t">${esc(T.failed)} · ${name}</div><div class="jc-e">${esc(errText(j.error))}</div>`; return; }
        if (j.status === 'stopped') {
          card.innerHTML = `<div class="jc-head"><div class="jc-t">${name}${in_}</div>${j.kind === 'generate' ? `<button type="button" class="jc-go">${esc(T.resume)}</button>` : ''}</div>
            <div class="jc-s">${esc(T.stopped)}</div>`;
          if (j.kind === 'generate') card.querySelector('.jc-go').onclick = () => start(j.pid, label || j.title, j.lang);
          return;
        }
        card.innerHTML = `<div class="jc-head"><div class="jc-t">${name}${in_}</div>
            <button type="button" class="jc-stop"${j.stopping ? ' disabled' : ''}>${esc(T.stop)}</button></div>
          <div class="jc-s">${esc(stageOf(j, T))}</div>
          <span class="sb-prog"><i style="width:${pct(j)}%"></i></span>${note ? `<div class="jc-n">${esc(note)}</div>` : ''}`;
        card.querySelector('.jc-stop').onclick = () => stopJob(j.id);
        // readable (parsed, or converted): the paper opens in its own words now, and its levels come in while it is read
        if (j.pid && (j.status === 'done' || (j.readable && j.status === 'running'))) location.href = `/p/${j.pid}?lang=${encodeURIComponent(j.lang || sel.value)}`;
      };
      return cb;
    }
    async function start(ref, label, langOf) {
      const lang = langOf || sel.value, mine = {};
      latest = mine;
      card.hidden = false;
      try {
        await submit(ref, lang, false, onCard(label, mine));
      } catch (x) { card.hidden = true; fail(errText(x.message)); }
    }
    // MinerU has no local fallback: a PDF, picture or other MinerU-only file needs a key before it can be read.
    function mineruCard(name) {
      const T = t();
      card.hidden = false;
      card.innerHTML = `<div class="jc-t">${esc(T.mineru_needed)}</div><div class="jc-s">${esc(name)}</div><p class="jc-why">${esc(T.mineru_needed_why)}</p>
        <div class="jc-acts"><button type="button" class="primary jc-mineru">${esc(T.mineru_settings)}</button><button type="button" class="jc-later">${esc(T.not_now)}</button></div>`;
      card.querySelector('.jc-later').onclick = () => { card.hidden = true; };
      card.querySelector('.jc-mineru').onclick = () => { card.hidden = true; openSettings({ mineru: true }); };
    }
    async function openUpload(file) {
      if (file.size > 100 * 1024 * 1024) { fail(isPdf(file) ? t().pdf_large : t().file_large); return; }
      const lang = sel.value, mine = {};
      latest = mine;
      card.hidden = false;
      card.innerHTML = `<div class="jc-t">${esc(file.name)}</div><div class="jc-s">${esc(isPdf(file) ? t().pdf_reading : t().file_reading)}</div><span class="sb-prog"><i style="width:4%"></i></span>`;
      try {
        const d = await uploadFile(file, lang);
        if (latest !== mine) return;
        took(d, file.name, mine, lang);
      } catch (x) {
        if (x.message === 'needs-mineru-key') mineruCard(file.name);
        else { card.hidden = true; fail(errText(x.message)); }
      }
    }
    // the server's reply to a file: the document read already, or the job that reads it
    function took(d, name, mine, lang) {
      if (d.paper) { location.href = `/p/${d.paper}?lang=${encodeURIComponent(lang)}`; return; }   // read already
      watch(d.job, onCard(name, mine, ''));
    }
    // an item of the Zotero library (zotero.py): its file, read as one dropped here is; else its paper online,
    // generated as a link is
    async function readItem(item, title) {
      err.hidden = true;
      const lang = sel.value, mine = {};
      latest = mine;
      card.hidden = false;
      card.innerHTML = `<div class="jc-t">${esc(title)}</div><div class="jc-s">${esc(t().file_reading)}</div><span class="sb-prog"><i style="width:4%"></i></span>`;
      try {
        const d = await api('/api/zotero/read', { item, lang });
        if (latest !== mine) return;
        if (d.ref) {
          if (!modelName) { card.hidden = true; fail(t().no_model); return; }
          start(d.ref, title);
          return;
        }
        took(d, d.name || title, mine, lang);
      } catch (x) {
        if (x.message === 'needs-mineru-key') mineruCard(title);
        else { card.hidden = true; fail(errText(x.message)); }
      }
    }
    pickItem = readItem;
    document.getElementById('zlib-open').onclick = () => openLibrary();
    form.onsubmit = async (e) => {
      e.preventDefault();
      err.hidden = true;
      const ref = document.getElementById('ref').value.trim();
      if (!/\d{4}\.\d{4,5}|PMC\d{4,}|PPR\d{4,}|10\.\d{4,9}\/\S|^https?:\/\/[^\s/]+\.[^\s/]+/i.test(ref)) { fail(t().bad_ref); return; }   // an arXiv or Europe PMC id, a DOI, any web page's link
      if (!modelName) { fail(t().no_model); return; }   // connect a model first (the card below)
      start(ref);
    };
    // a file, from the drop zone or dropped anywhere on the page: a PDF/picture goes through MinerU, a common Office or
    // e-book file through TextFold's own reader; a Markdown or text file is stored, then generated
    async function openFile(file) {
      err.hidden = true;
      if (!file) return;
      if (forEngine(file)) { openUpload(file); return; }
      if (!isText(file)) { fail(t().md_only); return; }
      if (file.size > 12_000_000) { fail(t().fl_md_large); return; }   // (the import's own limit)
      if (!modelName) { fail(t().no_model); return; }
      try {
        const r = await api('/api/import', { name: file.name, text: await file.text() });
        start(r.paper, r.title);
      } catch (x) { fail(x.message === 'too-large' ? t().fl_md_large : errText(x.message)); }
    }
    // several at once: they go in one after another, and the card says what came of them; the page stays here, the
    // sidebar showing each (one file opens as before)
    function openFiles(list) {
      const files = [...list];
      if (!files.length) return;
      if (files.length < 2) { openFile(files[0]); return; }
      beginBatch(files, false);
    }
    // a retry stays a batch even for one file: the summary (and its Retry, if it fails again) is where it came from
    async function beginBatch(files, again) {
      err.hidden = true;
      const T = t(), mine = {};
      latest = mine;
      card.hidden = false;
      const step = (k, file) => {
        if (latest !== mine) return;
        card.innerHTML = `<div class="jc-t">${esc(T.fl_adding.replace('{k}', k + 1).replace('{n}', files.length))}</div><div class="jc-s">${esc(file.name)}</div>` +
          `<span class="sb-prog"><i style="width:${Math.round((100 * k) / files.length) + 4}%"></i></span>`;
      };
      // (an earlier batch still uploading: say this one is waiting; otherwise say which file is about to go up, while
      // the library is read, rather than leave an earlier summary up)
      if (queued) card.innerHTML = `<div class="jc-t">${esc(T.fl_waiting)}</div>`;
      else step(0, files[0]);
      const draw = (got) => {
        if (latest !== mine) return;
        const [head, lines, not] = filesSaid(got, files.length, T);
        const acts = (got.retry.length ? `<button type="button" class="primary jc-retry">${esc(T.fl_retry)}</button>` : '') +
          (got.mineru.length ? `<button type="button" class="${got.retry.length ? '' : 'primary '}jc-mineru">${esc(T.mineru_settings)}</button>` : '');
        card.innerHTML = `<div class="jc-head"><div class="jc-t">${esc(head)}</div><button type="button" class="jc-stop jc-close">${esc(T.close)}</button></div>` +
          lines.map((l) => `<div class="jc-s">${esc(l)}</div>`).join('') +
          (not.length ? `<div class="jc-n">${esc(T.fl_skipped)}</div>${not.map((l) => `<div class="jc-e">${esc(l)}</div>`).join('')}` : '') +
          (got.failed.length ? `<div class="jc-n">${esc(T.fl_failed)}</div>${got.failed.slice(0, 6).map(([n, why]) => `<div class="jc-e">${esc(n)}: ${esc(why)}</div>`).join('')}` : '') +
          (got.stopped.length ? `<div class="jc-n">${esc(T.fl_stopped)} ${esc(got.stopped.slice(0, 6).join(', '))}</div>` : '') +
          (acts ? `<div class="jc-acts">${acts}</div>` : '');
        card.querySelector('.jc-close').onclick = () => { card.hidden = true; };
        const r = card.querySelector('.jc-retry');
        if (r) r.onclick = () => { card.hidden = true; beginBatch(got.retry.slice(), true); };
        const m = card.querySelector('.jc-mineru');
        if (m) m.onclick = () => { card.hidden = true; openSettings({ mineru: true }); };
      };
      await addFiles(files, sel.value, step, draw, again);
    }
    const fileIn = document.getElementById('file'), zone = document.getElementById('dropzone');
    fileIn.multiple = true;
    fileIn.accept = [...ENGINE_EXT, ...TEXT_EXT].map((x) => `.${x}`).join(',');
    zone.title = [...ENGINE_EXT, ...TEXT_EXT].filter((x) => !['htm', 'mht', 'jpeg', 'tif', 'markdown', 'mdown'].includes(x)).map((x) => `.${x}`).join(' ');
    zone.onclick = () => fileIn.click();
    fileIn.onchange = () => { openFiles(fileIn.files); fileIn.value = ''; };   // (openFiles copies the list first)
    let depth = 0;   // dragenter and dragleave fire for every child the file passes over
    const dropping = (on) => { zone.classList.toggle('dragging', on); document.getElementById('dropzone-t').textContent = on ? t().drop_md : t().drop_zone; };
    document.addEventListener('dragenter', (e) => { if ([...e.dataTransfer.types].includes('Files')) { depth++; dropping(true); } });
    document.addEventListener('dragleave', () => { if (--depth <= 0) { depth = 0; dropping(false); } });
    document.addEventListener('dragover', (e) => { if ([...e.dataTransfer.types].includes('Files')) e.preventDefault(); });
    document.addEventListener('drop', (e) => {
      if (!e.dataTransfer.files.length) return;
      e.preventDefault(); depth = 0; dropping(false);
      openFiles(e.dataTransfer.files);
    });
    renderLanding();
    // the landing is built before a local provider's background probe answers: look again for a moment, so a model
    // found a second later is shown without a reload
    if (!modelName) {
      let tries = 0;
      const discover = async () => {
        const d = await api('/api/models').catch(() => null);
        if (d && d.models.length) {
          modelName = d.selectedName || ''; askName = d.askName || '';
          renderSidebar(); renderLanding();
        } else if (++tries < 6) setTimeout(discover, 1500);
      };
      setTimeout(discover, 600);
    }
    // a first visit: how TextFold works, once (not when arriving mid-way: a file to generate, or back from OpenRouter)
    if (window.TFTutorial && !window.TFTutorial.seen() && !/[?&]start=/.test(location.search) && !location.hash.startsWith('#or-'))
      setTimeout(() => { if (!document.querySelector('dialog[open]')) window.TFTutorial.open(uiLang); }, 350);
    // a file dropped on a paper's page comes here, stored already: generate it (?start=<id>&t=<title>)
    const started = new URLSearchParams(location.search);
    if (started.get('start')) {
      history.replaceState(null, '', '/');
      if (modelName) start(started.get('start'), started.get('t')); else fail(t().no_model);
    }
    if (started.get('zotero')) { history.replaceState(null, '', '/'); readItem(started.get('zotero'), started.get('t') || ''); }
    // a PDF dropped on a paper's page, uploaded there: its job followed here
    if (started.get('follow')) {
      history.replaceState(null, '', '/');
      const job = jobs.find((j) => j.id === started.get('follow')), mine = {};
      latest = mine;
      card.hidden = false;
      const ref = started.get('ref');
      if (job) watch(job, onCard(ref ? null : started.get('t'), mine, ref ? t().pdf_online.replace('{ref}', ref) : ''));
    }
    if (jobs.some(live)) startPolling();
  }

  // ── a Zotero library (zotero.py): its collections as Zotero shows them, each item read in a click ──
  async function openLibrary() {
    const dlg = h('dialog', 'settings zlib'); document.body.append(dlg);
    const COL = 'pf-zotero-col';
    let st = { ok: true, libraries: [] }, cols = [], items = null, col = store.get(COL) || '', query = '', timer = null, seq = 0;
    const opened = new Set();
    const q = (sel) => dlg.querySelector(sel);
    const lib = () => st.library || '';
    async function load() {
      st = await api('/api/zotero').catch((x) => ({ ok: false, error: x.message, libraries: [] }));
      cols = [];
      if (st.ok && lib()) {
        cols = await api(`/api/zotero/collections?lib=${encodeURIComponent(lib())}`).catch(() => []);
        if (col && !cols.some((c) => c.key === col)) col = '';
        // the chosen collection's parents open, so it shows in the tree
        for (let c = cols.find((x) => x.key === col); c && c.parent; c = cols.find((x) => x.key === c.parent)) opened.add(c.parent);
      }
      render(); list();
    }
    async function list() {
      items = null; renderItems();
      if (!st.ok || !lib()) return;
      const mine = ++seq;
      const qs = new URLSearchParams({ lib: lib(), collection: query ? '' : col, q: query });
      const got = await api(`/api/zotero/items?${qs}`).catch(() => []);
      if (mine === seq) { items = got; renderItems(); }
    }
    function tree(parent) {
      return cols.filter((c) => c.parent === parent).map((c) => {
        const kids = cols.some((x) => x.parent === c.key), open = opened.has(c.key);
        return `<li><div class="zl-col${c.key === col && !query ? ' on' : ''}" data-col="${esc(c.key)}">` +
          `<button type="button" class="zl-tw" data-tw="${esc(c.key)}"${kids ? '' : ' disabled'}>${kids ? (open ? '▾' : '▸') : ''}</button>` +
          `<span>${esc(c.name)}</span></div>${kids && open ? `<ul>${tree(c.key)}</ul>` : ''}</li>`;
      }).join('');
    }
    const treeHtml = () => `<div class="zl-col${!col && !query ? ' on' : ''}" data-col=""><span>${esc(t().z_all)}</span></div><ul>${tree('')}</ul>`;
    function render() {
      const T = t();
      const libs = (st.libraries || []).map((l) => `<option value="${esc(l.id)}"${l.id === lib() ? ' selected' : ''}>${esc(l.name || T.z_mine)}</option>`).join('');
      dlg.innerHTML = `<div class="st zlb"><div class="zl-head"><h2>${esc(T.z_lib)}</h2>
          ${st.ok && libs ? `<select class="zl-lib" aria-label="${esc(T.z_lib)}">${libs}</select>` : ''}
          <button type="button" class="zl-x" aria-label="${esc(T.st_close)}">×</button></div>
        ${!st.ok ? `<p class="st-note warn">${esc(st.error === 'api-off' ? T.z_api_off : T.z_off)}</p>` : ''}
        ${st.ok && lib() ? `<input class="st-search zl-q" type="search" placeholder="${esc(T.z_search)}" value="${esc(query)}">
          <div class="zl-body"><nav class="zl-tree">${treeHtml()}</nav><div class="zl-items"></div></div>` : ''}</div>`;
      q('.zl-x').onclick = () => dlg.close();
      const ls = q('.zl-lib');
      if (ls) ls.onchange = async () => { st = await api('/api/zotero/library', { library: ls.value }).catch(() => st); col = ''; store.set(COL, ''); load(); };
      const box = q('.zl-q');
      if (box) box.oninput = () => { clearTimeout(timer); timer = setTimeout(() => { query = box.value.trim(); renderTree(); list(); }, 300); };
      wireTree();
      renderItems();
    }
    function renderTree() { const n = q('.zl-tree'); if (!n) return; n.innerHTML = treeHtml(); wireTree(); }
    function wireTree() {
      dlg.querySelectorAll('.zl-col').forEach((n) => { n.onclick = () => {
        col = n.dataset.col; store.set(COL, col); query = ''; if (q('.zl-q')) q('.zl-q').value = ''; renderTree(); list();
      }; });
      dlg.querySelectorAll('.zl-tw').forEach((b) => { b.onclick = (e) => {
        e.stopPropagation(); if (opened.has(b.dataset.tw)) opened.delete(b.dataset.tw); else opened.add(b.dataset.tw); renderTree();
      }; });
    }
    function renderItems() {
      const box = q('.zl-items');
      if (!box) return;
      const T = t();
      if (items === null) { box.innerHTML = '<p class="st-note">…</p>'; return; }
      if (!items.length) { box.innerHTML = `<p class="st-note">${esc(T.z_none)}</p>`; return; }
      box.innerHTML = items.map((it, i) => {
        const who = it.authors.length > 2 ? `${it.authors[0]} et al.` : it.authors.join(', ');
        const p = it.paper && papers.find((x) => x.id === it.paper);
        const act = it.paper ? `<a class="zl-go" href="/p/${esc(it.paper)}${p ? `?lang=${pick(p)}` : ''}">${esc(T.z_open)}</a>`
          : it.arxiv || it.file || it.doi || it.children ? `<button type="button" class="zl-go primary" data-i="${i}">${esc(T.z_read)}</button>`
          : `<span class="zl-no">${esc(T.z_nofile)}</span>`;
        const tags = [it.arxiv ? 'arXiv' : '', it.file].filter(Boolean).map((x) => `<em>${esc(x)}</em>`).join('');
        return `<div class="zl-item"><div class="zl-tx"><div class="zl-t">${esc(it.title)}</div>` +
          `<div class="zl-m">${esc([who, it.year].filter(Boolean).join(' · '))}${it.citekey ? ` <code>${esc(it.citekey)}</code>` : ''}${tags}</div></div>${act}</div>`;
      }).join('');
      box.querySelectorAll('button.zl-go').forEach((b) => { b.onclick = () => {
        const it = items[+b.dataset.i];
        dlg.close();
        pickItem(`${lib()}/${it.key}`, it.title);
      }; });
    }
    dlg.addEventListener('close', () => dlg.remove());
    dlg.innerHTML = '<div class="st zlb"><p class="st-note">…</p></div>';
    dlg.showModal();
    load();
  }

  // ── settings: the model and its API providers ──
  async function openSettings(opts) {
    let data = await api('/api/models');
    const app = window.desktop && window.desktop.checkForUpdates ? await window.desktop.version() : null;   // in the app: its version
    let form = null;          // the provider being added or edited: {key?, preset, name, base, api_key, found, picked}
    let advancedOpen = !!(opts && (opts.add || opts.minted || opts.mineru));   // (provider forms and MinerU live in Advanced)
    const tests = {};         // the last connection test of each model: the levels' (gen), the questions' (ask)
    const dlg = h('dialog', 'settings prefs'); document.body.append(dlg);
    const T = () => t();
    const host = (u) => { try { return new URL(u).host; } catch { return u; } };
    const groupName = (g) => (data.providers.find((p) => p.key === g) || {}).name || g;
    const modelOptions = (chosen) => {
      const groups = [];
      for (const m of data.models) {
        let g = groups.find((x) => x.key === m.group);
        if (!g) groups.push(g = { key: m.group, items: [] });
        g.items.push(m);
      }
      return groups.map((g) => `<optgroup label="${esc(groupName(g.key))}">${g.items.map((m) =>
        `<option value="${esc(m.id)}"${m.id === chosen ? ' selected' : ''}>${esc(m.name)}</option>`).join('')}</optgroup>`).join('');
    };
    const testBtn = (k) => {
      const t = T(), r = tests[k];
      return `<button type="button" class="st-btn st-testbtn${r ? (r.ok ? ' ok' : ' bad') : ''}" data-test="${k}">${r ? (r.ok ? `✓ ${r.seconds} s` : `✕ ${esc(t.test_bad)}`) : esc(t.test)}</button>`;
    };

    function connectionSection() {
      const t = T(), cur = data.models.find((m) => m.id === data.selected);
      const shown = cur ? (data.selectedName || cur.name) : '', group = cur ? groupName(cur.group) : '';
      const name = !cur ? t.st_none : shown.toLowerCase().includes(group.toLowerCase()) ? shown : `${group} · ${shown}`;
      const or = form && form.minted ? '' : `<button type="button" class="st-btn st-or">${esc(t.st_or)}</button>`;   // (a key is waiting for its models)
      return `<div class="st-list">
        <div class="st-item"><i class="st-dot${cur ? '' : ' off'}"></i><div class="st-main"><b>${esc(t.st_current)}</b>
          <span class="st-meta">${esc(name)}</span></div>${or}</div>
      </div>`;
    }

    function modelSection() {
      const t = T();
      if (!data.models.length) return '';
      const failed = tests.gen && !tests.gen.ok ? `<p class="st-models-err">${esc(t.st_gen)}: ${esc(tests.gen.error || '')}</p>` : '';
      return `<div class="st-models">` +
        `<label for="st-gen">${esc(t.st_gen)}</label><select name="model" id="st-gen" class="st-model wide">${modelOptions(data.selected)}</select>${testBtn('gen')}` +
        `</div>${failed}`;
    }

    function askSection() {
      const t = T();
      if (!data.models.length) return '';
      // questions: the levels' model unless another is chosen; its reasoning, where it has levels of it (Auto: the default)
      const asked = data.models.find((m) => m.id === (data.askModel || data.selected)), efforts = (asked && asked.efforts) || [];
      const effort = efforts.length ? `<select class="st-effort" aria-label="${esc(t.st_effort)}" title="${esc(t.st_effort)}"><option value="">${esc(t.eff_auto)}</option>${efforts.map((e) =>
        `<option value="${esc(e)}"${e === data.askEffort ? ' selected' : ''}>${esc(t[`eff_${e}`] || e)}</option>`).join('')}</select>` : '';
      const failed = tests.ask && !tests.ask.ok ? `<p class="st-models-err">${esc(t.st_ask)}: ${esc(tests.ask.error || '')}</p>` : '';
      return `<div class="st-models">` +
        `<label for="st-ask">${esc(t.st_ask)}</label><select id="st-ask" class="st-askmodel${effort ? '' : ' wide'}"><option value="">${esc(t.st_same)}</option>${modelOptions(data.askModel)}</select>${effort}${testBtn('ask')}` +
        `</div>${failed}`;
    }

    function providerSection() {
      const t = T();
      const src = (p) => p.source === 'thoughtdag' ? t.st_from_td : p.source === 'env' ? t.st_from_env : p.source === 'local' ? t.st_auto : t.st_added;
      const rows = data.providers.map((p) => `<div class="st-item"><div class="st-main"><b>${esc(p.name)}<span class="st-src ${p.source}">${esc(src(p))}</span></b>
        <span class="st-meta">${esc(host(p.base))}</span></div><span class="st-aside">${esc(t.st_models.replace('{n}', p.models.length))}</span>
        ${p.source === 'ui' ? `<span class="st-acts"><button type="button" class="st-btn st-edit" data-key="${esc(p.key)}">${esc(t.st_edit)}</button><button type="button" class="st-btn danger st-del" data-key="${esc(p.key)}">${esc(t.st_remove)}</button></span>` : ''}</div>`).join('');
      return `<div class="st-list">${rows}${form ? providerForm() : `<button type="button" class="st-addrow st-add"><span aria-hidden="true">＋</span>${esc(t.st_add)}</button>`}</div>`;
    }

    function providerForm() {
      const t = T();
      const preset = data.presets.find((p) => p.id === form.preset) || {};
      const opts = data.presets.map((p) => `<option value="${p.id}"${p.id === form.preset ? ' selected' : ''}>${esc(p.name || 'Custom')}${p.region ? ` (${p.region})` : ''}</option>`).join('');
      // the models found: the picked ones first (a long list, such as OpenRouter's, would bury them), then as listed;
      // a search box narrows the list as you type, without losing what is ticked
      const found = form.found ? [...form.found].sort((a, b) => form.picked.includes(b.id) - form.picked.includes(a.id)) : null;
      const list = found && !found.length ? `<p class="st-note warn">${esc(t.st_none)}</p>` : found ? `<div class="st-label">${esc(t.st_pick)} <span class="st-count"></span></div>` +
        (found.length > 12 ? `<input type="search" class="st-search" placeholder="${esc(t.st_search)}" autocomplete="off">` : '') +
        `<div class="st-pick">${found.map((m) =>
        `<label data-id="${esc(m.id.toLowerCase())}"><input type="checkbox" value="${esc(m.id)}"${form.picked.includes(m.id) ? ' checked' : ''}>${esc(m.id)}${m.free ? ` <em class="free">${esc(t.free)}</em>` : ''}${(preset.recommend || []).includes(m.id) ? ' <em>★</em>' : ''}</label>`).join('')}</div>` : '';
      // OpenRouter: a key made by one authorisation (OAuth PKCE) instead of pasting one
      const oauth = form.preset === 'openrouter' && !form.minted ? `<div class="st-oauth"><p>${esc(t.or_hint)}</p><button type="button" class="primary pf-oauth">${esc(t.or_button)}</button></div>` : '';
      const minted = form.minted ? `<p class="st-note ok">${esc(t.or_minted)}</p>` : '';
      return `<div class="st-form">
        <label>${esc(t.st_preset)}<select class="pf-preset">${opts}</select></label>${oauth}${minted}
        ${form.preset === 'custom' ? `<label>${esc(t.st_name)}<input class="pf-name" value="${esc(form.name || '')}"></label>` : ''}
        <label>${esc(t.base_url)}<input class="pf-base" value="${esc(form.base || '')}" placeholder="https://…/v1"></label>
        ${preset.nokey || form.minted ? '' : `<label><span>${esc(t.api_key)}${preset.keyUrl ? ` · <a href="${preset.keyUrl}" target="_blank" rel="noopener">${esc(host(preset.keyUrl))}</a>` : ''}</span><input class="pf-key" type="password" placeholder="${esc(form.key ? t.st_key_kept : 'sk-…')}"></label>`}
        <div class="st-row"><button type="button" class="st-btn pf-fetch">${esc(t.st_fetch)}</button><span class="pf-err"></span></div>
        ${list}
        <div class="st-row end"><button type="button" class="st-btn pf-cancel">${esc(t.cancel)}</button><button type="button" class="primary pf-save"${form.found && form.found.length ? '' : ' disabled'}>${esc(t.st_save_provider)}</button></div></div>`;
    }

    let formShown = false;
    function render() {
      const t = T(), body = q('.stp-body'), y = body ? body.scrollTop : 0;   // (drawn again on each change: the place is kept)
      dlg.innerHTML = `<div class="stp" tabindex="-1" autofocus>
        <header class="stp-head"><h2>${esc(t.settings)}</h2><button type="button" class="stp-x st-close" aria-label="${esc(t.close)}" title="${esc(t.close)}"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 6l8 8M14 6l-8 8"/></svg></button></header>
        <div class="stp-body">
        <section><div class="st-list">
          <div class="st-item"><label class="st-main" for="st-ui"><b>${esc(t.language)}</b></label><select class="st-ui" id="st-ui">${I18N.CODES.map((c) => `<option value="${c}"${c === uiLang ? ' selected' : ''}>${esc(I18N.NATIVE[c])}</option>`).join('')}</select></div>
          ${app ? `<div class="st-item st-app"><div class="st-main"><b>TextFold ${esc(app)}</b><span class="st-meta">${esc(t.up_note)} <a href="https://github.com/cjdem/textfold" target="_blank" rel="noopener">★ ${esc(t.up_star)}</a></span><span class="st-upd-msg" aria-live="polite"></span></div><button type="button" class="st-btn st-upd">${esc(t.up_check)}</button></div>` : ''}
        </div></section>
        <section><h3>${esc(t.st_models_h)}</h3>${connectionSection()}${modelSection()}</section>
        <details class="st-adv"><summary>${esc(t.st_advanced)}</summary>
          <section>${askSection()}</section>
          <section><h3>${esc(t.st_providers)}</h3>${providerSection()}</section>
          <section class="st-mineru"></section>
        </details>
        </div>
        <footer class="stp-foot"><p>${esc(t.key_note)}</p><button type="button" class="primary st-close">${esc(t.st_close)}</button></footer></div>`;
      wire();
      renderMineru();
      const adv = q('.st-adv');
      if (adv) { adv.open = advancedOpen; adv.addEventListener('toggle', () => { advancedOpen = adv.open; }); }
      q('.stp-body').scrollTop = y;   // (after MinerU's part, which makes the sections their full height)
      if (form && !formShown) q('.st-form').scrollIntoView({ block: 'nearest' });   // adding or editing a provider: the form in view
      formShown = !!form;
    }
    const q = (sel) => dlg.querySelector(sel);
    // MinerU's Cloud API: the only PDF reader, and the fallback for a picture.
    function renderMineru() {
      const box = q('.st-mineru');
      if (!box) return;
      const t = T(), m = data.mineru || {};
      const bad = m.baseOk === false;
      box.innerHTML = `<h3>${esc(t.st_mineru)}</h3><div class="st-list">
        <div class="st-item"><i class="st-dot${m.api && !bad ? '' : ' bad'}"></i><div class="st-main"><b>MinerU Cloud API</b><span class="st-meta">${esc(bad ? t.mineru_url_invalid : m.api ? t.mineru_connected : t.mineru_not_connected)}</span></div></div>
        <div class="st-item st-key"><label class="st-main" for="st-mineru-key"><b>${esc(t.mineru_key)}</b><span class="st-meta">${esc(t.mineru_key_note)}</span></label>
          <input id="st-mineru-key" class="st-mineru-key" type="password" autocomplete="off" spellcheck="false" placeholder="${esc(m.api ? t.mineru_key_kept : t.mineru_key_ph)}">
          <button type="button" class="st-btn st-mineru-save">${esc(t.save)}</button>
          ${m.api ? `<button type="button" class="st-btn danger st-mineru-clear">${esc(t.mineru_clear)}</button>` : ''}</div>
        <div class="st-item st-key"><label class="st-main" for="st-mineru-url"><b>${esc(t.mineru_url)}</b><span class="st-meta">${esc(t.mineru_url_note)}</span></label>
          <input id="st-mineru-url" class="st-mineru-url" type="text" inputmode="url" autocomplete="off" spellcheck="false" value="${esc(m.base || '')}" placeholder="${esc(m.official || '')}">
          <button type="button" class="st-btn st-mineru-url-save">${esc(t.save)}</button>
          ${m.base && m.official && m.base !== m.official ? `<button type="button" class="st-btn st-mineru-url-reset">${esc(t.mineru_official)}</button>` : ''}</div>
        <div class="st-item"><div class="st-main"><b>${esc(t.mineru_limits_h)}</b><span class="st-meta">${esc(t.mineru_limits)}</span></div></div>
        <div class="st-item"><div class="st-main"><b>${esc(t.mineru_privacy_h)}</b><span class="st-meta">${esc(t.mineru_privacy)}</span></div></div>
        <div class="st-item"><label class="st-main" for="st-tier"><b>${esc(t.tier)}</b></label><select class="st-tiersel" id="st-tier">${['fast', 'accurate'].map((k) =>
          `<option value="${k}"${(data.pdfTier || 'fast') === k ? ' selected' : ''}>${esc(t['tier_' + k])}</option>`).join('')}</select></div>
      </div>`;
      const save = box.querySelector('.st-mineru-save'), input = box.querySelector('.st-mineru-key');
      const put = async (key) => {
        save.disabled = true;
        try {
          const next = await api('/api/settings', { mineru_api_key: key });
          data.mineru = next.mineru; data.pdfTier = next.pdfTier;
          renderMineru();
        } catch (x) {
          save.disabled = false;
          input.setCustomValidity(errText(x.message));
          input.reportValidity();
        }
      };
      save.onclick = () => {
        const key = input.value.trim();
        if (!key) { input.setCustomValidity(t.mineru_key_empty); input.reportValidity(); return; }
        input.setCustomValidity('');
        put(key);
      };
      input.oninput = () => input.setCustomValidity('');
      const clear = box.querySelector('.st-mineru-clear');
      if (clear) clear.onclick = () => { if (confirm(t.mineru_clear_q)) put(''); };
      const urlSave = box.querySelector('.st-mineru-url-save'), urlInput = box.querySelector('.st-mineru-url');
      const putUrl = async (value) => {
        urlSave.disabled = true;
        const reset = box.querySelector('.st-mineru-url-reset');
        if (reset) reset.disabled = true;
        try {
          const next = await api('/api/settings', { mineru_api_url: value });
          data.mineru = next.mineru; data.pdfTier = next.pdfTier;
          renderMineru();
        } catch (x) {
          urlSave.disabled = false;
          if (reset) reset.disabled = false;
          urlInput.setCustomValidity(errText(x.message));
          urlInput.reportValidity();
        }
      };
      urlSave.onclick = () => { urlInput.setCustomValidity(''); putUrl(urlInput.value.trim()); };
      urlInput.oninput = () => urlInput.setCustomValidity('');
      const urlReset = box.querySelector('.st-mineru-url-reset');
      if (urlReset) urlReset.onclick = () => putUrl('');   // (empty means the official base; the typed value is not needed)
      box.querySelector('.st-tiersel').onchange = async (ev) => {
        const next = await api('/api/settings', { pdf_tier: ev.target.value });
        data.mineru = next.mineru; data.pdfTier = next.pdfTier;
        renderMineru();
      };
    }
    const update = (d) => { data = d; modelName = d.models.length ? (d.selectedName || '') : ''; askName = d.askName || ''; renderSidebar(); if (landing) renderLanding(); render(); };

    function wire() {
      dlg.querySelectorAll('.st-close').forEach((b) => { b.onclick = () => dlg.close(); });
      const up = q('.st-upd');
      if (up) up.onclick = async () => {   // an answer either way; one found shows as the corner's toast too
        const msg = q('.st-upd-msg'), t = T();
        up.disabled = true; msg.textContent = '…';
        const r = await window.desktop.checkForUpdates().catch(() => ({ kind: 'check-failed' }));
        up.disabled = false;
        msg.textContent = r.kind === 'latest' ? t.up_latest : r.kind === 'dev' ? t.up_dev : r.kind === 'disabled' ? t.up_disabled : r.kind === 'check-failed' ? t.up_check_failed
          : r.kind === 'ready' ? t.up_ready.replace('{v}', r.version) : t.up_new.replace('{v}', r.version || '');
      };
      q('.st-ui').onchange = (e) => { setUiLang(e.target.value); render(); };
      const or = q('.st-or');
      if (or) or.onclick = async () => { or.disabled = true; if (window.desktop) dlg.close(); await connectOpenRouter(location.pathname + location.search); };
      const sel = q('.st-model');
      if (sel) sel.onchange = async () => { delete tests.gen; if (!data.askModel) delete tests.ask; update(await api('/api/models/select', { model: sel.value })); };
      const askSel = q('.st-askmodel'), effSel = q('.st-effort');
      if (askSel) askSel.onchange = async () => { delete tests.ask; update(await api('/api/models/select', { task: 'ask', model: askSel.value || null, effort: null })); };
      if (effSel) effSel.onchange = async () => { delete tests.ask; update(await api('/api/models/select', { task: 'ask', model: data.askModel || null, effort: effSel.value || null })); };
      dlg.querySelectorAll('.st-testbtn').forEach((tb) => {
        tb.onclick = async () => {
          const k = tb.dataset.test;
          tb.disabled = true; tb.textContent = '…';
          tests[k] = await api('/api/settings/test', k === 'ask' ? { task: 'ask' } : { model: data.selected }).catch((e) => ({ ok: false, error: e.message }));
          render();
        };
      });
      const td = q('.st-td');
      if (td) td.onchange = async () => update(await api('/api/settings', { use_thoughtdag_env: td.checked }));
      dlg.querySelectorAll('.st-del').forEach((b) => { b.onclick = async () => update(await api('/api/providers/remove', { key: b.dataset.key })); });
      dlg.querySelectorAll('.st-edit').forEach((b) => {
        b.onclick = () => { advancedOpen = true; const p = data.providers.find((x) => x.key === b.dataset.key);
          const known = data.presets.some((x) => x.id === p.preset);   // (a preset removed since it was saved: edit it as custom)
          form = { key: p.key, preset: known ? p.preset : 'custom', name: p.name, base: p.base }; render(); };
      });
      const add = q('.st-add');
      if (add) add.onclick = () => { const p = data.presets.find((x) => x.id === 'magpie') || data.presets[0]; form = { preset: p.id, name: '', base: p.base }; render(); };
      if (!form) return;
      const ps = q('.pf-preset');
      ps.onchange = () => { const p = data.presets.find((x) => x.id === ps.value); form = { preset: p.id, name: '', base: p.base }; render(); };   // another kind: a new provider, the edited one stays
      const keep = () => { form.base = q('.pf-base').value.trim(); if (q('.pf-name')) form.name = q('.pf-name').value.trim(); if (q('.pf-key') && q('.pf-key').value) form.api_key = q('.pf-key').value.trim(); };
      q('.pf-fetch').onclick = () => fetchModels();
      const pick = q('.st-pick'), count = q('.st-count'), search = q('.st-search');
      const recount = () => { if (count && pick) count.textContent = `· ${pick.querySelectorAll('input:checked').length}`; };
      if (pick) { pick.onchange = recount; recount(); }
      if (search) search.oninput = () => {
        const words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
        pick.querySelectorAll('label').forEach((l) => { l.hidden = !words.every((w) => l.dataset.id.includes(w)); });
      };
      const oa = q('.pf-oauth');
      if (oa) oa.onclick = async () => { oa.disabled = true; if (window.desktop) dlg.close(); await connectOpenRouter(location.pathname + location.search); };
      q('.pf-cancel').onclick = () => { form = null; render(); };
      q('.pf-save').onclick = async () => {
        keep();
        const picked = [...dlg.querySelectorAll('.st-pick input:checked')].map((i) => i.value);
        const d = await api('/api/providers/save', { key: form.key, preset: form.preset, name: form.name, base: form.base, api_key: form.api_key, models: picked, minted: !!form.minted });
        form = null; update(d);
      };
    }
    async function fetchModels() {
      if (!form) return;
      if (q('.pf-base')) form.base = q('.pf-base').value.trim();
      if (q('.pf-name')) form.name = q('.pf-name').value.trim();
      if (q('.pf-key') && q('.pf-key').value) form.api_key = q('.pf-key').value.trim();
      const err = q('.pf-err');
      if (err) err.textContent = '…';
      try {
        const r = await api('/api/providers/probe', { base: form.base, api_key: form.api_key, key: form.key, preset: form.preset, minted: !!form.minted });
        form.found = r.models; form.picked = r.picked; render();
        q('.pf-save')?.scrollIntoView({ block: 'nearest' });   // (the list and Save are what the fetch was for)
      } catch (x) { const e2 = q('.pf-err'); if (e2) e2.textContent = x.message; }
    }

    dlg.addEventListener('close', () => dlg.remove());
    if (opts && opts.add) { const p = data.presets.find((x) => x.id === 'magpie') || data.presets[0]; advancedOpen = true; form = { preset: p.id, name: '', base: p.base }; }   // Magpie is the default local provider
    if (opts && opts.minted) {   // back from OpenRouter with a key: the models to pick, free ones first
      advancedOpen = true;
      const p = data.presets.find((x) => x.id === 'openrouter');
      form = { preset: 'openrouter', name: '', base: p.base, minted: true };
    }
    render();
    dlg.showModal();
    if (!data.models.length && !form) {   // (a local provider's probe may still be answering)
      let tries = 0;
      const look = async () => {
        const d = await api('/api/models').catch(() => null);
        if (d && d.models.length && dlg.isConnected) { update(d); return; }
        if (++tries < 6 && dlg.isConnected) setTimeout(look, 1500);
      };
      setTimeout(look, 600);
    }
    if (form) q('.st-form')?.scrollIntoView({ block: 'nearest' });   // (the render's call runs before the dialog is shown)
    if (opts && opts.mineru) q('.st-mineru')?.scrollIntoView({ block: 'nearest' });
    if (opts && opts.minted) fetchModels();
  }

  renderSidebar();
  // back from OpenRouter's consent page (#or-minted, or #or-failed=why)
  if (location.hash.startsWith('#or-')) {
    const hash = location.hash;
    history.replaceState(null, '', location.pathname + location.search);
    if (hash === '#or-minted') openSettings({ minted: true });
    else alert(t().or_failed.replace('{error}', decodeURIComponent(hash.split('=')[1] || '')));
  }
})();
