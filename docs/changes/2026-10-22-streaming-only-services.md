# A service that answers only streamed is read

**Date:** 2026-10-22
**Branch:** `worktree-streaming-only-services`

## What and why

Some OpenAI-compatible services answer a chat completion only as a stream of server-sent events: a request without
`"stream": true` is refused, and a streamed reply is not a JSON body. TextFold asked every endpoint the same way and
read every body as JSON, so such a service failed on every call — even though the reply's pieces, joined, are the
same chat completion. This change reads a streamed reply and asks for a stream only after a service refused the
requests sent before it, so every endpoint that works today gets exactly the request it got.

## The change

- `textfold/llm_openai.py` — `_post` looks at the response's `Content-Type` and the body's first bytes (after a
  byte-order mark or whitespace): a `text/event-stream` answer, asked for or not, goes to `_events`.
- `_events(raw)` joins a stream into one chat completion: the `data:` lines, the first choice's `delta` (or `message`)
  `content`, a content that is a list of parts (a non-string `text` no longer raises: a non-falsy one is stringified,
  a falsy one is empty), the last `usage` a chunk carries, and `[DONE]` ends it. A malformed data line (bad JSON, or
  nested too deeply) is skipped. A chunk that is only an `error` is returned as it came, for the caller to report.
- `call` — the request shapes now carry a third field, streamed or not. The two plain streamed requests
  (`"stream": true`, with and without JSON mode) are tried last, after every reasoning/JSON-mode combination, so no
  endpoint that answers today sees a different first request. A refusal whose message mentions "stream" jumps
  straight to them; any other refusal moves on as before. The index that worked is remembered for the run, as before.
- `call` — a 200 response without a `choices[0]` object (a JSON error object, or an error-only stream) moves on to
  the next shape instead of reporting "no JSON in reply" at once, which is what makes the second streamed shape — the
  one without JSON mode — reachable. A `choices[0]` that is an object without a usable message still ends as "no
  JSON in reply" on a streamed shape (upstream's `_content` returns an empty string there too; a non-streamed shape
  with a reasoning field still takes the existing next-shape fallback). The error-body advance is the part of
  upstream's `_content` this change needs inline; R5 still brings the content-list handling and the rest.
- `call` — an HTTP error's body is read at most 300 bytes and only where it is needed (a refusal whose text decides
  the jump, or the final message). The rate-limit/busy path does not read it at all, so a slow or truncated error
  body cannot stop the wait-and-retry that worked before. A body already closed reads as empty rather than raising.
  The response is closed either way.
- `tests/test_streaming.py` — a local server with ten endpoints: answers whole; takes a stream alone and says so;
  takes one and says nothing; streams unasked; streams with a JSON content type; streams with a byte-order mark and a
  JSON content type; refuses JSON mode with a stream as an HTTP error; refuses it as a 200 error body; refuses the
  first request with a truncated 503; refuses JSON mode with a truncated body. Ten tests drive `call` through them
  (including the remembered shape, both streamed shapes, the 200 error body, the truncated retry and refusal, and
  stream detection with and without its content type); two use a fake response to pin that a busy body is not read
  and that a closed body reads as empty; five test `_events` directly (pieces joined, parts/comments/other choices,
  an error chunk, `message` and a non-string part with CRLF, a byte-order mark).

## Docs checked

- `textfold/llm_openai.py`'s module docstring — updated with the streaming paragraph.
- `docs/DEVELOPMENT.md` — not needed: it names the module in the layout, not the request shapes.
- `README.md`, `README.zh-CN.md` — not needed: no user-facing setting or promise changes.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: the stored replies are the
  same JSON.
- `site/`, `desktop-mygo/`, `.claude/agents/` — not needed.
- `pyproject.toml`, `requirements.txt` — not needed: only the standard library, already used.

## Decisions

- **Ask for a stream only after a refusal.** Streaming everywhere would change the request for every provider,
  including those whose non-streamed answer works and whose streamed one may not; the round's rule is that every
  other endpoint keeps the requests it got. The remembered index means a service pays the refusal once per run.
- **Jump on the word "stream".** A refusal that names a stream (OpenAI-compatible services do: "only stream=true is
  supported") lets the client skip the remaining shapes; a refusal that does not is treated as before, and the
  streamed shapes are reached after them.
- **Do not bring all of `_content` in.** Upstream's commit reads the joined reply through `_content` (content as a
  string or parts, and a body that is not a completion), but `_content` belongs to the next upstream change, R5, which
  this fork has not ported. The joined reply has the ordinary `choices[0].message.content` shape, and the tests read
  that directly. The one part of `_content` this change does need — a 200 body that is not a completion — is inline,
  so the second streamed shape is reachable; R5 still brings the content-list handling and the rest of `_content`.
- **A streamed reply is read whole, not incrementally.** TextFold's callers want the finished JSON object, and the
  cache and the cost accounting work on a finished reply; reading the stream to its end keeps the existing contract.
- **The error body is not read on the retry path.** A busy service's body says nothing the client acts on; reading it
  can block on a slow or truncated response and turn a retry into an exception. The first 300 bytes are read only
  when the text decides something.

## Concurrency and locks

None added. `_WORKED` is the same per-process dictionary it was, written after a successful call; two concurrent
calls for the same service may each learn the shape, which is harmless. The reply cache and its locks are untouched.

## How it was verified

- `python .claude/hooks/verify.py` — 239 tests, OK (baseline 222; 17 added).
- The ten service tests exercise the real `_post` against a local HTTP server: whole answer unchanged; a service
  that says "stream" is asked twice; one that says nothing is asked three times; a service that streams unasked is
  read on the first request; a stream with a JSON content type is read, with and without a byte-order mark; the
  stream without JSON mode is tried after JSON mode is refused (as an HTTP error and as a 200 error body); a 503
  with a truncated body still retries; a 400 with a truncated body still moves on. The remembered index is checked
  on the second call.
- Two tests with a fake response pin that a busy error's body is never read (its `read` raises) and that a body
  already closed reads as empty.
- `_events` tests cover UTF-8 pieces, a content list, comment lines, another choice's chunks, an error chunk, a
  `message` chunk with CRLF, a non-string text part, and a byte-order mark.
- `textfold-verifier` — two passes, below.

## Verifier

`textfold-verifier`, first pass — found two real failures in behaviour the change claims. (1) Reading every HTTP
error's body before the retry branch made a slow or truncated 429/503 body raise `IncompleteRead`/`TimeoutError`
instead of retrying (demonstrated with a local server); fixed: the busy path closes the error unread, and `_said`
reads at most 300 bytes and tolerates truncated or slow bodies. (2) A 200 error body yielded empty text and, because
a streamed shape carries no reasoning fields, never tried the streamed-without-JSON-mode shape; fixed with an inline
not-a-completion check, tested through `/picky200`. It also found the record's timeout claim was false (fixed: per
socket operation, not wall-clock), coverage gaps for the second streamed shape, the content-type-less stream, the
retry and malformed chunks (tests added), `_events` raising on a non-string part or deeply nested JSON (fixed), a BOM
not stripped (fixed), and documented limits it did not fix: the "stream" substring heuristic, a comment-first stream
without the event-stream content type, the missing `stream_options` usage, and multiline `data:` events.

`textfold-verifier`, second pass — confirmed the substantive fixes and the first-request identity for eight
provider/level combinations and every old success index, then found: the record said "without a `choices[0]` message"
where the code advances only when `choices[0]` is not an object (wording fixed; the residual is documented as
upstream's too); the busy test asserted only that the retry happened (a fake response whose `read` raises now pins
that the body is not read); `_said` would raise on an already-closed body (now safe, with a test); a slow 4xx body
still delays the next shape (documented under Not measured); and the R5 wording was too broad (fixed). It reported
no endpoint that works today broken by the change.

`textfold-verifier`, third pass — confirmed the two Retry tests pin the unread body and the closed-body tolerance, and
that `/stubborn` and `/nakedbom` reach their paths, then found four small items, all corrected: the record's
"still ends the walk" is scoped to streamed shapes (a non-streamed shape with a reasoning field does take the
fallback); the byte-order-mark test now puts the mark before a content-bearing chunk, so it pins `_events`'s
`utf-8-sig` rather than passing under plain UTF-8; the closed-body test now asserts the response is closed; and a
test comment no longer claims the partial refusal text was used. It found nothing that breaks an endpoint.

## Measured

| | before | after |
|---|---|---|
| tests | 222 | 239 |

## Not measured

- **Smoothness: unmeasured.** No `tools/zoombench.py` run was made (it needs `playwright` and exported comparison
  pages, neither installed here); this change touches no reader code, and the zoom axis is not reported as
  unaffected.
- No real provider was called: the tests use a local server, so a provider's own stream quirks (heartbeat comments,
  `event:` lines, a chunk split across TCP reads) are covered only as far as the parser's rules. The client reads the
  whole body before parsing, so a chunk split across reads is already joined.
- **A stream is not bounded by the request `timeout` in wall-clock terms:** `urllib`'s timeout applies to each socket
  operation, and `read()` stops when the server closes or goes silent for that long. A service that sends a heartbeat
  forever can hold the call open; this was already true of a non-streamed reply that trickles, and the change does
  not add a deadline.

## Pitfalls

- A `choices[0]` that is an object without a usable message (`{"choices": [{}]}`, `{"choices": [{"message": null}]}`)
  still ends the walk with "no JSON in reply" on a streamed shape — the shapes this change adds carry no reasoning
  field, so the existing next-shape fallback does not fire. A non-streamed shape with a reasoning field does take
  that fallback. Upstream's `_content` returns an empty string there too, so this is not a regression.
- A slow 4xx refusal body delays the next shape: the refusal's first bytes decide whether to jump to the streamed
  shapes, so the client waits up to the socket timeout for them. A truncated body is fine (its partial text is used);
  a stalled one costs the timeout once, then the next shape is tried (demonstrated with `timeout=1`).
- The jump is a substring test on the first 300 bytes of a refusal: a 400/404/415/422 whose message mentions
  "stream" for another reason (or an HTML error page that does) skips the remaining non-streamed shapes. Upstream's
  heuristic is the same; a real provider with that wording was not found.
- A body that is not JSON but starts with `data:` is taken for a stream. Every endpoint TextFold speaks to returns
  JSON or an event stream, so this is the intended reading; a stream whose first line is a comment (`: ping`) and
  whose `Content-Type` is not `text/event-stream` is still missed.
- The streamed shapes ignore the reasoning spellings (`{}`), because a service that refuses everything but a stream
  has already refused the shapes that carry them; a service that takes a stream *and* needs a reasoning field is not
  handled (upstream's is the same).
- A streamed reply's `usage` is usually absent unless the request asks for `stream_options: {"include_usage": true}`,
  which this change does not send (some services would refuse it). An OpenRouter streaming-only service therefore
  reports no cost, and the run's cost sum undercounts it; the service failed entirely before this change.
- Multiple `data:` lines forming one event (the SSE rule) are parsed line by line; a JSON object split across lines
  would be lost. Upstream is the same, and the providers seen send one line per chunk.
- Reading the stream whole means a long reply is held in memory once, as a non-streamed reply already was.

## Rejected

- **Streaming every request.** It would change the wire for endpoints that work, against the round's rule, and the
  streamed shape is the fallback, not the default.
- **Porting all of `_content` early.** It is R5's change; doing it here would mix two upstream commits and make R5's
  record claim work already done.
- **Reading the error body before the retry wait.** It lets a truncated or slow body replace the retry with an
  exception, and the body is not used on that path.
- **Parsing incrementally into the caller.** No caller consumes partial JSON; the cache stores a finished reply.
