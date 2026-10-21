# API providers only, with a local Magpie gateway first

**Date:** 2026-10-21
**Branch:** `worktree-provider-only-magpie`
**Commit:** `d09d60a` (the change; this record follows in its own commit)

## What and why

TextFold reached models through the product's Claude Code, Codex and Pi CLI runtimes as well as API providers. Those
runtimes are gone: generation now uses API providers only. An optional local Magpie gateway is discovered at
`http://127.0.0.1:3425/v1/models`, listed first, and used as the default model source when one is available. The
ChatGPT bridge, the other providers, and PDF conversion through MinerU followed by TextFold's own parsing are unchanged.

## The change

- `textfold/agents.py` — deleted: the product scan, agent catalogs and one-shot CLI runtimes.
- `textfold/llm.py` — only the Anthropic SDK and OpenAI-compatible API paths remain; no subprocess dispatch.
- `textfold/models.py` — API-only catalog; Magpie first and default; explicit choices and legacy ids handled safely;
  settings updates share one re-entrant lock and are written through an atomic replacement.
- `textfold/providers.py` — Magpie preset, non-blocking dynamic discovery with a short cache, display names, reasoning
  levels, `MAGPIE_BASE_URL`/`MAGPIE_MODELS`, manual configuration precedence, and the local token.
- `textfold/procenv.py` — the bridge's Windows child environment and UTF-8 text helper, moved out of `agents.py`.
- `textfold/bridges.py` — uses `procenv`; the ChatGPT bridge and OpenRouter authorization remain.
- `textfold/server.py` — removed the agent scan route, state and startup scan; settings changes go through
  `models.update_settings`; the Magpie probe uses the local token.
- `textfold/__main__.py`, `textfold/pipeline.py`, `textfold/zotero.py` — API-only model resolution and messages; Zotero's
  library choice joins the shared settings update path.
- `textfold/web/app.js`, `i18n.js`, `app.css` — no Agents UI; Magpie is the default provider form; landing and settings
  retry briefly while a local probe answers; source labels describe automatic local providers.
- Tests — API-only scope, Magpie discovery/offline/manual/default/collision/resolve/chat, legacy ids, two-writer
  settings updates, retained bridge environment/UTF-8 behavior, and updated API fixtures.
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md`, `docs/requirements/product-scope.md`, `site/strings.py`,
  `site/build.py`, `pyproject.toml` — current promises describe API providers and optional Magpie, not CLI runtimes.

## Docs checked

- `README.md`, `README.zh-CN.md` — model setup and table updated; historical entries no longer promise runtime discovery.
- `docs/DEVELOPMENT.md` — model access, Magpie, `TEXTFOLD_NO_MODELS`, Layout and UTF-8 sections updated.
- `docs/requirements/product-scope.md` — the current scope now says API-only and records what was lost.
- `site/strings.py`, `site/build.py` — app copy and llms.txt/structured-data copy updated.
- `pyproject.toml` — the optional-dependency comment no longer mentions agents.
- `.claude/agents/`, `.claude/skills/`, `docs/WORKFLOW.md` — deliberately unchanged: development workflow, not product
  runtime. Historical `docs/changes/` records left intact.

## Decisions

- Magpie stays external: no install, package, dependency or copied code, so no NOTICE change.
- Model ids are read from `/models`; no observed id is hard-coded.
- A manually configured Magpie is authoritative and suppresses the automatic row; otherwise the first discovered model
  is the default. A shared id resolves to Magpie because it is first.
- The ChatGPT bridge still uses Codex's login, but TextFold no longer runs the Codex CLI.

## Concurrency and locks

`models._SETTINGS_LOCK` spans load, mutation and save for every server/Zotero settings writer; the file is replaced
atomically from a temporary file. `tests/test_agent_encoding.py` runs two threads changing separate fields and checks both
survive. Magpie probes use one background-probe lock and publish a snapshot under a second lock; the provider cache key
includes the probe's answer.

## How it was verified

- `python .claude/hooks/verify.py` — **196 tests, 13.791 s, OK** (baseline before the change: 195 tests, 7.176 s).
- `git diff --check` — no whitespace errors (only Git's LF→CRLF notices).
- `python site/build.py` — built `assets`, `index.html`, `llms.txt`, `robots.txt`, `sitemap.xml`, `zh.html` and
  `preview.html`; no unfilled fields.
- Real local Magpie: 6 models discovered; default `auto/deepseek-v4.1-flash`; resolve base/key/protocol correct; a chat
  call returned `{"ok": true}`; `textfold get` wrote levels with that model in isolated temporary settings and data.
- Browser preview with isolated settings: settings showed Magpie first with 6 models, model selector only Magpie,
  no Agents section; the landing hid its connect panel once the probe answered.
- Unreachable Magpie simulated with another provider configured: catalog returned in 0.057 s with OpenRouter,
  default `openrouter/auto`.
- Chinese Markdown import, parse and static page build completed without encoding errors.
- `textfold-verifier` findings: (1) the Magpie row and provider-cache key came from two snapshots, so a probe answering
  between them could cache disagreeing rows; fixed to one snapshot. (2) duplicate stored Magpie rows were only partly
  filtered; fixed to coalesce every `magpie` UI row. (3) invalid/malformed discovery entries were not all exercised;
  added. (4) the record was pending and had no hash/workflow note; completed. (5) the retained bridge text helper has no
  current product pipe; kept for the bridge contract, and the env helper is covered. (6) a fixed temporary settings path
  was process-local; now a unique temp file is used. (7) a test passed `{}` and read the machine's settings; fixed.
  (8) the settings retry could redraw an open provider form; it now does not retry while a form is open. (9) a second
  record read found a stale temp-name assertion and a dead test patch for the removed helper; fixed.

## Measured

| | before | after |
|---|---|---|
| Tests | 195 | 196 |
| Magpie discovery, catalog call (unreachable gateway) | — | 0.057 s |

The CLI runtime's tests were removed and API/Magpie/settings coverage was added; the net count is one higher.

## Not measured

- **Zoom smoothness was not measured.** `tools/zoombench.py` needs `playwright` and exported comparison pages under
  `out/compare/`, neither available here; no claim is made that zoom is unaffected.
- The real gateway was not stopped: offline behavior was tested with an unreachable local port and the suite's fake
  server, not by interrupting the user's Magpie.
- Two separate TextFold processes saving settings at once are not serialized: the lock is in-process. The unique temp
  file prevents a torn replacement, but the last writer can still win; cross-process locking was not added.
- Site deployment and a full MinerU conversion were not rerun; both are outside this change.

## Pitfalls

- A generation started before the background probe answered initially saw no model. `models.resolve` now waits up to two
  seconds for an in-flight probe; landing and settings page rendering still never wait.
- Server settings writers originally reloaded and saved independently, so two updates could erase each other. All now use
  the shared lock and atomic replacement.
- Manual Magpie must suppress the automatic row or the UI shows two Magpie groups; the key is normalized on save and load.
- Deleting `agents.py` would have broken the bridge's `child_env`; the bridge helper moved to `procenv.py` first.
- `magpie_label` may carry mojibake; `display_name` is used first, then the label, then the id.
- The provider row and its cache key must come from one Magpie snapshot; reading them twice lets a probe answer in between.
- Every stored `magpie` row must be filtered, not only the first; a hand-edited settings file can hold two.
- Historical README and `docs/changes/` text is not a current promise; current setup text was updated separately.

## Rejected

- Hard-coding the five observed Magpie model ids, or making Magpie a Python dependency.
- A synchronous probe on the landing page (blocks a closed local port) or leaving an automatic probe for a manually
  configured Magpie (wrong endpoint, pointless wait).
- Keeping an agent fallback after removing the runtimes, or removing the ChatGPT bridge with them.

## Workflow

The plan gate, isolated worktree, full suite, site build, live-gateway checks and independent verifier were used; the
local log was written before merge. The independent verifier took about sixteen minutes and found one ordering bug,
one duplicate-row bug, one test gap and several tidy-ups, all addressed above. No step was skipped; nothing was pushed.
