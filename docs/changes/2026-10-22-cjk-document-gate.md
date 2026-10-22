# The CJK rules belong to a Chinese or Japanese document, and the zoom only adds

**Date:** 2026-10-22
**Branch:** `worktree-cjk-document-gate`

## What and why

R14 gave a Chinese paper five levels, but gated the CJK rules per unit: a Chinese paragraph inside an English paper
took the Chinese budgets, a bilingual paper could get a Chinese prompt with English units, and a paper mostly in
English with one Chinese quotation took the claim-sentence path. It also put the reader's CJK-only changes behind
per-unit flags, and the background hiding used `l3: false`, which a zoom could not undo — at Brief a background unit
was gone even with "keep my highlights" on, because the hiding happened before the marked passages were added. This
ports upstream `6e2cada`: the document is the unit, `meta.cjk` tells the reader, the reader's CJK rules (footnote
markers, the page-break join, the apparatus lines, the reference heading, the section summary at Brief, an empty
stake row) apply to such a page only, and `l3` is removed — a stepped-down unit is read at Brief and Key and hidden at
Takeaway and Topic, so the zoom only adds. A number and its stop at the head of a CJK sentence (`1.研究背景`) no
longer end a sentence.

## The change

- `textfold/ladder.py` — `cjk_doc(doc)` says what `budgets_for(doc) is CJK_BUDGET` already decided, in one place:
  a document whose first 4000 characters are more than 20% CJK. `prompt_for`, `build` and `store` call it; `build`
  passes its answer to `assemble`/`local` for every unit, and `apply_en`/`assemble` pass it for a stored or a local
  layer. `fold_background` and `dress` return at once unless it is true. `dress` keeps only the page-break half (its
  `l3` sieve, `LISTY` and `_listy` are gone), joins a pair only when both halves are CJK, and its docstring says so.
- `textfold/store.py` — `assemble` sets `meta["cjk"] = True` for such a document (nothing is stored; the parse is
  re-read every time) and passes the document's answer to `local`; `apply_en` does the same for a unit the stored layer
  has no entry for.
- `textfold/tokens.py` — `_split_sentences_cjk` does not end a sentence at a stop that follows a lone digit at the
  head of a CJK sentence, so `1.研究背景与意义。` is one sentence and the heading keeps its number.
- `textfold/web/reader.js` — `CJK_DOC` from `meta.cjk` (and `doc.cjk` on the page and in the keyframe sandbox) gates
  every CJK-only rule: the footnote-marker strip at Brief, hiding an apparatus unit below Full, a stepped-down unit
  showing no Topic, the reference-heading section, the section summary at Brief, the empty stake row and the scrolling
  contents card at Topic. `view` carries `glue` only; the L3 `l3` early return is gone; the "keep my highlights" early
  return is before any hiding, as it was. In the hot path a unit's pieces are computed once (upstream computes them
  twice on a CJK page: once to know whether the unit exists at this level, once to draw it); the not-hot keyframe draw
  still computes them again inside `textHtml`.
- `textfold/web/reader.css` — `.doc.cjk[data-level="3"] .stake` (the section's line at Brief), the scrolling contents
  card at Topic, and `.doc:not([data-level="4"]) .chunk.ref` (a reference heading the converter made into an empty
  section).
- `tests/test_cjk.py` — upstream `6e2cada`'s 26 tests: the three `l3` tests go, the heading test and
  `TestEnglishAsBefore` (the English prompt, no apparatus, no glue, no `cjk` in the meta, an English section not
  dressed) arrive. One fixture was adapted: `"We sum over i = 1, ..., N to get the loss."` is no longer dot leaders
  (R14's rule needs a trailing page number), so the test that shows an English dot-leader-looking line still folds
  uses `"… the loss. 12"` and asserts the apparatus reading explicitly.
- `tests/test_chinese_levels.py` — the round-trip test keeps `glue` and no longer writes `l3`; two tests are new: a
  Chinese document's page is marked (`meta.cjk`) and an English one is not, and a Chinese unit in an English document
  takes the English path (first-sentence Brief, an apparatus-looking line folding normally).

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the reader paragraph (a CJK document's folded levels, `meta.cjk`, the stepped-down
  unit read at Brief and Key), the splitter paragraph (`1.研究背景`), and the stored-sentence paragraph (`glue` only;
  an old `l3` is ignored).
- `docs/format.md` — no change: `cjk` is a page's meta, not an export field; `glue` is a layer internal.
- `README.md`, `README.zh-CN.md` — not needed: no level's meaning changed for the reader; a stepped-down unit now
  appears at Brief instead of being hidden, which is the promised "a zoom only adds".
- `docs/upstream/2026-10-22.md` — not changed: it is the round's review, not current behaviour.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/` when built; no endpoint or string changed.

## Decisions

- **The document, not the unit, decides.** `cjk_doc` is `budgets_for(doc)` by another name, so the prompt, the units
  and the section passes cannot disagree. A Chinese paragraph in an English paper folds in English words and gets the
  first-sentence Brief; an English paper is exactly what it was. The cost is that a genuinely bilingual paper reads
  in its majority language throughout — recorded in Pitfalls.
- **`l3` goes rather than moving to the reader.** The zoom's promise is that it adds. A unit the section's own line
  already summarises is no longer hidden at Brief; its takeaway is empty, so Topic has nothing to show. At Brief it is
  read, which is what the upstream commit asks for, and a layer generated by R14 that carries `l3: false` is simply
  read (the key is ignored, no migration and no staleness marker).
- **The reference-heading rule is document-level too.** Upstream applies it to every page; here an empty section whose
  title is `[X/OL]` or a URL is dropped below Full only for a CJK document, so an English paper's headings do not
  disappear. The CSS selector itself is not gated, but no English page gets the class.
- **Keep R14's fork fixes.** The tightened dot-leader rule, `…` as a whole ending, `dress` stepping over apparatus,
  `section_ladder` honouring its caller's budget, the topic's `P2P`/`3.5`, atoms in glue, `go` on a hidden unit and
  `translate.worded` skipping a suppressed unit are unchanged; R15's tests carry them where they interact. `dress`
  gains one guard the verifier's finding asked for: a pair is joined only when both halves are CJK, so an English
  paragraph inside a Chinese paper does not become `conditionThe`.
- **No new writer.** `meta.cjk` is computed in `store.assemble` and never written; `glue` lives in the same `lad`
  object `store.save_en` already writes; nothing new reads or writes `layers/en.json`.

## Concurrency and locks

None added. `store.assemble` only reads the parse and the layers; `meta` is rebuilt on every call. The generation
queue remains the only writer of `layers/en.json`, translations the only writer of `tr-*.json`, and `store.LOCK`
still covers trash, cards and conversion.

## How it was verified

- `python .claude/hooks/verify.py` — 362 tests, OK (R14 baseline 354: 26 upstream `test_cjk.py` tests replace 23;
  the fork's `test_chinese_levels.py` goes from 13 to 18 — the `l3` round-trip test becomes a `glue` one, and the
  document marker, the Chinese unit in an English paper, the English paragraph in a Chinese paper, the English
  opening and the store's own `cjk` argument are held).
- English identity: `ladder.prompt_for`, `ladder.local` and `store.assemble` were run from `main`'s package and this
  branch's package on an English fixture and on the stored English paper (92 units, 16 chunks); no difference in the
  prompt, no unit layer, no chunk layer, and no `cjk` key in the meta.
- Chinese, no model: `store.assemble` on a Chinese fixture marks `meta.cjk`; `ladder.local(u, atoms, False)` on a
  Chinese unit gives the first-sentence Brief (`[0,1,2,3,4]`), and `ladder.assemble(..., False)` on a footnote gives a
  non-empty Brief, which is the English path; the same with `True` takes the CJK path (the R14 tests).
- `node --check textfold/web/reader.js`; `git diff --check` clean.
- In the in-app browser, a disposable Chinese paper (a contents line, a footnote, a page-break pair, a paragraph with
  ① glued into its first sentence, a unit whose takeaway was set to step down): `#doc` carried `doc cjk`; at Brief the
  contents line and the footnote were hidden with no text left, the ① was stripped (`监管框架包括三项要求。`), the
  page-break unit read `而该条例的法律位阶为行政法规，加强了对第三方支付机构的监管力度。`, and the stepped-down
  unit was shown; at Topic the two apparatus units and the stepped-down unit were hidden; the empty stake row was
  hidden. A disposable English paper carried `doc` and no `cjk`, and at Brief its only unit was shown with its first
  sentence and nothing hidden. No console or server error. The `ref` section and the scrolling contents card were not
  produced by these fixtures (both need a converter-made empty section or a long contents card).
- `textfold-verifier` — one pass, no blocking finding. It confirmed the English identity end to end (the stored
  paper's 92 units and 16 chunks, every `prompt_for`, and a mocked `build` on five English and mixed fixtures), that
  no live layer carries `tn: 0` or `l3`, that `meta.cjk` is set only for a CJK document, that the CJK passes and R14's
  fixes are intact, that `pieces` run under Node behaves as described, that the tokenizer's heading guard changes no
  English split (`1. Introduction.` is three sentences as before), and that `test_cjk.py` differs from upstream only in
  the one adapted fixture. Its non-blocking findings and what was done with them: (1) `dress` used the document gate,
  so an English paragraph inside a Chinese paper was glued onto the next unit with no space
  (`The first conditionThe second condition.`) — fixed: `dress` leaves a pair alone unless both halves are CJK, with a
  test; (2) the 4000-character sample can read a Chinese body behind an English abstract as English — inherited from
  upstream, now pinned by a test that says so and in Pitfalls; (3) three reader behaviours differ from R14 only for an
  English unit with `ev: []`, `l3: false` or `tn: 0`, which R14 could not generate and the stored paper has none of —
  recorded below; (4) the heading guard is narrow (`“1.研究背景”。` still splits) — the comment and the docs say "at the
  head of a sentence", which is what it does; (5) the gate boundary and the store's `cjk` argument had no test — the
  latter now has one through `store.assemble` (a Chinese unit in an English paper keeps the first-sentence Brief); (6)
  the record overstated the single `pieces` call — corrected; (7) the round doc's tick and the sentence-renumbering
  warning for old layers — done (`docs/DEVELOPMENT.md`).

## Measured

| | before | after |
|---|---|---|
| Python tests | 354 | 362 |
| English `prompt_for` / `local` / `assemble` compared with `main` | — | 3 of 3 identical; 0 unit or chunk layers differ |
| Chinese page's meta | no marker | `cjk: true`; an English page carries none |

## Not measured

- **Zoom smoothness: unmeasured.** The reader now computes a CJK unit's `pieces` at a folded level even when it is
  not about to draw its text (the not-hot keyframe draw pays it twice), adds a class to the sandbox root, and hides an
  apparatus unit and an empty stake row before drawing. No `tools/zoombench.py` run was made
  (it needs `playwright` and exported `out/compare/` pages, neither present), so the axis is not reported as
  unaffected.
- **No real Chinese or Japanese paper and no model.** The parser and the ladder were exercised on Markdown fixtures;
  whether a model answers the Chinese prompt in Chinese, and how a real PDF's headings split, were not.
- **The translated view.** A translation layer carries no `glue`; the reader takes `glue` from the translation's `lad`
  when one is shown, so a translated Chinese page has no page-break join. The browser check used the base layer.

## Pitfalls

- A bilingual paper reads in its majority language throughout: an English paragraph in a Chinese paper takes the
  Chinese budgets and the claim-sentence Brief, and a Chinese paragraph in an English paper takes the English ones.
  `budgets_for` samples the first 4000 characters, so a paper whose abstract is English and whose body is Chinese is
  read as English throughout (`test_a_paper_that_opens_in_english_is_read_as_english`).
- A page break inside an English paragraph in a Chinese paper is no longer joined: `dress` leaves a pair alone unless
  both halves are CJK, because the reader's glue has no separator and English words are spaced.
- The heading guard renumbers sentences in a unit that begins `N.`; `store.apply_en` only drops an ordinal past the
  end, so an old layer's evidence can point at a neighbouring sentence. Regenerating the language fixes it.
- The reader's CJK-only decisions mean an English unit with `ev: []` is not hidden below Full, and one with `tn: 0`
  shows its topic at Topic. R14 could not generate either for an English paper, and no stored layer here has one; a
  hand-made layer that does would show it as before rather than hidden.
- An old layer with `l3: false` is read as if the key were not there: at Brief a background unit that R14 hid is now
  shown. That is the intended repair, but a paper read yesterday looks different today without being regenerated.
- An apparatus unit keeps its card and notes; a note opened on it steps to Full (`go`).
- The reference-heading rule matches the title, not the unit: a real section whose title is a bare URL would be
  hidden below Full on a CJK page.
- `is_apparatus` is still a set of patterns: a Chinese argument line under 120 characters that opens with ① or with
  dot leaders and a page number can fold to nothing. On a CJK document that is now the document's decision, not the
  unit's.

## Rejected

- **Keeping the per-unit gate and only adding `meta.cjk` for the reader.** It leaves a Chinese unit in an English
  paper on the CJK path and a bilingual paper with a prompt its units do not follow; the round asks for the document
  gate.
- **Migrating stored layers to drop `l3`.** Nothing reads the key now, so a migration would rewrite papers for no
  visible change; ignoring it is cheaper and reversible.
- **Hiding the stepped-down background at Brief in the reader.** It would keep R14's look but break the zoom's
  "only adds" promise, and the upstream commit removes it for that reason.
