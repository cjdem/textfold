<div align="center">

<img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/logo.svg" width="72" alt="TextFold">

# TextFold

**Fold any text, from a one-screen map to every word**

<sub>Formerly PaperFold</sub>

> **This is a fork.** TextFold was created by Xia Chen. This fork is maintained by cjdem and is
> not affiliated with or endorsed by the original author. It is Windows-only: the desktop app
> replaces the Electron shell with MyGo, and the app and the Python package send every PDF and
> picture to MinerU's Cloud API, so the local PDF engine is gone. See [NOTICE](NOTICE) for the
> attribution and changes.

<img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-6B5CE7?style=flat-square">
<img alt="Runs on your computer" src="https://img.shields.io/badge/runs-on_your_computer-E08A3C?style=flat-square">
<a href="LICENSE"><img alt="Apache License 2.0" src="https://img.shields.io/badge/license-Apache_2.0-6B5CE7?style=flat-square"></a>

**English** · [简体中文](README.zh-CN.md)

**Paste a link:** any web page · arXiv · PubMed Central · bioRxiv · medRxiv · Wikipedia · GitHub<br>
**Drop one or more files:** PDF · Word · PowerPoint · Excel · EPUB · HTML · CSV · pictures · Markdown · text

**[Download the app ↓](#get-started)** · [What's new ↓](#whats-new)

<br>

<img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/zoom.gif" width="880" alt="A paper folding from its full text into a map of its sections, and back">

</div>

## Read with less in your head

Choose the level of detail you need, and lower your cognitive load.

| | Level | Each paragraph becomes | In whose words |
|:-:|---|---|---|
| **1** | **Full** | the paragraph as written | the author's |
| **2** | **Brief** | its one to three key sentences, verbatim | the author's |
| **3** | **Key** | its point and the reason for it | AI, resting on the Brief sentences |
| **4** | **Takeaway** | one line on the spine of its section | AI |
| **5** | **Topic** | a few words; the text becomes a map of section cards | AI |

## What you get

- **Words that travel.** As you zoom, every word that stays slides to its new place and the rest fade around it.
- **Zoom under your fingers.** Stop halfway, turn back, or open one paragraph alone.
- **Make the page yours.** Aa sets the size, width and font, light or dark, a paper or plain style, line spacing, and which margins show. `F` dims everything but the paragraph you are on, and the place you left is kept.

- **Beside the original.** Open a paper's or a PDF's own pages next to the text, each paragraph shown where it stands on its page.
- **Ask AI about exactly what you read.** Select a passage, or ask about the whole text. The answer comes structured: the short answer first, then the evidence, each point citing the paragraph it rests on, one click away.
- **Notes that zoom with the text.** Highlight and write in the margin; what you marked stays as you zoom out, and is saved with the page.
- **A reading card you can keep.** Four sections — the question, the method, the setup and the results — with every point editable and linked back to the passage it came from. A new draft waits beside the card instead of replacing what you wrote.
- **The whole text as a map.** At Topic, choose Map beside the zoom bar and its sections become a mind map; a note on the whole paper sits in its left column.

- **Your language.** English and Simplified Chinese, translated sentence by sentence, with every formula as typeset.

- **Your library, in order.** Search it with Ctrl+K, keep documents in nested folders (drag one in, or right-click it), select several to move or delete, keep a delete reversible for ten seconds, name a document, and list it by kind, when it came in, or when you last opened it.

<table>
<tr>
<td width="50%"><img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/notes.png" alt="Highlights in the full text and a note in the margin"></td>
<td width="50%"><img src="https://raw.githubusercontent.com/cjdem/textfold/main/docs/assets/keep.png" alt="The highlighted passages kept at the Takeaway level"></td>
</tr>
<tr>
<td align="center"><sub>Highlight and write in the margin…</sub></td>
<td align="center"><sub>…and keep what you marked as you zoom out.</sub></td>
</tr>
</table>

## Works on your Zotero

Click **Zotero library**, under the drop zone, and your library is there as Zotero shows it: your collections, your group libraries, a search. **Read** opens any item.

- **An item on arXiv** opens from arXiv. Any other opens from its PDF, with the PDF beside the text, or from the EPUB, saved web page or Word (DOCX) file it holds. An item with only a DOI opens from Europe PMC. An old Word, PowerPoint or Excel attachment is no longer imported: the item tries its DOI first, then says the format is no longer supported.
- **It keeps what you entered in Zotero:** the title, the authors and the citekey.
- **It stays on your computer.** TextFold asks the Zotero app you already run, the way citation plugins do: no account, no key, nothing sent to Zotero's servers, and nothing in your library changed.

To turn it on, in Zotero 7: **Settings › Advanced › Allow other applications on this computer to communicate with Zotero**.

## Get started

**[Download the app](https://cjdem.github.io/textfold/#download)** for Windows. Everything it needs is inside, Python included; the one exception is WebView2, which Windows 11 already has and Windows 10 may ask for.

Or install the Python package from this fork, on Windows:

```bash
python -m pip install git+https://github.com/cjdem/textfold
python -m textfold serve
```

Open `http://localhost:3017`. The first time, [connect a model](#connect-a-model); then paste a link or drop one or more files, and pick a language. You need Python 3.9 or newer on Windows.

| Paste or drop | What TextFold reads |
|---|---|
| A paper's link or DOI: arXiv, PubMed Central, bioRxiv, medRxiv | its text as the site structures it (an arXiv paper without an HTML version is read from its PDF; another DOI needs an open full text in Europe PMC) |
| Any other web page | its article, without the menus, the adverts, or the text it hides from its readers |
| A Wikipedia article, a GitHub repository | the article; the README, with its pictures |
| A PDF | its text and structure, always through MinerU's Cloud API; the original stays beside it for the side-by-side view |
| A Word (DOCX), PowerPoint (PPTX) or Excel (XLSX) file, a CSV, an EPUB, a saved web page | the document with its headings, tables, pictures and formulas: common Word, Excel, CSV, EPUB and HTML files are read on your computer |
| A picture | its text, read by MinerU's Cloud API |
| An item of your Zotero library | its arXiv paper, else its PDF or other file, else its DOI. [Works on your Zotero ↑](#works-on-your-zotero) |
| A Markdown or text file | the file as written |

Every PDF and picture is uploaded to MinerU's Cloud API. Add a key under **Settings › Advanced › MinerU API**. The key is kept in `~/.textfold/settings.json` and is never sent back to the page. The API address in the same section can be changed for a v4-compatible service; the official address is the default, and files and the key go to the address you set. Nothing is installed locally and there is no offline PDF fallback. Common Word, PowerPoint, Excel, EPUB, CSV and HTML files stay on your computer.

New RTF, OpenDocument (.odt, .ods, .odp) and old Word, PowerPoint or Excel files (.doc, .ppt, .xls) are no longer accepted: save them as DOCX, PPTX, XLSX or PDF first. Documents already in the library keep opening, and their generated levels stay.

New OFD and TIFF files are also refused after the local MinerU engine was removed. Documents already in the library remain readable.

What you read is kept in your system's folder for app data, shared with the desktop app.

<details>
<summary>Run it from the code instead</summary>

```bash
git clone https://github.com/cjdem/textfold.git
cd textfold
python -m pip install -r requirements.txt
python -m textfold serve
```

What you read is then kept in the clone.

</details>

## Connect a model

TextFold sends every model request to an API provider. It does not run a coding agent, a CLI or a local bridge. If the optional [Magpie gateway](https://github.com/yetone/magpie) is already running on your computer, TextFold discovers its models from `http://127.0.0.1:3425/v1/models` and lists them first; Magpie stays an external service and is not installed by TextFold. Its model IDs are read dynamically. A model you already chose, if still available, stays selected; otherwise the first Magpie model becomes the default.

| You have | What to do |
|---|---|
| Magpie running locally | Nothing. TextFold connects to its OpenAI-compatible API and lists the models Magpie reports. |
| Nothing yet | Click **OpenRouter in one click · free models**. Authorize once, and free models are ready. |
| An API key | **Settings › Advanced settings › API providers › Add provider**, then pick a provider: OpenRouter, Anthropic, OpenAI, DeepSeek, Google AI Studio, Z.ai GLM or 智谱 GLM, GLM Coding Plan, Kimi Code, Moonshot, MiniMax, Ollama, Magpie, or **Custom** for any OpenAI-compatible endpoint. |

The Anthropic API is spoken through its official SDK: the Windows app includes it, and a copy run from source needs `pip install anthropic`. Keys stay in `~/.textfold/settings.json` and are never sent back to the page.

If Magpie is unavailable, TextFold uses the other available providers. Your questions can go to a stronger model than the one that writes the levels: **Settings › Advanced settings › Answering questions**, with its **Reasoning** level.

## In the reader

| Do | To |
|---|---|
| Pinch, or Ctrl + scroll | zoom around the pointer |
| `1` to `5` | jump to a level |
| **Aa**, at the top | size, width and font; light or dark, style, line spacing, margins |
| `F` | focus on the paragraph being read |
| Click a paragraph | open just that paragraph |
| Click a figure | see it enlarged |
| **Original**, at the top | read beside the paper's PDF |
| **Export**, at the top | your notes or the reading card as Markdown; more formats and the whole page in the dialog |
| **Reading card**, at the top | keep the four questions a paper answers, with evidence back to the text |
| **Cards / Map**, beside the zoom bar | show the Topic level as cards, or as a mind map |
| **Pin**, in the sidebar | keep the library open beside the text |
| Select text | highlight, write a note, or ask |
| **Ask the paper**, bottom right | ask about the whole text |
| `L` | next language |
| `Ctrl+K` or `/` | search your library |

## Export

**Export**, at the top of the reader, opens the two everyday files directly: your notes as Markdown, and the reading card as Markdown. **More export options…** opens the save dialog: the whole text at the level you are reading, as one HTML file that opens anywhere without a server (with the notes you choose and, if you like, its original PDF to read beside it), as PDF, Markdown or JSON, or only your notes as a page, a PDF, Markdown for Obsidian or JSON.

TextFold is a tool, and its license covers its code. When you share a file, follow the terms of the original text, shown under its title.

## What's new

> The entries before this fork's October 21 changes are the original project's history; this
> fork's changes are in [docs/changes/](docs/changes/). The original project's macOS app is not
> part of this fork.

- **October 23, 2026: a PDF import picks up where it stopped.** If the connection to MinerU drops while it reads a PDF, importing the same file again continues the same batch instead of uploading and parsing it again; a new batch is submitted only when the service no longer has the task or the batch never received the file.
- **October 23, 2026: two windows no longer overwrite each other.** Notes, reading cards and the Zotero index take a cross-process lock for every save, and library files are written whole or not at all; a note or card save, a generation, a re-conversion and a move to the trash cannot overwrite each other, and a deleted document is not recreated by a late save or conversion.
- **October 23, 2026: the reader and the library, tuned.** The Aa menu sets size, width and font; light or dark, a paper style, line spacing, focus (F), the place you left, a pinned sidebar, margins, a heading scale and the Topic map. The library gets nested folders, multi-select, a ten-second Undo and names for documents; the whole-paper note stays in the Topic map's left column, and the whole text exports as Markdown at the level being read.
- **October 22, 2026: the ChatGPT plan entry is gone.** TextFold no longer runs a local bridge or uses a ChatGPT subscription. Connect an API key, OpenRouter, or the Magpie gateway instead.
- **October 18, 2026: a reading card for every paper.** **Reading card**, at the top of a paper, keeps what it asks and contributes, how it works, what it measured and what it found, in four sections you can edit. Every point links back to the passage; a new draft waits as a candidate, and the card exports to Markdown.
- **October 21, 2026: PDFs use MinerU's Cloud API only.** Every PDF now goes directly to MinerU, without first reading its text or looking for an online version. The local 3.4 GB engine and the offline PDF path are gone. Add a key in Settings; PDFs and pictures leave your computer for conversion.
- **October 17, 2026: MinerU's servers read your files.** Put `mineru_api_key` in `~/.textfold/settings.json` and PDFs, Word/PowerPoint/Excel files, HTML and pictures are read by MinerU's cloud API: no 3.4 GB engine to install, and the file leaves your computer.
- **October 17, 2026: English documents come with their Simplified Chinese.** An English document opened in the app is made with its Simplified Chinese version at the end of the same generation, so it reads in Chinese without a second request.
- **October 15, 2026: PDFs open without the engine.** A PDF with its own text, as most papers have, opens at once, its figures cut from the page; only a scan still needs the PDF engine. An arXiv paper with no HTML version is read from its PDF. Thanks to [@sylvainHellin](https://github.com/sylvainHellin).
- **October 15, 2026: your library, and your questions.** Search the library, keep documents in folders, and list them by when they came in or were last opened. A question has its own send and stop, any turn of a conversation can be deleted, and questions can go to a stronger model than the one that writes the levels. Thanks to [@suhyungJang](https://github.com/suhyungJang).
- **October 14, 2026: an app for Mac and Windows.** Download TextFold for macOS (Apple silicon or Intel, signed and notarized by Apple) or Windows, with everything it needs inside. The desktop app updates itself when you say so. [Download ↓](#get-started)

<details>
<summary>Earlier</summary>

- **October 14, 2026: your Zotero library.** **Zotero library**, under the drop zone, shows your library and its collections as Zotero does, and opens any item in a click: from arXiv when it is there, else from its own PDF. Thanks to [@adalach](https://github.com/adalach). [Works on your Zotero ↑](#works-on-your-zotero)
- **October 14, 2026: arXiv pages, read more safely.** What could run script in a page is taken out before the reader draws it, and its figures stay as they were. Thanks to [@neil-patel77](https://github.com/neil-patel77).
- **October 13, 2026: save a page as one file.** **Export**, at the top of the reader, opens the export menu; **More export options…** opens the save dialog: the page as one HTML file, with your notes and its original PDF if you like, or only your notes. [Export ↓](#export)
- **October 13, 2026: Word, PowerPoint, Excel, e-books and more.** Drop a Word, PowerPoint or Excel file, a CSV, an EPUB or a saved web page, and it opens at once, formulas included, with nothing more to install.
- **October 13, 2026: whole figures, and a guide.** A figure the PDF engine cut into pieces now comes out whole, cut from its page. A short guide opens on your first visit, and again from **How it works**.
- **October 9, 2026: PaperFold is now TextFold.** The same reader, named for everything it folds: papers, web pages, PDFs and READMEs. Links to the old repository lead here, and your settings move over by themselves.
- **October 9, 2026: any web page, and PDFs.** Paste any web page's link and read its article at five levels, without the text the page hides from its readers. Drop a PDF: when it names a paper that can be read online, that version opens with your PDF beside it; any other PDF is converted on your computer.
- **October 8, 2026: any GitHub README.** Paste a repository's link and read its README at five levels, with its logo, badges and GIFs as on GitHub.
- **October 8, 2026: read beside the original.** **Original**, at the top of a paper, opens its PDF at the left and shows each paragraph on its page as you read. A new paper opens as soon as it can be read, while its levels are written.
- **October 6, 2026: more than arXiv.** PubMed Central, bioRxiv, medRxiv, Wikipedia in any language, and your own Markdown files.

</details>

<br>

## Original project's contributors

<a href="https://github.com/neil-patel77" title="@neil-patel77"><img src="https://github.com/neil-patel77.png?size=80" width="40" height="40" alt="@neil-patel77" /></a>
<a href="https://github.com/adalach" title="@adalach"><img src="https://github.com/adalach.png?size=80" width="40" height="40" alt="@adalach" /></a>
<a href="https://github.com/suhyungJang" title="@suhyungJang"><img src="https://github.com/suhyungJang.png?size=80" width="40" height="40" alt="@suhyungJang" /></a>
<a href="https://github.com/sylvainHellin" title="@sylvainHellin"><img src="https://github.com/sylvainHellin.png?size=80" width="40" height="40" alt="@sylvainHellin" /></a>
<a href="https://github.com/jlamweil" title="@jlamweil"><img src="https://github.com/jlamweil.png?size=80" width="40" height="40" alt="@jlamweil" /></a>

This fork is maintained by [cjdem](https://github.com/cjdem). Contributions are welcome: start with [CONTRIBUTING.md](CONTRIBUTING.md).

<br>

<div align="center">

**If TextFold helps you read, ⭐ [star it](https://github.com/cjdem/textfold) so others can find it.**

</div>

---

<div align="center">

<sub>Built on [trafilatura](https://github.com/adbar/trafilatura), which finds the article on a web page, [PDFium](https://pdfium.googlesource.com/pdfium/) by way of [pypdfium2](https://github.com/pypdfium2-team/pypdfium2), which cuts figures from the original page, [MinerU](https://github.com/opendatalab/MinerU), whose Cloud API reads every PDF, and [mammoth](https://github.com/mwilliamson/python-mammoth), which reads Word files; PDFs are shown with [PDF.js](https://github.com/mozilla/pdf.js) and formulas with [KaTeX](https://katex.org). The desktop shell uses [MyGo](https://github.com/egoist/mygo). Thanks to their authors.</sub>

[Apache 2.0](LICENSE) © 2026 Xia Chen; fork changes © 2026 cjdem · [Development](docs/DEVELOPMENT.md) · [Format](docs/format.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Feedback](https://github.com/cjdem/textfold/issues)

</div>
