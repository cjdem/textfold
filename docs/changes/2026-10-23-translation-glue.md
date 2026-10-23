# A translation is read with the base layer's page-break join and step-down

**Date:** 2026-10-23
**Branch:** `worktree-translation-glue`

## What and why

A Chinese document can be generated in English and then translated back to Chinese (`tr-zh`). The base layer's units
carry two things the reader uses: `glue`, the half of a sentence a page break left in the unit before, and `tn: 0`, a
takeaway that stepped down out of Takeaway because its section had too many background lines. The translation layer
carried neither, so a translated unit opened mid-sentence (the join was lost) and a background line the base hides at
Takeaway and Topic came back there — and in an export of the translated text. Now a document read for the reader
(`store.assemble`) gives the translated unit the base's `glue` and `tn: 0` in memory; the layer file is not changed,
and a generation that attaches the layer to fill its gaps saves it without those fields.

## The change

- `textfold/store.py` — `apply_tr(doc, lang, tr, view=False)`: attaches a translation layer, and when `view` is true
  gives each translated unit what the text gives it (`_translation_view`): the base's `glue` when the translation has
  none, the language is `zh` and the base's join is not Japanese or Korean (kana or hangul in any written form), and
  `tn: 0` when the base's takeaway stepped down. `assemble` reads with `view=True`; the pipeline attaches without it (default), so
  `save_tr` never writes another layer's fields into `tr-<lang>.json`.
- `tests/test_translation_view.py` — new, eight cases: the join is carried; the step-down is carried; a translation's
  own join is kept; a base with neither leaves it alone; a Japanese join is not copied; every written form of kana and
  hangul (halfwidth, phonetic extensions, jamo) refuses the join; attaching without the view and saving leaves the file
  clean; `assemble` reads a document with the view and the file still has neither field.
- `docs/DEVELOPMENT.md` — the CJK reading paragraph and the layer notes say a translation is read with the base's
  `glue` (a Chinese translation of Chinese words) and `tn: 0`, and that the view is made when a document is read, not
  written into the layer.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the translation's view of `glue` and the step-down.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: the stored layer format is
  unchanged (the view is made when a layer is applied for reading, and the pipeline's save writes the layer as the
  model gave it).
- `README.md` / `README.zh-CN.md` — not needed: no new capability; a translated Chinese document reads as it was meant
  to.
- `docs/requirements/`, `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`,
  `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`,
  `.claude/agents/`, `CLAUDE.md`, `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency, version,
  platform, security, contribution, desktop or process change.

## Decisions

- At read time (`assemble`), not generation time: a `tr-zh` layer already on disk is fixed without being regenerated.
- The view is off by default and the pipeline never turns it on: the pipeline attaches a layer, fills its gaps and saves
  it, and a view baked into the layer would leave the base's `glue`/`tn` in the translation file, where a later base
  change could not reach it and a later fill would make the layer inconsistent.
- The base's `glue` rather than a translation of it: the page break cut the text in the same place, so the fragment is
  the same words; translating it at read time would need a model call while a paper opens.
- The join is copied only into a Chinese translation, and only when the join itself has no kana or hangul: a Japanese
  or Korean document's tail is another language's sentence, and prepending it to Chinese would be wrong. The test is
  the tail's characters, covering every written form (`tokens.CJK`'s three kana ranges plus hangul jamo, syllables and
  halfwidth); `tn: 0` is copied for any language, since it counts a section's lines, not words. Reading characters
  rather than detecting the text's language errs the other way for a Chinese tail that quotes a Japanese word: that
  join is dropped for the translation (the base still joins it), which is rarer than a Japanese tail reaching Chinese.
- A translation's own `glue` is not overwritten: a future generator that translates the join itself keeps its result.
- `tn: 0` is copied only when the base's is exactly 0. A unit whose base has levels keeps the translation's own
  takeaway length.

## Concurrency and locks

Not applicable: the view is applied to the parsed document in memory; no file is written and no lock is taken. The
layer file keeps what the model gave it.

## How it was verified

- `python .claude/hooks/verify.py` — 484 tests, OK (38.7 s); `git diff --check` prints nothing.
- `tests.test_translation_view` — 8 tests, OK; against the base's `store.py` (a scratch tree from `b427440`) eleven
  errors (the five view tests plus the end-to-end read, and the kana/hangul test once per form, all on the missing
  `view` kwarg or the view they never got) and the save-path test passes there because the base had no view to bake
  in — it guards the path this change adds. The join, step-down, Japanese and save tests all pin real behaviour.
- The save test reads `tr-zh.json` back from disk and finds no `glue` and the translation's own `tn`, so the pipeline's
  fill-and-save path cannot persist the view. The end-to-end test reads the file again after `assemble` and finds it
  unchanged, so a read cannot persist it either.

## Not measured

- A real translated paper in the reader or an export: the tests apply layers to a document dict and run `assemble` on
  a stored paper; no browser session.
- A Japanese or Korean document in the reader: the guard is exercised at the function level for every written form of
  kana and hangul it covers, not through a parsed document. A Japanese tail of kanji only has no kana and would pass
  the guard; rare, and the same risk the base language has. The reverse — a Chinese tail quoting a Japanese word —
  loses its join in the translation; reasoned, not run.
- An English document: `dress` does not write `glue` for it (the rule is CJK only), so nothing is copied; not
  exercised separately.
- Zoom smoothness: no reader JavaScript is touched; unmeasured here (`tools/zoombench.py` needs `playwright` and
  exported comparison pages, neither installed).

## Pitfalls

- The first version mutated the translation layer's `lad` inside `apply_tr`; the pipeline's fill path then saved that
  same object, writing the base's `glue` and `tn: 0` into `tr-zh.json` — and the next read would treat them as the
  translation's own. The view is now a separate step, off by default.
- The view is applied to the assembled document only. Anything that reads a raw translation layer (the pipeline's
  fill, a test) sees exactly what was stored.
- `tn: 0` on a translated apparatus unit hides its takeaway at Takeaway, as it does in the base; such units are not
  translated (`translate.worded` skips them), so this is a guard rather than a common case.
- The base's `glue` is in the base's words; the copy is limited to a Chinese translation and a join without kana or
  hangul. The reader's `view()` is where the two fields are consumed.

## Rejected

- Writing the join into the translation when it is generated: layers already on disk would stay broken, and the next
  reader would still see the gap.
- Mutating the layer in `apply_tr`: the pipeline saves the attached layer, so the view would be persisted and later
  base changes would not reach it.
- Translating the join when the paper opens: a model call on the reader's path, for a fragment the base already holds.
- Copying the base's `ev` or `topic`: the translation's sentence numbers and topic are its own; only the cut and the
  step-down are the text's.
