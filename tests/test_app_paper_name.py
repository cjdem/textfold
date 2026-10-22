"""A document's name in the library is a row of words in two languages, a sidebar input, a reader head and a page title;
there is no JS test runner here, so this holds what a Python test can see of it: the word exists in both languages, the
name reaches the list and the page (server.py, build.py), the sidebar shows it and writes it in place, and the reader's
head puts it over the document's own title and follows a rename made in the sidebar.

Run from the repo root:
    python -m unittest discover tests
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


class PaperName(unittest.TestCase):
    def test_the_name_words_are_written_in_both_languages(self):
        js = text("i18n.js")
        block = re.search(r"const NAME = \{(.*?)\n  \};", js, re.S).group(1)
        langs = re.findall(r"^\s*(\w+): \[(.*?)\],?$", block, re.M)
        self.assertEqual([c for c, _ in langs], ["en", "zh"])
        for code, words in langs:
            vals = ast.literal_eval(f"[{words}]")
            self.assertEqual(len(vals), 4, code)
            self.assertTrue(all(v.strip() for v in vals), code)
        self.assertIn("for (const [code, [a, b, c, d]] of Object.entries(NAME)) Object.assign(S[code], { d_name: a, d_unname: b, n_paper_note: c, n_paper_note_tip: d });", js)

    def test_the_name_reaches_the_list_the_page_and_the_reader(self):
        lib = (ROOT / "textfold" / "library.py").read_text(encoding="utf-8")
        self.assertIn('"names": {p: n for p, n in names.items() if store.valid_id(p) and isinstance(n, str) and n.strip()}', lib)
        self.assertIn('**({"name": d["names"][p["id"]]} if p["id"] in d["names"] else {})', lib)   # (the list carries it)
        self.assertIn("def name(pid, value):", lib)
        self.assertIn('v = re.sub(r"\\s+", " ", str(value or "")).strip()[:200]', lib)
        self.assertIn("def name_of(pid):", lib)
        server = (ROOT / "textfold" / "server.py").read_text(encoding="utf-8")
        self.assertIn("def assembled(pid, only=None):", server)
        self.assertIn('doc["meta"]["name"] = name', server)
        self.assertIn('sig += ((build.WEB / "template.html").stat().st_mtime, library.name_of(pid))', server)   # (a renamed page is drawn again)
        self.assertIn("hit = (sig, build.page(assembled(pid), app=True))", server)
        self.assertIn('if u.path == "/api/papers/name":', server)
        self.assertIn('name_paper(str(body.get("paper", "")), body.get("name"))', server)
        self.assertIn("def name_paper(pid, value):", server)
        self.assertIn("def trash_paper(pid):", server)   # (both take store.LOCK: no name outlives the delete it raced)
        self.assertIn("with store.LOCK:", server)
        self.assertIn("trash_paper(pid)", server)
        self.assertIn("doc = assembled(pid, only=[lang] if body.get(\"langs\") == \"current\" else None)", server)
        build = (ROOT / "textfold" / "build.py").read_text(encoding="utf-8")
        self.assertIn('escape(doc["meta"].get("name") or doc["meta"]["title"])', build)
        reader = text("reader.js")
        self.assertIn("const trTitle = lang !== 'en' && m.titles && m.titles[lang], below = m.name ? trTitle || m.title : trTitle ? m.title : '';", reader)
        self.assertIn("paperHead.innerHTML = `<h1>${esc(m.name || trTitle || m.title)}</h1>${below ? `<div class=\"orig\">${esc(below)}</div>` : ''}", reader)
        self.assertIn("function rename(name) {", reader)
        self.assertIn("document.title = name || D.meta.title;", reader)
        self.assertIn("window.__reader = { setLevel, setLang, setUi, rename,", reader)

    def test_the_sidebar_shows_the_name_and_writes_it_in_place(self):
        js = text("app.js")
        self.assertIn("let renaming = null;     // the document whose name in the library is being written", js)
        self.assertIn("const own = (p.titles && p.titles[uiLang]) || p.title, title = p.name || own;", js)
        self.assertIn('if (renaming === p.id) {', js)
        self.assertIn('<input class="sb-dname-in" value="${esc(title)}" placeholder="${esc(own)}"', js)
        self.assertIn("act.matches('.sb-q, .sb-fname-in, .sb-dname-in')", js)   # (a poll's redraw keeps what is typed)
        self.assertIn("else if (e.target.matches('.sb-dname-in')) {", js)
        self.assertIn("if (e.key === 'Enter') { e.preventDefault(); saveDocName(e.target.value); }", js)
        self.assertIn("else if (e.target.matches('.sb-dname-in') && renaming !== null) saveDocName(e.target.value);", js)
        self.assertIn("function editDocName(pid) {", js)
        self.assertIn("async function saveDocName(value) {", js)
        self.assertIn("async function nameDoc(pid, name) {", js)
        self.assertIn("papers = await api('/api/papers/name', { paper: pid, name });", js)
        self.assertIn("window.__reader.rename(p.name || '')", js)
        self.assertIn("const own = [p.title, ...Object.values(p.titles || {})].includes(name);", js)   # (its own title written back clears it)
        self.assertIn("await nameDoc(pid, own ? '' : name);", js)
        self.assertIn("fold([p.name || '', p.title, ...Object.values(p.titles || {}), ...(p.authors || []), p.id].join(' '))", js)   # (the search covers it)
        self.assertIn("const title = p.name || (p.titles && p.titles[uiLang]) || p.title;", js)   # (a delete says the name)
        menu = js[js.index("function docMenu(btn, pid, at) {"):js.index("\n  }", js.index("function docMenu(btn, pid, at) {"))]
        self.assertIn('data-act="rename">${esc(T.f_rename)}</button>', menu)
        self.assertIn('(p && p.name ? `<button type="button" role="menuitem" data-act="unname">${esc(T.d_unname)}</button>` : \'\') +', menu)
        self.assertIn("else if (a.dataset.act === 'rename') editDocName(pid);", menu)
        self.assertIn("else if (a.dataset.act === 'unname') nameDoc(pid, '');", menu)
        self.assertIn("if ((!row || !row.querySelector('.sb-item')) && !(head && head.querySelector('.sb-fmenu'))) { closeMenu(); return; }", js)   # (a row being named: no menu)
        css = text("app.css")
        self.assertIn(".sb-fname-in, .sb-dname-in { flex: 1;", css)
        self.assertIn(".sb-dname-in { display: block; width: 100%; height: 36px; font-weight: 550; font-size: 13.5px; }", css)


if __name__ == "__main__":
    unittest.main()
