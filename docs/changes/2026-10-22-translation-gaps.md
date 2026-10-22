# A translation that came back without paragraphs is asked for them again

**Date:** 2026-10-22
**Branch:** `worktree-translation-gaps`

## What and why

The reported fault (upstream's): some paragraphs of a paper stayed in English. One call that failed (a timeout, a rate
limit, a reply that was not JSON) or one paragraph the model left out was stored as it was, and because the
translation existed, opening it never asked again. This change ports the translation part of `d457cfa` only — the
library naming, whole-text notes and nested folders in that commit are R22/R23.

Two moments now ask for what is missing, and only that: while a language is built, a part that failed or a paragraph
the model left out is asked for once more at once, the paragraphs alone; a stored translation that still has gaps
(made before this change, or failed twice) has them asked for the next time its language is generated, and the app
asks as that language is opened. The rest of the translation is kept. A line the model translated without a takeaway
(a list of keywords) keeps its first sentence instead of being discarded.

## The change

- `textfold/translate.py` — `worded(u)` (a unit with more than one word character: a formula, a citation or a
  figure's leftover letter is no gap); `gaps(doc, lang)` (units of the sections with no translation in the language);
  `_ask` (the parallel parts, now with a retry mode), `_again` (the gaps as parts), `_counter` (progress across the
  first pass and the retry), `build` (first pass, then one retry of the gaps — also when every first-pass call failed,
  so a document of one section is retried too; it raises only when every call of both passes failed), `fill` (a stored
  layer's gaps, the rest kept), `_titles` (the headings and paper title call, extracted from `build`). A retry asks
  the model with `force=True`: its prompt can be identical to the first-pass prompt whose kept reply left the
  paragraph out, and reading that reply back would leave the gap in place. `assemble` takes a translated line's first
  sentence as its takeaway when the model gave none.
- The R5 reply-shape guards are kept inside `_ask`, for both passes: a reply that is not an object or names no unit is
  a failed part and its cached reply is forgotten; a shape error while assembling a part clears that part's units and
  forgets the reply. A retry reply that still leaves a paragraph out is forgotten too, so the next fill asks again
  rather than reading it back; first-pass replies are kept (the rest of their sections is in them).
- `textfold/store.py` — `assemble` records `meta["gaps"][lang]` (the number of worded units without a translation) for
  a translation that is not stale.
- `textfold/pipeline.py` — `build` no longer returns a failed count; a built layer is saved even when gaps remain, and
  the log says how many paragraphs it has none for. A current stored layer with gaps is filled by `translate.fill` and
  saved with the model label `old + new` when the model differs. The fork's `also_zh` default-Chinese path fills a
  current gapped layer too, and a failure there does not fail the generation the reader asked for.
- `textfold/web/app.js` — `fillGaps(lang, asked)` on a reader page: when `PAPER.gaps[lang]` is set, no job is shown for
  the paper and a model is connected, it submits a normal generation for that language (the pipeline takes the fill
  path). Once per tab session for a given count, so a paragraph that will not translate is not asked for at every
  opening; `DRApp.fill` lets the language menu ask anyway. It is called when the reader's language is set (a switch) and
  once after the page's jobs and models are loaded.
- `textfold/web/reader.js` — the language button and each language menu item show the gap count, and the menu's first
  item asks for them again (in the app; a saved page shows the count only).
- `textfold/web/i18n.js`, `textfold/web/reader.css` — the three strings in English and Simplified Chinese, and the fill
  item's style.
- Tests: `tests/test_translation_gaps.py` (13 tests); `tests/test_reply_shapes.py` now pins that a build whose every
  call fails is not saved; `tests/test_default_zh.py` pins that a partial default-Chinese pass is saved with its gaps
  and filled on the next run.
- `docs/DEVELOPMENT.md` — the stored-translation paragraph says what is asked for and when.

## Docs checked

- `docs/DEVELOPMENT.md` — updated (one paragraph, as above).
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: layers, notes and cards keep
  their shape; `meta.gaps` is computed at assembly and not written to disk.
- `README.md`, `README.zh-CN.md` — not needed: no command, setting or format changes.
- `site/`, `desktop-mygo/`, `.claude/agents/` — not needed: no app or site change; the reader's page payload grows by
  one computed key (`gaps`) when a translation has gaps.
- `pyproject.toml`, `requirements.txt` — not needed: no new dependency.

## Decisions

- **R5's "a partial layer is not saved" is replaced by "saved with gaps, then filled".** R5 refused to save a
  translation with a failed part because a partial layer, once current, was never completed; the reported fault is
  the other side of that. `fill` is the completion path now, and a nearly complete translation with a count and a
  fill button is more useful than no translation at all. The build still raises (and nothing is saved) when every
  call of both passes failed, so a model outage does not produce an empty layer. (A reply that arrives, names its
  units and translates none is not an error — pre-existing, and the gap path recovers it on the next fill.)
- **The retry runs before giving up, and asks the model.** Upstream raises as soon as every first-pass task errored,
  which would mean a one-section document (a note, a heading-less page) never has its failed call asked again — the
  verifier's blocking finding. The raise now waits for the retry, and fires only when every call of both passes
  failed. The retry also passes `force=True`: the gap prompt can be byte-identical to the first-pass prompt whose
  kept reply omitted the paragraph, and a cache read would reproduce the omission without asking anything.
- **The R5 reply-shape guards stay.** They are what makes an unreadable reply a failed part rather than a silent
  partial save; the retry then asks for exactly those paragraphs.
- **Only worded units count.** A formula or citation alone, or a one-letter caption fragment ("D"), is not asked for
  again; it would come back the same. A lone CJK character is one word character and is likewise not a gap.
- **A retry reply that still omits a paragraph is not kept.** Reading it back on the next generation would reproduce
  the omission without asking the model; forgetting it means the next fill asks anew. First-pass replies stay cached.
- **A translated line without a takeaway keeps its first sentence.** Seen with a real model on keyword lines; before,
  the line was dropped (no takeaway meant no unit), so the paragraph stayed English.
- **Fill only while the layer stands on the current English base.** A stale layer may have renumbered units and a
  different text under it; it is rebuilt (with the retry) rather than filled.
- **The default-Chinese path fills too.** This fork makes a Simplified Chinese version at the end of an English
  generation; if that stored layer is current but gapped, it is filled there, best-effort, because otherwise it would
  wait until the reader opens it in Chinese.
- **The auto-fill is once per tab session per gap count, and only for the language being read.** A paragraph that
  will not translate would otherwise be asked for on every opening; another language's gaps are shown in the menu and
  filled when the reader switches to it. The menu's fill item bypasses the once-per-session guard.
- **A saved static page shows the count but no fill item.** There is no app to run a job there.

## Concurrency and locks

None added. Fill is an ordinary generation job (the server runs generation jobs one at a time, and `Jobs.submit`
returns a queued or running job for the same paper and language instead of starting another), so it cannot interleave
with another generation's model calls or saves; a layer is still written by `store.write` to a temp file and replaced.
The app submits at most one fill per paper and language per tab session, and none while a job for the paper is shown.

## How it was verified

- `python .claude/hooks/verify.py` — 282 tests, OK (baseline 269; 13 added; two R5 tests rewritten, the suite count
  unchanged for them).
- The new tests pin: a failed part asked for again at once (and the section's own lines taken from the retried call);
  a one-section document's failed call asked again, and one that fails twice raising with no translation; an omitted
  paragraph asked for alone, with the retry a real call (`force=True`); a reply with no unit it names forgotten and
  asked again; a failed retry not taking the first pass's section lines; a paragraph omitted twice staying a gap with
  its reply forgotten while the first replies stay cached; a stored layer's gaps recorded as `meta.gaps`, filled by
  `fill` with the rest kept; a fill whose every call fails again raising and leaving the gaps; a generation filling a
  stored layer and a second generation not asking; a gapped layer opening without a model; a formula/letter not being
  a gap; a translated line without a takeaway kept.
- In the browser (a worktree server on a demo paper whose Chinese layer was missing one paragraph): the language
  button showed `简体中文 1 段未译`, and opening the page started the gap-fill job (`正在补译 1 段没翻译的段落`). The
  machine has a model configured, so the job began a real request; the server was stopped at once, and no reply was
  cached. The demo paper and the temporary launch configuration were deleted afterwards. The menu's fill item was not
  clicked, and completion/reload after a real fill was not observed.
- `node --check` on `app.js`, `reader.js`, `i18n.js`.
- `textfold-verifier` — one long pass. Its blocking finding (a one-section document's every-first-call-failed case
  raised before the retry) is fixed: the retry now runs first, and the raise needs both passes to fail; a test pins
  it. Its high non-blocking finding (a retry could read back the kept first-pass reply under an identical prompt) is
  fixed by asking the retry with `force=True`; a test pins it. Its other findings are recorded under Pitfalls. It
  verified the retry's unit mapping on a 40-paragraph, three-part section (the middle part failing once: every unit
  kept its own translation), `meta.gaps` accuracy (count, absence when complete, absent for stale, `only=` filtering),
  both pipeline fill paths, the R5 guards in both passes, static exports, and that the generation queue keeps the
  auto-fill from interleaving with another save.

## Measured

| | before | after |
|---|---|---|
| tests | 269 | 282 |

## Not measured

- **Smoothness: unmeasured.** The reader's language button, menu and styles change; no `tools/zoombench.py` run (it
  needs `playwright` and exported comparison pages, neither installed here), so the zoom axis is not reported as
  unaffected.
- No real model reply that omits paragraphs; all tests use a stand-in. A provider failure during fill was not seen
  end to end (the job-error toast path is the server's existing one).
- No long paper's gaps. The retry's unit mapping across parts was checked with a constructed 40-paragraph section in
  three parts (by the verifier), but no real long document was built or filled.
- The auto-fill's completion and page reload were not observed against a live model (the request it started was
  stopped; no reply was cached).

## Pitfalls

- A paragraph the model omits every time stays a gap. Its reply is forgotten each time, so every fill asks again; the
  app's once-per-tab-session guard keeps that from happening on every opening of the same tab, and the count is shown
  rather than hidden.
- **Regenerate can replace a complete translation with a gapped one.** The build branch always saves; if the new
  sample omits a paragraph, or one part fails while others succeed, the old layer is replaced and those paragraphs
  show English until a fill succeeds — for good if no model is available. This is the deliberate reversal of R5 (see
  Decisions); the English text and the rest of the new translation are kept.
- A gapped layer saved as current makes the next generation take the fill path instead of rebuilding; `force`
  (Regenerate) still rebuilds the whole language.
- A fill whose every retry call fails raises out of `generate`, so the job shows as failed although the stored layer
  is intact and readable; the `also_zh` fill catches the same failure and only logs it. The main path stays faithful
  to upstream and tells the reader the fill did not happen.
- `Jobs._same` matches a queued or running generation by paper and language, not by `force`: a Regenerate clicked
  while an auto-fill for the same language is running returns that fill job, so no fresh sample is taken. Before this
  change no path submitted a generation without the reader asking; the reader can click Regenerate again once the
  fill has finished.
- `gaps()` counts units of the sections (`doc["chunks"]`), as `build` translates them. A document parsed without any
  section has no translation tasks at all — pre-existing, unchanged here.
- The first pass's reply for a part that omitted a paragraph stays cached; a later forced rebuild reads it again and
  asks for the same gap again (the retry reply's own prompt is separate, cached, and bypassed by the retry's force).
- `worded()` treats a unit with one word character or none as nothing to translate, so a one-letter word ("I") or a
  one-letter list item is never a gap; the same rule rightly excludes a figure's leftover "D".
- When the model differs from the one that made the layer, the saved model label becomes `old + new`.
- Auto-fill only covers the language being read; the other language's gaps show in the menu and fill when switched to.

## Rejected

- **Keeping R5's failed count and refusing to save.** A part that failed and then succeeded in the retry would still
  be refused, and a paragraph that failed twice would leave no layer instead of a nearly complete one.
- **Retrying by resending the whole section.** The fault is lost paragraphs, not a bad section; asking for the gaps
  alone keeps the rest byte-identical and costs one call per missing run.
- **Filling a stale layer.** Its base is another English version and parser changes can renumber units; rebuild it.
- **Auto-filling on every load with no guard.** A paragraph that will not translate would be asked for at every
  opening of the same tab.
- **Porting the rest of `d457cfa`** (library naming, whole-text notes, nested folders): R22/R23.
