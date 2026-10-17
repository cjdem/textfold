# An English document is made with its Simplified Chinese version by default

**Date:** 2026-10-17
**Branch:** `worktree-default-zh`

## What and why

The reader generates one language at a time: whatever was picked on the
landing (the reader's own language by default). An English paper opened by a
reader whose interface is English, or generated before they switched, had no
Chinese version until they asked for one explicitly. Asked for: an English
material should get a Simplified Chinese version by default.

## The change

- `textfold/pipeline.py` — `generate(..., also_zh=False)`; after the language
  asked for is made, if `also_zh` and a model is configured and that language
  was not `zh`, the Simplified Chinese translation is built at the end of the
  same generation and saved (`tr-zh`). `_wants_zh(en, tr)` decides whether it
  still has to be: the English base is a layer with a version, and the
  Chinese one is missing, is no layer at all, or stands on an older base.
  An unreadable `tr-zh` (bad JSON, foreign encoding) is read inside the
  guarded block and counts as no layer, so it is remade and the save
  replaces it; the default pass never forces (a forced regeneration of
  another language reuses its cached replies).
- `textfold/translate.py` — `build` now returns `(cost, parts that failed)`.
  The default is saved only when nothing failed: a partial Chinese layer
  saved as current would never be completed, so it is left for the next
  generation (the successful parts stay cached).
- A failure in this default does not fail the job: the exception is logged
  (`the Simplified Chinese version could not be made (...)`) and the
  generation of the requested language still finishes `done`; a stop
  (`llm.Stopped`) still stops everything.
- `textfold/server.py` — the app's generation passes `also_zh=True`. The
  command line (`python -m textfold get`, `export`) does not: the default
  belongs to the app, not to every caller of the pipeline. The default runs
  under its own `zh` stage, labelled in all twelve languages, so the
  progress card does not say "Translating · Français" while it translates
  Chinese.
- `docs/DEVELOPMENT.md` — the sentence that said "nothing is generated
  unasked" now names its one exception.
- `tests/test_default_zh.py` (new, 14 tests) — the rule (no base, missing
  layer, corrupt layer, current base, older base); the generation itself,
  with the model calls stubbed (an English generation also makes `zh`; a
  current `zh` is not made again; asking for `zh` makes it once; `also_zh`
  off makes none; no model makes none; a failing default leaves the job
  done; an unreadable layer is remade; a partial pass is not saved); and the
  app's wiring (the job runner's `pipeline.generate` call carries
  `also_zh=True`).
- `CLAUDE.md` — 118 tests.

Every document in this reader has an English base (it is what translations
are built from), so the rule applies to all materials, not only papers whose
original language is English. A `zh-Hant` generation also gets the
Simplified default — the two are different translations and the reader may
want either; stated here as the product decision it is.

## How it was verified

- The 14 tests run the real `pipeline.generate` against a stored page with
  the ladder, links and translation builds stubbed, so the branch that decides
  and saves the Chinese version is exercised, not only the predicate; the
  wiring test drives the real `Jobs` class with `pipeline.generate` stubbed
  and asserts the app's call carries `also_zh=True`. On `main` the predicate
  tests fail with `AttributeError`, the generation tests with
  `TypeError: generate() got an unexpected keyword argument 'also_zh'`.
- `python .claude/hooks/verify.py` — **118 tests, OK**.
- `textfold-verifier`, two passes. The first reviewed an earlier design in
  which the server queued a *separate* `zh` job after a finished generation.
  It showed three real problems: the reader page watches any live job for its
  paper and, on completion, navigates to that job's language and switches the
  interface language (`app.js`), so the unasked job would have moved the
  reader to Chinese; an exception in the post-success hook turned an
  already-finished job into `error`; and a user's stop of the Chinese job was
  forgotten by the next generation. It also found the check-then-act race,
  FIFO ordering, and that no test covered the wiring. The design was
  replaced by the in-pipeline one, which removes the extra job and with it
  the UI, race, ordering and stop problems. The second pass verified that
  redesign and found two survivors, both fixed here: the `tr-zh` read sat
  outside the guarded block (a corrupt layer failed the whole job), and a
  partial Chinese pass was saved as current (never completed); it also noted
  the progress card's misleading label (now its own `zh` stage), the forced
  pass (now never forced), a versionless English base (now no default), the
  untested wiring (now tested), and two wrong statements in this record
  (corrected). The fixes made after that second pass were not re-verified
  independently; the record says so rather than implying a clean third pass.

## Not measured

- **No end-to-end generation ran in this session** (a `claude -p` spawned
  from inside this session carries host-auth variables and answers "Not
  logged in"), so the Chinese pass was not observed against a real model; the
  decide-and-save path is tested with stubs, and the model call behind it is
  the one every translation already uses.
- **The default's failure note is not shown in the app.** It is a line in
  the job's log (`/api/jobs` JSON, and the server's own history), and the app
  renders no job logs; a reader whose default failed sees the requested
  language done and no Chinese version, without a message. Deliberate — the
  default is unasked — but stated rather than implied.
- **Smoothness: unmeasured.** No file the reader loads was changed, but
  `tools/zoombench.py` needs `playwright` and an exported page under
  `out/compare/`, neither on this machine, so the axis is not reported as
  unaffected.
