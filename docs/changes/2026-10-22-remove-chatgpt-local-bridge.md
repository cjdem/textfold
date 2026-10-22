# Removing the ChatGPT local bridge, keeping OpenRouter

**Date:** 2026-10-22
**Branch:** `worktree-remove-chatgpt-bridge`

## What and why

TextFold had two one-click model doors: an OpenRouter key made by OAuth, and a ChatGPT subscription through the npm
`openai-oauth` bridge on `127.0.0.1:10531`. The product scope now says no subscription aggregation and no agent
runtime, so the bridge is the last thing of its kind. This removes it: every model now comes from an API provider —
OpenRouter, Magpie, an Anthropic or OpenAI-compatible key, or Ollama. **What is lost:** the in-product ChatGPT
subscription entry. A reader who used it needs an API key, OpenRouter, or the Magpie gateway.

## The change

- `textfold/openrouter.py` — new; the OpenRouter OAuth half of `bridges.py` moved over unchanged (PKCE, the code
  exchange, `minted`/`take_minted`, the desktop flag).
- `textfold/bridges.py`, `textfold/procenv.py` — deleted; the bridge probe/start/provider injection, and the Windows
  child PATH and text settings that only the bridge used.
- `textfold/models.py` — no `bridges` import, no `bridge_status()` in the provider cache key, no automatic bridge
  provider row.
- `textfold/providers.py` — the `chatgpt-bridge` preset is gone; `custom` stays last, which `server.py` relies on.
- `textfold/server.py` — `/api/bridge` and `/api/bridge/start` are gone, and `bridge` leaves `/api/models` and the
  landing boot; the OpenRouter routes and `/oauth/openrouter` now call `openrouter`.
- `textfold/web/app.js`, `i18n.js`, `app.css` — the bridge card, settings row, start/polling, copy command and
  `bridge_*`/`cn_gpt` strings and styles are gone; the OpenRouter blocks are untouched. A saved provider whose
  preset no longer exists finally edits as Custom instead of showing a preset that is not really selected.
- tests — bridge-only assertions leave `test_landing_page.py`, `test_magpie.py`, `test_agents_scope.py` and
  `test_agents_windows.py`; `test_agent_encoding.py` inlines the UTF-8 pipe settings; `tests/test_openrouter.py` is
  new (the S256 challenge against a fixed verifier, the exchange body, `minted`/`take_minted`, the desktop flag,
  the `#or-minted`/`#or-failed` return pages, the bridge routes 404, the OpenRouter routes alive), and
  `test_agents_scope.py` pins that a saved provider whose preset is gone still lists.
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md`, `site/build.py` — the removed door's promises are gone, and
  the READMEs' "What's new" records the loss.

## Docs checked

- `README.md`, `README.zh-CN.md` — updated: the ChatGPT plan row is gone; a What's new entry records the loss.
- `docs/DEVELOPMENT.md` — updated: bridge bullet removed; Models, home-page probes, `TEXTFOLD_NO_MODELS`, Layout, the
  tests line and the UTF-8 paragraph rewritten; the UTF-8 rule itself is kept.
- `site/` — updated: the llms() bullet; rebuilt, and `dist/`/`preview.html` are git-ignored.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no data format changed.
- `pyproject.toml` — not needed: no dependency or platform metadata changed.
- `requirements.txt` — updated: the anthropic comment no longer names the removed Codex and Pi integrations.
- `NOTICE`, `LICENSE`, `SECURITY.md` — not needed: attribution, licence and security are unchanged.
- `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md` — not needed: formats unchanged; the upstream
  divergence list already says the bridge is removed in this round.
- `desktop-mygo/README.md`, `.claude/agents/` — not needed: the app packages the Python tree; the payload is rebuilt
  at packaging time, not here.

## Decisions

- OpenRouter moved to `openrouter.py` rather than staying in a file named `bridges.py` that no longer holds a bridge.
- `gpt-5.5` stays in `default_model`: it is an OpenAI API model id, not a subscription-specific one.
- A saved `chatgpt-bridge` provider stays in `~/.textfold/settings.json` — existing user data is not deleted. It
  becomes an ordinary row pointing at a dead port; its edit form falls back to Custom (name, base and key kept),
  and the reader can remove it. `~/.textfold/bridge.log` stays on disk too.
- The acceptance grep is scoped to product code and current user-facing docs; historical records keep the words as
  the audit trail.

## Concurrency and locks

No new shared state. `~/.textfold/settings.json` keeps its single writer (`models._SETTINGS_LOCK` plus the atomic
replace); no migration was added, so there is no second writer. `bridge.log` is no longer written, and existing
content stays. The two-writer test in `tests/test_agent_encoding.py` still passes.

## How it was verified

- `python .claude/hooks/verify.py` — 206 tests, OK (baseline 196; 3 bridge-only tests removed, 13 added).
- `node --check textfold/web/app.js` and `node --check textfold/web/i18n.js` — both pass.
- `grep` over `textfold/`, both READMEs, `docs/DEVELOPMENT.md` and `site/build.py` — no `openai-oauth`,
  `127.0.0.1:10531`, `chatgpt-bridge` or `ChatGPT bridge`. The only exact-string occurrences left are the saved-row
  fixture in `tests/test_agents_scope.py`, which pins that the old row survives.
- `python site/build.py` — built; the generated pages contain no bridge or ChatGPT strings.
- Browser, server started with `TEXTFOLD_NO_MODELS=1` — the landing offers only OpenRouter and Other API options;
  Settings has the OpenRouter entry and no bridge row; the provider presets have no `chatgpt-bridge`; no console
  errors and no `/api/bridge` requests. A second run without that flag, with a temporary launcher pointing
  `models.SETTINGS` at a scratch settings file that holds a saved `chatgpt-bridge` row, showed the row still listed
  and editing as Custom, with its name and base kept; the real `~/.textfold/settings.json` was not touched.
- `textfold-verifier` — read the diff and ran the suite independently (202 at that point): it did not falsify the
  claim. It found one real UI defect on the saved-row edit path (fixed and checked in the browser), three test gaps
  (the S256 challenge relation, the `/oauth/openrouter` return pages, and the saved unknown-preset row; all added),
  and stale wording in `requirements.txt`, `models.py` and `_quiet_children`'s docstring (fixed). It also noted that
  `engine.py`'s curl text pipe still decodes in the locale code page; that predates this change and belongs to R2.

## Measured

| | before | after |
|---|---|---|
| tests | 196 | 206 |

## Not measured

- **Zoom smoothness is unmeasured on this machine.** `tools/zoombench.py` needs `playwright` and an exported
  comparison page, and neither is installed. This change touches `app.js` (landing and Settings, not `reader.js`),
  but the axis stays unmeasured; "no impact on performance" would be a claim nobody made.
- The OpenRouter flow against the real service. The new tests mock the exchange; no browser authorisation was run.
- An already-running `npx openai-oauth` process and the old `~/.textfold/bridge.log`: neither was inspected or
  stopped; the change only removes the code.

## Pitfalls

- `models.default_model` still prefers `gpt-5.5`; it used to enter a catalog through the bridge's recommend list.
  Keeping the preference is deliberate for readers with an OpenAI API key or a saved model list.
- `server._quiet_children()` had to stay: `engine.py` still runs curl through `subprocess.run` (and therefore
  `Popen`); deleting it with the bridge would have brought back a console window on Windows.
- A saved `chatgpt-bridge` row is listed and can be removed; editing it falls back to Custom and keeps its name,
  base and key, because its preset no longer exists. It still points at a dead port — that is the recorded loss,
  not a migration.
- `engine.py`'s curl download still passes `text=True` without an encoding, so its (error) text is decoded in the
  locale code page. This predates this change and belongs to R2's explicit-UTF-8 pass; the deleted `procenv.TEXT`
  was the only thing that documented the rule.
- The ignored `desktop-mygo` payload copies still contain the old bridge until the payload is rebuilt.

## Rejected

- Keeping OpenRouter in `bridges.py` to shrink the diff — the module name would keep describing something that is
  gone.
- Deleting saved `chatgpt-bridge` rows, or migrating them — it would delete user data and add a second settings
  writer.
- Keeping `procenv.py` for the later UTF-8 work — its only production user was the bridge; that change can add its
  own helper.
- Rewriting historical records so a repo-wide grep is clean — it would falsify the audit trail.
