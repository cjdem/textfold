# The local server answers only requests addressed to this computer

**Date:** 2026-10-22
**Branch:** `worktree-server-host-check`

## What and why

A web page can point its own domain at `127.0.0.1` (DNS rebinding); the browser then treats requests to that name as
same-origin and lets the page read what the local server returns. The server listened on loopback and checked the
Origin of writes, but it never checked whom a request was addressed to, so a rebinding page could still `GET` the
library. This ports upstream `4fee928`: a request whose Host header is not `localhost`, `127.0.0.1` or `[::1]` is
answered 421 before any route runs. Browsers set Host from the address being fetched and pages cannot forge it, so
the allowed names are exactly the ones a local reader uses.

## The change

- `textfold/server.py` — `LOCAL_NAMES` and `addressed_here()` (case-insensitive, any port, exact name only), checked
  at the top of both `do_GET` and `do_POST`; the module docstring says why.
- `tests/test_server_host.py` — new; two unit tests for the name check and three on a real server with a temporary
  HOME and data folder: a forged name reads nothing and writes nothing, the three local names read as before, and a
  request with no Host is refused.
- `SECURITY.md` — the local-server bullet now names DNS rebinding and the 421 answer.

## Docs checked

- `SECURITY.md` — updated: the guard is stated where the server's other protections are.
- `docs/DEVELOPMENT.md` — not needed: it does not describe the Host or Origin checks; the module docstring and
  `SECURITY.md` are where this is documented.
- `README.md`, `README.zh-CN.md` — not needed: no user-facing promise about how the server is addressed changes.
- `site/` — not needed: the site is static and never talks to a local server.
- `pyproject.toml`, `requirements.txt` — not needed: no dependency or platform change.
- `NOTICE`, `LICENSE` — not needed: attribution and licence unchanged.
- `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md` — not needed: formats unchanged.
- `desktop-mygo/README.md`, `.claude/agents/` — not needed: the app reaches the server at `127.0.0.1:3017`, an
  allowed name; the agent prompts do not describe this route.

## Decisions

- Any port is allowed; only the name is checked. `localhost:3017` and `127.0.0.1:31917` are both this computer.
- The allowed set is fixed to the three loopback names. A configurable allowlist would be a way to turn the guard
  off by accident, and the product is loopback-only.
- `localhost.` (a trailing-dot FQDN) and `127.0.0.2` are refused. They are not addresses the reader is given, and
  accepting them widens the surface for no user benefit.
- 421 is answered before the body is read, before any route, and before any state changes; a rejected write cannot
  create a folder, start OpenRouter state or enqueue a job.

## Concurrency and locks

No shared state is added. The check is stateless and runs before any handler, so a refused request cannot interleave
with a save, a generation or a conversion. The real-server tests include rejected writes and then assert the folder
list, the paper list, the job queue and OpenRouter's minted state are unchanged (`{"folders": [], "of": {}}`, the one
imported paper, `[]`, and `{"minted": false}`).

## How it was verified

- `python .claude/hooks/verify.py` — 211 tests, OK (baseline 206; 5 added).
- `git diff --check` — clean.
- `textfold-verifier` — could not break it; no browser-reachable Host variant got through, and the tests would fail
  if the guard were removed. It noted that the write test observed only the folder side effect (it now also checks the
  paper list, the job queue and OpenRouter's minted state), that `or 'localhost:3017'` had become dead code (removed),
  and that the docstring's "request" overstated the two implemented methods (now "GET or POST"). It probed duplicate
  `Host` headers and absolute-form targets with raw sockets and judged both unreachable from a browser; both are
  recorded below. It also noted that the fixture's free-port picker has a bind-close race (test-only, unchanged) and
  that a failure after `Popen` would leak the child (now cleaned up by a class cleanup).

## Measured

| | before | after |
|---|---|---|
| tests | 206 | 211 |

## Not measured

- The extra work per request is one regular expression on a header. Request latency was not measured; no target was
  set for it, and this change does not touch the reader, rendering or stored data.

## Pitfalls

- The check must stay before the route table in **both** methods. A future route added in a new `do_PUT`/`do_DELETE`
  would need its own check; the server has none today.
- `Host` is absent in an HTTP/1.0 request that omits it; that is refused, like any other name but this computer's.
- The OpenRouter callback is built from the Host header; after this change it can only be a local name, which is
  what the consent redirect needs.
- `localhost.` is a valid DNS spelling of localhost but is refused. A reader who types it gets 421; the app and its
  own links use `localhost` without the dot.
- `[::1]` is accepted as a Host name, but the server listens on IPv4 only; it is a name the guard allows, not a
  reachable address on this build. A future IPv6 listener would also need `::1` in the Origin allowlist.
- Duplicate `Host` headers and an absolute-form request target are not defended. Browsers cannot send either (Host is
  a forbidden header, one authority per request; absolute-form only goes to a configured proxy), and routing uses
  the path, never the target's authority. Verified with raw sockets, not a browser.
- The first commit attempt failed in the pre-commit suite: R0's bridge-route test sent `b"{}"` with a GET, and
  Windows aborted the connection before the 404 was read (`WinError 10053`). The test now sends a body only for
  POST; three consecutive suite runs passed. That fix is on `main` as `69e92ad`.

## Rejected

- Accepting `127.0.0.0/8`, `0.0.0.0` or `[::ffff:127.0.0.1]` — wider than the addresses the reader is given, with no
  use case.
- A configurable list of allowed names — a second way to disable the guard, and nothing needs it.
- Trusting `X-Forwarded-Host` — the client can set it; it is not a name the browser was made to use.
- Relying on the Origin check for reads — navigations and `GET`s do not carry an Origin, which is the hole this
  closes.
