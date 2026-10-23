# TextFold: development notes

How the reader works, how to run and extend it. For what it is and how to use it, see the [README](../README.md).
The notes format is [notes-format.md](notes-format.md); the reading card's is
[reading-card-format.md](reading-card-format.md).

The same semantic zoom as ThoughtDAG's plaques, applied to a paper's HTML (LaTeXML) version:

| Level | What a paragraph shows | Source |
|---|---|---|
| **Full** | the paragraph as written; key sentences in darker ink | author, verbatim |
| **Brief** | 1–3 of its sentences | author, verbatim (chosen by the model) |
| **Key** | takeaway + one sentence of reason | model, written |
| **Takeaway** | one headline sentence, on an outline with role dots | model, written |
| **Topic** | a noun phrase; the paper becomes a map of section cards | model, written |

Serif text is the author's; sans text is a summary. At every level the words that survive the next zoom-out are darker, and a level change moves each surviving word (and formula) to its new place instead of swapping the text.

## Use

```bash
python -m pip install -r requirements.txt   # beautifulsoup4, lxml, Pillow
python -m textfold serve                    # http://localhost:3017  (ThoughtDAG keeps 3001)
```

The same code is a Windows-only Python package (`pyproject.toml`): `python -m pip wheel . --no-deps` builds it, with
the reader's pages (`textfold/web/`) inside, and `pip install .` gives the `textfold` command. The docs write
`python -m textfold` instead: pip puts that command's own folder (`Scripts\`, under the install or the user's
`%APPDATA%\Python`) where the PATH may not reach, so `textfold` alone is not always found, and `python -m textfold`
always is. Run from a clone, papers are
kept in the clone; installed, in the system's folder for app data (`store.app_data()`, shared with the desktop app).

The landing takes a link or ID (arXiv, PubMed Central, Europe PMC, bioRxiv, medRxiv, a DOI, Wikipedia), or one or more
files (the dashed box under the bar, or dropped anywhere on the page), and a language; a line under the bar names
the sources it reads; the sidebar lists every paper generated so far. Several files go up one at a time, each into the
server's own queue (conversion, then its levels), at most 50 at once; a file already in the library, or the same file
twice in one batch, is not added twice, and the card says what was taken, what waits for a MinerU key, and what
failed; a failed upload or conversion that may pass is offered again. In a paper,
the language menu switches between generated languages, generates a new one, or regenerates the current one.
One language, the reader's (two languages: English, 简体中文 — `langs.LANGS` is the list): the browser's, or the
one last chosen (kept in the browser, `pf-ui-lang`). The
interface speaks it, and a paper is read in it: its text, and the names of its own parts (figures, tables, theorems,
references, equations). A switch of either is a switch of both: the paper's menu at the top right, a language
generated there, Settings, or the two menus of the landing. A paper that has not that language yet opens in one it
has, and the interface stays; nothing is generated unasked but one: an English document is made with its Simplified
Chinese version by default, at the end of the generation of whichever language was asked for (`pipeline.generate`'s
`also_zh`, which the app passes and the command line does not), so an English paper is readable in Chinese without a
second request. A question is answered in the language it is asked in, the interface's when that is unclear.
A translation of any other language, stored before the reader offered only these two, stays on disk but is neither
listed nor read (`store.languages` filters by `langs.LANGS`, and `pipeline.generate` refuses such a language); nothing
deletes it.

Where things are kept: the code in the project (`textfold/`, with the reader's pages in `textfold/web/`); papers and exports in `papers/` and `out/` of the
project, or wherever `TEXTFOLD_DATA` points (`PAPERFOLD_DATA`, its earlier name, is read too); settings and keys in
`~/.textfold/`.

The app is `desktop-mygo/`: a Go/MyGo window around the same Python server, with its own CPython
(python-build-standalone) and packages (the Anthropic SDK among them, which `requirements.txt` leaves optional for a
development checkout but the app's Settings need), so a reader installs nothing. MyGo owns the window, Python
lifecycle, native dialogs, external links and the signed update feed; it does not reimplement the reader or document
pipeline in Go. A copy installed by the old Electron shell cannot consume that feed and is reinstalled once; after
that the app updates itself. The Windows app is built by `.github/workflows/desktop.yml` on a `v*` tag, and the website by
`.github/workflows/site.yml` when that run finishes a release for a `v*` tag, so the page goes up with the installer it
offers rather than on any push to `main`; the PyPI workflow remains parked in `.github/workflows-disabled/` (GitHub runs
only `.github/workflows/`). A tag build needs the `MYGO_UPDATER_PRIVATE_KEY` secret, and stops before it leaves a draft
release without it.

Models (⚙ Settings): the current connection, the default model and its test, plus the OpenRouter one-click entry.
API providers, the questions' model and reasoning, and the MinerU API key and address are under
**Advanced**. TextFold makes model calls through API providers only; it does not scan for or run Claude Code, Codex or Pi
CLI runtimes.

- **Magpie**, an optional external local gateway ([project](https://github.com/yetone/magpie)), is discovered from
  `http://127.0.0.1:3425/v1/models`; model ids are dynamic and labels use `display_name`, then `magpie_label`, then the id.
  `MAGPIE_BASE_URL` overrides the `/v1` base, and `MAGPIE_MODELS` can supply a comma-separated local override. Calls use
  OpenAI-compatible `/chat/completions` with the `magpie` token. TextFold does not install Magpie. It is listed first and
  its first model becomes the default unless Settings selects another available model; a collision resolves to Magpie.
  Probes run in the background with a short-lived cache, so an unavailable gateway does not delay the page or server.
- **OpenRouter in one click**: OAuth with PKCE. The server makes the verifier, OpenRouter returns a code, and the code
  and verifier become a key kept in memory until the reader picks models and saves. Free models are listed first and a
  new connection picks five of them.
- **API providers** include environment and `.env` keys for Zhipu, Qwen, OpenAI, Anthropic, Google, DeepSeek, Kimi and
  OpenRouter, plus Ollama and Magpie as local API gateways. Other services can be added in Settings from presets or as
  custom OpenAI-compatible endpoints. Provider model lists are fetched from `/models`; keys added in Settings stay in
  `~/.textfold/settings.json` (mode 600), outside the project folder. A key the server holds is used only for the
  address it was saved with: a probe or a save that would move a saved key, or the minted OpenRouter key, to another
  base is refused, while a key typed in the request may be tested against any address. A page on another localhost
  port cannot drive a writing POST (when it carries an Origin, its port must be the server's; a request with no Origin
  is a command line or a native client). The OpenRouter return is a GET and is outside that rule.
- **Thinking, per task** is selected by the reader's task settings: `models.DEFAULT_THINKING` sets levels and takeaways
  off, translation off, questions low, and reading cards low. API providers use supported fields: the Claude API's
  thinking and effort by model; OpenAI-compatible APIs use provider-specific fields such as `reasoning`, `thinking`,
  `enable_thinking` or `reasoning_effort`. Magpie reports supported reasoning levels with its dynamic model list.
  If an API refuses a spelling, TextFold tries supported alternatives and then retries without a reasoning field; a
  failure with a level set is retried at the model default and explained in `note`.
- **The home page does not wait on local ports.** Magpie and Ollama probes refresh in the background; the last
  result is returned at once. `provider_list` caches rows for ten seconds, keyed by settings, environment and probe
  results, and `save_settings` clears the cache. A stopped local gateway does not prevent other providers from appearing
  or working.

Command line, without the server:

```bash
python -m textfold 2512.23916 --lang zh              # generate English + Simplified Chinese, then export
python -m textfold export 2512.23916                # one self-contained HTML file in out/<id>/
```

### Is the same paper always the same?

Only because it is stored. The model samples differently on every run, so two generations of one paper differ in
wording, chosen key sentences and topics (Full is the author's text and never changes). Each paper keeps
versioned layers in `papers/<id>/layers/` (`en.json`, `tr-<lang>.json`); the reader is assembled from them with no
model call, so it reads the same every time it is opened. Regenerate writes a new version; a translation built on an
older English version is marked outdated. A translation that came back without a paragraph (a call that failed, one
the model left out) is asked for once more at once; a stored one that still has gaps has them asked for when it is
next generated, or as the app opens that language, the rest kept (`translate.gaps`, `meta.gaps`). Model replies are
also cached by prompt in `papers/<id>/llm-cache/`.

In the page: pinch or Ctrl-scroll zooms around the pointer, scrolling over the level bar or dragging it zooms too,
keys `1`–`5` jump to a level, `-`/`=` step, `L` cycles languages, clicking a paragraph below Full opens just that one,
`Esc` closes it. The zoom is continuous: it can stop half way or turn back, and it lays nothing out while it runs. When
the reader is still, the screen is laid out at each level ahead of time (in a hidden copy, one level per idle moment),
and a zoom plays those keyframes; the page takes over again at rest.

A heading carries its depth in its size: a section's 27px with a rule under it (an inset shadow, so the zoom's copies
carry it, `looks()`), a subsection's 21.5px, the next as large as the serif text (18.5px), the deepest in a lighter ink
(`--ink-2`); at Topic the heading is a card's label (13.5px, no rule; the header of a group of cards is 17px with the
rule, 14.5px and no rule when nested). The sizes scale with `--fs`; a section's margins and padding do too.

The Aa menu beside the language's sets the type for every text in this browser (`localStorage` `textfold.type`): the
size in seven steps from 86% to 135% (the whole column scales with it, so a line holds as many words), the column's
width (narrow, standard, wide, capped so the margins keep the notes their room: `--colw`, `--colmax`) and the font of
the author's words (serif or sans-serif; the written levels stay sans and are told by colour and size). It is CSS's
`--fs`, `html[data-width]` and `html[data-font]`; the zoom's sandbox, whose copy of the sheet rewrites `html[…]` to
`:host(…)`, is given the font, width, hidden margins and size too (`mirrorType`; the size is an inline `--fs`, which
the sandbox's own `:host { --fs: 1 }` would otherwise override), or the last frame of a zoom would sit apart from the
page it gave way to. A printed page is the usual size: the print rule resets `--fs` and the column with `!important`.

The Aa menu also sets the light: light, dark or the system's, and a style (the default, or paper, the warm unbleached
page), two choices that combine — each style has its light and its dark — as `html[data-theme]` and
`html[data-style]`; and the line spacing (tight, standard, loose: `--lh`, which multiplies the line-height of the
levels' text, a section's line and figure captions; a print uses the standard spacing). The app reads the same stored
choice before the reader is built on the landing (`app.js`), so the sidebar and the landing take the chosen brightness
too. The menu also shows or hides a margin: the conversations on the right, the reader's own notes on the left
(`html[data-hide~="asks"]`, `[data-hide~="notes"]`; this fork no longer draws the argument links upstream also had, so
there is no third). Beside it the menu offers focus (`F`, or `Esc` to leave): the top bar, the zoom bar, the sidebar and
the chat move off the page and come back while the pointer is at their edge.

The reader keeps where a text was being read — the paragraph at the reading line and the level, in `localStorage`
`textfold.pos`, for the last 300 texts — and comes back there when the text is opened again without a place in its
link, saying so with a word over the page and offering the beginning; a 2px line under the top bar shows how far in
the text it is. A link that names a place (`#u=`, `#n=`, `#b=`, `#level=`) wins over the stored place.

A Chinese document's folded levels leave out what is not argument: an apparatus line (a contents line, a footnote)
exists only at Full, and a background unit whose takeaway stepped down is read at Brief and Key but not at Takeaway or
Topic. A sentence a page break cut in half is joined at its first word. `ladder.dress` writes the join into the layer
(`glue`); the page is marked `meta.cjk` and only such a page takes these rules, so an English section ends where its
sentences do and shows as before. A translation is read with the base layer's `glue` and with `tn: 0` where the base's
takeaway stepped down (`store.assemble`): the step-down belongs to the section, and the join is the base's words, so
it is copied only into a Chinese translation, and only when the join itself has no kana or hangul (every written form:
halfwidth, the phonetic extensions, hangul jamo). The view is made when a document is read; a generation attaches
layers without it, so nothing of the base is written into `tr-<lang>.json`.

At Topic, a section with sections under it heads a row of their cards (`parent`, `top` for the shallowest, `newrow` for
a section that follows a deeper one), and the choice beside the zoom bar switches Topic between those cards and a map
of the text's outline (`textfold.topicview`, this browser): the title at the left, the top-level sections each a branch
in a colour of its own (their subsections in their parent's colour), each paragraph's topic at a branch's end. The
reader's own notes on the whole paper are drawn above the title in the map's left column (the map covers the page's
margin), and a click opens the note beside that card; the map stays. The map is drawn over the page at rest at Topic
and only then — the page stays under it, so a zoom plays from the cards as ever, the map gone as the zoom starts. A
section folds and unfolds with a click (or "Sections only" folds them all to their sections), and a topic opens its
paragraph at Key.

Notes: select text anywhere (a paragraph at any level, a section's summary or its title) to highlight it, write a note,
or ask the model about it (the answer, in the reading language, cites the paragraphs it rests on; a cite opens that
paragraph to its full text in place). The reader's own notes sit in the left margin, the conversations with the model
in the right. Full and Brief show whole cards, Key shows them compact, and Takeaway and Topic show only a
mark, with the notes on hover. Highlights zoom with the words. `#n=<note id>` opens the reader at a note. A note of the
reader's own can be on the whole text, not a passage (the notes menu's **New note**): it sits by the paper's title, is
shown at every level, and opens beside the head; at Topic it sits under the title, in the column, so a narrow window
or a docked sidebar cannot push it off screen, and with the map shown it is drawn in the map's left column (above the
title) and opens beside that card. It has no quote and no Ask beside it, since the chat is where the whole paper is
asked about, and the chat never treats it as a conversation. A new one is a draft: the words typed are kept when it
closes, even before the 700 ms save timer, and an empty draft is not kept.

What the model is given for a question (`textfold/notes.py`, `prompt`): the title, the abstract and a line per section
(with where the reader is); the level they read at and whose words it shows (at Key and below, a warning that the
selection is the model's wording, not the authors'); the selection and its paragraph in the authors' words (or, for a
section, its summary and each paragraph's point); up to five passages from anywhere in the paper that share the
question's telling words (IDF over the English and the reading-language text; symbols such as D=4 kept whole, CJK
matched by character pairs, question words dropped); the earlier turns; and the paragraphs it may cite. The system
prompt asks it to answer from the paper, say where, and keep general knowledge apart.

The notes button opens the list of every highlight, note and question, by section and filtered by kind: a click flies
to the passage (opening its paragraph in place where the zoom hides it) and opens the note; × deletes it after a
second click, and **New note** writes one on the whole text. Below the list, **More export options…** opens the save dialog. The **Export** button beside the notes
opens a menu with **Export notes (Markdown)** — every highlight, note and question, with the whole-paragraph choice
saved in the dialog — **Export reading card (Markdown)** in the app (the card drawer's own export; a paper without a
card opens the drawer to make one), and **More export options…**, which opens the dialog where every other export is.
The whole text: one HTML file (`POST /api/export`: `build.page` with the notes of the kinds chosen, in the language
being read or all of them; the file opens in that language and keeps its notes apart from any other page's in the
viewer's browser, `D.saved`; with the original PDF if chosen, and PDF.js, so that the file opens the side-by-side view
by itself: `D.pdf`, `D.pdfjs`, and a converted PDF's page map, `D.pdfmap`), or a PDF at the level being read (the
column as it stands, paragraphs opened in place included, every paragraph drawn at that level first, the notes of the
kinds chosen under their paragraphs, the level named on top and the TextFold mark at the end; Ctrl+P prints the same),
or Markdown at the level being read: in the language being read, each heading, the section summaries where the level
shows one (Topic, Takeaway, Key, and Brief in a CJK document), the paragraphs as bullets at the written levels and as
paragraphs at Brief and Full, the marks chosen under their paragraph (a highlight alone in the author's words, `==…==`),
and at Topic an outline that an outliner or a mind-map plugin draws. It is the text's paragraphs, headings and lists:
display equations, figures and tables are not in it.
Only the marks: one small HTML page made in the browser (the passages quoted, or each mark in its whole paragraph if
chosen; the notes, the questions and answers with their citations as labels, formulas as MathML, a link to the source,
the mark), a PDF, Markdown for Obsidian (block ids, callouts, links back) or the notes data (JSON, with `made_by`).
The menu and the dialog both say that TextFold is a tool and that a file shared follows the terms of the original
text; neither judges a license. Where a file goes, the reader chooses: the desktop app's own save dialog
(`Desktop.SaveFile`, through `desktop-mygo/preload.js`), Chrome's file picker, else the
browser's downloads; a PDF through the system's print dialog.
While the file is made (seconds, for a whole text with its PDF), the mark folds and unfolds in place of the dialog's
buttons. A page that is a file (saved, or published) has its mark lead to the repository and ends with it.

The chat (the button in the corner, in the app) asks about the whole paper. Each conversation is a note with
`on: "paper"`; the model is given the abstract, every paragraph's point section by section (at most 60,000
characters: a long paper keeps every section and fewer paragraphs each) and eight passages found for the question.
The answer cites up to five paragraphs; a cite opens its paragraph in place.

**Reading card** (the button at the top of a paper, `textfold/cards.py` and `web/card.js`): a drawer apart from the
document, with four sections — research question and contributions, method and assumptions, data and experimental
setup, results and limitations — of separately editable points. A point may be a found statement, a missing one, one
not applicable with its reason, or one to check; a model point starts unchecked, the reader can mark it checked, and
changing its text or evidence puts it back to check. A generated card is a draft: the document's own units are sent in
parts of about 26,000 characters (with the rows of any table in that part, so a number kept only in a table still has
a caption to cite), each point names one to three units, and the section, block and PDF page of every evidence are
read from the document again rather than trusted from the reply. A point the model marked found with no valid
evidence becomes check. Parts keep their section and evidence mapping; a failed part leaves the others and marks the
card partial. A first complete or partial result becomes the card; a later one is a candidate until the reader merges
or replaces the card with it, or discards it. The document's units, blocks and section metadata are fingerprinted, so
a changed document marks the card for review while a regenerated layer or translation does not; a lost unit or a
quote no longer in the text is shown as broken or mismatched, keeps its excerpt, and can be linked again. Cards live
in the document's own folder (`papers/<id>/card.json`, `docs/reading-card-format.md`), follow it to the trash and back,
and are kept when a PDF is converted again. Without a model the card can still be written by hand; selecting a
passage offers **Add to reading card**. The Markdown export writes the saved card with its states, evidence and
`#u=`/`#b=` links, with no model call.

In the app the mark (in the bar and in the sidebar's rail) leads home; the rail's second button opens the list of
papers. A paper is deleted from the list after a prompt that says what goes with it: its folder (layers, model
replies, notes) moves to `papers/.trash/<id>-<time>/`, with its place in the library (`library.json`: its folder, name
and dates), from where it comes back whole with `POST /api/papers/restore` (the reader's Undo: its folder if that is
still there, its name, its dates). The delete route also takes several at once (`{papers: [ids]}`): the ones being generated stay, and
the answer says which went and which stayed. A paper being generated cannot be deleted. The list is searched (Ctrl+K or /), ordered by kind, by when each document came in or by when it was
last opened, and kept in folders inside one another, a document in one at most: dragged there, or moved from the menu a
right click opens on it. A folder holds folders as deep as the reader makes them: **New folder inside** and **Move up a
level** in its menu, or its head dragged into another (not into itself, nor into one inside it), and a folder's count
takes in the documents in the folders inside it. Deleting a folder moves what is in it, documents and folders, up into
its parent. A document takes a name in the library (right click, **Rename**; its own title written back, or
the field emptied, gives the title again): shown in the list, the page's title and its head, with its own title below;
the search covers it too. Folders, names and dates are in `library.json` beside `papers/` (`library.py`). The format, the contract for every export, is `docs/notes-format.md`; the server keeps notes in
`papers/<id>/notes.json`, a static page in the browser.

Over a paper the sidebar opens from its rail and covers the text. Its pin (`localStorage` `textfold.sbpin`) keeps it
open beside the paper instead, as on the landing, and folds or opens it as there: the page, the zoom bar and a PDF beside
the text start at its edge (`html.app.sb-docked`, which sets `--rail` to the sidebar's width and takes that width out of
the column's cap). A window too narrow for the sidebar and the margins both (`html.sb-narrow`: the width left of the
sidebar under 1248px) has the notes and answers in the column, as beside a PDF, and `layoutSides` stands down.

Several documents are picked to go together: ⌘/Ctrl-click or Shift-click a row (Shift takes every row shown from the
one picked last), **Select** in a row's menu, or ⌘A/Ctrl+A while the list has the focus picks every row shown; Esc lets
go. A bar under the list says how many and moves them into a folder (or a new one named there) or deletes them, and a
picked row dragged carries the others, the pointer showing how many. A delete says what went in the corner and offers it
back for ten seconds (`POST /api/papers/restore`, the folder and dates it came from); deleting the paper being read
takes the page home, and the landing offers the same Undo from `sessionStorage` `textfold.undo`. A delete also says
which picked ones stayed behind: those still being generated (`busy`) and those whose folder could not move to
`papers/.trash` (`failed`).

Links: argument links (supports / builds on / qualifies / explains) were written by a model into English layers before
2026-10-18. Generation no longer calls for them, the reader no longer draws them, and the stored edges stay on disk;
`textfold get` still exports them. A stored link names its units by id; after a parser change those ids can name other
paragraphs, so a regenerated English layer drops the links instead of carrying them over. Author cross-references come
from the parser and stay: hovering a reference previews its target; clicking jumps there and a Back pill returns.

## Other sources: one parser, through semantic HTML

arXiv's LaTeXML page is read by `parse.py`. Every other source is first written as plain semantic HTML (headings,
paragraphs, lists, tables, figures with captions, math, footnotes), and `semantic.normalize` rewrites that HTML in
the shape LaTeXML gives arXiv's pages: sections with titles, `ltx_p` paragraphs, figures and tables with their
captions and labels, equation tables, footnotes inside the text, a references section as a bibliography. So every
source is cut into units by the same code and drawn by the same reader; a new format is a converter to semantic HTML,
nothing more. Text before the first heading becomes an untitled first section with the id `abstract`, so it is the
context every model call is given, as an abstract is.

`normalize` is also where a document is made safe. The reader runs on the local server's origin, so a script in a
file could drive that server: only the elements and attributes a document needs are kept, links only to `#`, http(s)
and mailto, images only as files the import stored. Markdown is rendered with HTML in it shown as text.

Markdown (`markdown.py`): CommonMark with GitHub's tables and strikethrough, footnotes, definition lists, YAML front
matter (title, authors, license) and math, `$...$` and `$$...$$` by Pandoc's rules and `\(...\)`, `\[...\]` as chat
models write them; formulas become MathML with their LaTeX as `alttext`, as LaTeXML writes them. A lone image is a
figure, its caption the paragraph after it ("Figure 1: ...") or its alt text; a "Table 1: ..." paragraph next to a
table is its caption; a numbered heading ("2.1 Methods") keeps its number apart.

A document is stored by `local.py` as a paper is: `papers/md-<title words>-<hash>/` with `source.html` (normalized),
`source.md`, `meta.json` and `img/`, the images copied from beside the file, downloaded, or decoded, once. The id
carries a hash of the text, so the same file opened twice is one paper and an edited file a new one; a stored document
is never rewritten, since its layers belong to the text they were made from. `python -m textfold notes.md` does the same
from the command line (images found beside the file); the landing sends the file's text (`POST /api/import`), so
images given by a relative path are left out there and shown by name.

JATS XML (`jats.py`), the format of PubMed Central, Europe PMC, bioRxiv and medRxiv, PLOS and eLife: sections keep
their titles (and their markup), figures and tables their labels and captions, formulas the MathML the publisher wrote
(its TeX, where given, as alttext), citations and cross-references link to their targets, the reference list becomes the
bibliography. Figures an archive keeps apart (`<floats-group>`) are placed after the paragraph that first cites them.

Europe PMC (`epmc.py`) is where papers beyond arXiv are fetched: a PMC id (an open-access article), a PPR id (a
preprint whose full text it holds: bioRxiv, medRxiv, Research Square and others), any link holding one, or a DOI, looked
up there (`no-fulltext` when it holds no open full text). One request for the XML through its public REST API; figures
from PubMed Central's CDN (the XML names each one's blob in a processing instruction) or, for a preprint, Europe PMC's
file service. Stored as `papers/pmc<n>/` or `papers/ppr<n>/`, with `source.xml`, once. A full text it does not hold
comes back as an HTTP 500, read as `no-fulltext`.

bioRxiv and medRxiv (`biorxiv.py`) are read from the servers themselves: Europe PMC holds the full text of about one
bioRxiv preprint in seventeen. A link or DOI (prefixes 10.1101 and 10.64898) is looked up in their API, which gives each
version's JATS; the newest version whose XML has a body is read (a version just posted carries the abstract alone).
Their XML draws tables and display formulas as pictures, shown as such; a formula pictured inside a line stays in it
(`pf-inline`, an atom). Figures are served under their HighWire ids (`F1.large.jpg`), other pictures from the site's
`embed/` folder. Every request to www.biorxiv.org and www.medrxiv.org waits seven seconds after the last, as their
robots.txt asks (faster, their firewall blocks the reader's address for a while), so a paper with many pictures takes a
minute or two; the job's progress counts them. Stored as `papers/biorxiv-<DOI suffix>/` or `papers/medrxiv-…/`. When a site
still turns this computer away (HTTP 403 for the XML), the preprint is read from Europe PMC if it holds the full text,
under the same id; else the job says so.

Wikipedia (`wiki.py`), any language edition: the title is resolved by the Action API (redirects followed to the article
itself) and the article's Parsoid HTML read from the MediaWiki REST API; a Chinese article is asked for in zh-cn, since
its source mixes scripts and leaves the words it must not convert empty until it is converted. Left out: infoboxes,
navigation boxes and sidebars, hatnotes, maintenance notices, inline icons, layout tables, and the sections that only
list links ("See also", "External links", "Further reading", in the larger editions' words). Links to other articles
are read as their words, so the model can rephrase and translate them; a formula keeps its MathML (its TeX without
Wikipedia's `{\displaystyle …}` as alttext), and one alone in its line is a display formula; the reference lists
become one bibliography the marks [1] point into. Stored as `papers/wiki-<language>-<page id>/` with the revision read and
the day it was read (`snapshot`, shown under the title and carried into the notes' exports: the article may have changed
since), under CC BY-SA 4.0.

The model is still told it reads a paper. A document written in Chinese (or Japanese kana) is read with levels in its
own language, written to character budgets; another language is read with English levels over its own text. Making the
levels in every document's own language is the next step.

## PDFs and web pages

A PDF dropped on the landing goes directly to MinerU Cloud API (`take_pdf` in `server.py`). No browser code reads its
text, no arXiv id or DOI changes the route, and no online paper or local text parser takes precedence. Without
`mineru_api_key`, the server answers `needs-mineru-key` with HTTP 409 and removes the refused upload. With a key, the
file is uploaded to the MinerU API base, read there, and its zip (`*_content_list_v2.json`, `images/`) written into the
same `structured_content.json` the reader consumes (boxes from 0-1000 to 0-1; tiers mapped to `pipeline`/`vlm`; a PDF
with no text read once more with OCR). The base is `https://mineru.net/api/v4` unless `mineru_api_url` names another
v4-compatible address: http or https, a host, no query, fragment or sign-in, and the trailing `/` stripped. A saved
address that cannot be used fails the conversion with `bad-mineru-url` rather than quietly sending the file to the
official service, and one conversion keeps the base it started with. Only v4-compatible endpoints are supported; the
self-hosted `mineru-kit` API is v1 and is not reached by this setting. Fast is MinerU's pipeline tier; accurate is its
vision model. The landing's batch card and the MinerU settings state its limits: at most 600 pages per file, and a
priority quota of 2,000 pages a day. PDFium
(`pypdfium2`) remains only to cut figures from the original page using MinerU's boxes. A PDF imported before this
change opens from its stored result. The document leaves this computer for conversion at the address in the setting.
`pdfdoc.py` turns `structured_content.json` into the document: running heads and page numbers out, the title from the
page or the file, heading depth from numbering, a figure's panels grouped under the caption that names it, figures from
after the references put before them, short front matter dropped.

A conversion keeps `_mineru.json` in its output folder: the batch's id, whether the file reached it, the pass (1, or
the OCR pass 2) and the stage. A lost connection is retried on the same batch — the polls, the signed upload and the
download have their own tries, and a stop ends the job — and an attempt that still cannot reach the service raises
`engine.Resumable`; the conversion queue keeps its output folder then, where a refusal removes it. Importing the same
file again — or converting it again — continues that batch, because a document's id is the hash of its bytes and its
upload and output folders are named after it. The file is sent again only when the API no longer has the task (-60012),
when it reports the batch has no file (-60011), when the signed upload URL refuses it, or when the batch still has no
file after a lost upload. The state holds no key and no signed URL, and a file whose bytes changed starts from the
beginning.

Other files take the same entry (`POST /api/files`, `take_file`; `doc-<file hash>`, the file kept as `original.<ext>`).
New imports of RTF, OpenDocument (.odt, .ods, .odp) and old Office files (.doc, .ppt, .xls) are refused with
`legacy-format`, in the server and before the picker offers them. Those kinds stay in `engine.FILES` so a document
converted before the rule still opens. TextFold reads the common kinds itself, at once (`office.py`):
.docx through mammoth, its formulas turned from OMML into LaTeX first (`omml.py`, written for what latex2mathml and
KaTeX both read); .pptx, .xlsx and .epub from their own XML; .csv and .tsv; and a saved page's article (.html, .mhtml,
its pictures from inside the file). It writes the engine's shape (`structured_content.json` and `images/`), so
`pdfdoc.py` stores both alike; a file whose structure is its own keeps its headings' depths, its captions and its
notes. Pictures use MinerU's API. OFD and TIFF are no longer accepted as new imports because their only reader was the
removed local MinerU engine; existing documents are not deleted.

The server has two queues (`Jobs`): generation (model calls) and conversion (MinerU API calls), each one job at a
time; a conversion's `next` is the generation that follows it. A converted PDF opens as soon as it is stored.

Any other link is a web page (`webpage.py`): fetched with TextFold's own user agent, its hidden elements removed (they
are where text meant for a model is put), its article taken out by trafilatura as Markdown and stored through the
Markdown path. Too little text (`web-notext`), a refusal (`web-blocked`), and a link to a PDF (fetched, then read as a
dropped PDF) each have their own answer.

A Zotero library (`zotero.py`): **Zotero library**, under the landing's drop zone and at the foot of the sidebar,
opens the library chosen (the reader's own, or a group) as Zotero shows it, its collections at the left and the items
of the one chosen at the right, through Zotero Desktop's local API (`localhost:23119`, read only, on once the reader
allows other applications to talk to Zotero). `POST /api/zotero/read` reads an item by the best text it has: its file
first (a PDF, an EPUB, a saved page, a Word DOCX), where Zotero says it is or in its `storage/`, given to `take_file`
as a dropped file is; else its arXiv paper or DOI, handed back to the page to generate as a pasted link is. A
legacy-only attachment (RTF, OpenDocument, old Office) comes after the online references and is refused by
`take_file`, which shows its message. A stored file wins even when the item also names an arXiv paper or DOI. A file is
read only when it is one TextFold reads (a PDF by its first bytes, any other by its name), and a file name that leaves
`storage/` is not followed. `zotero.json`, in the data folder,
says which item became which document, so the library marks what is open, and keeps the item's record: a document read
from the item's own file takes Zotero's title, authors, date, DOI and citekey (`zotero.apply`, once it is stored), and
lists among the papers. The page may change the library chosen and
nothing else: Zotero's address and data folder (`"zotero": {"base", "data_dir"}`) are set in the settings file only.
`tests/test_zotero.py` runs it all against a fake Zotero.

`TEXTFOLD_NO_MODELS=1` makes a server find no model at all (no API provider), and `llm.call` refuses to ask one
whatever spec is handed to it — a test's, a direct caller's: for test servers and CI, so that nothing calls a model
by accident. A reply already kept on disk is still read when the caller passes a spec; a call naming a model id is
refused at resolution before the cache is consulted, and a `force` call is refused. Without a model a document is
still fetched and parsed, and reads as written.

## No other server

A page asks no other server for anything: no font service, no CDN. The fonts (Inter, Source Serif 4, as woff2 subsets)
and KaTeX live in `textfold/web/vendor/`. The app serves them from `/static/vendor/`; a single exported file carries the
Latin faces inside, and KaTeX too when the model wrote math that
matches no formula of the paper. (Loading Google Fonts sends a visitor's IP address to Google, which a German court
found unlawful without consent in 2022.)

## Smoothness is a rule

No change may make the zoom less smooth. Measure before and after with the GPU at 2x pixels, reading the frames the
screen actually showed, on a dense paper (2512.23916):

```bash
python -m textfold export 2512.23916
python tools/zoombench.py 2512.23916                 # out/compare/<id>/<version>.html pages
```

The tool drives Windows' Direct3D 11 backend (`--use-angle=d3d11`) and needs `playwright` and an exported page under
`out/compare/`, so on a machine without them the axis stays **unmeasured** — say so, never "no impact on performance".
Its numbers are Windows numbers and cannot be compared with the Metal ones recorded before this fork went
Windows-only.

Frame intervals from requestAnimationFrame in a default headless browser hide most of what a reader feels.

## Layout

```
textfold/fetch.py    arXiv HTML + metadata, figure images
textfold/parse.py    LaTeXML → units (paragraph, list item, caption) as token streams; math, citations, refs stay atomic
textfold/latexml_safe.py  what an arXiv page may carry into the reader: scripts, handlers and script URLs out, figures kept
textfold/semantic.py any semantic HTML → the HTML parse.py reads; the sanitizing boundary
textfold/markdown.py a Markdown file → semantic HTML (front matter, footnotes, math)
textfold/local.py    documents from this computer: stored as papers (md-…), with their images
textfold/jats.py     JATS XML → semantic HTML (PubMed Central, Europe PMC, bioRxiv, PLOS, eLife)
textfold/epmc.py     papers from Europe PMC by PMC or PPR id, link or DOI (pmc…, ppr…)
textfold/biorxiv.py  preprints from bioRxiv and medRxiv, from their own JATS (biorxiv-…, medrxiv-…)
textfold/wiki.py     Wikipedia articles, any language edition (wiki-<lang>-<page id>)
textfold/github.py   a GitHub repository's README (gh-<owner>--<repo>)
textfold/webpage.py  any other web page: its article (trafilatura), hidden text removed first (web-<host>-<hash>)
textfold/engine.py   MinerU Cloud API only: upload, poll, unpack; pypdfium2 crops figures from MinerU's boxes
textfold/pdfdoc.py   a converted PDF as a document: MinerU's structured output into Markdown and HTML (pdf-<file hash>;
                     another file, doc-<file hash>)
textfold/office.py   Word, PowerPoint, Excel, CSV, EPUB and saved web pages read without the engine, in its shape
textfold/omml.py     Office's formulas (OMML) as LaTeX
textfold/pdf.py      a paper's original PDF for the side-by-side view (source.pdf)
textfold/zotero.py   a Zotero library through Zotero Desktop's local API; an item read as a link or a dropped file
textfold/tokens.py   tokenizer, sentence splitter (English .?! and Chinese 。！？), LCS alignment
textfold/ladder.py   one model call per section; validation; written words aligned to source words for the morph; a
                     Chinese document's character budgets, apparatus and background, and the page-break glue
textfold/links.py    argument links; generation stopped calling it (2026-10), the reader no longer draws stored links
textfold/translate.py  a language the reader offers: sentence-aligned translation + short levels, one call per section (langs.py: English and Simplified Chinese)
textfold/store.py    versioned layers per paper; assembling a reader from them
textfold/pipeline.py fetch → parse → English ladder (once) → translation, with progress
textfold/server.py   local server: pages, /api/papers, /api/jobs (and /api/jobs/stop), /api/generate, /api/card, /api/settings
textfold/providers.py API providers: environment registry, presets, dynamic Magpie and /models probing
textfold/models.py   API model catalog; settings; resolving a model id
textfold/openrouter.py  OpenRouter one-click authorization (OAuth PKCE)
textfold/llm.py     cached API model calls; llm_openai.py: OpenAI-compatible endpoints
textfold/build.py    reader pages: app mode (served) and static mode (one file)
textfold/library.py  the sidebar's library: folders inside one another, the names given documents, when each came in and was last opened (library.json)
textfold/notes.py    the reader's notes (docs/notes-format.md) and questions answered by the model
textfold/cards.py    a document's reading card (docs/reading-card-format.md): evidence, candidates, staleness, Markdown
textfold/fold.py     the TextFold format (docs/format.md) and a document at one level as Markdown (python -m textfold get)
textfold/web/   reader.js (render + FLIP morph), card.js/card.css (the reading card drawer), app.js (sidebar, landing,
                settings, jobs), i18n.js, CSS, templates
tests/          python -m unittest discover tests: the arXiv page's safety pass, the Zotero library (a fake Zotero),
                API providers, OpenRouter's authorisation, and a Windows child process without a console window
desktop-mygo/  the app (its README): Go/MyGo window around the same Python server, native dialogs, lifecycle and signed updates
tools/zoombench.py  zoom smoothness as the screen sees it (Windows' d3d11 GPU backend, 2x, Chrome's frame trace), on
                out/compare/<id>/ pages; needs playwright and an exported page
```

Atoms (formulas, citations, cross-references, footnotes) are numbered in reading order, and the stored layers name
them by number. A parser change that reads more of a page (description lists, October 2026) renumbers every atom after
the new ones, so a paper generated before it needs its layers made again, or its atom numbers mapped from the old parse
to the new one by content and order.

Sentences are numbered the same way: a layer's `evidence`, a translation's sentence ranges and a card's evidence name
a sentence by its place in the unit's parsed sentences, not by its text. The October 2026 splitter change (Chinese
`。！？`) therefore reinterprets stored Chinese layers: an evidence `[0]` that meant the whole paragraph now means its
first sentence, which is the Brief they were meant to show; a translation stored before it keeps that paragraph as one
sentence until it is made again. A paragraph written in Chinese or Japanese kana is never cut into parts, so a Chinese
paragraph that was one unit keeps its id and the later ids do not move; a paragraph that mixes Chinese and English can
still change its part count, because the sentence count it is cut by has changed. An ordinal past the end of a part
is dropped when the layer is applied, and the first sentence stands in. A unit with no CJK character and no `。！？`
takes the older splitter, so its sentence numbers and parts do not move; in a unit with CJK, a closing quote, bracket
or brace glued to a stop (a run such as `.")` stays with its sentence) and an ASCII stop beside a CJK character also
end a sentence; a number and its stop at the head of a CJK sentence (`1.研究背景`) end no sentence, so a layer made
before that guard can have an ordinal that still fits a shorter sentence list and now points at another sentence.

A generated layer may also carry `glue` (the half of a sentence a page break left in the unit before it). An older
layer has no `glue` and is read as it was; a translation is shown with the base's `glue` and with `tn: 0` when the
base's takeaway stepped down, made when the document is read and not written into the translation's file. A layer from
before the document gate may carry `l3: false`, which nothing reads now (a stepped-down unit has an empty takeaway
instead). A unit with no written levels at all (an apparatus
line) has `ev: []` and stays at Full.

A layer also keeps `h`, a fingerprint of each unit: its words and the atoms it names (an atom's id and visible text).
A unit is keyed by id, and a parser change can leave the same id naming a different part (the mixed paragraph above)
or renumber its atoms, so `apply_en` reads a unit whose fingerprint no longer matches with its local levels, and the
reader reports the base stale; a translation of that base is reported stale too. A layer written before `h` is
trusted only when its unit ids are exactly this parse's; a different set means some id may have moved, so its units
are read local and the layer is stale. Regenerating replaces the layer and clears it.

Every text file TextFold itself reads or writes names UTF-8, whatever the computer's locale: model replies in
`llm.py`, layers in `store.write`, notes in `notes.py`, settings in `models.py`, a paper's `source.html` and
`meta.json`, the library, the Zotero index and the reader's web assets. Its own files are read through
`store.read_text`: UTF-8 first (a byte-order mark, as Notepad writes, is read as UTF-8 and dropped), else the system's
codepage — GBK on a Chinese Windows, which is what an older TextFold wrote there. The read writes nothing; the file's
next save writes UTF-8. A file in neither encoding is an error, never replacement text that a save could then persist.
The exceptions are the ones with a marker
or a rebuild: a stored web address is read by `store.read_url` (it carries a byte-order mark), and the model's reply
cache is ASCII-only (a non-ASCII cache is a miss and is made again). The system's codepage is `store.codepage()`, from
`locale.getencoding()` or, before Python 3.11, Windows' ANSI code page: `locale.getpreferredencoding()` returns UTF-8
under the UTF-8 mode the app runs in, so it cannot stand for the encoding an old file was written in. An imported Markdown file
is decoded as UTF-8 first, then GBK, then the system's codepage, then UTF-8 with stand-ins; the command line's import path does this,
while a file dropped on the landing page is decoded by the browser before it is sent. Text from elsewhere — an HTML
page, an SVG, an Office file — is decoded by its declaration or, where it names none, by the local codepage; that is
the content's rule, not TextFold's. On the command line, stdout and stderr speak UTF-8 as well. Document metadata and library JSON are ASCII-escaped, so a reader with any encoding sees plain ASCII: titles
and folder names may contain characters absent from GBK. Stored web addresses use a UTF-8 byte-order mark so earlier
text can still be read correctly; exported pages and CLI output use UTF-8 as well.

Layers, notes, cards, the library, the Zotero index and a kept PDF are written whole or not at all
(`store.write_text_atomic`, `store.write_bytes_atomic`): a temporary file of its own beside the file, flushed to the
disk, then moved over it. A crash leaves the old file; the app and `textfold serve` may share a data folder and write one
file at once, and neither writes into the other's temporary file nor moves it away, so the file is one of the two, never
their mixture. Every read-modify-write of the reader's own files — the library, the notes, a card and the Zotero
index — is serialized across processes by a lock byte in a lock file in the data folder (`library.lock`, `notes.lock`,
`cards.lock`, `zotero.lock`; the files stay, and the OS releases the byte when a process ends), so one process's save
cannot drop another's folder or name, note, card edit or Zotero link. The lock files stay out of `papers/`, whose
folders move to the trash. A re-conversion of a PDF holds the `papers` lock and the notes' and card's locks for its
whole document write — it snapshots those files, rebuilds the folder and copies them back — so a save made during it
waits for the rebuilt document and lands in it rather than being overwritten by the snapshot's copy, and a trash or an
Undo in another process waits for the rebuild, as does a layer save or an import (`local.store_doc`) — the last writes
into a temporary folder of its own (`tempfile.mkdtemp`), never a fixed name two writers share. The `papers` lock is
one file for all documents: a conversion or a slow import of any document makes another document's trash, Undo, layer
save or import wait up to 60 s and then fail, and a layer save waits while holding `store.LOCK`, so card saves and the
trash in that process wait behind it too. The move to the trash is serialized within one process (the server holds
`store.LOCK` while the library forgets the document and the folder moves) and, across processes, by the same `papers`
lock; a save crossing it either travels with the folder or fails loudly, and the library's forget-and-move is still
not atomic against another process's library write. A `library.json` that cannot be trusted is neither read as an
empty library nor saved over: not JSON at all, a top level that is not an object, or a `folders`, `of`, `names`,
`added` or `opened` field that is not the container the library writes.
Its bytes are copied to `library.json.corrupt-<time>` and the read fails (`library.LibraryError`, answered as a 500
carrying its message). A bad row inside a good list or object is dropped instead (a folder entry without a name, a date
that is not a date). An empty file is an empty library; a file in neither encoding still fails with
`UnicodeDecodeError`, as it did, and is not copied. A card save also names the revision it was composed against
(`rev`), so a save that lost a race is refused rather than written over a newer card. A note, a card, a PDF or a layer
does not create the document's folder as it is written: a save that crosses the move to the trash fails instead of
leaving a ghost folder that keeps the Undo from finding the trashed one, and a re-conversion of a document already in
the trash fails rather than making the folder again.
