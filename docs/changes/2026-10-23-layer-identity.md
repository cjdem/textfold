# An English layer whose units no longer match the parse is read with local levels and reported stale

**Date:** 2026-10-23
**Branch:** `worktree-layer-identity`

## What and why

A stored layer is keyed by unit id. The ids follow parse order, and a mixed Chinese/English paragraph that crosses the
part boundary can be cut into a different number of parts when the sentence splitter changes, so every later id can
move onto another paragraph. `store.apply_en` matched stored levels by id alone and only dropped an evidence ordinal
past the end of the part, so after an upgrade an old paper could show another paragraph's takeaway and topic in a
unit while the reader reported nothing stale. Now a layer keeps a fingerprint of each unit; a unit whose fingerprint
no longer matches is read with its local levels, and the base — and any translation built on it — is reported stale.
A layer saved before fingerprints is trusted only when its unit ids are exactly this parse's. The fingerprint covers
the atoms a unit names, because a stored ladder names them by id and a parser change renumbers atoms.

## The change

- `textfold/store.py` — `unit_hash(u, atoms)` fingerprints what the reader will see for a unit: each token's words,
  an inline math's LaTeX, and an atom's id plus its visible text; spacing flags, unit id and role are not part of it.
  `save_en` writes `h: {uid: hash}` beside the ladders. `apply_en` attaches a stored ladder only when its fingerprint
  matches (a layer with no `h` is trusted only when its unit ids are exactly this parse's — an old layer's ids are all
  there is to check), falls back to `ladder.local` for each unit it cannot verify, and returns whether the stored
  ladder was used whole. `assemble` adds `en` to `meta.stale` when it was not, and marks every translation of that
  base stale too.
- `textfold/fold.py` — an export of a layer whose base fell back says so: `provenance.stale` is true (see
  `docs/format.md`) and the Markdown says the stored levels may no longer match the text and a paragraph that could
  not be matched may be read from the author's first sentences. A translation that merely rests on an older base is
  left to the reader's language menu, as before.
- `tests/test_layer_identity.py` — new, twelve cases: a layer whose units still match is used whole; a unit whose
  words changed is read with its own levels; an atom renumbered under the same visible text also falls back; a
  spacing-flag change alone keeps the layer; a layer saved before fingerprints with the same ids is used whole (a
  guard); an old layer whose ids moved puts no other paragraph's takeaway on this one (the audit's `u0, u1, u2`
  against `u0, u0~2, u2, u3`); that old layer through `assemble` is stale and every unit local; `save_en` keeps a
  fingerprint of every unit; a paragraph whose words changed is reported stale and read local end to end; a
  translation of that base is reported stale too; a translation merely on an older base is not marked in the export
  (the reader's menu reports that one); an export of a stale layer carries `provenance.stale` and says it in the
  Markdown.
- `tests/test_cross_process_writes.py` — a second layer writer in another process: two `save_en` calls leave one
  writer's layer whole, its `units` and `h` from the same save.
- `docs/DEVELOPMENT.md` — the layer notes say what `h` is, when a unit falls back to local, and when the layer is
  stale.
- `docs/format.md` — the provenance section defines `stale`.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: `h`, the local fallback, the stale report, and the old-layer rule.
- `docs/format.md` — updated: `provenance.stale`, since the export's written levels can be part local after a
  fallback and the machine-readable AI mark must not claim otherwise.
- `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no note or card reads `h`.
- `README.md` / `README.zh-CN.md` — not needed: the reader already labels a translation "outdated"; the English base
  now uses the same existing label. No new promise.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`, `docs/requirements/`,
  `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`,
  `.claude/agents/`, `CLAUDE.md`, `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency (hashlib is
  standard), version, platform, security, contribution, desktop or process change; this is a fix from the pre-push
  audit, not a new feature with a requirements document.

## Decisions

- Fingerprint the unit's words **and its atoms** — an id and the atom's visible text. The defect is that an id now
  names other tokens; a stored ladder also refers to atoms by id, so the same visible words under a renumbered atom
  are a different unit for the reader. Spacing flags are excluded: they change how the words are set, not which words
  the layer describes.
- Per unit, not per layer: a moved unit is read local while the rest of the layer still stands; this is what a parser
  change usually leaves.
- A layer with no `h` is trusted only when its id set equals this parse's. The audit's shape changes the id set
  (`u1` gone, `u0~2` and `u3` new), so the equality catches it; with no stored fingerprint there is nothing else to
  check, and attaching by the intersection is exactly the bug.
- `apply_en` returns whether the layer was used whole; `assemble` is the only caller that reports it. The pipeline
  ignores the answer because nothing on that path reports staleness.
- Stale covers the translations of that base: their units were keyed by the same ids. They are still applied — the
  translation file carries no fingerprint of the source it translated — but the language button says "outdated" and
  regenerating rebuilds them against the current parse.
- An export says `stale` rather than flipping `local` or `ai_generated`: after a fallback the written levels are part
  model-written and part the author's first sentences, and a single flag cannot honestly claim either whole. The
  Markdown carries the same sentence a reader sees.
- Regenerating replaces the layer and its `h`, which clears the stale mark.

## Concurrency and locks

`save_en` still writes one file through `store.write` under the same locks, with one more key in the same atomic
JSON, so `units` and `h` can never be from different saves. `apply_en` and `assemble` read layers and write nothing.
A two-process test now saves a layer with a non-empty `h` and checks the result is one writer's whole layer.

## How it was verified

- `python .claude/hooks/verify.py` — 497 tests, OK (42.7 s); `git diff --check` prints nothing.
- `tests.test_layer_identity` — 12 tests, OK; `tests.test_cross_process_writes` — 10 tests, OK.
- Against the base's `store.py` (a scratch tree from `3881bde`, the merge this begins from) eleven of the twelve
  fail: five error (four on the missing `store.unit_hash`, one `KeyError: 'h'` in the `save_en` test) and six fail —
  the old-layer same-id guard only on the new return value, and five on behaviour: the old layer whose ids moved, the
  old layer with a changed set through `assemble`, the paragraph whose words changed, its translation, and the
  export's `stale` flag. The twelfth, the translation-on-an-older-base export, passes there because the base's export
  has no `stale` key at all; it guards that the new key stays scoped. The two-writer test is not base-checked: it
  asks for `unit_hash` directly.
- The end-to-end tests rewrite `source.html` after saving a layer, so `assemble` re-parses the same id with different
  words, as a parser change leaves it.

## Not measured

- A real mixed Chinese/English paper with a layer made before this change, opened in the reader: the tests build the
  id shift by hand and rewrite a source; no browser session.
- The "outdated" label on the English button in the browser: `meta.stale` is asserted, the drawing is not.
- An atom renumbering produced by a real parser run: the atom case is built by hand; no parser was changed here.
- A real `textfold get` on a stale layer: the export is tested through `fold.document` and `fold.markdown`, not the
  command line.
- A stale translation's display: it is marked stale but its stored ladders are still applied; only the marking is
  tested.
- Zoom smoothness: no reader JavaScript is touched; unmeasured here (`tools/zoombench.py` needs `playwright` and
  exported comparison pages, neither installed).

## Pitfalls

- The fingerprint includes an atom's visible text, so a re-parse that normalizes math LaTeX (`x^2` to `x^{2}`) marks
  the layer stale although its words and ids still fit. Conservative: the model was asked about the old spelling.
- A layer saved before this change whose id set is unchanged but whose words changed cannot be detected; only layers
  written from now on carry fingerprints.
- In a layer with fingerprints, a stored unit this parse no longer has makes the layer stale while its matching units
  still use their stored ladders; a layer without fingerprints and with a different id set is read local whole.
- Section ladders are still attached by chunk id and are not fingerprinted; a parse that renames a section loses its
  ladder (`None`) rather than misfiling it, and LaTeX section ids are stable.
- Stored unit edges are still applied by id when the layer is stale; the links UI no longer exists, so a stale edge is
  not drawn.
- A translation made *after* the parse change while the old base was stale is rebuilt from correct text but is still
  reported stale, because its `base` is the old English version. Conservative, and regenerating clears it.
- `provenance.stale` marks only the base's mismatch with the parse. A translation whose base version is merely older
  is still shown as "outdated" in the reader's language menu but is not flagged by the export, as before this change.
- The flag can be true while every remaining paragraph kept its stored ladder (a unit the layer has but the parse no
  longer does), and a translation export can show translated paragraphs while the base fell back. The Markdown
  therefore says the levels "may no longer match" and a paragraph "may be" the author's first sentences, not that
  they are.
- `h` and `provenance.stale` are additive JSON keys; every reader ignores an unknown key, and the format's version
  stays 0.

## Rejected

- Fingerprinting only the words (`tokens.plain`): a renumbered atom with the same visible text kept the hash equal
  while the stored ladder's `{"a": id}` then resolved to another atom — a silent wrong summary, the exact defect this
  change exists to stop.
- A whole-parse fingerprint: any parser change would mark every layer stale even when every unit still fits.
- Hashing the stored ladder: it always matches itself.
- Rewriting old layers to add `h`: a writer nobody asked for, and the old words are no longer anywhere to hash.
- Dropping a stale translation's ladders: it would hide whole translated paragraphs over a unit or two of doubt;
  the stale label plus regenerate is the visible, reversible answer.
- Setting `provenance.local` or `ai_generated` for a stale export: the levels are mixed, and either flag would
  mislabel one part; `stale` says what is true.
- A lock or a version bump on `layers/en.json`: the file's writer is already serialized and the keys are additive.
