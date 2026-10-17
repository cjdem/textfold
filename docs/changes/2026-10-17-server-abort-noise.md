# A browser that leaves is not a server error

**Date:** 2026-10-17
**Branch:** `worktree-server-abort-noise`

## What and why

Started normally and used from a browser, the server printed, for a page
load the browser abandoned (a reload, a tab closed, a request superseded):

```
Exception occurred during processing of request from ('127.0.0.1', 56209)
ConnectionAbortedError: [WinError 10053] 你的主机中的软件中止了一个已建立的连接。
During handling of the above exception, another exception occurred:
...
ConnectionAbortedError: [WinError 10053] ...
```

Two tracebacks per aborted request. `Handler.send` caught `BrokenPipeError`
and `ConnectionResetError` around `self.wfile.write(data)` — but Windows
raises `ConnectionAbortedError` (WinError 10053) for a client that has gone,
and it can arrive while the headers are flushed, before the body write. The
uncaught exception reached the dispatcher's `except Exception`, which tried
to send a JSON 500 on the same dead socket; that raised again, and
socketserver printed both.

## The change

- `textfold/server.py`, `Handler.send`: the whole response — status line,
  headers, body — is wrapped in `try/except ConnectionError`. One clause
  covers `BrokenPipeError`, `ConnectionResetError` and
  `ConnectionAbortedError`; a send on a socket whose reader has gone is
  dropped, exactly as the old clause intended but with the Windows case and
  the header flush included. Every normal response goes through `send`
  (one `wfile.write` site); the two other writers the verifier found take
  the same guard: the base class's own 400/501 replies (`Handler.send_error`
  overridden) and the `/p/<id>` 302 redirect, which wrote its headers
  directly.
- `tests/test_server_abort.py` (new) — the real `Handler.send` (from
  `make_handler`), with a stub whose socket aborts at the body and at the
  headers: neither raises. Both fail on `main` with the user's
  `ConnectionAbortedError`.
- `CLAUDE.md` — 104 tests.

## How it was verified

- The two new tests exercise the exact exception path; on `main` they raise
  `ConnectionAbortedError` (10053), the error in the log; with the change
  they pass.
- `python .claude/hooks/verify.py` — **104 tests, OK**.
- `textfold-verifier`: the fix is sound and hides nothing real (the body
  encoding and `json.dumps` stay outside the `try`, so a genuine 500 is still
  reported); it found the two response paths that still wrote outside the
  guard — the `/p/<id>` 302 redirect and the base class's 400/501 replies —
  both now guarded as above.
- No browser was driven in this change; the exception's shape and timing are
  taken from the reported log and reproduced in the stub.

## Not measured

- **Smoothness: unmeasured.** No file the reader loads was changed, but
  `tools/zoombench.py` needs `playwright` and an exported page under
  `out/compare/`, neither on this machine, so the axis is not reported as
  unaffected.
