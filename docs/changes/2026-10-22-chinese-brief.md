# Chinese sentences end at 。！？, so Brief shows one sentence

**Date:** 2026-10-22
**Branch:** `worktree-chinese-brief`

## What and why

`split_sentences` only ended a sentence at `. ? !`, and required a space and a capital to follow. Chinese is written
without spaces and ends a sentence at `。！？`, so a Chinese paragraph parsed as one sentence: every level below Full,
Brief included, repeated the whole paragraph, and the ladder's numbered evidence offered one choice. This ports
upstream `770fb08`'s splitter for units that contain CJK, keeps the older splitter for English units so no existing
English paper's sentence numbers or parts move, brings forward `4897e24`'s guard that keeps an unspaced paragraph one
unit, and makes Full the unit's own text rather than sentences joined by spaces. A paragraph that mixes Chinese and
English can still change its part count: its sentence count is what changed, and its stored layers are knowingly left
stale until the paper is generated again.

## The change

- `textfold/tokens.py` — `split_sentences` dispatches on the unit's text: no CJK character and no `。！？` takes
  `_split_sentences_latin` (the old function, unchanged), either one takes `_split_sentences_cjk` (upstream `770fb08`:
  stops are `.?!` plus `。！？`; a run of stops and closing quotes/brackets (`" ” 」 ） 】 }` …) stays with the sentence;
  a CJK sentence needs no space or capital after the stop; an ASCII stop inside Chinese also ends a sentence; the
  abbreviation and initial guards for `.` are unchanged).
- `textfold/parse.py` — `cjk_heavy(toks)` (CJK characters — Han and kana, the tokenizer's own class — more than 20% of
  the unit's text) and a long unspaced paragraph is not cut into parts at 12 sentences, because a cut part takes the
  next free unit id and every later id would shift under its stored layer.
- `textfold/store.py` — `apply_en` drops a stored evidence ordinal that points past the end of the part it is applied
  to, and the first sentence stands in when none is left; a stored entry that is not a non-empty object falls back to
  the local ladder. A sentence split out before it can make a stored English paragraph cross the 12-sentence point and
  be cut into shorter parts; the reader indexes sentences with `ev`, and an out-of-range number threw there.
- `textfold/fold.py` — `full` is `_text(toks, A)`, the unit's tokens as written; the old `" ".join(sentences)`
  inserted a space between Chinese sentences (and could add one where the source had none).
- `tests/test_tokens.py` — upstream `770fb08`'s ten boundary tests (Chinese without spaces, fullwidth and ASCII stops,
  mixed languages, quotes and brackets, repeated stops, final closers, decimals/semicolons, abbreviations, `Fig. 2`
  inside Chinese), one pinning the English side of the dispatch (an ASCII apostrophe and a run of closing quotes and
  brackets after a stop do not end an English sentence), and one where a `。` alone selects the Chinese rules.
- `tests/test_chinese_brief.py` — five tests: the no-model Brief is the first sentence and Full is verbatim; evidence
  `[1]` survives `save_en`/`assemble`/`document`/`markdown` with inline math; a 15-sentence Chinese paragraph stays one
  unit with valid ranges and the following paragraph keeps `u1`; a 15-sentence Japanese paragraph stays one unit; a
  15-sentence English paragraph is still cut into `u0, u0~2, u0~3`.
- `tests/test_stored_evidence.py` — a stored evidence `[9]` on a two-sentence unit becomes `[0]` when the layer is
  applied, and the Brief is the first sentence; an empty stored ladder falls back to the local one.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the `tokens.py` map line names both stop sets, and the stored-number paragraph now
  covers sentence ordinals (the reinterpretation of old Chinese layers, the part-count risk for mixed paragraphs, the
  out-of-range fallback, and what the dispatch does to English).
- `README.md`, `README.zh-CN.md` — not needed: both already promise 1–3 verbatim key sentences; this makes that true
  for Chinese.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no field or format change; the
  contracts already say `brief` is the author's sentences at `evidence` and `full` is verbatim.
- `docs/upstream/2026-10-22.md` — not changed: the review is the source for this round, not current behaviour.
- `site/`, `desktop-mygo/` — not needed: no endpoint, string or shell change; the payload copies `textfold/` when built.
- `SECURITY.md`, `pyproject.toml`, `requirements.txt` — no change.

## Decisions

- **Dispatch rather than one splitter for every unit.** Upstream `770fb08` changes pure-English boundaries too: ASCII
  `'`, `}` and a run of closers (`.")`) now end a sentence there. On a paragraph over 12 sentences that can change the
  part count and shift every later unit id, landing stored English layers on other paragraphs. A unit with no CJK
  therefore keeps the old function exactly; only a unit that contains CJK takes the new rules. This is a deliberate
  divergence from upstream's single function, recorded so R14/R15 do not "restore" it.
- **Take `4897e24`'s `cjk_heavy` guard now, though R14 owns the commit.** Without it, the first Chinese paragraph over
  12 sentences becomes parts; every later positional unit id shifts, and a stored layer, card and note anchor then
  name another paragraph. The guard is ten lines and R14 will not take that hunk again; its folding work is untouched.
- **Existing Chinese layers are reinterpreted, not migrated.** Evidence is a sentence ordinal, so a stored `[0]` now
  means the first sentence instead of the whole paragraph — exactly the Brief those layers were meant to show. A
  translation stored before this keeps its own single sentence for the paragraph and shows the old Brief until it is
  made again; nothing is rewritten, and a migration would be a new writer of `layers/en.json` needing its own
  serialization test.
- **Mixed paragraphs are knowingly left stale.** A paragraph containing both scripts can change its sentence count
  across the cut threshold, so its part count and later unit ids can move. There is no content mapping here; the paper
  is regenerated when that matters, and the record and `docs/DEVELOPMENT.md` say so.
- **Out-of-range evidence falls back at assemble time.** The source-language reader does not filter `ev` (the
  translation path does), so a shrunk part could throw while drawing Brief. Dropping the number there protects the
  page, the payload and exports at once; a reader-only filter would leave `fold.document` and any later consumer
  exposed. A stored entry that is not a non-empty object is treated as absent and gets the local ladder, as before.
- **Full is the unit's tokens, not a join.** The join inserted a space between Chinese sentences, contradicting
  `docs/format.md`'s verbatim promise. English Full is unchanged: a sentence boundary there exists only where the
  source had whitespace, which the tokens still carry.

## Concurrency and locks

None: `split_sentences`, `cjk_heavy` and the evidence filter are pure functions over a parse at read time, and this
change writes no file, cache or setting. The stored-data consequence above is a change of interpretation, not a new
writer; the existing generation/translation/`store.LOCK` rules are untouched.

## How it was verified

- `python .claude/hooks/verify.py` — 318 tests, OK (baseline 299; 19 new).
- `python -m unittest discover -s tests -p "test_tokens.py" -v` — 12 tests, OK; `-p "test_chinese_brief.py" -v` — 5
  tests, OK; `-p "test_stored_evidence.py" -v` — 2 tests, OK.
- old vs new `split_sentences` on 98 English paragraphs (README, CONTRIBUTING, DEVELOPMENT, WORKFLOW, format) and 8
  edge cases (`Dr.`, `et al.`, `Fig. 2`, `?!`, `}`, a closing quote): 0 differences. After the dispatch this is by
  construction for a unit with no CJK; the comparison is the check that the dispatch selects the old function.
- `textfold get` on a disposable `TEXTFOLD_DATA` with `TEXTFOLD_NO_MODELS=1`: Brief printed `这是背景。`; Full printed
  `这是背景。实验显示吸附量下降。这个结果支持结论。` with no inserted spaces.
- `git diff --check` clean.
- `textfold-verifier` — one pass, then a narrow re-check. The first pass found two blocking problems, both addressed:
  pure-English boundaries moved around `'` and closer runs (fixed by the dispatch, with tests), and the guard's
  "no later unit id shifts" claim was false for mixed and previously cut paragraphs (fixed in the record and
  `docs/DEVELOPMENT.md`; the risk is stated, not denied). It also found the empty-ladder fallback (fixed), Japanese
  kana not counted by the guard (fixed: the tokenizer's CJK class), and weak long-paragraph assertions (fixed: the
  following paragraph's id and the English part ids are pinned). A narrow re-check confirmed both blocking findings
  resolved, a 30k pure-ASCII fuzz with 0 range differences from `main`, and no new defect; it noted the wording for a
  bare `。！？` selecting the Chinese rules, now fixed here and in `docs/DEVELOPMENT.md`.

## Measured

| | before | after |
|---|---|---|
| Python tests | 299 | 318 |
| English paragraphs and cases with a changed sentence boundary | — | 0 of 106 |

## Not measured

- **Zoom smoothness: unmeasured.** The change is in the parser, the layer application and the format export, not the
  reader's rendering code; no `tools/zoombench.py` run was made (it needs `playwright` and exported `out/compare/`
  pages, neither present here), so the zoom axis is not reported as unaffected.
- **No real model or translation.** The suite and the manual check are model-free; a translated Chinese layer
  regenerated after this change, and a model returning a different sentence count than the prompt listed, were not
  exercised. `translate.py` already warns and truncates on a count mismatch.
- **The reader page was not opened.** The server-side sentences, the payload's evidence and the exports are covered;
  no JavaScript changed.
- **No real Chinese or Japanese paper from the library was opened.** The parser was exercised on Markdown imports and
  the test documents only. The one stored paper here is English and has no CJK.

## Pitfalls

- The dispatch is per unit: one CJK character or a bare `。！？` in an otherwise English unit switches the whole unit
  to the Chinese rules, so its English boundaries, part count and later ids can move. A unit with neither is unchanged.
- `cjk_heavy` is a text heuristic (CJK > 20%), not a document flag. A paragraph that mixes the scripts and crosses the
  threshold stays one unit even if the old parse cut it, so its part count changes in the other direction too.
- `cards.fingerprint` hashes unit ids and text but not sentence ranges, so an old Chinese card is not marked stale
  while its evidence now points at a sentence rather than the paragraph. Card evidence clamps out-of-range numbers and
  re-checks the quoted text, so it does not crash. Notes made in the same language use their stored token range; a
  note read in the other language falls back to `sents` and now marks the first sentence instead of the paragraph.
- A stored `ev` that is still in range but now means another sentence cannot be told apart from a correct one; the
  fallback only handles numbers past the end.
- A translation made before this change is not marked stale (`store.assemble` compares the English layer's version,
  which did not change) and `translate.gaps` cannot see it; only regenerating that language repairs it.
- R15's `1.研究背景` guard is deliberately not here: until it lands, a number followed by `.` at the start of a Chinese
  unit still ends a sentence.
- Do not take `4897e24`'s own `tokens.py` in R14: it is written against the old splitter and would undo the dispatch.
  R15's two-line guard belongs inside `_split_sentences_cjk`.

## Rejected

- **A literal `770fb08` port for every unit.** It changes pure-English boundaries and can shift English unit ids on a
  long paragraph; the verifier reproduced the shift. The dispatch keeps English exactly as it was.
- **A separate module for the Chinese splitter.** `docs/DEVELOPMENT.md` places the sentence splitter in
  `textfold/tokens.py`; the two private functions and the dispatch stay there.
- **Migrating stored Chinese layers.** It would rewrite `layers/en.json` without the user asking, needs the generation
  queue or `store.LOCK`, and needs a two-writer test; reinterpretation is enough and the reader now shows the intended
  sentence.
- **Leaving Full as `" ".join(sentences)`.** It would insert spaces into every Chinese Full export, breaking the
  format's verbatim promise.
- **Filtering out-of-range evidence only in `reader.js`.** The source view would stop throwing, but the payload and
  `fold.document` would still carry an ordinal no sentence backs.
