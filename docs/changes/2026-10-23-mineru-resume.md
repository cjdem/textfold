# A MinerU conversion resumes where a lost connection stopped it

**Date:** 2026-10-23
**Branch:** `worktree-mineru-resume`

## What and why

A PDF import failed with `SSL: UNEXPECTED_EOF_WHILE_READING` while polling MinerU, after the file had been uploaded
and while MinerU was still reading it. The engine raised on the first poll failure, the conversion queue deleted the
output folder, and the batch id went with it; importing the file again would have uploaded and parsed it a second time.
The conversion now keeps a small state file beside its output and retries each stage on the same batch, so a lost
connection at the poll, the download or the parse resumes where it stopped. A refusal — or a stop — drops the state,
and the conversion queue removes the folder.

## The change

- `textfold/engine.py` — a state file (`_mineru.json`: file fingerprint, base, pass, batch id, uploaded, stage)
  written through the shared atomic writer as each stage is reached; `_retry`/`_pause` for transient failures; a typed error
  for each API answer (task gone, no file, refused, link gone); retries on the poll with a 10-miss limit and the
  existing 30-minute wait; a poll-first check after a lost upload answer; a 5xx on the signed upload retried on its
  URL, any other 4xx replacing the batch; download retries that ask the batch for a fresh link; a pass whose output is
  already unpacked is finished from that output, without the network; the OCR pass keeps its own state, so a resume continues
  pass 2 rather than pass 1. A permanent failure or a stop drops the state, for the command line as well as the queue.
  Importing the file again — or re-converting it — is the resume, because a document's id is the hash of its bytes.
- `textfold/server.py` — the conversion queue deletes its output folder only when the failure is not `Resumable`.
- `tests/test_engine_retry.py` — 26 tests: poll retries, -60012, a lost upload answer, an upload that did not land
  (and the new batch it is sent to), a resume whose batch cannot be reached (the batch id is kept), -60011, -60003 and a
  5xx upload, download retries and refreshed links, an incomplete zip, a finished output, a parsed pass finished
  without the network, a changed file, the same bytes from two paths (the server's and the command line's), a refused
  result (not resumed), Stop during a wait, A0211 and HTTP 401, the service-error code, the state holding no key or
  URL, two writers of one state, curl's 5xx/4xx answers and urllib's 4xx, the OCR pass and its resume, and both queue
  cleanup paths.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the state file, the per-stage retries, `Resumable`, and what a re-import resumes.
- `docs/format.md` — not needed: `_mineru.json` is internal to a conversion and no reader opens it.
- `README.md` / `README.zh-CN.md` — not needed: what the reader is promised has not changed.
- `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: neither format is touched.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md` — not needed: no version,
  dependency, platform or licence change.
- `docs/requirements/` — not needed: this is a fix, not a feature with a requirements document.

## Decisions

- The signed upload URL is not stored: it is a capability valid for 24 hours, and the batch can be checked first. If a
  resumed attempt finds the file did land, it polls; if the batch answers `waiting-file` at the end of the grace, the
  batch is replaced rather than re-signed. If no poll could be made, the batch id is kept and `Resumable` is raised:
  an unreachable API is not evidence that the file did not land.
- A create whose answer is lost still leaves an untracked batch (the API has no list call); it has no file, stays
  `waiting-file`, and is never read. That is the one unavoidable duplicate.
- A new batch is submitted only when the API no longer has the task (-60012), when it reports the batch has no file
  (-60011), when the signed upload URL answers a 4xx other than 408/429, when -60003 asks for the file once more, or
  when the batch still has no file after a lost upload. A 5xx on the upload is retried on the same URL; -60010
  (extract failed) is reported rather than retried, because a second extraction costs quota and usually fails the same
  way.
- The 30-minute wait for one pass is unchanged; a wait that runs out raises `Resumable`, so the next conversion
  resumes it.
- Stop and a refusal delete the state; a lost connection keeps it.

## Concurrency and locks

The server's conversion queue runs one conversion at a time and `pdfdoc.relayout` uses its own temporary folder, but
the command line converts into the same `uploads/<pid>-<tier>` as the server. The state is identified by the file's
bytes (size and sha256), not its path, so the server's `uploads/<pid>.pdf` and the command line's own path share one
state and one batch. It is written through `store.write_text_atomic`: a unique temporary file, flushed and moved over
the state, and a move that retries. The last writer wins, and the file is always one whole state, never a mixture.
Two processes that start at the same instant, before either has written a state, can still create two batches; one
becomes an orphan, and the last state names the other. `tests/test_engine_retry.py` runs two writers of one state and
the same bytes from two paths.

## How it was verified

- `python .claude/hooks/verify.py` — 527 tests, OK (501 before; 26 added).
- `git diff --check` — clean.
- The independent verifier read the diff, the record and the documents above. It found: a 5xx upload treated as a
  refusal; a resume that erased the batch id when the API could not be reached; a state write that was not the shared
  atomic one; a permanent failure leaving a resumable state for the command line; curl's 22 blurring 4xx and 5xx; and
  missing tests for the parsed pass, the state's contents and a two-writer state. A second read found the state keyed
  by the file's path, though the server and the command line use different paths; -60011 missing from the "sent again"
  sentence; and the urllib fallback calling only 403/404 a dead link. All are fixed above; its remaining notes are in
  the local log (`notes/2026-10-23-mineru-resume.md`).

## Not measured

- No live disconnect was made against MinerU: the tests stand in the API, the upload and the download, and raise at
  each stage. The real network behaviour is what the change is for, and only a future use can confirm it.
- Smoothness was not measured (`tools/zoombench.py` still needs `playwright` and exported comparison pages here). This
  change does not touch the reader, the zoom or the rendered output.

## Pitfalls

- The state lives in the output folder, so the OCR pass's wipe deletes it: the new pass writes a fresh state before its
  first call. A crash in that instant redoes pass 1, which is the only re-upload this design cannot avoid.
- curl's exit code 22 means an HTTP error; the status `-w` prints decides: a 4xx other than 408/429 is a dead link, and
  5xx/429 is retried on the same one. Only curl's other exit codes are connection failures and are retried.
- When the API cannot be reached at all, `_landed` keeps the batch id and raises `Resumable`; only a batch that
  answered `waiting-file` at the end of its grace is replaced.
- `_get` now deletes a partial file on failure; a truncated zip otherwise reaches `_unzip` and looks like a corrupt
  result.
- The download URL is never persisted either: a resume before `parsed` asks the batch for a fresh link.
- `_fingerprint` reads the whole file: once per attempt, and once more when an existing folder's state is checked
  and then thrown away. A 200 MB PDF is small beside the upload.

## Rejected

- Storing the signed upload URL or the download URL in the state: both are capabilities, and neither is needed to
  resume a known batch.
- Replacing the batch on any upload rejection: a 5xx does not say the upload failed, so it is retried, and only a 4xx
  other than 408/429 (or a batch that answers `waiting-file` after the grace) replaces it.
- A fixed temporary name for the state: two processes convert the same folder, so the shared atomic writer is used.
- A background daemon that keeps polling after a job fails: the reader's re-import is the resume, and a daemon would
  need its own lifecycle and stop.
- Retrying -60010 automatically: quota cost with little chance of a different result.
- A global registry of conversions: the output folder already is one, named by the content hash.
- Persisting the MinerU key or the Authorization header: never.
