# A model's reply is read whatever shape JSON mode gives it

**Date:** 2026-10-22
**Branch:** `worktree-reply-shapes`

## What and why

An OpenAI-compatible endpoint asked for JSON mode promises valid JSON, not the JSON Schema's shape. Models answer the
same question with the units as a list of objects (as asked), as a JSON string, as one JSON string, or as an object
keyed by unit id; a section as a string; the text of a reply as a list of parts. A generation that met one of these
failed, or raised while reading the reply and left the whole job failed, though the content was all there. This
change reads the shapes the providers actually return, and when a reply still cannot be read, treats that chunk as a
failed call: its units fall back to a local ladder, and the kept reply is dropped so a plain retry asks the model
again. A failed job's last log lines also go to stdout, which the MyGo app keeps as `server.log`.

## The change

- `textfold/llm.py` — `as_obj(v)` reads a reply part that should be an object, also from a JSON string;
  `units_of(out)` reads a reply's units as a list, a JSON string, a list of JSON strings, or an object keyed by id
  (the key is the unit's id, whatever the value says of itself), dropping what it cannot read. `call` now returns
  the kept reply's path as `"file"` (cached and fresh), and `forget(rec)` deletes that file, leaving it if another
  process holds it open.
- `textfold/llm_openai.py` — `_content(d)` returns a reply's text: `message.content` as a string, as a list of text
  parts (a reasoning part is not the reply), or a plain string message; `None` when the body is not a chat
  completion. `call` uses it for the reply and for the "not a completion, try the next shape" branch that R4 added
  inline. `_events` joins a streamed content list through the same `_join_parts`.
- `textfold/ladder.py` — `section_ladder` accepts a section written as a string, including one encoded as a JSON
  string twice. `build` reads the chunk's units through `llm.units_of`; a reply that still cannot be read is caught,
  logged, its kept reply is forgotten, and the chunk's units are left to the local ladder. Such a shape error is
  **not** counted as "nothing came back": a one-chunk document (a short note) still falls back locally instead of
  failing the job.
- `textfold/translate.py` — reads units through `llm.units_of` and the section through `llm.as_obj`. A part whose
  reply is not an object, or names no unit of that part (including a reply whose `units` is a string that does not
  parse, or an empty list), is a failed part: the kept reply is forgotten, any partial translation of that part is
  removed, and the caller is told the part failed. A shape error inside the per-unit reading is handled the same way.
- `textfold/pipeline.py` — the language the reader asked for now respects that failed count, as the default Simplified
  Chinese version already did: a partial translation is not saved as current, so the next run makes it again.
- `textfold/links.py` — a link list entry that is not an object is skipped, as a bad link already was.
- `textfold/server.py` — a failed job's last 12 log lines are printed to stdout (`flush=True`), which MyGo writes to
  `server.log`.
- `tests/test_reply_shapes.py` — new: units as asked and in their other shapes, the keyed id winning; what cannot be
  read is dropped; `as_obj`; `_content` for text, parts, a reasoning part and non-completions; a section as a string
  and as a JSON string twice; a one-chunk document falling back to local ladders; a translation reply naming no unit
  failing its part with nothing half-translated left; `forget` drops a kept reply (fresh and cached returns name
  their file) and the next call asks again, with `_once` mocked.
- `tests/test_streaming.py` — its `content()` helper now reads through `llm_openai._content`, as the client does.

## Docs checked

- `docs/DEVELOPMENT.md` — not needed: the layout line still names `llm.py`; no module boundary moves.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: the stored replies and layers
  keep their format; a dropped reply is simply not kept.
- `README.md`, `README.zh-CN.md` — not needed: no user-facing promise changes; a job that could not be read now fails
  with a message instead of an unhandled shape error.
- `site/`, `desktop-mygo/`, `.claude/agents/` — not needed: MyGo already keeps the server's stdout as `server.log`,
  which the new print uses.
- `pyproject.toml`, `requirements.txt` — not needed: standard library only.

## Decisions

- **Unreadable units are dropped, not guessed.** A unit whose reply entry cannot be read cannot be trusted to belong
  to a unit; `units_of` drops it and the unit falls back to the local ladder, with the existing "missing from reply"
  warning. A caller never sees a half-read unit. The one exception is a units object keyed by id: the key names the
  unit, so a keyed value that is a JSON string keeps its key as its id.
- **A shape that still breaks is a failed call.** The chunk-level `try` catches anything the shapes did not foresee,
  logs it, deletes the cached reply, and leaves that chunk's units to the local fallback. It is counted apart from a
  call that never came back: a document whose only chunk replied with an unreadable shape still gets local ladders
  instead of a failed job, because the model did answer.
- **A translation part that names no unit is a failed part, not a warning.** `translate.build` reports it through
  `failed`, and `pipeline.generate` now checks that count for the requested language too, so a layer with whole parts
  untranslated is not stamped as current. This is the one place where a dropped shape must fail rather than fall
  back: a local "translation" does not exist. A reply that names some units but omits others still yields warnings
  and a layer without them — the behaviour before this change, and the caller's count cannot tell it from a model
  that chose to leave a unit out.
- **The cache contract gains one key.** `call` returns `"file"`, so `forget` can name the reply; a caller that keeps
  the returned dict keeps the path too. The cached reply itself is unchanged on disk (ASCII-escaped, UTF-8), and
  `_read_cache`'s old-cache rule is untouched.
- **Only text parts are the reply.** A content list may carry a reasoning part beside the answer; joining it would put
  the model's scratch text in front of the JSON. Parts without a `type` are text, as most providers send them.
- **The failed-job print is stdout, not a new logging framework.** Under MyGo stdout is `server.log`; under
  `textfold serve` it is the console. The page already shows the job's log; this is the copy that survives the page.

## Concurrency and locks

No lock added. In-process there is one generation worker, so two chunks of one run do not share a cache key;
`llm.forget` can race a reader only across processes sharing `TEXTFOLD_DATA` (the MyGo app and `textfold serve`).
A missing file reads as a cache miss (`_read_cache` raises `OSError`, which `call` catches) and the model is asked
again; if the file is held open on Windows (a second process, say), the delete is skipped and the next run reads it
once more.
The generation's own locks and the reply cache's per-file writes are unchanged.

## How it was verified

- `python .claude/hooks/verify.py` — 257 tests, OK (baseline 239; 18 added).
- The new tests cover each shape, the keyed id, the fallback for a one-chunk document, the translation part that names
  no unit (three unreadable shapes), a field-wrong translation reply, the late failure removing what its part already
  translated, the requested language not saving a failed part (`pipeline.generate` with `translate.build` mocked),
  the section as a string twice, the cache-drop path and a reply held open; the streaming tests still pass through
  `_content`.
- `textfold-verifier` — see below.

## Verifier

`textfold-verifier` — it confirmed the 239 baseline and that the new tests fail on it, and found three behaviour gaps
and several test/record weaknesses. (1) A non-object reply to a later translation part was now read as "no units"
instead of raising, so the part counted as a success and an incomplete layer could be saved as current; fixed with
the failed-part guard above. (2) A one-chunk document (a note) never reached the local fallback, because the
all-chunks-failed raise fired first; shape errors are now counted apart from call errors, and a test pins it.
(3) `translate.build` still crashed the job on an unforeseen unit field; the per-part reading is now wrapped like the
ladder's, with partial translations removed. It also showed the keyed-by-id test never asserted the id (fixed, and a
keyed JSON-string value keeps its key), the cache test never exercised the cached `"file"` return (fixed), the
section-as-a-string shape had no test (two added, including a doubly encoded string, which also fixed the quotes kept
around it), a reasoning content part was joined into the reply (now skipped), `forget` could raise on Windows when
another process holds the file (now leaves it), and the record's links/`TypeError` wording was wrong (fixed). It
found the reply reading itself sound: `units_of` drops every unreadable shape without raising, `_content` changes no
case that used to work, and the ladder does not swallow `Stopped`.

`textfold-verifier`, second pass — confirmed the ladder fallback (a one-chunk note now saves local ladders), the
keyed id, the doubly encoded section, the cached `"file"`, and that the translate `try` cannot swallow `Stopped`.
It found the guarantee only half-made: `pipeline.generate` ignored `failed` for the language the reader asked for
(the `also_zh` path already checked it), so a multi-part translation with one unreadable part could still be saved as
current; fixed there, with a test that mocks a failed build and asserts no save. It also showed the guard test never
reached the guard (the test document had no English ladders, so the prompt raised first); the test document now
carries local ladders, and the guard is tested with three unreadable reply shapes plus a wrongly typed field. It
noted `_join_parts` had narrowed R4 by skipping any part not labelled `"text"`; the skip is now only the reasoning
part types, so `output_text` and unlabelled parts still count. It called the `unread` list dead (removed), `forget`'s
`OSError` path untested (a held-open file test added), and the record's incomplete-layer claim too broad (now scoped:
whole parts, not omitted units).

`textfold-verifier`, third pass — confirmed the pipeline hunk and that its test fails on the previous code, and that
the translate guard and catch are reached. It found the "nothing half-translated left" assertions still trivial (the
test document had one unit, so no translation was ever written before the failure); a two-unit part whose second
unit is wrongly typed now pins the cleanup. It also found `_join_parts` raising on a part whose `type` is not a
string (the set membership); a non-string type is simply not a reasoning part now, with a test. The held-open test's
wording was narrowed to what it does, and the pipeline test now asserts the translation was asked for, not only that
it was not saved.

## Measured

| | before | after |
|---|---|---|
| tests | 239 | 257 |

## Not measured

- **Smoothness: unmeasured.** No `tools/zoombench.py` run (it needs `playwright` and exported comparison pages,
  neither installed here); no reader code is touched, and the zoom axis is not reported as unaffected.
- No real model was called: the shape tests use literal replies, and the cache/fallback tests mock `_once` and
  `llm.call`. A provider's own JSON-mode quirks beyond the shapes read here are not covered.
- No job-queue run: `pipeline.generate` is called in a test with `translate.build` mocked, and `ladder.build` /
  `translate.build` are called directly with a parsed note and stand-in replies. A real generation end to end was not
  run.

## Pitfalls

- `units_of` drops an entry whose id is missing even when the rest is readable; the unit falls back to the local
  ladder and is reported as "missing from reply", the same as a unit the model left out.
- `as_obj` accepts only a JSON **object** in a string; a string that parses to a list is `{}`.
- The chunk-level fallback catches `Exception`; a programming error inside the reading path is logged and turned into
  a local fallback for that chunk rather than crashing the job. Call errors are still counted, and a run in which
  every model call failed raises the first one.
- A translation reply that names some units but omits others is a warning and a part counted as success; the layer is
  saved without the omitted units (pre-existing, and unchanged by this change).
- A section written as a JSON **array** (`'["a", "b"]'`) still becomes the raw JSON text of the takeaway; only a
  section string, and a string encoded twice, are understood.
- The printed job log is the job's in-memory log (last 12 lines), and a provider's error text appears there as it
  does on the page; `server.log` is local to the machine.

## Rejected

- **Asking the model again inside the same run for an unreadable reply.** The chunk falls back locally and the reply
  is dropped; the next run asks again. A retry loop would multiply cost on a model that answers the same wrong shape.
- **Coercing a string unit into a unit by position.** A string has no id; guessing which unit it belongs to could put
  one unit's takeaway on another's text.
- **Saving a translation part as current when its reply named no unit.** The layer would never be completed.
- **A new logging module for the failed job.** stdout is already `server.log` under MyGo; a logger would add a
  dependency and a configuration surface for one line.
