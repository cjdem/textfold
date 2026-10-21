# API providers only, with Magpie as the default

## Problem and outcome

TextFold currently reaches models through both product-side command-line agents (Claude Code, Codex and Pi) and API providers. This feature removes those product-side agent runtimes and uses API providers only, with the locally running Magpie gateway first in the provider list and as the default model source when the reader has no explicit model preference. Magpie remains an optional external service: TextFold neither packages nor installs it. PDF conversion remains MinerU Cloud API followed by TextFold's local parsing and is independent of model access.

The `.claude/agents/` prompts used by the development workflow are not product agents and must remain. The ChatGPT bridge and all existing API providers remain supported.

## Data contract

- Magpie is discovered over HTTP from `GET http://127.0.0.1:3425/v1/models`. `MAGPIE_BASE_URL`, when set, overrides the API base for both discovery and chat requests. Treat it as the `/v1`-style base (trim a trailing slash, append `/models` for discovery, and let the OpenAI caller append `/chat/completions`). Parse model ids from `data[].id`; use `display_name`, then `magpie_label`, then the id for the displayed name. The model list stays dynamic and no currently observed Magpie ids are hard-coded. `MAGPIE_MODELS` may provide a local override if implemented without disproportionate complexity.
- The catalog row is an OpenAI-compatible API model: provider key `magpie`, name `Magpie`, protocol `openai`, default base `http://127.0.0.1:3425/v1`, local source, and API key/token `magpie` when a manually configured Magpie has no key. Requests use `/v1/chat/completions` (or the equivalent path under an overridden base), never Magpie's Anthropic or Gemini endpoints.
- Magpie is first in `provider_list` and the model catalog. `settings.model`, when explicitly set to a usable model, wins. Otherwise choose Magpie's first model, then retain the existing fallback order `gpt-5.5`, `openrouter/free`, then the first API model.
- If a saved model id is an obsolete agent id such as `claude/claude-code/...`, treat it as unavailable and use the default without crashing.
- A model id shared by Magpie and another provider resolves to Magpie because Magpie is first; this intentional precedence is documented.
- No document, layer, card, note, or settings schema/version is added or changed. Existing settings continue to be read and written by the current settings code in `~/.textfold/settings.json`; provider discovery and its short-lived cache are runtime state.

## States and transitions

- **Magpie unknown / probe pending:** a background probe begins; catalog and landing requests return from cached data without waiting for the local port.
- **Magpie online:** a successful models response is cached for about ten seconds and exposed as one local provider row with the dynamic model list.
- **Magpie offline or probe failed:** use a short request timeout (about 1.5 seconds), keep the page and server responsive, retain other providers, and fall back through the existing default order. A later background refresh can discover Magpie without restarting TextFold.
- **Magpie manually configured:** use the saved manual configuration as authoritative, or coalesce it with automatic discovery into one row; never display two Magpie groups. An empty key uses `magpie` as the local token.
- **Settings explicitly select a model:** preserve that selection when it resolves; an obsolete or unknown selection falls back safely.
- **Model request:** resolve the chosen model as an API model and send it through the OpenAI-compatible chat-completions path. Normal provider errors are reported through existing model-call error handling.

## Failure paths

- Connection refused, timeout, malformed JSON, missing/non-list `data`, or entries without a usable `id`: do not block the landing/settings page or fail server startup; ignore invalid entries and use the other providers and fallback default.
- Magpie unavailable on first startup: do not install it or wait synchronously; the remaining provider behavior stays available.
- A saved old agent model: treat it as unavailable and fall back rather than invoking or looking for a CLI.
- A model id collision: Magpie wins by catalog order, as documented.
- A Magpie chat-completions error: report using existing API-provider failure behavior; do not try an agent runtime or another Magpie protocol.
- Automatic discovery plus a manual Magpie configuration: use the manual configuration or coalesce the rows, without duplicate groups.

## Shared state and concurrency

This feature adds no persistent document writes and no new settings format. Model selection, provider add/edit/remove, general settings, Zotero library selection, and the one-time legacy settings migration all write `~/.textfold/settings.json` through `models.save_settings`; today these callers can race because there is no shared settings lock. Route settings updates through one re-entrant lock spanning reload, mutation and save, and make the file replacement atomic, so concurrent independent updates do not erase each other. Test two simultaneous updates to separate settings fields. The provider probe/catalog cache is transient: coalesce Magpie probes with a lock, publish cached results safely, and include the latest result in the provider-list cache key; concurrent refreshes must not make the landing wait on a local network request. Existing generation, conversion, note/card save and trash writers keep their current queues and locks; this feature adds no writer to `card.json`, `notes.json`, layer files, or document folders.

## Scope

- Remove the product CLI agent implementation and all product UI, state, startup scanning/thread, settings resolution, and current docs that promise automatic Claude Code/Codex/Pi discovery.
- Preserve ChatGPT bridge subprocess behavior by moving only its needed child environment and UTF-8 text-pipe helpers into a small independent helper or `bridges.py`, including Windows handling.
- Add automatic and manual Magpie provider support, dynamic model discovery, ordering, default selection, API resolution, and OpenAI-compatible calls.
- Update `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md`, `site/strings.py` (`app_p`), `pyproject.toml` optional-dependencies comments, tests, settings UI text and `textfold/web/app.css` comments. Add `docs/changes/2026-10-21-provider-only-magpie.md` with `Docs checked` and `Pitfalls`. Keep `.claude/agents/`, development workflow agents/skills, ChatGPT bridge, MinerU/PDF behavior, and all other API providers.

## Acceptance criteria

### Tests

- [test] `python .claude/hooks/verify.py` passes; record baseline and final counts.
- [test] `textfold/agents.py` is absent and product code does not import `agents`.
- [test] `models.catalog` has no entry with `kind == "agent"`; `/api/agents/scan` is absent; server state has no `agents`, `scanning`, or `scannedAt` fields and startup launches no agent scan thread.
- [test] One model call does not launch `claude`, `codex`, or `pi` subprocesses.
- [test] Fake HTTP/urllib coverage exercises Magpie online and offline, dynamic names and ids, Magpie-first ordering, default first Magpie model, explicit settings override, safe fallback, and resolve base/key/protocol.
- [test] Legacy agent settings resolve safely without a crash.
- [test] Keep applicable UTF-8 subprocess regression coverage for the ChatGPT bridge on Windows.
- [test] Concurrent settings updates to separate fields both survive the settings save.
- [test] `git diff --check` passes.

### Manual

- [manual] With the already installed local Magpie gateway running, the settings page shows Magpie first and selects its first model by default; a small generation or `textfold get` call succeeds through Magpie.
- [manual] With Magpie stopped, startup and the settings page do not block, and another configured provider remains usable. Do not install Magpie if it is unavailable; record the manual check as skipped if necessary.
- [manual] Settings contain no Agents section and model choices contain API providers only.
- [manual] `python site/build.py` builds successfully if site content is changed; do not deploy.

### Documentation and unmeasured behavior

- [test] Current docs no longer promise automatic discovery of Claude Code, Codex, or Pi. Update `README.md` and `README.zh-CN.md` model tables and setup instructions, `docs/DEVELOPMENT.md` model access, `TEXTFOLD_NO_MODELS`, Layout and UTF-8 sections, `site/strings.py` `app_p` copy, and `pyproject.toml` optional-dependencies comments. Leave historical `docs/changes/` entries intact.
- [test] The committed record is `docs/changes/2026-10-21-provider-only-magpie.md`, includes `Docs checked` and `Pitfalls`, and reports the commit hash, baseline/final test counts, verifier findings, manual results, unverified items, and workflow friction. The local Chinese log is kept under ignored `notes/` and copied to the main checkout before worktree cleanup. No key appears in source, records, or logs.
- [manual] Complete the feature skill's plan approval, isolated worktree, independent verifier and local merge stages; report any phase that blocked or required human action, without bypassing a check.
- [unmeasured] Zoom smoothness remains unmeasured on this machine. The reader/zoom is outside scope; do not claim it was measured or unaffected.

## Non-goals

- Do not change PDF/MinerU, reader/zoom, desktop shell, release workflows, or site deployment.
- Do not remove the ChatGPT bridge, OpenRouter, Anthropic, Ollama or other providers; do not change the `anthropic` extra.
- Do not package, install, or make Magpie a hard dependency. It is an external MIT-licensed gateway; link its repository in the docs. Add MIT attribution to `NOTICE` only if Magpie code is copied.
- Do not remove `.claude/agents/`, `.claude/skills/`, or `docs/WORKFLOW.md`. If the feature workflow itself causes a problem, record and report it instead of skipping verification.
- Do not push or touch `papers/`, `out/`, `library.json`, or `~/.textfold/`; do not commit keys.
- Preserve Windows-only behavior, UTF-8 behavior and the zoom-smoothness constraint.
