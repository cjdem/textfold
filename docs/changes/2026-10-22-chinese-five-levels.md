# A Chinese paper folds to five levels, and an English paper folds as before

**Date:** 2026-10-22
**Branch:** `worktree-chinese-five-levels`

## What and why

R13 gave a Chinese paragraph sentences, but the ladder still measured them in English words: `tokens.words` counts a
Han character as one word, so a Chinese takeaway was cut at 14 characters instead of about 40 and a topic at 3 instead
of 8; the no-model levels took the first sentence, where Chinese units often open with a lead-in and the claim comes
later; contents lines and footnotes became key sentences; a paragraph a page break cut in half lost its subject; and a
section's background read as a list of documents and years. This ports upstream `4897e24`'s ladder and reader changes
for Chinese (and Japanese kana), so a CJK document's levels are written and cut in characters and its Brief is prose.
Unlike the upstream commit, every CJK branch is gated here, so an English paper's prompt, levels and page are exactly
what they were; R15 has the upstream document gate and the remaining reader polish.

## The change

- `textfold/ladder.py` — the CJK character budgets (40/60/8/40), clause edges, fillers, ordinals, apparatus patterns,
  claim markers, and the helpers `is_apparatus`/`suppressed`, `_cjk_share`, `budgets_of`/`budgets_for`,
  `_claim_sentence`, `cjk_topic_span`/`cjk_takeaway`/`cjk_topic`, `repeats_section`/`citation_first`,
  `fold_background` (at most two background lines in a row at Takeaway; a line that opens with its source or repeats
  the section's line steps down) and `dress` (`glue`: the half sentence a page break left in the unit before;
  `l3: false`: background the section's line already summarises; the item-number and repeat-to-the-section sieves).
  `prompt_for` asks a CJK document for one sentence of N characters, with the six writing rules; `assemble` and
  `local` take a `cjk` argument (None: judged from the unit) and use the claim sentence, clause-edge takeaway, noun
  phrase and `。`; `topic_tokens`/`section_ladder` take the CJK topic budget; `build` warns in characters, and runs
  `fold_background`/`dress` for a CJK document only, after the reply's `try` so a post-pass bug cannot discard the
  model's levels.
- `textfold/translate.py` — `worded` refuses a unit whose ladder is suppressed (an apparatus line), so the gap-fill
  path does not ask for it again; the first translation pass still sends a section's units as before.
- `textfold/web/reader.js` — `view` carries `glue` and `l3`; Brief hides a unit with `l3 === false`, drops CJK
  footnote markers (①-⑩, ⑴-⒑, ⒈-⒑) from text tokens but leaves formulas and citations whole, and joins a page-break
  half at the first word (before a formula if the sentence opens with one); `drawUnit` hides a unit with no pieces
  below Full, so an apparatus line exists only at Full; a stepped-down unit shows no Topic; and `go` (a note, a cite)
  steps to a level that shows a hidden unit (Full) before scrolling.
- `tests/test_cjk.py` — upstream `7ae86b9`'s 23 model-free tests: splitter and `cjk_heavy` (R13's ground), apparatus,
  the topic span, the background rules and `dress`.
- `tests/test_chinese_levels.py` — thirteen tests for this fork: a Chinese unit's five levels without a model (the
  written Key/Takeaway is the claim sentence, Brief the author's first), an apparatus line folding to nothing below
  Full, the Chinese prompt's character budgets and rules, an English document keeping its prompt and levels, a stored
  `glue`/`l3` surviving `save_en`/`assemble`, a contents line not becoming glue, a paragraph ending `……` carrying
  nothing, a long ellipsis in an argument not read as dot leaders, `section_ladder` keeping the budget it is given,
  a topic keeping `P2P` and `3.5`, a Chinese model reply using `。` and the 8-character topic budget (and an
  apparatus reply folded), an English dot-leader-looking line still folding, and a suppressed unit skipped by
  translation.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the `ladder.py` map line, the reader paragraph (what a Chinese folded level leaves
  out and joins), the "levels made in English first" paragraph (a Chinese document's levels are in Chinese now), and
  the stored-sentence paragraph (the new optional `glue`/`l3`/`ev: []`).
- `docs/format.md` — updated: a local document's written levels are the author's first sentence, or a Chinese unit's
  claim sentence. No field or version change; `glue`/`l3` are layer internals, not the export's fields.
- `README.md`, `README.zh-CN.md` — not needed: the five-level table already says what each level is; the anchoring
  promise still holds (Brief is `evidence`, Key is the written line).
- `docs/upstream/2026-10-22.md` — not changed: the review is the source for this round, not current behaviour.
- `site/`, `desktop-mygo/` — not needed: no endpoint, string or shell change; the payload copies `textfold/` when built.
- `SECURITY.md`, `pyproject.toml`, `requirements.txt` — no change (`bisect`, `difflib` and `json` are stdlib).

## Decisions

- **Gate the CJK rules instead of taking them ungated.** Upstream `4897e24` says English takes the old path, but it does
  not: its prompt's six rules and section wording go to every document, `is_apparatus` can fold an English dot-leader
  line to nothing, `local` gives English the claim-sentence pick, and `dress` glues and hides English units. `6e2cada`
  (this round's R15) exists to fix that. This fork's rule is that an existing paper reads as it did, so the port gates
  the prompt by the document's text and the per-unit decisions by `budgets_of(u)`; `dress`/`fold_background` run for
  a CJK document only. The gate is per unit for the ladder and per section for the two structure passes; R15 replaces
  it with `cjk_doc`/`meta.cjk`, adds the reader's document-level polish, removes `l3`, and takes the `1.研究背景`
  guard. English is byte-identical, not merely "unchanged in spirit": `prompt_for`, `local`, `assemble`,
  `section_ladder` and a mocked `build` were compared against `main` on the stored English paper and an English
  fixture, and no unit or chunk layer differed.
- **A Chinese document's levels are written in Chinese, in `layers/en.json`.** The prompt asks for one sentence of N
  characters and the punctuation of the text's language, so the base layer holds Chinese for a Chinese paper. The
  layer's name is the base layer, not its language. The reader's Chinese view still shows the `tr-zh` layer (a Chinese
  "translation" of that base), which carries no `glue`/`l3`; a Chinese reader therefore sees the five levels but not
  the page-break join or the background hiding until that language is generated again. That is a fork-specific limit,
  recorded rather than papered over.
- **Brief is the author's sentence, Key is the written claim.** `local` on a CJK unit returns `ev: [0]`, so the
  format's `brief` is the first sentence while `key`/`takeaway` are the claim sentence chosen from the unit. This keeps
  the evidence contract (`brief` is exactly `evidence`) and matches the written line; `docs/format.md`'s local
  provenance now says so.
- **Small corrections to upstream's heuristics, kept because they are what makes the feature safe.** A dot-leader
  contents line must end with a page number, or a Chinese argument with `…………` folds to nothing; `……` at the end of a
  paragraph is a whole sentence, so it is not carried into the next; `dress` steps over apparatus as well as footnotes
  when it looks for the half sentence, so a contents line cannot become glue; the topic skip does not treat a space
  after Latin letters or a version's decimal point as a filler or a clause edge; `section_ladder` keeps the budget its
  caller gives it (the build passes the document's, a translation passes its language's); a stepped-down unit shows no
  Topic; and an atom as the glued sentence's first word keeps the glue rather than losing it to `"[object Object]"`.
  These are the verifier's findings, fixed here; R15 can carry them unchanged.
- **No new writer.** The new keys live inside the `lad` object `store.save_en` already writes, under the generation
  queue. Old layers lack them and are read as before; `apply_en` keeps the whole dict, and `fold.unit` ignores what it
  does not use. No second writer or new lock is introduced, so no two-writer test is added; the existing
  generation/translation/`store.LOCK` rules are untouched.
- **The reader's polish waits for R15.** The section summary at Brief, the reference-heading section, the scrolling
  Topic card and the empty stake row are upstream `4897e24`'s, but each changes every document's page; they are left
  for R15's document flag, so this change touches only what a CJK layer carries.

## Concurrency and locks

None added. The change adds optional keys to `layers/en.json`, written only by `store.save_en` inside the one
generation job; translations still write `tr-*.json` only; `store.trash`/`pdfdoc.store_pdf` keep `store.LOCK` and the
levels go with the text they were made from. Reading (`store.assemble`, `fold`, the reader) is unchanged in its locks.

## How it was verified

- `python .claude/hooks/verify.py` — 354 tests, OK (baseline 318; 23 upstream + 13 fork).
- `python -m unittest discover -s tests -p "test_cjk.py" -v` — 23 tests, OK; `-p "test_chinese_levels.py" -v` — 13
  tests, OK.
- English identity: `prompt_for`, `local`, `assemble` and `section_ladder` were run from `main`'s package and this
  branch's package and diffed — no difference; the verifier repeated it on the stored English paper (92 units,
  16 chunks), added five reply shapes and a mocked `build`, and found 0 unit or chunk layer differences and no English
  `glue`/`l3`. `fold_background` leaves an English section alone (upstream test) and `dress` returns on one (fork
  test).
- Chinese, no model: `store.assemble` → `fold.unit` gives Full ≠ Brief = one sentence, a non-empty claim Key, Takeaway
  and Topic; a contents line and a citation footnote have empty levels and their Full text; the prompt asks for
  `ONE sentence of at most 40 characters` and carries the six rules.
- In the in-app browser, a disposable Chinese paper with a crafted `layers/en.json` (one unit `l3: false`, one unit
  `glue`, a contents line and a footnote): at Brief the background unit and both apparatus lines were hidden and the
  second half of the page-break pair showed the first half's text joined to its own; at Key the background unit came
  back and the apparatus lines stayed hidden; at Full every unit and both apparatus lines were shown as written.
- `node --check textfold/web/reader.js`; `git diff --check` clean.
- `textfold-verifier` — one pass. It confirmed the English identity claim on every attempt (prompt, no-model levels,
  reply shapes, a mocked build on the stored paper) and found two blocking defects in the CJK passes: a contents line
  could become the page-break glue for the paragraph after it (fixed: `dress` steps over apparatus too), and a
  paragraph ending `……` was treated as cut and carried into the next (fixed: `…` is a whole ending). It also found
  the dot-leader false positive on a long `…………` argument (fixed: dot leaders need a page number), the translation
  budget overwritten by the source document (fixed: `section_ladder` keeps its budget; the build passes the
  document's), a topic losing `P2P` or `3.5` (fixed: the second-filler skip needs a filler, a decimal point is not an
  edge), atom tokens becoming `"[object Object]"` and losing the glue (fixed: atoms pass through, the glue goes before
  one), a note on a now-hidden unit scrolling to a zero rect (fixed: `go` steps to the level that shows it), a
  suppressed unit being translated (fixed: `translate.worded` skips it), a stepped-down unit still showing a Topic
  (fixed: an empty takeaway means no topic), and stale comments/docs (fixed). Its remaining disclosures (a translated
  view without `glue`/`l3`, the per-unit gate, the English-only reader hunks left to R15) are the Pitfalls below.

## Measured

| | before | after |
|---|---|---|
| Python tests | 318 | 354 |
| English `prompt_for` / `local` / `assemble` / `section_ladder` compared with `main` | — | 4 of 4 identical; 0 unit or chunk layers differ in a mocked build |
| Chinese sentences in the fixture → distinct levels, no model | — | 3 → 5 (Brief 1 sentence, claim Key) |

## Not measured

- **Zoom smoothness: unmeasured.** The reader hides units, joins a piece at Brief, computes `pieces` before the
  text/hot split and steps a hidden unit into view; all are in the `pieces`/`drawUnit` path the keyframe sandbox draws.
  No `tools/zoombench.py` run was made (it needs `playwright` and exported `out/compare/` pages, neither present), so
  the axis is not reported as unaffected.
- **No real model.** The Chinese prompt was inspected, not answered: whether a model returns Chinese to it, and how
  `translate.build` then treats a Chinese base, were not exercised. No real Chinese or Japanese paper is in this
  clone; the parser and ladder were exercised on Markdown imports and crafted layers.
- **The translated view.** A Chinese reader's `tr-zh` layer carries no `glue`/`l3`; the browser check used the base
  layer. A regenerated Chinese document's Chinese view was not checked.
- **The keyframe path.** The browser check was at rest at each level; a zoom between levels with a hidden unit or a
  glued first word was not observed. The `go` fix was reasoned and reviewed, not clicked.

## Pitfalls

- `l3` hides a background unit at Brief even with "keep my highlights" on; the early return runs before the marked
  passages are added. R15 removes `l3` (the zoom only adds), which also removes this.
- `view` takes `glue`/`l3` from the translation's lad when a translation is shown, and `translate.assemble` writes
  neither. A translated Chinese page therefore has no page-break join and no background hiding; regenerating that
  language does not help until the translation carries the same structural facts. `translate.worded` keeps a
  suppressed unit out of the gap-fill path, but the first translation pass still sends it, and an already-stored
  translation of one still has its own line at Key.
- The CJK branches are per unit/section, not per document: a Chinese paragraph inside an English paper takes the CJK
  rules, and an English unit with a Chinese quotation over 20% takes the CJK claim path. `budgets_for` samples the
  first 4000 characters, so a bilingual paper can get a Chinese prompt while its English units take the old local
  path. R15's `cjk_doc` makes the document the unit.
- `is_apparatus` is a set of patterns, not a parser: a Chinese argument line under 120 characters opening with ①, or
  with a dot-leader run and a trailing number, can still fold to nothing. It is gated to CJK units here. The tightened
  dot-leader rule requires a page number, so a contents line ending in a roman numeral or a five-digit page is missed
  (a miss, not a false positive).
- An apparatus unit has empty levels but keeps its card/notes; a note opened on it steps to Full.
- The prompt changed for CJK documents only; an English paper's cached replies still match. A Chinese paper generated
  before this change is not marked stale and keeps its old levels until generated again.
- `_widen` adds sentences 0 and 1 to `ev` when the first sentence after a glue is under six characters; with an old
  layer this cannot happen (no glue), and the evidence filter in `apply_en` still bounds the ordinals.
- `section_ladder` now keeps its caller's budget; the build passes the document's topic budget, a translation its
  language's. A new caller that passes nothing gets the English 3.

## Rejected

- **The ungated upstream port.** It changes every English paper's prompt, no-model Key and Brief (glue, hidden list
  items, dot-leader units folded away) until R15; the branch would merge a known English regression.
- **Waiting for R15 to do both.** R14's tests and the feature's goal would land with no behaviour, and the round asks
  for R14 first; the gate is the smallest way to keep this change one feature.
- **Writing every language's levels in its own language.** It would change the ladder's output language for all
  non-English sources, the `layers/en.json` contract and `translate`'s "English base" assumption; that is its own
  round, not this port.
