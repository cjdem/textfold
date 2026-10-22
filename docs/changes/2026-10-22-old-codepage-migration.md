# A library an older TextFold left on a Chinese Windows opens again

**Date:** 2026-10-22
**Branch:** `worktree-old-codepage-migration`

## What and why

TextFold 0.10.9 and before wrote its own files on Windows in the system's codepage — GBK on a Chinese Windows: a
paper's `meta.json`, `source.html` and layers, the library, the settings, the notes, the Zotero index. 0.10.10 reads
and writes UTF-8, and R2 made those reads strict: such a file raises `UnicodeDecodeError` where its text is Chinese
(`0xa1` begins `。` in GBK), the library is read as empty and the next save writes that emptiness over it. R2 guarded
the two files that are saved without a reader's act (`library.load`, `zotero.links/link`) by re-raising, which keeps
the bytes but makes the app fail to open. This change reads each old file in the codepage it was written in, so the
library opens; the read writes nothing, and the file's next save writes UTF-8.

It also fixes two readers that asked `locale.getpreferredencoding()` for "the system's encoding". The app runs in
UTF-8 mode (`PYTHONUTF8=1`, and MyGo starts it so), under which that call returns `utf-8`, not the codepage: a page
stored by an older TextFold on a GBK machine was read as UTF-8 with replacement characters instead of its Chinese
text, and an address stored before the byte-order mark was misread the same way.

## The change

- `store.py` — `codepage()` is new here (upstream had it in `local`) and returns the locale's encoding from `locale.getencoding()`;
  before Python 3.11, where that does not exist, Windows' ANSI code page (`GetACP`) answers, because
  `getpreferredencoding()` returns UTF-8 under the UTF-8 mode the app runs in. `read_text(f)` reads a file of
  TextFold's own: UTF-8, else `codepage()`, and line ends normalized as `Path.read_text` gave them. It writes
  nothing. A file in neither encoding raises `UnicodeDecodeError`: an already damaged file is not shown as replacement
  text that the next save would persist.
- `store.parsed` — reads `source.html` and `meta.json` through `read_text`, so an old page decodes in the codepage
  too; `_read_html` is deleted (its job is `read_text`'s, and its `getpreferredencoding` fallback was the UTF-8-mode
  bug above).
- `store.read_url` — the old-address fallback uses `codepage()` rather than `getpreferredencoding()`. The byte-order
  mark stays the marker for addresses written now, as `webpage.register` writes it and `webpage.fetch` reads it.
- Readers switched to `read_text`: `store.read`, `store.papers` (a paper's `meta.json`, its notes count),
  `library.load`, `models.load_settings`, `notes.read`, `pdf.path/where`, `pdfdoc.place/relayout/read_output`,
  `server` (a job's title, two meta reads), `zotero.links/link/apply`, `cards.read/_meta`.
- `local._read` — tries UTF-8, then GBK, then `store.codepage()`, then UTF-8 with stand-ins. GBK stays the second
  try, as it was: a Markdown file that is not UTF-8 is most likely Chinese, on whatever Windows it is opened.
- `build._svg_text` — the undeclared-SVG fallback uses `store.codepage()`, for the same UTF-8-mode reason.
- `library.py`, `zotero.py` — the `UnicodeDecodeError` re-raises stay, now around `store.read_text`: a damaged file is
  not read as empty and saved over.
- `zotero.py` — `apply` writes a `meta.json` it converts through a temp file and replace, rather than truncating the
  file in place; a crash while converting an old meta cannot leave it half written.
- Comments in `pdfdoc.py`, `engine.py`, `fetch.py` that said these files are read with the system's encoding now say
  UTF-8.
- `tests/test_old_codepage_files.py` — new: a GBK paper (meta and source) opens and its bytes are left as they were;
  the papers list and translated titles; the library's folders, and its next save writes UTF-8; the settings and the
  notes, and their next saves write UTF-8; the Zotero index keeps its rows, and the new link is saved UTF-8; a UTF-8
  file is untouched; a file in neither encoding raises and its bytes are unchanged (the library and Zotero guards
  included); and, with `getencoding()` absent, `codepage()` is Windows' ANSI code page.
- `tests/test_agent_encoding.py` — R2's two "a GBK file raises" tests move to the migration test file.
- `tests/test_engine_api.py` — an old page is simulated by writing it in GBK, without the skip that a UTF-8-mode
  machine used to need; the bytes are left as they were.
- `tests/test_stored_text.py` — an old address is written in `store.codepage()`.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: its encoding paragraph now names `store.read_text` as the reader of TextFold's own
  files, says a read writes nothing and the next save writes UTF-8, names its two exceptions (the marked web address
  and the rebuildable reply cache), and says `store.codepage()` — not `getpreferredencoding()`, which UTF-8 mode
  sways.
- `README.md`, `README.zh-CN.md` — not needed: an old library opening is the documented behaviour working, no new
  promise.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: the formats and their JSON
  bytes do not change.
- `site/` — not needed: the site does no text I/O in the product.
- `pyproject.toml`, `requirements.txt` — not needed: no dependency or platform change; the Python 3.9/3.10 path is
  handled in `codepage()`.
- `NOTICE`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md` — not
  needed.
- `desktop-mygo/README.md`, `.claude/agents/` — not needed: MyGo already sets `PYTHONUTF8=1`, and no agent prompt
  describes file I/O.

## Decisions

- **Read only; no rewrite on read.** Upstream's `store.read_text` decodes an old file and writes it again as UTF-8.
  The verifier showed that its compare-before-replace guard is check-then-act: a save that lands between the compare
  and `os.replace` is overwritten by the stale text (reachable through `GET /api/folders` and `POST /api/opened`, and
  across the MyGo app and `serve`, which share a data folder). No portable atomic compare-and-swap exists on Windows,
  and every writer would have to take one lock for a migration write to be safe. Instead the read leaves the file
  alone: the library is decoded in the codepage on every read, and the next save that writes it — a paper opened
  (`library.opened`), a folder changed, a new paper's date stamped — writes UTF-8. A library whose `added` dates are
  already complete is not rewritten on boot; it stays GBK until one of those saves, and reads as before meanwhile.
- **A file in neither encoding raises.** R2 chose this for the two auto-saved files; R3 extends it to every own file.
  Replacement text looks harmless because the read does not write, but the app does: the verifier showed a GBK
  `library.json` truncated inside its last character loading as an empty library, after which `library.stamp` saves
  that emptiness on boot. Raising keeps the bytes and fails the request, which is the lesser harm for a file that is
  already damaged. An old codepage file takes this path only when the machine's codepage is no longer the writer's —
  on a Windows whose ANSI code page is UTF-8 (the "Use Unicode UTF-8" setting), a GBK file raises and the library does
  not open, its bytes kept.
- **Line ends are normalized on the way out** exactly as `Path.read_text` does, so a decoded file's JSON parses as
  before and layer stamps do not change.
- **`llm._read_cache` stays ASCII-only.** A cached reply from before R2 was written with `ensure_ascii=False`, and no
  marker says whether in the codepage or UTF-8; a wrong guess would put mojibake in a document unseen. A non-ASCII
  cache is a miss, the call is made again once, and the file is rewritten ASCII-escaped — cheaper than a silent wrong
  translation, and it is not a file a reader wrote.
- **`webpage` keeps `store.read_url`.** An address is stored with a byte-order mark because GBK's `D2 BB` ("一") is
  also valid UTF-8; `read_text`'s UTF-8-first rule would silently read another address, and its strict UTF-8 would
  keep the mark in the string. The reader is fork-specific and is left in place, with its codepage fallback fixed.
- **A GBK file opened on a machine whose codepage is single-byte (cp1252) is read as that codepage's mojibake.** No
  marker tells the two apart, and a single-byte codepage accepts almost any bytes. Nothing is destroyed by the read;
  the reader sees the wrong text before any save, and a save would write that text. The same limit exists upstream.

## Concurrency and locks

The change adds no write on any read path, so no lock is added or needed: `store.read_text` only reads bytes. The
writes that convert an old file are the app's own save paths. Most already write a temp file and replace it, under
their lock; `zotero.apply` did not, and now does. `local.store_doc` replaces a paper's folder whole (temp folder, then
rename), as before. One pre-existing limit remains: `zotero.apply`'s read-modify-write is not serialized with another
`apply`, so two at once could lose one update or collide on the temp name; this change neither adds nor widens that
window. The invariant "a save,
a generation, a re-conversion and a move to the trash must not interleave" is untouched, and no new two-writer test is
needed because no new writer exists.

## How it was verified

- `python .claude/hooks/verify.py` — 222 tests, OK (baseline 214; 10 added in the new file, 2 removed from R2's guard
  tests).
- New tests as listed above; the "left as it was" assertions compare the file's bytes before and after a read.
- `store.papers()` over the clone's `papers/` (with `store.DATA` pointed at it, read-only) lists the remaining paper
  and its languages; its files were already UTF-8, so nothing was rewritten.
- `textfold-verifier` — its report changed the design. It found that the compare-before-replace guard is check-then-act
  and a save inside that window is lost (finding 1); that a file in neither encoding was read with stand-ins and then
  saved over by the boot's `library.stamp` (finding 2); that on Python 3.9/3.10 `codepage()` fell back to
  `getpreferredencoding()` and answered UTF-8 under the app's UTF-8 mode (finding 3); that a GBK file opened under
  another codepage decoded as mojibake (finding 4; now read-only, and documented); that the temp file's cleanup could
  re-raise (finding 5; gone with the rewrite); that the "two-writer" test only exercised save-before-check (finding 6;
  the rewrite and its test are gone); that the record named the wrong `cards` function (finding 7; fixed); that the
  line-ending pitfall contradicted itself (finding 8; the rewrite is gone and the in-memory rule is stated); that the
  record's verifier section was missing (finding 9; this section); that three comments still said "the system's
  encoding" (finding 10; fixed); that DEVELOPMENT overstated the switch (finding 11; its exceptions are named); and
  that `local._read` had replaced its hardcoded GBK with the current codepage (finding 12; GBK is tried again). Its
  invariant review found no parser, atom or rendering change; zoom smoothness remains unmeasured, and it judged the
  record's "unmeasured" honest.
- `textfold-verifier`, second pass — confirmed findings 1–12 resolved and that the read path writes nothing, then
  found four overclaims and two gaps, all addressed: every conversion save is *not* atomic (`zotero.apply` truncated
  `meta.json` in place; now temp file and replace); the re-raise guards were no longer tested (two tests restored,
  asserting `library.load/stamp/opened` and `zotero.links/link` raise on a file in neither encoding and its bytes are
  unchanged); a decodable but invalid `library.json` is still read as empty and saved over at boot (pre-existing,
  now stated); the boot does not convert a library whose `added` dates are complete (record corrected); a Windows
  whose ANSI code page is UTF-8 makes an old GBK file raise, not open (now disclosed, and the 3.9/3.10 test asserts
  the ANSI code page instead of "not UTF-8"); and DEVELOPMENT stated the Markdown import order without GBK (fixed).

## Measured

| | before | after |
|---|---|---|
| tests | 214 | 222 |

## Not measured

- **Smoothness: unmeasured.** No `tools/zoombench.py` run was made: it needs `playwright` and exported comparison
  pages, neither installed here, so the zoom axis is not reported as unaffected. The reader page and the boot list do
  pass through `store.read_text` (a fallback decode on an old file, a plain UTF-8 decode on any other), and the cost
  of that on a large library is not benchmarked.
- A real GBK library was not opened in the app: the one old paper this clone had was removed at the requester's
  request in R2 and will be re-imported. The tests write GBK files and open them through the same readers the server
  uses, on a scratch data folder.
- Python 3.9/3.10 under UTF-8 mode is covered by a unit test of `codepage()` (with `getencoding` removed); the whole
  app was not run on those versions.

## Pitfalls

- A GBK file whose bytes are also valid UTF-8 is read as UTF-8 (`D2 BB` is U+04BB); no marker tells them apart. R2's
  record already named this limit; `read_url` is the one place with a marker, which is why it keeps its own reader.
- A GBK file moved to a machine whose codepage is single-byte is read as that codepage's mojibake (see Decisions).
  Nothing is destroyed until a save, and the reader sees the wrong text first.
- `store.read_text` normalizes CRLF to LF in the text it returns, as `Path.read_text` did. The file keeps its bytes,
  so its line ends are unchanged on disk until a save writes them the way every writer does.
- A file in neither encoding now raises instead of being shown with replacement characters: the home page or a
  request fails until the file is repaired or moved aside. That is deliberate; the alternative is an automatic save of
  what could not be read. A file that *does* decode but is invalid JSON (a truncated UTF-8 `library.json`) is still
  read as empty by `library.load` and saved over by the boot's `library.stamp` — pre-existing, not introduced here,
  and outside this change's scope.
- On a Windows whose ANSI code page is UTF-8, `store.codepage()` is `cp65001`; a GBK file then fails both decodes and
  raises (bytes kept), and the library does not open until the file is converted on a machine that reads GBK. The
  test for the Python 3.9/3.10 path asserts the ANSI code page, so it holds there too.
- `models.load_settings` may rewrite the settings file while importing ThoughtDAG's `.env`; that write goes through a
  temp file and replacement under the settings lock, as before.

## Rejected

- **Rewriting an old file as UTF-8 at read time**, upstream's approach and the requester's first choice
  (compare-before-replace): the compare and the replace are not one atomic step, so a save inside the window is lost,
  and on Windows there is no atomic compare-and-swap to close it. The verifier demonstrated the loss through the
  server's own endpoints. A read that writes nothing cannot lose a save.
- **A version stamp or a one-off upgrade command.** The file's own bytes already say whether it is UTF-8; a stamp
  would need to be written into formats that many tools read, and an upgrade step does not exist in this app.
- **Reading a file in neither encoding with `errors="replace"`, as upstream does.** The boot save persists it.
- **Migrating `llm`'s reply cache with the rest.** See Decisions: a wrong decode is invisible in a generated document,
  a rebuilt call is not.
- **Rewriting `webpage`'s address handling to plain UTF-8**, as upstream did: this fork writes the mark, and an old
  address in GBK is exactly the ambiguous case the mark exists for.
