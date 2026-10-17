// The reading card: four sections of short, checkable points, each with the passages that support it (cards.py).
// A drawer beside the reader, never part of the page that zooms: opening it or editing it lays nothing out in the
// document. Its evidence leads back to the text (reader.js), and a selection there can become an item's evidence.
(() => {
  'use strict';
  const R = window.__reader;
  if (!R || !R.app) return;   // the app's reader only: a static page has no server to keep a card in
  const I18N = window.DR_I18N;
  const ID = R.meta.id;
  const t = () => I18N.t(R.ui);
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const h = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const clip = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
  const when = (s) => { const x = String(s || ''); return x ? x.slice(0, 16).replace('T', ' ') : ''; };
  const langName = (l) => I18N.NATIVE[l] || l;
  const pickId = () => 'c-' + Math.random().toString(36).slice(2, 10);

  let data = null;           // the server's card payload
  let loadFailed = false;    // the last GET failed: data may be its placeholder, so open (or export) tries again
  let loadNotice = '';       // the line that failure put above the card, cleared when a later load succeeds
  let job = null;            // a generation under way
  let view = 'card';         // 'card' or 'candidate'
  let armed = null;          // {item, drop}: the item the next selection in the text is linked to
  let notice = '';           // a failure or a stop, shown above the card
  let saveState = '';        // '' | 'saving' | 'saved' | 'failed'
  let saveError = '';
  let dirty = false, saving = false, saveTimer = 0, pollTimer = 0;
  let editSeq = 0, savedSeq = 0;   // what the reader has typed since the last save, and what that save carried

  // ── the button and the drawer ────────────────────────────────────────
  const btn = h('button', 'cardbtn');
  btn.type = 'button';
  const pane = h('aside', 'cardpane');
  pane.hidden = true;
  pane.setAttribute('role', 'dialog');
  document.body.append(pane);
  const toastEl = h('div', 'cardtoast');
  toastEl.hidden = true;
  document.body.append(toastEl);
  const npick = document.querySelector('.notespick');
  const notesBtn = npick && npick.querySelector('.notesbtn');
  if (npick && notesBtn) notesBtn.before(btn); else if (npick) npick.append(btn);

  function label() {
    btn.innerHTML = `<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="2.5" width="14" height="15" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6.5 6.5h7M6.5 10h7M6.5 13.5h4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>` +
      `<span>${esc(t().card_title)}</span>${data && data.exists ? '<i class="carddot"></i>' : ''}`;
    btn.classList.toggle('busy', !!job);
    btn.classList.toggle('has', !!(data && data.exists));
    btn.title = t().card_title;
    btn.setAttribute('aria-label', t().card_title);
  }

  let toastTimer = 0;
  function toast(message, bad = false) {
    clearTimeout(toastTimer);
    toastEl.textContent = message;
    toastEl.classList.toggle('bad', !!bad);
    toastEl.hidden = false;
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 3800);
  }

  const live = (j) => j && (j.status === 'queued' || j.status === 'running');
  const focusedInPane = () => !!(document.activeElement && pane.contains(document.activeElement) &&
    document.activeElement.matches('textarea, select, input'));

  async function api(op, body) {
    const r = await fetch(`/api/card/${encodeURIComponent(ID)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ op, ...body }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || r.statusText);
    return d;
  }

  const why = (e) => e === 'no-model' ? t().card_no_model : e === 'no-items' ? t().card_generate_failed.replace('{e}', e)
    : e === 'stale-card' ? t().card_conflict : e === 'too-many-evidence' ? t().card_too_many
    : e === 'language-mismatch' ? t().card_language_mismatch : e === 'no-unit' ? t().card_need_unit
    : e === 'no-item' ? t().card_no_items : String(e || '');

  async function load() {
    try {
      const r = await fetch(`/api/card/${encodeURIComponent(ID)}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || r.statusText);
      data = d;
      loadFailed = false;
      if (notice === loadNotice) notice = '';   // (a generation's own error stays)
      loadNotice = '';
    } catch (e) {
      data = data || { exists: false, sections: {}, document: { title: R.meta.title }, titles: {}, hints: {}, model: null };
      loadFailed = true;
      loadNotice = t().card_load_failed.replace('{e}', e.message);
      notice = loadNotice;
    }
    label();
    render();
  }

  async function resumeJob() {
    let jobs = [];
    try { jobs = await (await fetch('/api/jobs')).json(); } catch { /* the server may be starting */ }
    const j = jobs.find((x) => x.kind === 'card' && x.pid === ID && live(x));
    if (j) { job = j; label(); render(); watchJob(); }
  }

  async function watchJob() {
    clearTimeout(pollTimer);
    if (!job) return;
    let jobs = [];
    try { jobs = await (await fetch('/api/jobs')).json(); } catch { /* try again below */ }
    const j = jobs.find((x) => x.id === job.id) || jobs.find((x) => x.kind === 'card' && x.pid === ID && live(x));
    if (!j) {   // finished and gone from the list: the card has the result (or the failure was reported below)
      job = null;
      label();
      if (dirty && !await flush()) { notice = t().card_save_failed.replace('{e}', saveError); render(); return; }
      await load();
      return;
    }
    job = j;
    if (j.status === 'done') {
      job = null; notice = ''; label();
      if (dirty && !await flush()) { notice = t().card_save_failed.replace('{e}', saveError); render(); return; }
      await load();
      return;
    }
    if (j.status === 'error') {
      job = null; notice = why(j.error); label();
      if (focusedInPane()) paintJob(); else render();
      return;
    }
    if (j.status === 'stopped') {
      job = null; notice = t().card_stopped; label();
      if (focusedInPane()) paintJob(); else render();
      return;
    }
    label();
    if (focusedInPane()) paintJob(); else render();   // a poll must not take the field the reader is typing in
    pollTimer = setTimeout(watchJob, 1000);
  }

  function open() {
    pane.hidden = false;
    btn.classList.add('on');
    render();
    if (!data || loadFailed) load().then(resumeJob); else resumeJob();
  }
  function close() {
    if (dirty) saveNow();
    pane.hidden = true;
    btn.classList.remove('on');
  }

  // ── editing and saving ───────────────────────────────────────────────
  function setSave(state, error = '') { saveState = state; saveError = error; paintSave(); }
  function paintSave() {
    const line = pane.querySelector('.cp-save');
    if (!line) return;
    if (saveState === 'saving') line.innerHTML = `<span class="cp-dot"></span>${esc(t().card_saving)}`;
    else if (saveState === 'failed') line.innerHTML = `<span class="cp-err">${esc(t().card_save_failed.replace('{e}', saveError))}</span>` +
      `<button type="button" data-act="save-now">${esc(t().card_save_retry)}</button>`;
    else if (saveState === 'saved') line.innerHTML = `<span class="cp-ok">✓</span>${esc(t().card_saved)}`;
    else line.innerHTML = dirty ? esc(t().card_unsaved) : '';
  }
  function markDirty() {
    editSeq++;
    dirty = true;
    setSave('saving');
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveNow, 650);
  }
  function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(saveNow, 650); }
  async function saveNow() {
    clearTimeout(saveTimer);
    if (!dirty || saving || !data || !data.exists) return;
    const seq = editSeq;
    const local = data.sections;
    const body = { lang: data.lang, rev: data.rev, sections: local };
    saving = true;
    setSave('saving');
    try {
      const res = await api('save', { card: body });
      saving = false;
      if (editSeq !== seq) {   // typed since this request: keep the newer local sections, take the new revision
        data = { ...res, sections: local };
        dirty = true;
        setSave('saving');
        scheduleSave();
      } else {
        data = res;
        dirty = false;
        setSave('saved');
        if (!focusedInPane()) render(); else paintSave();
      }
    } catch (e) {
      saving = false;
      if (e.message === 'stale-card') {   // another tab saved first: reload rather than overwrite it
        dirty = false;
        toast(t().card_conflict, true);
        await load();
        return;
      }
      setSave('failed', e.message);
      if (pane.hidden) toast(t().card_save_failed.replace('{e}', e.message), true);
    }
  }
  async function flush() {
    if (saveTimer) { clearTimeout(saveTimer); await saveNow(); }
    for (let i = 0; i < 100 && (saving || dirty); i++) {
      if (saving) { await new Promise((r) => setTimeout(r, 60)); continue; }
      await saveNow();
      if (saveState === 'failed') break;   // (a retry loop would hammer the server; the reader sees Retry)
    }
    return !dirty && !saving;
  }

  function item(id) {
    for (const key of Object.keys(data.sections || {})) {
      const it = (data.sections[key] || []).find((x) => x.id === id);
      if (it) return { key, it, list: data.sections[key], at: data.sections[key].indexOf(it) };
    }
    return null;
  }
  function changed(it) {   // the server does the same: a changed point is the reader's to check again
    it.verified = false;
    if (it.state === 'found') it.state = 'check';
    if (it.origin === 'model') it.edited = true;
  }

  // ── drawing ──────────────────────────────────────────────────────────
  function sourceLine() {
    const d = data.document || {};
    const bits = [];
    if (d.authors && d.authors.length) bits.push(esc(d.authors.slice(0, 6).join(', ') + (d.authors.length > 6 ? ' et al.' : '')));
    if (d.year) bits.push(esc(d.year));
    else if (d.date) bits.push(esc(d.date));
    if (d.url) bits.push(`<a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.label || d.url)}</a>`);
    if (d.doi) bits.push(`DOI ${esc(d.doi)}`);
    if (d.version) bits.push(esc(d.version));
    if (d.citekey) bits.push(`<code>${esc(d.citekey)}</code>`);
    return bits.length ? `<div class="cp-src">${bits.join(' · ')}</div>` : '';
  }

  function jobBlock() {
    if (!job) return '';
    const pct = job.total ? Math.round((100 * job.done) / job.total) : 6;
    return `<div class="cp-job" role="status"><div class="cp-job-h"><b>${esc(t().card_generating)}</b>` +
      `<span>${job.done || 0}/${job.total || 0}</span><button type="button" data-act="stop-job">${esc(I18N.t(R.ui).stop)}</button></div>` +
      `<div class="cp-bar"><i style="width:${pct}%"></i></div></div>`;
  }
  function paintJob() { const box = pane.querySelector('.cp-jobs'); if (box) box.innerHTML = jobBlock(); }

  function langSelect(selected) {
    return `<select class="cp-genlang">${I18N.CODES.map((l) =>
      `<option value="${l}"${l === selected ? ' selected' : ''}>${esc(langName(l))}</option>`).join('')}</select>`;
  }

  function emptyBody() {
    const L = R.lang && I18N.NATIVE[R.lang] ? R.lang : 'en';
    const can = !!(data.model);
    return `<div class="cp-body">
      <div class="cp-head">
        <div class="cp-title"><b>${esc(t().card_title)}</b></div>
        <button type="button" class="cp-x" data-act="close" aria-label="${esc(I18N.t(R.ui).close)}">×</button>
      </div>
      <div class="cp-doc"><div class="cp-doc-t">${esc((data.document || {}).title || R.meta.title)}</div>${sourceLine()}</div>
      <p class="cp-intro">${esc(t().card_intro)}</p>
      <div class="cp-start">
        <label class="cp-lang"><span>${esc(t().card_draft_lang)}</span>${langSelect(L)}</label>
        <div class="cp-start-acts">
          <button type="button" class="cp-primary" data-act="generate"${can ? '' : ' disabled'}>${esc(t().card_generate)}</button>
          <button type="button" data-act="manual">${esc(t().card_manual)}</button>
        </div>
      </div>
      ${can ? '' : `<p class="cp-note">${esc(t().card_no_model)}</p>`}
      ${notice ? `<p class="cp-bad">${esc(notice)}</p>` : ''}
      <div class="cp-jobs">${jobBlock()}</div>
      <div class="cp-save"></div>
    </div>`;
  }

  function badges(it) {
    const out = [];
    out.push(`<span class="ci-origin ${it.origin === 'user' ? 'user' : it.edited ? 'edited' : 'model'}">${esc(it.origin === 'user' ? t().card_origin_user : it.edited ? t().card_origin_edited : t().card_origin_model)}</span>`);
    if (it.state && it.state !== 'found') out.push(`<span class="ci-state ${stateOf(it.state)}">${esc(stateWord(it.state))}</span>`);
    if (it.verified) out.push(`<span class="ci-checked">✓ ${esc(t().card_verified)}</span>`);
    if (it.recheck) out.push(`<span class="ci-recheck">${esc(t().card_recheck)}</span>`);
    return out.join('');
  }
  const stateWord = (s) => ({ missing: t().card_missing, na: t().card_na, check: t().card_check, found: t().card_found })[s] || s;
  const stateOf = (s) => ['found', 'missing', 'na', 'check'].includes(s) ? s : 'check';   // (a class name from stored data)

  function evidenceChip(ev, i, itemId, editable) {
    const where = [ev.label, ev.sectionTitle && !ev.label ? ev.sectionTitle : '', ev.page ? `p. ${ev.page}` : ''].filter(Boolean).join(' · ');
    const bad = ev.broken ? ' broken' : ev.mismatch ? ' mismatch' : '';
    return `<span class="ci-evone${bad}">` +
      `<button type="button" class="ci-chip${bad}" data-act="${ev.broken ? 'quote' : 'jump'}" data-unit="${esc(ev.unit || '')}" data-block="${esc(ev.block || '')}"` +
      ` title="${esc(ev.quote || '')}"><span class="ci-where">${esc(where || ev.unit || '')}</span>` +
      `<span class="ci-q">“${esc(clip(ev.quote || '', 110))}”</span>` +
      `${ev.broken ? `<span class="ci-broken">${esc(t().card_broken)}</span>` : ev.mismatch ? `<span class="ci-broken">${esc(t().card_mismatch)}</span>` : ''}</button>` +
      `${ev.broken && editable ? `<button type="button" class="ci-relink" data-act="relink" data-item="${esc(itemId)}" data-index="${i}">${esc(t().card_relink)}</button>` : ''}` +
      `${editable ? `<button type="button" class="ci-evx" data-act="unlink" data-item="${esc(itemId)}" data-index="${i}" aria-label="${esc(t().card_remove_evidence)}">×</button>` : ''}` +
      `</span>`;
  }

  function itemHtml(it, key, n, editable) {
    const evs = it.evidence || [];
    const issue = it.issue && ({ 'no-evidence': t().card_issue_no_evidence, 'bad-citation': t().card_issue_bad_citation })[it.issue];
    return `<article class="ci${it.state !== 'found' ? ' ' + stateOf(it.state) : ''}${it.verified ? ' verified' : ''}" data-item="${esc(it.id)}" data-key="${esc(key)}">
      <div class="ci-top">${badges(it)}
        ${editable ? `<span class="ci-acts">
          <button type="button" data-act="up" data-item="${esc(it.id)}" title="${esc(t().card_move_up)}" aria-label="${esc(t().card_move_up)}">↑</button>
          <button type="button" data-act="down" data-item="${esc(it.id)}" title="${esc(t().card_move_down)}" aria-label="${esc(t().card_move_down)}">↓</button>
          <button type="button" data-act="del" data-item="${esc(it.id)}" title="${esc(t().card_delete_item)}" aria-label="${esc(t().card_delete_item)}">×</button>
        </span>` : ''}
      </div>
      ${editable
        ? `<textarea class="ci-text" rows="2" placeholder="${esc(t().card_item_ph)}" data-item="${esc(it.id)}">${esc(it.text || '')}</textarea>
           <div class="ci-tools">
             <label><span>${esc(t().card_state)}</span><select data-act="state" data-item="${esc(it.id)}">` +
               ['found', 'missing', 'na', 'check'].map((s) => `<option value="${s}"${it.state === s ? ' selected' : ''}>${esc(stateWord(s))}</option>`).join('') +
             `</select></label>
             <button type="button" class="ci-checkbtn${it.verified ? ' on' : ''}" data-act="verify" data-item="${esc(it.id)}">${esc(it.verified ? t().card_verified : t().card_unverified)}</button>
           </div>`
        : `<div class="ci-ro">${esc(it.text || '')}</div>`}
      ${issue ? `<div class="ci-issue">${esc(issue)}</div>` : ''}
      <div class="ci-ev"><span class="ci-ev-h">${esc(t().card_evidence)}</span>${evs.length ? '' : `<span class="ci-none">${esc(t().card_no_evidence)}</span>`}
        ${evs.map((ev, i) => evidenceChip(ev, i, it.id, editable)).join('')}
        ${editable ? `<button type="button" class="ci-arm" data-act="arm" data-item="${esc(it.id)}">${esc(t().card_arm)}</button>` : ''}
      </div>
    </article>`;
  }

  function sectionHtml(key, n) {
    const L = data.lang && I18N.NATIVE[data.lang] ? data.lang : 'en';
    const heading = ((data.titles || {})[L] || {})[key] || key;
    const hint = ((data.hints || {})[L] || {})[key] || '';
    const items = (data.sections || {})[key] || [];
    return `<section class="cp-sec">
      <h3>${n}. ${esc(heading)}</h3>${hint ? `<p class="cp-hint">${esc(hint)}</p>` : ''}
      ${items.length ? items.map((it) => itemHtml(it, key, 1, true)).join('') : `<p class="cp-empty">${esc(t().card_section_empty)}</p>`}
      <button type="button" class="cp-add" data-act="add" data-key="${esc(key)}">+ ${esc(t().card_add_item)}</button>
    </section>`;
  }

  function candidateBanner() {
    const c = data.candidate;
    if (!c) return '';
    return `<div class="cp-cand">
      <div class="cp-cand-h"><b>${esc(t().card_candidate)}</b><span>${esc(langName(c.lang))} · ${esc(when(c.at))}</span></div>
      ${c.partial ? `<p class="cp-bad">${esc(t().card_candidate_partial.replace('{n}', c.failed || 0))}</p>` : ''}
      ${c.stale ? `<p class="cp-warn">${esc(t().card_candidate_stale)}</p>` : ''}
      <div class="cp-cand-acts">
        <button type="button" class="cp-primary" data-act="candidate">${esc(t().card_review)}</button>
        <button type="button" data-act="merge">${esc(t().card_merge_all)}</button>
        <button type="button" data-act="replace">${esc(t().card_replace_all)}</button>
        <button type="button" data-act="discard">${esc(t().card_discard)}</button>
      </div></div>`;
  }

  function candidateBody() {
    const c = data.candidate;
    if (!c) { view = 'card'; return cardBody(); }
    const L = c.lang && I18N.NATIVE[c.lang] ? c.lang : 'en';
    const titles = (data.titles || {})[L] || {};
    const issues = { 'no-evidence': t().card_issue_no_evidence, 'bad-citation': t().card_issue_bad_citation };
    const one = (it) => `<article class="ci cand" data-item="${esc(it.id)}">
        <div class="ci-top">${badges(it)}<button type="button" class="ci-adopt" data-act="adopt-item" data-item="${esc(it.id)}">${esc(t().card_adopt)}</button></div>
        <div class="ci-ro">${esc(it.text || '')}</div>
        ${it.issue ? `<div class="ci-issue">${esc(issues[it.issue] || '')}</div>` : ''}
        <div class="ci-ev">${(it.evidence || []).map((ev, i) => evidenceChip(ev, i, it.id, false)).join('')}</div>
      </article>`;
    const secs = Object.keys(data.sections || {}).map((key, n) => {
      const rows = ((c.sections || {})[key] || []).map(one).join('') || `<p class="cp-empty">${esc(t().card_section_empty)}</p>`;
      return `<section class="cp-sec cand"><h3>${n + 1}. ${esc(titles[key] || key)}</h3>${rows}</section>`;
    }).join('');
    return `<div class="cp-body">
      <div class="cp-head">
        <button type="button" class="cp-back" data-act="back">← ${esc(t().card_back)}</button>
        <button type="button" class="cp-x" data-act="close" aria-label="${esc(I18N.t(R.ui).close)}">×</button>
      </div>
      <div class="cp-cand-h"><b>${esc(t().card_candidate)}</b><span>${esc(t().card_candidate_lang.replace('{lang}', langName(c.lang)))} · ${esc(when(c.at))}</span></div>
      ${c.partial ? `<p class="cp-bad">${esc(t().card_candidate_partial.replace('{n}', c.failed || 0))}</p>` : ''}
      ${c.stale ? `<p class="cp-warn">${esc(t().card_candidate_stale)}</p>` : ''}
      <div class="cp-cand-acts">
        <button type="button" class="cp-primary" data-act="merge">${esc(t().card_merge_all)}</button>
        <button type="button" data-act="replace">${esc(t().card_replace_all)}</button>
        <button type="button" data-act="discard">${esc(t().card_discard)}</button>
      </div>
      ${secs}
    </div>`;
  }

  function cardBody() {
    const g = data.generation;
    const L = data.lang && I18N.NATIVE[data.lang] ? data.lang : 'en';
    return `<div class="cp-body">
      <div class="cp-head">
        <div class="cp-title"><b>${esc(t().card_title)}</b><span class="cp-badge">${esc(langName(data.lang))}</span></div>
        <span class="cp-tools">
          <button type="button" data-act="export">${esc(t().card_export)}</button>
          <button type="button" class="cp-x" data-act="close" aria-label="${esc(I18N.t(R.ui).close)}">×</button>
        </span>
      </div>
      <div class="cp-doc"><div class="cp-doc-t">${esc((data.document || {}).title || R.meta.title)}</div>${sourceLine()}</div>
      <div class="cp-meta">${data.created ? `<span>${esc(t().card_created)} ${esc(when(data.created))}</span>` : ''}` +
        `<span>${esc(t().card_updated)} ${esc(when(data.updated))}</span>` +
        `${g ? `<span>${esc(t().card_generated_with.replace('{model}', g.model || '').replace('{at}', when(g.at)))}</span>` : ''}</div>
      ${data.stale ? `<p class="cp-warn">${esc(t().card_stale)} <button type="button" class="cp-linkbtn" data-act="review">${esc(t().card_reviewed)}</button></p>` : ''}
      ${g && g.partial ? `<p class="cp-bad">${esc(t().card_candidate_partial.replace('{n}', g.failed || 0))}</p>` : ''}
      ${notice ? `<p class="cp-bad">${esc(notice)}</p>` : ''}
      ${candidateBanner()}
      <div class="cp-actions">
        <label class="cp-lang"><span>${esc(t().card_draft_lang)}</span>${langSelect(L)}</label>
        <button type="button" data-act="generate"${data.model && !job ? '' : ' disabled'}>${esc(t().card_generate)}</button>
      </div>
      ${data.model ? '' : `<p class="cp-note">${esc(t().card_no_model)}</p>`}
      <div class="cp-jobs">${jobBlock()}</div>
      <div class="cp-save"></div>
      ${Object.keys(data.sections || {}).map((key, n) => sectionHtml(key, n + 1)).join('')}
    </div>`;
  }

  function render() {
    label();
    const at = pane.querySelector('.cp-body');
    const top = at ? at.scrollTop : 0;
    pane.innerHTML = !data ? `<div class="cp-body"><div class="cp-loading">…</div></div>`
      : !data.exists ? emptyBody()
      : view === 'candidate' ? candidateBody() : cardBody();
    pane.setAttribute('aria-label', t().card_title);
    const body = pane.querySelector('.cp-body');
    if (body) body.scrollTop = top;
    paintSave();
  }

  // ── the actions ──────────────────────────────────────────────────────
  async function generate() {
    const sel = pane.querySelector('.cp-genlang');
    const lang = sel ? sel.value : (data.lang || R.lang || 'en');
    if (!await flush()) { toast(t().card_save_failed.replace('{e}', saveError), true); return; }
    notice = '';
    try {
      const j = await api('generate', { lang });
      job = j;
      render();
      watchJob();
    } catch (e) {
      notice = why(e.message);
      render();
    }
  }

  const pickLanguage = () => {
    const sel = pane.querySelector('.cp-genlang');
    return sel ? sel.value : (R.lang || 'en');
  };

  async function createManual() {
    try {
      data = await api('create', { lang: pickLanguage() });
      render();
      const first = pane.querySelector('.cp-add');
      if (first) first.focus();
    } catch (e) {
      notice = t().card_save_failed.replace('{e}', why(e.message));
      render();
    }
  }

  async function adopt(mode) {
    if (!await flush()) { toast(t().card_save_failed.replace('{e}', saveError), true); return; }
    if (mode === 'replace' && !confirm(t().card_replace_confirm)) return;
    try {
      data = await api('adopt', { mode });
      view = 'card';
      notice = '';
      render();
    } catch (e) {
      notice = why(e.message);
      render();
    }
  }

  async function adoptItem(id) {
    if (!await flush()) { toast(t().card_save_failed.replace('{e}', saveError), true); return; }
    try {
      data = await api('adopt_item', { id });
      if (!data.candidate) view = 'card';
      render();
    } catch (e) {
      notice = why(e.message);
      render();
    }
  }

  async function discard() {
    if (!confirm(t().card_discard_confirm)) return;
    if (!await flush()) { toast(t().card_save_failed.replace('{e}', saveError), true); return; }
    try {
      data = await api('discard', {});
      view = 'card';
      notice = '';
      render();
    } catch (e) {
      notice = why(e.message);
      render();
    }
  }

  async function review() {
    if (!await flush()) { toast(t().card_save_failed.replace('{e}', saveError), true); return; }
    try {
      data = await api('review', {});
      render();
    } catch (e) {
      toast(why(e.message), true);
    }
  }

  function exportMd() {   // the picker opens on the click itself; the file is made after it is chosen
    const name = data.exportName || `${ID} reading-card.md`;
    R.saveAs(name, async () => {
      if (!await flush()) throw new Error(saveError || '');
      const r = await fetch(`/api/card/${encodeURIComponent(ID)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op: 'export', base: location.origin }) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || r.statusText);
      return d.markdown;
    }, 'text/markdown').then((done) => { if (done) toast(t().card_exported); },
      (e) => toast(t().card_export_failed.replace('{e}', why(e.message)), true));
  }

  async function linkSelection(anchors, itemId, drop) {
    try {
      data = await api('evidence', { item: itemId, anchors, ...(drop === undefined ? {} : { drop }) });
      toast(t().card_added);
      if (!pane.hidden) render();
      return true;
    } catch (e) {
      toast(why(e.message), true);
      return false;
    }
  }

  // which item a selection supports: a small chooser over every item, in the card's own reading order
  let picker = null;
  function openPicker(anchors) {
    const items = [];
    for (const key of Object.keys(data.sections || {})) for (const it of data.sections[key] || []) items.push({ key, it });
    if (!items.length) { toast(t().card_no_items); open(); return; }
    if (picker) picker.remove();
    const L = data.lang && I18N.NATIVE[data.lang] ? data.lang : 'en';
    const titles = (data.titles || {})[L] || {};
    picker = h('div', 'cardpick');
    picker.innerHTML = `<div class="cpick"><div class="cpick-h"><b>${esc(t().card_pick)}</b><button type="button" class="cpick-x" aria-label="${esc(I18N.t(R.ui).close)}">×</button></div>` +
      `<div class="cpick-q">“${esc(clip((anchors[0].quote || {}).exact || '', 180))}”</div><div class="cpick-list">` +
      items.map(({ key, it }, i) => `<button type="button" class="cpick-item" data-i="${i}"><span class="cpick-s">${esc(titles[key] || key)}</span>` +
        `<span class="cpick-t">${esc(clip(it.text || t().card_no_evidence, 120))}</span></button>`).join('') +
      `</div></div>`;
    document.body.append(picker);
    const shut = () => { if (picker) { picker.remove(); picker = null; } document.removeEventListener('keydown', onKey, true); };
    const onKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); shut(); } };
    document.addEventListener('keydown', onKey, true);
    picker.querySelector('.cpick-x').onclick = shut;
    picker.addEventListener('click', (e) => {
      if (e.target === picker) { shut(); return; }
      const b = e.target.closest('.cpick-item');
      if (!b) return;
      const it = items[+b.dataset.i].it;
      shut();
      linkSelection(anchors, it.id);
    });
    picker.querySelector('.cpick-item').focus();
  }

  // the reader's selection bar calls this: an armed item takes the passage, else the reader says which item it supports
  window.PFCard = {
    available: () => true,
    async exportMarkdown() {   // from the reader's export menu, without opening the drawer first
      if (!data || loadFailed) await load();
      if (loadFailed) { open(); return; }   // the drawer shows why it could not be loaded, and tries again next time
      if (!data || !data.exists) { toast(t().card_need_card); open(); return; }
      exportMd();
    },
    async fromSelection(anchors) {
      if (!data || loadFailed) await load();
      if (loadFailed) { open(); return; }   // (not "make a card first": the card may be there and the server not)
      if (!data || !data.exists) { toast(t().card_need_card); open(); return; }
      if (dirty && !await flush()) { toast(t().card_save_failed.replace('{e}', saveError), true); return; }
      const as = (anchors || []).filter((a) => a && a.unit && Array.isArray(a.sents) && a.sents.length);
      if (!as.length) { toast(t().card_need_unit); return; }
      if (armed) {
        const a = armed; armed = null;
        linkSelection(as, a.item, a.drop);
        return;
      }
      openPicker(as);
    },
    arm(itemId, drop) {
      if (armed && armed.item === itemId) { armed = null; toast(t().card_arm_cancelled); return; }
      armed = { item: itemId, drop };
      close();
      toast(t().card_armed);
    },
  };

  // ── events ───────────────────────────────────────────────────────────
  pane.addEventListener('keydown', (e) => {
    e.stopPropagation();   // the reader's keys (1–5, L, Esc) belong to the page, not to a field or this drawer
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') { e.preventDefault(); saveNow(); }
  });
  pane.addEventListener('wheel', (e) => { if (e.ctrlKey || e.metaKey) e.stopPropagation(); }, { passive: true });
  pane.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (!b) return;
    const act = b.dataset.act, id = b.dataset.item;
    if (act === 'close') { close(); return; }
    if (act === 'manual') { createManual(); return; }
    if (act === 'generate') { generate(); return; }
    if (act === 'stop-job' && job) {
      fetch('/api/jobs/stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: job.id }) }).catch(() => {});
      return;
    }
    if (act === 'save-now') { saveNow(); return; }
    if (act === 'export') { exportMd(); return; }
    if (act === 'candidate') { view = 'candidate'; render(); return; }
    if (act === 'back') { view = 'card'; render(); return; }
    if (act === 'merge') { adopt('merge'); return; }
    if (act === 'replace') { adopt('replace'); return; }
    if (act === 'discard') { discard(); return; }
    if (act === 'adopt-item') { adoptItem(id); return; }
    if (act === 'review') { review(); return; }
    if (act === 'jump') { close(); R.jumpToEvidence(b.dataset.unit, b.dataset.block || null); return; }
    if (act === 'quote') { toast(b.title || t().card_broken); return; }
    if (act === 'relink') { window.PFCard.arm(id, +b.dataset.index); return; }
    if (act === 'arm') { window.PFCard.arm(id); return; }
    if (act === 'add') {
      const key = b.dataset.key;
      if (!key || !data.sections) return;
      const it = { id: pickId(), text: '', state: 'found', origin: 'user', edited: false, verified: false, issue: '', evidence: [], _new: true };
      (data.sections[key] = data.sections[key] || []).push(it);
      dirty = true;   // (saved once there are words: an empty new point is not written)
      setSave('saving');
      render();
      const field = pane.querySelector(`.ci-text[data-item="${CSS.escape(it.id)}"]`);
      if (field) { field.focus(); field.setSelectionRange(0, 0); }
      return;
    }
    const found = id && item(id);
    if (!found) return;
    const { it, list, at } = found;
    if (act === 'up' && at > 0) { list.splice(at, 1); list.splice(at - 1, 0, it); markDirty(); render(); }
    else if (act === 'down' && at < list.length - 1) { list.splice(at, 1); list.splice(at + 1, 0, it); markDirty(); render(); }
    else if (act === 'del') { const key = found.key; data.sections[key] = list.filter((x) => x.id !== id); markDirty(); render(); }
    else if (act === 'verify') { it.verified = !it.verified; markDirty(); render(); }
    else if (act === 'unlink') { it.evidence = (it.evidence || []).filter((_, i) => i !== +b.dataset.index); changed(it); markDirty(); render(); }
  });
  pane.addEventListener('input', (e) => {
    if (!e.target.matches('.ci-text')) return;
    const art = e.target.closest('.ci');
    let found = item(e.target.dataset.item);
    if (!found && art && art.dataset.key && data.sections && Array.isArray(data.sections[art.dataset.key])) {
      // a save made while this field was still empty dropped the blank point, but the reader kept typing in it:
      // put the point back with those words rather than losing them when the next render replaces this field
      const it = { id: e.target.dataset.item, text: '', state: 'found', origin: 'user', edited: false,
                   verified: false, issue: '', evidence: [], _new: true };
      data.sections[art.dataset.key].push(it);
      found = { key: art.dataset.key, it, list: data.sections[art.dataset.key], at: data.sections[art.dataset.key].length - 1 };
    }
    if (!found) return;
    found.it.text = e.target.value;
    // the badges follow the words as they change: a found point becomes one to check, and a check mark goes
    if (found.it.state === 'found' && !found.it._new) {   // (a point just added is being written, not edited)
      found.it.state = 'check';
      let st = art && art.querySelector('.ci-state');
      if (art && !st) {
        st = h('span', 'ci-state check');
        const top = art.querySelector('.ci-top');
        top.insertBefore(st, top.querySelector('.ci-acts'));
      }
      if (st) st.textContent = t().card_check;
      const sel = art && art.querySelector('select[data-act="state"]');
      if (sel) sel.value = 'check';
      art && art.classList.add('check');
    }
    if (found.it.verified) {
      found.it.verified = false;
      if (art) {
        const badge = art.querySelector('.ci-checked'); if (badge) badge.remove();
        const vb = art.querySelector('.ci-checkbtn'); if (vb) { vb.classList.remove('on'); vb.textContent = t().card_unverified; }
        art.classList.remove('verified');
      }
    }
    if (found.it.origin === 'model') {
      found.it.edited = true;
      if (art) {
        const ed = art.querySelector('.ci-origin');
        if (ed) { ed.classList.remove('model'); ed.classList.add('edited'); ed.textContent = t().card_origin_edited; }
      }
    }
    markDirty();
  });
  pane.addEventListener('change', (e) => {
    if (!e.target.matches('select[data-act="state"]')) return;
    const found = item(e.target.dataset.item);
    if (!found) return;
    found.it.state = e.target.value;
    found.it.verified = false;
    markDirty();
    render();
  });
  pane.addEventListener('focusout', () => setTimeout(() => {
    if (!dirty && !saving && !pane.hidden) { const at = document.activeElement; if (!at || !pane.contains(at)) render(); }
  }, 0));

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (pane.hidden) open(); else close();
  });
  addEventListener('click', (e) => {
    if (!pane.hidden && !pane.contains(e.target) && e.target !== btn && !e.target.closest('.cardbtn')) close();
  });
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && dirty) saveNow(); });
  addEventListener('beforeunload', (e) => { if (dirty || saving) { e.preventDefault(); e.returnValue = ''; } });
  document.addEventListener('tf-lang', () => { label(); if (!pane.hidden) render(); });
  label();
})();
