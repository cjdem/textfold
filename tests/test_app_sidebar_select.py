"""The sidebar's multi-select is JavaScript, CSS and two languages' words; there is no JS test runner here, so this
holds what a Python test can see of it: the words exist in both languages, a click with ⌘/Ctrl or Shift picks a row
instead of opening it, the bar under the list moves or deletes the picked ones, a drag carries them together, and a
delete uses the bulk route, says what went and offers it back for ten seconds (also on the landing, from sessionStorage).

Run from the repo root:
    python -m unittest discover tests
"""
import json
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


def body_of(js, start):
    """The body of the function whose first line starts at `start` (up to the closing two-space brace)."""
    at = js.index(start)
    end = js.index("\n  }", at)
    return js[at:end]


class SidebarSelect(unittest.TestCase):
    def test_the_selection_is_written_in_both_languages(self):
        js = text("i18n.js")
        block = re.search(r"const sels = \(w\) => \(\{(.*?)\}\);", js, re.S).group(1)
        keys = re.findall(r"(\w+): w\[\d+\]", block)
        self.assertEqual(keys, ["sel_n", "sel_move", "sel_delete", "sel_clear", "sel_pick", "sel_del_n", "sel_del_confirm",
                                "sel_busy", "del_done", "del_done_n", "undo", "undone", "sel_tip", "sel_failed", "undo_gone", "undo_part"])
        self.assertEqual(re.findall(r"w\[(\d+)\]", block), [str(i) for i in range(16)])   # (each word its own index)
        self.assertIn("for (const [code, words] of Object.entries(SEL)) Object.assign(S[code], words);", js)   # (and they reach the app)
        body = re.search(r"const SEL = \{(.*?)\n  \};", js, re.S).group(1)
        langs = re.findall(r"^\s*(\w+): sels\(", body, re.M)
        self.assertEqual(langs, ["en", "zh"])   # (the fork's two reading languages)
        for lang in langs:
            words = json.loads(re.search(rf"\b{lang}: sels\((\[.*?\])\)", body, re.S).group(1))
            self.assertEqual(len(words), len(keys), lang)
            for key, word in zip(keys, words):
                self.assertTrue(word.strip(), f"{lang} {key}")
        # placeholders the app fills must be there, once each
        for lang in langs:
            words = dict(zip(keys, json.loads(re.search(rf"\b{lang}: sels\((\[.*?\])\)", body, re.S).group(1))))
            for key, ph in (("sel_n", "{n}"), ("sel_del_n", "{n}"), ("sel_del_confirm", "{k}"), ("sel_busy", "{n}"),
                            ("del_done", "{title}"), ("del_done_n", "{n}"), ("sel_failed", "{n}"), ("undo_part", "{n}")):
                self.assertIn(ph, words[key], f"{lang} {key}")
            self.assertIn("{n}", words["sel_del_confirm"], lang)

    def test_a_modifier_click_picks_a_row_and_the_bar_says_how_many(self):
        js = text("app.js")
        self.assertIn("const chosen = new Set();", js)
        self.assertIn("let chosenAt = null;", js)
        self.assertIn("for (const id of chosen) if (!listed.has(id)) chosen.delete(id);", js)   # (a deleted one is let go)
        # the row is marked, and its × gives way to the tick while any are picked
        self.assertIn("""`<div class="sb-row${chosen.has(p.id) ? ' chosen' : ''}" data-pid="${p.id}" data-q="${esc(hay(p))}">""", js)
        self.assertIn("(j ? stopBtn(j, T) : chosen.size ? '<span class=\"sb-check\" aria-hidden=\"true\"></span>'", js)
        # the bar under the list: how many, Move to…, Delete, and a × that lets go
        self.assertIn("""<nav class="sb-list${chosen.size ? ' choosing' : ''}">""", js)
        self.assertIn('<div class="sb-chosen" role="toolbar" aria-label="${esc(T.sel_n.replace(\'{n}\', chosen.size))}" title="${esc(selTip(T))}">', js)
        self.assertIn('<button type="button" class="sb-cmove">${esc(T.sel_move)}</button>', js)
        self.assertIn('<button type="button" class="sb-cdel">${esc(T.sel_delete)}</button>', js)
        self.assertIn('<button type="button" class="sb-cx"', js)
        self.assertLess(js.index('<nav class="sb-list${chosen.size'), js.index('<div class="sb-chosen" role="toolbar"'))
        self.assertLess(js.index('<div class="sb-chosen" role="toolbar"'), js.index('<div class="sb-foot">'))   # (above the foot, not in the list)
        # a button's handler is on the sidebar, not on each draw
        self.assertIn("else if (b.matches('.sb-cmove')) { e.stopPropagation(); if (menu) closeMenu(); else chosenMenu(b); }", js)
        self.assertIn("else if (b.matches('.sb-cdel')) deleteChosen([...chosen]);", js)
        self.assertIn("else if (b.matches('.sb-cx')) clearChosen();", js)
        # ⌘/Ctrl-click, Shift-click, and a plain click while some are picked
        self.assertIn("const a = e.target.closest('.sb-row[data-pid] > .sb-item');", js)
        self.assertIn("if (!a || e.button !== 0 || !(e.metaKey || e.ctrlKey || e.shiftKey || chosen.size)) return;", js)
        pick = js[js.index("const a = e.target.closest('.sb-row[data-pid] > .sb-item');"):js.index("}, true);")]
        self.assertIn("const pid = a.parentElement.dataset.pid, rows = shownRows().map((r) => r.dataset.pid);", pick)   # (the range is the rows shown)
        self.assertIn("if (e.shiftKey && i >= 0 && j >= 0) for (const id of rows.slice(Math.min(i, j), Math.max(i, j) + 1)) chosen.add(id);", pick)
        self.assertIn("else if (chosen.has(pid)) chosen.delete(pid);", pick)
        self.assertIn("chosenAt = pid;", pick)   # (the last pick, which Shift ranges from)
        self.assertIn("if (e.detail === 0) { const again = side.querySelector(`.sb-row[data-pid=\"${CSS.escape(pid)}\"] > .sb-item`); if (again) again.focus(); }", pick)
        self.assertIn("side.addEventListener('mousedown', (e) => { if (e.shiftKey && e.target.closest('.sb-row[data-pid] > .sb-item')) e.preventDefault(); });", js)
        # only the rows shown are picked, by Shift and by ⌘A; Esc lets go when the sidebar has the focus, unless a field
        # or a dialog is at work (the reader's Aa, note and chat overlays are not <dialog>s and must keep their Esc)
        self.assertIn("const shownRows = () => [...side.querySelectorAll('.sb-list .sb-row[data-pid]:not([hidden])')].filter((r) => r.offsetParent);", js)
        self.assertIn("if (side.classList.contains('collapsed') || menu || (e.target.closest && e.target.closest('input, textarea, select, [contenteditable]'))) return;", js)
        self.assertIn("const inside = side.contains(e.target) || side.contains(document.activeElement);", js)
        self.assertIn("if (e.key === 'Escape' && chosen.size && inside && !document.querySelector('dialog[open]')) { e.preventDefault(); clearChosen(); }", js)
        self.assertIn("else if (e.key === 'a' && (e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && document.activeElement && side.querySelector('.sb-list').contains(document.activeElement)) {", js)
        self.assertIn("for (const r of shownRows()) chosen.add(r.dataset.pid);", js)
        # a row's menu offers Select (unless it is picked already), and a right click on a picked one opens theirs
        self.assertIn("(chosen.has(pid) ? '' : `<button type=\"button\" role=\"menuitem\" data-act=\"pick\" title=\"${esc(selTip(T))}\">${esc(T.sel_pick)}</button>`) +", js)
        self.assertIn("else if (a.dataset.act === 'pick') { chosen.add(pid); chosenAt = pid; renderSidebar(); }", js)
        self.assertIn("if (row && chosen.size > 1 && chosen.has(row.dataset.pid)) chosenMenu(row.querySelector('.sb-item'), at);", js)
        self.assertIn("const selTip = (T) => T.sel_tip.replace('⌘', MAC ? '⌘' : 'Ctrl');", js)
        self.assertIn("const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);", js)

    def test_the_picked_ones_move_or_delete_together(self):
        js = text("app.js")
        menu = body_of(js, "function chosenMenu(btn, at) {")
        self.assertIn("const T = t(), ids = [...chosen], ins = new Set(ids.map((id) => folders.of[id] || null)), all = ins.size === 1 ? [...ins][0] : undefined;", menu)
        self.assertIn('aria-checked="${f.id === all}" data-to="${f.id}"', menu)   # (the folder they are all in, ticked)
        self.assertIn("([...ins].some(Boolean) ? `<button type=\"button\" role=\"menuitem\" data-to=\"\">${esc(T.f_take_out)}</button>` : '') +", menu)
        self.assertIn("if (a.dataset.act === 'new') editName('new', ids);", menu)
        self.assertIn("else if (a.dataset.act === 'delete') deleteChosen(ids);", menu)
        self.assertIn("else if ((a.dataset.to || null) !== all) moveTo(ids, a.dataset.to || null);", menu)
        # a folder made for them, then they are let go of; a move into one likewise
        move = body_of(js, "async function saveName(value) {")
        self.assertIn("const id = editing, name = value.trim(), papers = moving ? [].concat(moving) : [], parent = within, many = Array.isArray(moving);", move)
        self.assertIn("if (many && name) chosen.clear();", move)
        to = body_of(js, "async function moveTo(pids, folder) {")
        self.assertIn("const many = Array.isArray(pids);", to)
        self.assertIn("papers: [].concat(pids), folder }); if (many) chosen.clear();", to)
        # a drag carries the picked ones, says how many, and lights the folder only when one of them is elsewhere
        self.assertIn("dragging = chosen.size > 1 && chosen.has(pid) ? [...chosen] : [pid];", js)
        self.assertIn("e.dataTransfer.setData('application/x-textfold-paper', dragging.join(' '));", js)
        self.assertIn("if (dragging.length > 1) {", js)   # (one row needs no count)
        self.assertIn("e.dataTransfer.setDragImage(img, 14, 14);", js)
        self.assertIn("side.classList.toggle('from-folder', dragging.some((id) => folders.of[id]));", js)
        self.assertIn("return dragging.every((id) => (folders.of[id] || null) === to) ? undefined : to;", js)
        self.assertIn("if (fid) nestFolder(fid, to); else moveTo(pids.length > 1 ? pids : pids[0], to);", js)
        # one row picked asks one row's question
        chosen = body_of(js, "async function deleteChosen(ids) {")
        self.assertIn("if (ps.length < 2) { if (ps.length) await deletePaper(ps[0].id); return; }", chosen)
        self.assertIn("const n = ps.reduce((k, p) => k + (p.notes || 0), 0);", chosen)   # (their notes, as the confirm says)

    def test_a_delete_uses_the_bulk_route_and_offers_an_undo(self):
        js = text("app.js")
        gone = body_of(js, "async function deleteAll(ids, said) {")
        self.assertIn("r = await api('/api/papers/delete', { papers: ids });", gone)   # (R21a's route, one or many)
        self.assertIn("papers = r.papers;", gone)
        self.assertIn("for (const id of r.deleted) chosen.delete(id);", gone)
        self.assertIn("if (r.busy.length) alert(ids.length === 1 ? T.del_busy : T.sel_busy.replace('{n}', r.busy.length));", gone)
        self.assertIn("if (r.failed.length) alert(T.sel_failed.replace('{n}', r.failed.length));", gone)   # (R21a's failed list is said, not lost)
        self.assertIn("if (!r.deleted.length) { renderSidebar(); return; }", gone)
        self.assertIn("const undo = { ids: r.deleted, said: r.deleted.length === ids.length ? said : T.del_done_n.replace('{n}', r.deleted.length), until: Date.now() + UNDO_MS };", gone)
        self.assertIn("if (PAPER && r.deleted.includes(PAPER.id)) {", gone)
        self.assertIn("sessionStorage.setItem(UNDO, JSON.stringify(undo));", gone)
        self.assertIn("location.href = '/';", gone)
        self.assertIn("renderSidebar();\n    offerUndo(undo);", gone)
        single = body_of(js, "async function deletePaper(pid) {")
        self.assertIn("await deleteAll([pid], T.del_done.replace('{title}', title));", single)
        # ten seconds, the restore route, and the paper being read offered back where the page goes
        self.assertIn("const UNDO = 'textfold.undo', UNDO_MS = 10000;", js)
        undo = body_of(js, "function offerUndo(u) {")
        self.assertIn("const r = await api('/api/papers/restore', { papers: u.ids });", undo)
        self.assertIn("papers = r.papers; folders = r.folders;", undo)
        self.assertIn("if (r.restored.length === u.ids.length) {", undo)   # (only all of them is "Back in the library")
        self.assertIn("undoBox.innerHTML = `${sign('done', 'ok')}<b>${esc(T.undone)}</b>`;", undo)
        self.assertIn("undoTimer = setTimeout(() => { undoBox.hidden = true; }, 2500);", undo)
        self.assertIn("} else {   // (the trash was emptied meanwhile: say what did not come back)", undo)
        self.assertIn("undoBox.innerHTML = `${sign('warn', 'warn')}<b>${esc(r.restored.length ? T.undo_part.replace('{n}', r.restored.length) : T.undo_gone)}</b>${shut(T.close)}`;", undo)   # (an emptied trash is said)
        self.assertIn("close = () => { undoBox.querySelector('.g-x').onclick = () => { undoBox.hidden = true; }; };", undo)
        self.assertIn("undoTimer = setTimeout(() => { undoBox.hidden = true; }, Math.max(0, u.until - Date.now()));", undo)
        self.assertIn("const u = JSON.parse(sessionStorage.getItem(UNDO) || 'null');", js)
        self.assertIn("sessionStorage.removeItem(UNDO);", js)
        self.assertIn("if (u && Array.isArray(u.ids) && u.until > Date.now()) offerUndo(u);", js)
        # (the Undo is on the page before the reader's own toasts are: it shows on the landing too)
        self.assertLess(js.index("function offerUndo(u) {"), js.index("if (window.desktop && window.desktop.onUpdate)"))

    def test_a_menu_with_no_room_below_opens_above_its_button(self):
        js = text("app.js")
        menu = body_of(js, "function showMenu(btn, items, pick, at) {")
        self.assertIn("const below = r.bottom - s.top + 4;", menu)
        self.assertIn("menu.style.top = `${below + menu.offsetHeight + 8 > s.height ? Math.max(8, r.top - s.top - menu.offsetHeight - 4) : below}px`;", menu)

    def test_the_picked_rows_and_the_bar_are_styled(self):
        css = text("app.css")
        for rule in ('.sb-row.chosen > .sb-item, .sb-row.chosen > .sb-item:hover { background: var(--accent-soft); }',
                     '.sb-check { position: absolute; top: 10px; right: 8px; width: 16px; height: 16px; border-radius: 50%;',
                     '.sb-row.chosen .sb-check { border-color: var(--accent); background: var(--accent)',
                     '.sb-chosen { display: flex; align-items: center;',
                     '.sb-chosen button:hover, .sb-chosen button:focus-visible {',
                     '.sb-chosen .sb-cx {',
                     '.sb-dragimg { position: fixed; top: -200px; left: 0;'):
            self.assertIn(rule, css)
        # the tick keeps its tint under the pointer, as a picked active row too
        self.assertLess(css.index('.sb-row.chosen > .sb-item, .sb-row.chosen > .sb-item:hover'), css.index('.sb-row.chosen .sb-check'))
        # the bar is inside the sidebar's flex column: it must not be scrolled away with the list
        self.assertIn(".sb-list { flex: 1; overflow-y: auto;", css)


if __name__ == "__main__":
    unittest.main()
