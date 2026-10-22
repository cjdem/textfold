# Several files at once go in one after another, each its own job

**Date:** 2026-10-22
**Branch:** `worktree-multi-file-import`

## What and why

Only the first file of a drop or a multi-choice was taken: a reader with a folder of papers had to add them one by one,
and the page left for the first one before the others could be chosen. This change ports the browser side of upstream
`523e5f4` to this fork's app and adds the round's requirements: several files go to the existing per-file endpoint one
at a time, each becomes its own conversion/generation job in the server's existing queues, the page stays where it is,
the sidebar shows each with its stop, and a summary says how many were taken, which need a MinerU key, and why any was
not. At most 50 files at once; a file already in the library or repeated in the batch is skipped; an upload or
conversion that failed for a reason that may pass is offered again from the summary; the 100 MiB engine-file limit
stays and Markdown/text keeps its 12 MB import limit; MinerU's 600-page-per-file limit and 2,000-page-a-day priority
quota are stated. One file opens exactly as before. No server endpoint, header or MinerU batch was added.

## The change

- `textfold/web/app.js` — `addFiles(files, lang, step, done, again = false)`: the batch queue. It refreshes the
  library once, validates each file in the same order as the single-file path (an engine file: the 100 MiB limit;
  Markdown/text: 12 MB, then a model), uploads engine files one at a time to `POST /api/files` and text files to
  `POST /api/import` followed by the existing generate call, caps the batch at 50, and reports each accepted job's
  failure or stop through watchers. `filePid(file)` computes the server's content name in the browser (SHA-256 of the
  bytes, first 16 hex, `pdf-` when the bytes start with `%PDF-`, else `doc-` — the server's own routing) so a file
  already in `papers`, or the same bytes twice in the batch, is skipped before it is uploaded; a fallback after upload
  stops a job the server has just queued and the page did not already know (a job the page knew before the upload —
  another tab's live one in its list, or this batch's first copy — is left alone). A text file
  already in the library is recognised by its import id after `POST /api/import` (which stores the same text and title
  under the same paper) and skipped before a generation job starts; in a retry, a text file whose import succeeded but
  whose job did not is submitted again. Failed uploads and failed conversions that left no paper are kept for a Retry
  button; `filesSaid(got, m, T)` builds the summary.
- `textfold/web/app.js` — the landing's `openFiles`: one file calls the old `openFile`; two or more stay on the page and
  draw the summary card (taken count, queue line, MinerU-key line, limits, failed/stopped names, skipped names with why,
  Retry failed, a Settings button when a key is needed, Close). The file input takes `multiple`, and both drops call
  `openFiles`. A retry goes through `beginBatch` even for one file, so it keeps the summary and its Retry button
  instead of navigating; a batch queued behind another says it is waiting.
- `textfold/web/app.js` — a reader page's multi-file drop (`dropFiles`) stays on the page and shows the same summary in
  a toast of its own, so a generation's toast can be up at the same time and neither rewrites the other; a newer batch
  takes the toast over, a closed one stays closed, and a queued batch says it is waiting. The generation's watcher
  rebuilds its stage and progress bar if anything else has repainted or hidden its toast (also a pre-existing case: a
  drag hint over a running generation), and shows it again. One file keeps the old navigate behaviour.
- `textfold/web/app.js` — the single Markdown/text path (landing and reader page) refuses a file over 12 MB with its own
  message instead of reporting it as a PDF over 100 MB.
- `textfold/web/app.js` — the MinerU settings section shows the limits line.
- `textfold/web/i18n.js` — the batch strings in English and Simplified Chinese (`fl_*`, including `fl_retry`,
  `fl_md_large` and `fl_waiting`, `mineru_limits`, `mineru_limits_h`), and `drop_zone`/`drop_md` say one or more files.
- `textfold/web/app.css` — the summary card's Close hover.
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md` — one or more files; the batch's queues, cap and duplicate rule;
  MinerU's limits in the PDF section.
- `tests/test_mineru_routing.py` — two contract tests pin the server names the browser copies: `pdf-` + the first
  16 hex of SHA-256 for a PDF, and `doc-` + the same for an Office/HTML file. A change to `pdfdoc.pid_of` or either
  prefix fails the suite instead of silently letting the browser's pre-check stop matching. (The browser's own
  `filePid` has no test; see Not measured.)

## Docs checked

- `README.md`, `README.zh-CN.md` — updated: "Drop one or more files", and the getting-started sentence.
- `docs/DEVELOPMENT.md` — updated: the landing paragraph (one or more files, the queues, 50, duplicate skip, the card)
  and the PDF section (MinerU's limits).
- `site/` — not needed: the landing page describes the product, not the drop zone's count.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no stored format changes.
- `.github/workflows/desktop.yml` — not needed: no build or payload change.
- `desktop-mygo/` — not needed: the app's WebView shows the same page; `127.0.0.1` is a secure context, so
  `crypto.subtle` is available there (the feature falls back to uploading if it is not).

## Decisions

- **The existing per-file endpoint and queues, uploaded one at a time.** The round forbids a MinerU batch and a protocol
  change. Sequential uploads make the server's conversion queue (one at a time) and generation queue keep the order the
  reader chose, and each file keeps its own progress, stop and retry.
- **Duplicate means the same bytes.** The server names a document by its content (`pdfdoc.pid_of`); the browser computes
  the same name with `crypto.subtle` and skips the upload for a file already in `papers` or already in the batch. This
  meets "skip a repeated pid" without adding a header or an endpoint. The coupling is deliberate and documented: if
  `pdfdoc.pid_of` changes, the pre-check stops matching, the upload proceeds, and only the fallback (stop a job the
  page did not already know, for a duplicate) remains. A file whose name/type matches but bytes differ is a different
  paper, as on the server.
- **Text files use their import id, not the content name.** `/api/import` names a Markdown or text file differently, so
  the content-name pre-check does not apply; the import happens (the same text and title store the same paper) and the
  duplicate is recognised against `papers` before a generation job is started, so no job is queued for a text file
  already in the library or repeated in the batch.
- **A batch skips a file already in the library.** That is the "duplicate pid" rule, for engine files and text files
  alike. Regenerating an existing paper is still done from the paper itself (Regenerate), not by dropping its file into
  a batch; a single dropped file keeps the old behaviour, which does regenerate.
- **At most 50 files.** The first 50 are taken in order; the rest are listed as not added with that reason. The client
  limit is the round's; the server still accepts one file per request.
- **The summary has its own toast on a reader page.** A generation's toast and a batch's summary can be up at once; the
  batch must not repaint the generation's elements (the generation's watcher updates them from a later poll) and the
  generation must not erase the batch's result. Two elements, one owner each. The generation's watcher also rebuilds
  its own stage and progress bar if anything else repainted or hid that toast (a drag hint did, before this change),
  so its update cannot throw and leave the page's polling stopped.
- **The summary reports later job failures and stops.** The upload call returns a queued job; the card or toast is
  updated when a watched job ends in `error` or `stopped`, so a conversion or generation failure is not silent. A job
  that reports `needs-mineru-key` is counted with the files needing a key (the Settings button); the sidebar's per-file
  progress and stop remain the place to watch a batch.
- **Retry is offered where a second try can work.** The summary's Retry failed re-sends the files whose upload failed
  for a reason that may pass (a busy server, a network error, a temporary failure) and the files whose conversion
  failed and left no paper (a MinerU failure, not a missing key, which has its own button); it stays a batch even for
  one file, so its summary can offer the button again. A text file whose import succeeded but whose job did not start
  is submitted again (the import is idempotent, and the paper is already there). A generation that failed or was
  stopped leaves an unfinished paper whose sidebar row says Continue; it is not re-uploaded, which would duplicate the
  paper. A file the server refused for what is in it (bad file, not a PDF, legacy format, too large) is not offered
  again.
- **MinerU's limits are stated where the reader meets them.** The batch card shows them when PDFs are taken or need a
  key, and the MinerU settings section always shows them; the round asks for the 600-page and 2,000-page-a-day figures.
- **A reader page stays put for a batch, and navigates for one file.** This is upstream's rule; it keeps the reader's
  place while several files go in.
- **Markdown/text without a model is skipped, not stored.** The old single-file path refuses before importing; the batch
  does the same and says why, rather than leaving papers that cannot get levels.
- **The batch's language is the one chosen when it starts.** Changing the interface language mid-batch does not re-route
  files already going up.

## Concurrency and locks

Uploads from one page are serialized by `adding`; a batch started while another is running waits for it. The server's
conversion queue and generation queue each work one job at a time (unchanged), so no two conversions or generations run
together. The duplicate pre-check keeps a repeated file from adding a second job; the fallback stops a job the server
has just queued for a duplicate that slipped through, unless the page already knew that job. Stored documents are still
written by the existing store paths; this
change adds no writer. A batch abandoned by navigating away leaves only the files already sent and their jobs, as a
single upload does.

## How it was verified

- `python .claude/hooks/verify.py` — 284 tests, OK (baseline 282; two contract tests added).
- `node --check` on `textfold/web/app.js` and `textfold/web/i18n.js`; `git diff --check` clean.
- In the browser, against the worktree server with `TEXTFOLD_NO_MODELS=1`, a disposable library and a disposable
  settings home (no real model or MinerU call):
  - four files (two HTML, the second HTML's bytes again, one Markdown): the card said "2 of 4 files added", the
    duplicate was "already added" without being uploaded (`/api/jobs` had exactly two jobs, one per accepted file), the
    Markdown was skipped for the missing model, and both accepted files' failed generation jobs (no model) were listed;
    the sidebar showed both papers as unfinished.
  - the same bytes again after the first batch, with one new HTML: the library's copy was skipped before upload
    ("already added"), the new file was added with exactly one new job (the library refresh at the batch's start).
  - two PDFs with no MinerU key: "0 of 2", "2 need a MinerU key", the 600-page/2,000-page limits line, and the Settings
    button; no job was left.
  - 51 Markdown files: the 50-file cap held, the 51st was listed with that reason, six skipped lines and an ellipsis,
    and no job was made.
  - two files whose upload failed (the page's `fetch` was made to reject both `/api/files` posts, standing in for a
    network error): "0 of 2", both reasons, and "Retry failed"; clicking it added both on the second try, with exactly
    two new jobs.
  - a 12,000,008-byte Markdown file with one HTML: the Markdown was skipped as over 12 MB, with that message, and only
    the HTML was added.
  - a reader page with two HTML files dropped: the page stayed on `/p/<id>`, the batch's toast said "2 of 2 added" and
    listed the two failed jobs, and both papers appeared.
  - on a reader page with the drag hint in the generation toast, a two-file drop: both toasts stayed up, each with its
    own text, the page stayed, and no script error was logged over the following polls.
  - on a reader page, two uploads made to fail the same way: the batch's toast offered "Retry failed"; clicking it
    added both (the reader keeps its page).
  - one upload failed out of two (one file left in the retry): clicking "Retry failed" stayed on the landing, showed
    "1 of 1 files added", and its job appeared; the single-file path would have navigated.
  - a first batch of two files showed "Adding 1 of 2" with the first name at once; a second batch started while the
    first one's upload was held said it was waiting for the earlier files, then showed its own summary.
  - one HTML file alone: the page navigated to its reader as before.
  - the MinerU settings section showed the limits line.
- `textfold-verifier` — first report: one blocking finding (the reader-page batch repainted the generation's toast
  without its `.g-stage`, so the generation's watcher threw on the next poll, was never removed, and the page's polling
  stopped) and non-blocking findings. Fixed: the batch has its own toast element (`fileToast`), with a batch token and a
  durable Close; text files already in the library are skipped after import; the post-upload fallback also compares
  against `papers`; a Retry failed button was added for failed uploads and conversions; the pid test pins the exact
  name; a large Markdown file gets its own 12 MB message; the engine/text branch order now matches the single-file path;
  the unused collected-job list was removed; the per-file library refresh (up to 50 scans) became one refresh at the
  batch's start, the sidebar's poll keeping it current. The second pass confirmed the blocking finding resolved and
  found: a one-file landing retry taking the single-file path (fixed: `beginBatch` even for one file); a text file whose
  import succeeded but whose job failed being reported as "already added" on retry (fixed: a retry submits it); the
  watcher guard not covering a `closable` repaint's missing progress bar (fixed: it rebuilds on either missing part and
  shows the toast); a batch text import over the JSON limit reported as a PDF over 100 MB (fixed); the fallback stop
  able to stop another tab's job (fixed: only a job the page did not already know before the upload); the `doc-`
  prefix unpinned (fixed: a second contract test); a queued batch showing the earlier batch's progress (fixed: a
  waiting line only when a batch is already queued); and record wording about text names, key retries and "fresh" jobs
  (fixed). It also noted that the batch has no automated JavaScript test (the repo has no JS runner), recorded under
  Not measured. The narrow re-check confirmed all of these fixes (no blocking; the one-file retry, the `closable`
  rebuild, the text retry, the snapshot guard and both waiting paths in its harness; the waiting line was afterwards
  limited to a batch that is actually queued and re-checked in the browser), and left two limits recorded under
  Pitfalls: a job another page starts during the upload is not in the snapshot and may be the one stopped, and a
  retried text file whose paper another tab stored between attempts gets a redundant job (no duplicate paper).

## Measured

| | before | after |
|---|---|---|
| Python tests | 282 | 284 |

## Not measured

- **No accepted PDF was converted.** The browser check used no MinerU key, so the need-key path and the limits line were
  seen, but a batch of PDFs actually converted by MinerU was not run; that would call the real service.
- **The batch's browser code has no automated test.** The repository has no JavaScript test runner; the batch was
  checked in the browser, and the verifier ran the extracted functions with stubs in a scratch harness. Only the
  server's pid contracts are automated.
- **No real model.** All generation jobs failed with "no model"; the successful-job path, the sidebar's live progress
  for a batch, and stopping a running job from the sidebar were not observed end to end (the stop UI is existing).
- **Retry after a failed conversion was not observed.** The retry button was exercised with uploads made to fail (a
  patched `fetch`); a conversion that failed at MinerU and left no paper was not produced without calling the service.
- **A text file's import-succeeded-but-job-failed retry was not observed in a browser.** The check had no model, so
  text files were skipped before import; the narrow re-check exercised the `again` branch with stubs (its S10), not
  the real page.
- **Closing the batch's toast and then a job ending** was not observed live; the flag that keeps a closed toast closed
  is exercised only by inspection.
- **No 100 MiB file**; the double read of a large file (hashing, then uploading) was not measured.
- **No mobile/touch multi-select**; the picker's `multiple` and drag-and-drop were checked on the desktop browser.
- **Zoom smoothness: unmeasured.** `reader.js` and its zoom code are untouched (the changes are in `app.js`, the app
  around the reader), but no `tools/zoombench.py` run was made (it needs `playwright` and exported comparison pages,
  neither installed here); the zoom axis is not reported as unaffected.

## Pitfalls

- The browser's `filePid` copies `pdfdoc.pid_of` (SHA-256, 16 hex, `pdf-`/`doc-`). If the server's naming changes, the
  pre-check silently stops matching: duplicates are then uploaded, and only the fallback (stopping a job the page did
  not already know) acts. A second file whose bytes are the same is a duplicate; a same-named file with different
  bytes is not.
- Hashing reads every engine file fully before its upload, so a large file is read twice and held in memory once (up to
  the 100 MiB limit). The batch is sequential, so only one such buffer exists at a time.
- If `crypto.subtle` is unavailable, duplicates upload; the fallback stops a job the page did not already know, but a
  job may start (and, with a model, make a call) before the stop arrives.
- The pre-check compares against `papers`, refreshed once at the batch's start (and by the sidebar's own poll); a paper
  another tab adds during the batch is not seen, and the server's live-job dedupe decides. A file already accepted in
  this batch is skipped by the batch's own set of pids. The fallback stop only acts on a job this page did not already
  know before the upload (a job in its list is left alone, even if the server handed it back as a duplicate's job);
  the list is a snapshot, so a job another page starts during the upload is not in it and may be the one stopped.
- A text file's paper id includes its title, and the title falls back to the file name: two byte-identical Markdown
  files with no front-matter title or single heading, under different names, are two papers; the batch cannot call one
  a duplicate of the other.
- A retry submits a text file even when its paper is already in the library — that is the case it exists for (the
  import succeeded, the job did not). If another tab stored the same text between the two attempts, the retry asks for
  a generation of that paper: no new paper (the store is idempotent), at worst a redundant job, which the server's
  live-job dedupe may return instead of a new one.
- A batch skips a file already in the library; to regenerate an existing paper, open it and use Regenerate (or drop that
  one file alone, which keeps the old behaviour).
- The overflow beyond 50 is not uploaded; those names are listed with the cap as the reason.
- The summary shows at most six skipped and six failed/stopped names, then an ellipsis; the sidebar has the full list of
  live jobs, but a failed conversion that left no paper is only in this summary (the server keeps the job for ten
  minutes). The Retry button keeps the failed files' `File` handles until the card is replaced; the underlying data is
  not read unless the button is used.
- A retried upload can still fail, and then the Retry button is offered again; a file the server refuses for its content
  is not offered, so a permanent refusal is answered by choosing a different file, not by retrying.
- The reader page's batch toast and a generation's toast stack (one above the other); closing one leaves the other.
  A second batch replaces the first summary (there is one card, one toast): the first batch's uploads finish, its jobs
  stay in the sidebar, but its card no longer updates and its failed files are no longer offered for retry; until the
  earlier uploads finish, the second card says it is waiting. A batch's summary uses the interface language it started
  in; a language switch mid-batch does not redraw it in the new language. Navigating away during a batch stops the
  remaining uploads; the files already sent keep their jobs.
- The reader page's batch uses the reader's paper language (else the interface language) for the new files' levels,
  while a single dropped file uses the interface language, as before.

## Rejected

- **MinerU's batch endpoint** (up to 200 files): the round forbids it, and the existing per-file queue is what keeps
  each file's progress, stop and retry.
- **A new batch endpoint or a "skip if exists" header**: a protocol change the round forbids; the browser computing the
  content name keeps the existing protocol.
- **Making the server skip existing papers on upload**: it would change the single-file re-upload behaviour (a useful
  regeneration path) for every caller.
- **Skipping duplicates by file name and size**: two files with the same bytes under different names are the same paper
  (the server's own name says so); name/size would miss them.
- **A retry row per failed file**: one button that re-sends the failed files is the same per-file work (each goes up on
  its own) with less markup; a generation retry stays per unfinished paper (Continue), because re-uploading its file
  would duplicate the paper.
- **Storing Markdown/text without a model**: it would leave a paper that can never get levels; the batch says why it was
  not added instead.
