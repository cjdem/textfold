"""The whole text saved as Markdown at the level being read is JavaScript and two languages' words; there is no JS test
runner here, so this pins what a Python test can see of it: the new format in the save dialog and the file it makes, the
document pieces the Markdown is built from (headings, summaries only where the level shows one, paragraphs as bullets at
the written levels, a highlight marked in the author's words, the notes' block ids kept), and the notes' own Markdown
still written through the shared head and note writer.

Run from the repo root:
    python -m unittest discover tests
"""
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


class MarkdownExport(unittest.TestCase):
    def test_the_level_markdown_is_named_in_both_languages(self):
        words = re.findall(r'sv_md_level: "([^"]+)"', text("i18n.js"))
        self.assertEqual(len(words), 2)   # (the fork's two reading languages)
        self.assertEqual(words, ["Markdown, at {level}", "Markdown（{level}层）"])
        for word in words:
            self.assertIn("{level}", word)

    def test_the_save_dialog_offers_the_whole_text_as_markdown_at_this_level(self):
        js = text("reader.js")
        # the whole text gains Markdown; the marks keep theirs, and JSON stays the marks' own
        self.assertIn("const fmts = sv.what === 'whole' ? [...(D.app ? ['html'] : []), 'pdf', 'md'] : ['html', 'pdf', 'md', 'json'];", js)
        self.assertIn("md: sv.what === 'whole' ? t.sv_md_level.replace('{level}', t.levels[level]) : t.sv_md", js)
        # the file is named for the level, and made in the browser from what is on the page
        self.assertIn("whole && sv.fmt === 'md' ? [`${name} (${t.levels[level]}).md`, 'text/markdown', () => docMarkdown(kinds)]", js)
        # still one language: the all-languages choice is the server-made HTML's alone
        self.assertIn("const langs = sv.what === 'whole' && sv.fmt === 'html' && AVAIL.length > 1;", js)

    def test_the_document_markdown_follows_the_level_and_the_marks(self):
        js = text("reader.js")
        self.assertIn("const LEVEL_NAMES = ['topic', 'takeaway', 'key', 'brief', 'full'];", js)
        doc = re.search(r"function docMarkdown\(kinds\) \{(.*?)\n  \}", js, re.S).group(1)
        # its head says the level and the language, and its title is the one being read
        self.assertIn("mdHead(title, [`level: ${LEVEL_NAMES[level]}`, `lang: ${lang}`], null)", doc)
        self.assertIn("const m = D.meta, t = T[ui], title = m.name || (lang !== 'en' && m.titles && m.titles[lang]) || m.title;", doc)
        self.assertIn("`*${t.levels[level]} · ${BRAND}*`", doc)
        # the notes sit where they belong: the whole paper's first, a section's under its heading, a paragraph's under it
        self.assertIn("const notesAt = (k) => (mine.get(k) || []).flatMap((n) => noteMd(n, false));", doc)
        self.assertIn("out.push(...notesAt('¶'));", doc)
        self.assertIn("out.push(...notesAt(`§${c.id}`));", doc)
        # the page's own level decides: references are folded away, summaries where the level shows them (Brief too, in
        # a CJK document, where the page shows the section's line there)
        self.assertIn("if (!sc || (level < 4 && sc.sec.classList.contains('ref'))) continue;", doc)
        self.assertIn("const sum = level <= 2 || (CJK_DOC && level === 3) ? summaryOf(c) : '';", doc)
        # the text is the level's pieces; at the written levels a bullet, a caption in italics, a list's own marker
        self.assertIn("markedText(uid, L, L >= 3 ? marks : [])", doc)
        self.assertIn("if (!text && !under.length) continue;", doc)
        self.assertIn("`${'#'.repeat(Math.min(6, c.level || 2))} ${headingOf(c)}`", doc)
        self.assertIn("${L > 2 && u.marker && /\\d/.test(u.marker) ? u.marker : '-'} ${text}", doc)
        self.assertIn("const bullet = L <= 2 || u.role === 'item';", doc)
        self.assertIn("u.role === 'caption' ? `*${text}*` : text", doc)   # a caption is italic, not a paragraph
        self.assertIn(".replace(/\\n{3,}/g, '\\n\\n')", doc)
        # a highlight is marked by its anchor's tokens, not by searching for its words, and only where the level shows
        # the whole passage; the others go under the paragraph, as the notes' file writes them
        self.assertIn("if (under.length)", doc)
        mark = re.search(r"function markedText\(uid, L, marks\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("if (kindOf(n) !== 'hl' || !a || n.anchor.lang !== lang) continue;", mark)
        self.assertIn("p.i !== undefined && p.i >= a[0] && p.i <= a[1]", mark)
        self.assertIn("Array.from({ length: a[1] - a[0] + 1 }, (_, j) => a[0] + j).every((i) => have.has(i))", mark)
        self.assertIn("starts.add(at[0]); ends.add(at[at.length - 1]); inline.add(n);", mark)
        self.assertIn("parts[k].replace(/(\\s*)$/, '\\u0001$1')", mark)   # (the space after a word stays outside the mark)
        self.assertIn(".replace(/\\u0001/g, '==')", mark)
        # the builders it uses, and their definitions
        self.assertIn("p.gap ? '…' : typeof p.tok === 'string'", js)
        self.assertIn("tokPlain(p.tok)", js)
        self.assertIn("const headingOf = (c) => `${c.num || ''} ${secTitle(c)}`.trim();", js)
        self.assertIn("const summaryOf = (c) => { const lad = (trOf(c) && trOf(c).lad) || c.lad; return lad && lad.take.length ? toksText(lad.take, 0, lad.take.length - 1) : ''; };", js)

    def test_the_notes_markdown_is_the_same_file_through_the_shared_writers(self):
        js = text("reader.js")
        self.assertIn("saveAs(`${fileName()}.md`, () => notesMarkdown(kinds, sv.para), 'text/markdown')", js)   # (the menu's one-click export)
        notes = re.search(r"function notesMarkdown\(kinds, para\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("mdHead(D.meta.title, [], 'textfold/notes@1')", notes)
        self.assertIn("noteMd(n, para)", notes)
        # the head carries the data file's format line, the original title in italics when the H1 is translated
        head = re.search(r"function mdHead\(title, props, format\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("...(format ? [`format: ${format}`] : [])", head)
        self.assertIn("...(title !== m.title ? [`*${m.title}*`, ''] : [])", head)
        # and each note keeps its block id, its words and its link back
        note = re.search(r"function noteMd\(n, para\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("out.push('', `^${n.id}`, '');", note)
        self.assertIn("else if (!whole(n.anchor)) out.push(...mdQuote(", note)
        self.assertIn("[${T[ui].n_open}](${noteLink(n)})", note)


if __name__ == "__main__":
    unittest.main()
