# Generation no longer asks a model for argument links; stored ones still render

**Date:** 2026-10-18
**Branch:** `worktree-links-off`

## What and why

Item 4, first step, of the confirmed product scope. Every English generation used to make one
extra model call over the whole paper to add `supports` / `builds_on` / `qualifies` / `explains`
edges between units. The reading product does not need the model to invent that layer, and the
call costs time. Generation stops making it; the interface still draws the links stored in layers
that already have them, and author cross-references, Q&A evidence links and reading-card links
are untouched.

## The change

- `textfold/pipeline.py` — no import of `links`, no `progress("links")`, no `links.build` call;
  the docstring says the English ladder and the translation only.
- `textfold/models.py` — `TASKS` and `DEFAULT_THINKING` no longer contain `links`; the comment no
  longer says the links need thinking.
- `textfold/server.py` — the stages that mark a job readable no longer include `links`.
- `textfold/web/i18n.js` — the stage map loses `links` and both language arrays lose its label;
  `translate`, `done` and `zh` move up one slot.
- `textfold/links.py` — the module stays, uncalled, with a docstring note that generation stopped
  calling it on 2026-10-18, existing layers keep their links and the reader draws them, and a
  regenerated English layer has none.
- `textfold/store.py` — the layer description says `en.json` holds the English ladder and the
  argument links stored by older versions.
- `docs/DEVELOPMENT.md` — the thinking defaults, the "same paper always the same?" paragraph, the
  Links paragraph and the module map updated; the Links paragraph now records that a stored link
  names its units by id, so a parser change can make those ids name other paragraphs, and a
  regenerated English layer drops the links rather than carry them over.
- `tests/test_default_zh.py` no longer patches `pipeline.links`.
- New `tests/test_links_stopped.py` (4 tests): `links` is not a task or a thinking default;
  generation never calls `links.build`, reports no `links` stage, and saves a layer with no unit
  edges; a forced regeneration replaces the layer and its links; an old layer's unit edge is still
  applied when the paper is assembled.

## Decisions

- Keep `textfold/links.py` for now. Its functions still read and write the stored data, and the
  scope removes the interface that draws it in item 7; deleting the module belongs with that.
- Do not carry old links into a regenerated layer. Unit ids are positional when the source has no
  ids of its own, so after a parser change the same id can name a different paragraph; carrying
  edges by id would draw links between the wrong units. Regeneration has always replaced the
  English layer, so this is the same replacement with one kind of edge no longer regenerated.
- Leave `store.apply_en` as it is: old layers still apply their unit edges on open, with the
  existing existence check. The id-bound risk is documented rather than silently changed.
- Do not add a feature flag or a manual "rebuild links" command. The scope stops the default
  generation and removes the interface next; a flag would keep the capability alive.

## Rejected

- Keeping the call but hiding its output: it still costs the time and writes data the interface
  is about to lose.
- Carrying stored links through a forced regeneration by unit id: correct only while the parse is
  unchanged, and wrong without a visible error after a parser change.
- Deleting `links.py` now: the reader still draws stored links, and the format still describes
  them; item 7 removes the interface and then the module.
- Removing the author's cross-references or the evidence links in Q&A and reading cards: they are
  not argument links and are kept.

## What is lost

- New papers no longer get model-written argument links (supports / builds on / qualifies /
  explains), and one model call per English generation is gone with them.
- A forced regeneration of an English layer drops the links that layer had; the stored layer stays
  readable until it is regenerated.
- Author cross-references, Q&A evidence links, reading-card links and the rendering of stored
  argument links are unchanged.

## How it was verified

- `python .claude/hooks/verify.py` — **177 tests, OK** (6.9 s), of which four are new.
- `node --check textfold/web/i18n.js` — clean; evaluating the file in Node gives exactly
  `queued, fetch, parse, ladder, translate, done, zh` in both languages, with the Chinese labels
  on the shifted positions and no `links` key.
- The verifier's first pass found that the initial carry-over could attach stored links to
  different units after a parser change; the carry-over was removed and the test that assumed it
  was replaced. A second pass confirmed no carry-over remains, a fresh generation saves no unit
  edges, old layers still apply theirs on assembly, and `readable` is still set on every path.
- No parser, model, subprocess or encoding path changed; `git diff --check` is clean.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** no parser or semantic file changed; a fresh
  generation still gets the parse's cross-references at assembly.
- **Parser change renumbers atoms:** not applicable to this change, but the Links paragraph and
  the record now state its consequence for stored links: their unit ids can move, so a
  regeneration drops them instead of carrying them.
- **Persistent writes serialized per document:** no new writer or lock domain. `store.save_en` is
  still reached only from the single generation worker, and the write is the same tmp-plus-replace.
- **UTF-8 on a Chinese Windows:** the changed strings are UTF-8; the stage labels evaluate
  correctly in Node. No subprocess or file encoding changed.
- **No new dependencies:** requirements and package metadata untouched.

## Not measured

- Zoom smoothness: **unmeasured** on this machine (no `playwright`, no exported pages under
  `out/compare/`). The only reader file touched is `i18n.js` string data, but no claim is made
  that it is unaffected.
- The progress bar was not watched in a browser during a live generation; its stage map and
  labels were evaluated in Node, and the server's readable logic was exercised by the verifier.
- No real model call was made; the generation tests use stand-in tasks.
