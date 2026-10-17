# A reading card for every document

**Date:** 2026-10-18
**Branch:** `worktree-reading-card`

## What and why

A reader could keep highlights, notes and questions, but nothing that gathered what a paper asks, how it works, what
it measured and what it found into one editable record with a way back to the words. This adds that card: four fixed
sections, each point separately editable and checked, every generated claim tied to the document's own units. A
model drafts it, but a draft never overwrites the reader's card; it waits as a candidate. The card is the reader's
data, stored beside the notes and the layers and untouched by either.

## The change

- `textfold/cards.py` — the card file (`papers/<id>/card.json`, `textfold/reading-card` v1), evidence validation
  against the parsed document, generation in parts, candidates, adopt/merge/replace/discard, review, staleness
  fingerprint, Markdown export.
- `textfold/web/card.js`, `textfold/web/card.css` — the drawer: four sections, editing with auto-save and `rev`
  conflict handling, model/manual entrances, candidate view, evidence chips with jump/relink, export.
- `textfold/server.py` — `GET`/`POST /api/card/<id>`, and a card job on the generation queue with progress and stop.
- `textfold/web/reader.js` — selection-bar "Add to card", `jumpToEvidence` that opens a paragraph from any level,
  `#u=`/`#b=` deep links, and the reader context `card.js` uses.
- `textfold/web/i18n.js`, `textfold/web/app.js` — the card's English and Simplified Chinese words; a card job is not
  mistaken for a document generation in the sidebar.
- `textfold/models.py` — the `card` task, thinking `low`.
- `textfold/store.py` — one re-entrant lock around a document's card write and its move to the trash.
- `textfold/pdfdoc.py` — a re-converted PDF keeps its card, and holds that lock while the folder is replaced so a
  save made during the conversion lands after it.
- `textfold/build.py` — the app page loads the drawer's CSS and script; its own web files are read as UTF-8, which the
  new static-page test showed was needed on a Chinese Windows.
- `tests/test_cards.py` — 41 tests: storage and language, corrupt-card backup, editing and verification, evidence
  validation and relinking, page mapping, generation and partial failure, candidates, staleness, Markdown, no model.
- `docs/reading-card-format.md` — the data contract; `docs/DEVELOPMENT.md`, READMEs, `CLAUDE.md` and the requirement
  document updated.

## How it was verified

- `python .claude/hooks/verify.py` — 171 tests, OK, 6.8 s (130 before this branch).
- `git diff --check` — clean. `node --check` on `card.js`, `reader.js`, `i18n.js`, `app.js` — clean.
- In a browser on a synthetic document: the entrance, a hand-written card, auto-save and reload, a new point's state,
  adding a selected passage, evidence chips and their jump and relink, a candidate's review and adoption, Markdown
  export, a failed save and Retry, a changed document's review, `#u=` deep links, and the no-model card's manual
  entrance. A second server with `TEXTFOLD_NO_MODELS=1` showed the generation button disabled with its reason.
- Over HTTP against a temporary data folder: `GET /api/card`, `create`, `save`, `evidence` (the selected sentences
  became the authors' quote and the item went to `check`), `export` with its TextFold link, and a stale `rev` rejected
  with 400 `stale-card`.
- An independent `textfold-verifier` review reproduced three data-loss races — a candidate write invalidating a save
  in progress, a PDF re-conversion restoring its card snapshot over a save, and a save crossing the move to the
  trash. Each is fixed and has a regression test; the verifier's malformed-card, stale-candidate and focused-empty-
  field findings are fixed and tested too, and its re-check of the four bad-scalar reproductions found no remaining
  defect in that area.

## Not measured

- **Zoom smoothness: unmeasured.** `tools/zoombench.py` needs playwright, a browser and exported pages under
  `out/compare/`, none of which is on this machine. The drawer is fixed outside `#doc` and opening it lays nothing out
  in the document, but that is a design argument, not a measurement; no claim is made that zoom is unaffected.
- A real model's card quality, and a real model called through every provider: the tests use a stand-in reply.
- A converted PDF's page numbers against a real `layout.json`: the mapping is tested with a mocked `place`.
- The desktop app's save dialog and a narrow or mobile window.

## Rejected

- Keeping cards in `notes.json`: it would change the notes contract, and a card is not a highlight or a question.
- Writing a new generation straight over the card: it cannot be undone and would lose the reader's edits.
- Marking the card stale from layer or translation versions: regenerating those does not change the author's words,
  so evidence would go stale for nothing. The fingerprint hashes units, blocks and section metadata only.
- Trusting a client's section, block or page: the server reads all three from the document again.
- Reusing the question-answer size limit: a card needs its own parts and its own schema.
