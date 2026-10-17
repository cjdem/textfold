# Reading card format (`textfold/cards`, version 1)

A reader's reading card for one document: four sections of separately checkable points, each with the passages that
support it. One file per document, `papers/<id>/card.json`, beside its generated layers and its notes. It is the
reader's data, apart from `notes.json`: editing a card never changes a highlight, a note or a question, and changing
those never touches a card. Under `TEXTFOLD_DATA` the same path is used in that data folder; a document moved to
`papers/.trash/` carries its card with it and has it again when restored.

The four sections, in order, are fixed by `cards.KEYS`:

| Key | Section |
|---|---|
| `problem` | Research question and contributions |
| `method` | Method and assumptions |
| `setup` | Data and experimental setup |
| `results` | Results and limitations |

```json
{
  "format": "textfold/reading-card",
  "version": 1,
  "paper": {
    "id": "2512.23916",
    "version": "v1",
    "title": "…",
    "url": "https://arxiv.org/abs/2512.23916v1"
  },
  "lang": "en",
  "created": "2026-10-18T09:00:00Z",
  "updated": "2026-10-18T09:04:12Z",
  "rev": 7,
  "source": {
    "fingerprint": "sha256:…",
    "version": "v1",
    "at": "2026-10-18T09:00:00Z"
  },
  "generation": {
    "at": "2026-10-18T09:00:00Z",
    "model": "provider/model",
    "lang": "en",
    "fingerprint": "sha256:…",
    "version": "v1",
    "parts": 3,
    "failed": 0,
    "partial": false,
    "note": ""
  },
  "sections": {
    "problem": [
      {
        "id": "c-k3f9a2qx",
        "text": "The paper asks whether …",
        "state": "found",
        "origin": "model",
        "edited": false,
        "verified": false,
        "issue": "",
        "gen": {
          "at": "2026-10-18T09:00:00Z",
          "model": "provider/model",
          "fingerprint": "sha256:…",
          "lang": "en"
        },
        "evidence": [
          {
            "doc": "2512.23916",
            "unit": "S1.p2",
            "section": "S1",
            "quote": "…the authors' words…",
            "sents": [0, 1],
            "page": null,
            "block": null,
            "lang": "en"
          }
        ]
      }
    ],
    "method": [],
    "setup": [],
    "results": []
  },
  "candidate": null
}
```

## Card fields

- **format**, **version**: `textfold/reading-card`, `1`. A reader accepts a missing `format` for a hand-written card
  in this shape, but writes both fields on every save.
- **paper**: what the document was when the card was made: id, version, title, URL. It is a copy for reading and
  export; the live document's metadata comes from `meta.json`.
- **lang**: `en` or `zh`. It is the language of the card's own text, independent of the language the reader is reading
  the document in. A saved card keeps its language when the interface or the document's language changes, and a
  candidate in another language is not merged into a card that already has items (`language-mismatch`); replace the
  card instead.
- **created**, **updated**: ISO 8601 UTC timestamps.
- **rev**: a revision number for the card's own content, incremented when its sections, evidence or source stamp
  change. A save carries the `rev` it was made from; a different stored `rev` is refused (`stale-card`) so a slow
  request cannot overwrite a newer edit. Writing or discarding a candidate does not change `rev`: a draft is not the
  card, and a save made while the model was reading keeps the candidate.
- **source**: the document fingerprint and version the card was last accepted against, and when. When the document's
  own units, blocks or section metadata change, or its version changes, the card is shown as needing review; nothing
  in it is dropped. Regenerating a layer or a translation alone does not change the fingerprint.
- **generation**: the last model draft that became this card: when, which model, its language, the fingerprint and
  version it was drafted from, how many parts it read, how many failed, whether it is partial, and a note
  (`part-failed`). It is `null` for a hand-made card. Adopting a candidate replaces it.
- **sections**: the four keys, each an array of items, in the reader's order. A key always exists; it may be empty.
- **candidate**: `null`, or a complete draft with the same `generation` fields plus `sections`. It is not part of the
  card's content until the reader adopts it. A new draft replaces an older candidate, never the card.

## Items

- **id**: stable for the life of the item, `c-…`. A candidate adopted into a card keeps its own ids; a candidate item
  whose text already exists in the card adds its evidence to that item and is not duplicated.
- **text**: one point, plain text. Empty items are dropped on save unless their state is `missing` or `na`.
- **state**:
  - `found`: the document states it.
  - `missing`: this section's information was not clearly stated. The text says what is missing.
  - `na`: the section does not apply to this document. The text gives the reason.
  - `check`: contradictory, ambiguous, or a number, unit, formula or table that could not be read reliably.
- **origin**: `model` or `user`. An item the reader creates is `user`; a model item the reader changes keeps
  `origin: "model"` and gets `edited: true`.
- **edited**: a model item whose text, state or evidence the reader changed.
- **verified**: the reader has checked this item. Model items start `false`. Editing the text or the evidence clears
  it. Saving an item unchanged keeps it, even when the client omits the field.
- **issue**: `no-evidence` or `bad-citation` on a model item that claimed `found` without usable evidence. It is
  cleared when valid evidence is added or the item is no longer `found`.
- **gen**: for a model item, the draft it came from (`at`, `model`, `fingerprint`, `lang`). User items and candidates
  that the reader wrote have no `gen`.
- **evidence**: zero or more passages (see below). A hand-written item may have none; the reader shows "No source
  linked". A model item with no valid evidence is not shown as `found`.

## Evidence

- **doc**: the document id.
- **unit**: the parsed unit the passage is in (a paragraph, list item or caption), or `null` in a hand-written record
  that has no anchor. A unit that no longer exists makes the reference **broken**: the item and its excerpt are kept
  and shown, with a way to link it again.
- **section**: the section id the unit was in when the evidence was made. It is informational; the section is read
  from the document again whenever the card is shown.
- **quote**: a short excerpt in the authors' words, for the reader to compare and for finding the passage again. A
  quote that is no longer in its unit's text is **mismatched**: it is kept and shown, never silently replaced.
- **sents**: zero-based sentence numbers in the unit. Sentence numbering is shared by the document's languages, so a
  passage selected in a translation points at the same sentences in the original.
- **page**: the PDF page, only for a converted PDF whose layout maps the unit; otherwise `null`. The server computes
  it; a page sent by a client is ignored.
- **block**: the block id of a figure or table caption, when the unit has one; otherwise `null`.
- **lang**: the language the excerpt was taken from.

The server recomputes `section`, `block` and `page` from the document on every save and whenever it shows the card, so
a citation cannot name a page that is not in the document, and a re-converted PDF's moved unit gets its new page. The
reader's view adds `broken`, `mismatch`, `label`, `sectionNum`, `sectionTitle` and `recheck` to a copy; none of those
is stored.

## Writing and the model

The model is given the document's own units, the outline and the table text, in parts for a long document. It
returns items for the four sections, each with unit numbers as evidence. A reply that is not the asked-for shape
fails that part; the other parts are kept and the card is marked partial and visibly incomplete. A model item that
claims `found` with no valid unit is turned into `check` with an issue. When no part yields a usable item, generation
fails and the card is untouched. A stop during generation leaves the card exactly as it was.

No card exists: the first complete or partial result becomes the card, with `source` set and its partial state shown.
A card exists: the result becomes `candidate`. Adopting it can merge the candidate's items into the card (the
default) or replace the card's sections. Merging keeps the reader's items and adds only points whose text is not
already there; a placeholder (`missing` or `na`) is not added to a section that already has content. A candidate in
another language cannot be merged into a non-empty card; it can replace it. Discarding a candidate removes only the
candidate.

## Server operations

`GET /api/card/<id>` returns the payload: `exists`, `document` (title, authors, date, year, URL, DOI, version,
citekey, kind), `fingerprint`, `model` (whether generation is possible), `titles`, `hints`, `exportName`, the
card (`sections`, `counts`, `candidate`, `stale`, …) or empty sections when there is none.

`POST /api/card/<id>` takes one of:

| `op` | Body | Effect |
|---|---|---|
| `create` | `lang` | a blank card, unless one exists |
| `save` | `card: {rev, lang, sections}` | validate and save; `stale-card` if `rev` is not current |
| `evidence` | `item`, `anchors`, optional `drop` | add selected passages, replacing evidence at index `drop` |
| `adopt` | `mode`: `merge` or `replace` | the candidate becomes part of the card |
| `adopt_item` | `id` | one candidate item is merged into the card |
| `discard` | — | drop the candidate |
| `review` | — | the changed document is accepted as the card's source |
| `generate` | `lang` | start a generation job (not an `apply_op`); requires a model |

An unreadable `card.json` is copied aside as `card.bad-<time>.json` before a new card can be written; the reader is
not shown a damaged file as an empty card without that copy existing. A candidate whose shape cannot be drawn is
dropped from the view, leaving the card itself intact.

## Markdown

The export is made from the decorated saved card, without calling a model: YAML front matter (`title`,
`card_language`, `updated`, `format`), the document's bibliographic fields, the card's language and timestamps, the
generation line when there is one, any stale or broken-reference notice, then the four sections. Each item has its
origin, state, check mark and recheck mark, its text, its draft line for model items, and its evidence as a quote and
a TextFold link (`#u=<unit>&b=<block>`). A broken reference keeps the quote and has no link. A section that a partial
draft did not read says so instead of claiming there is nothing.
