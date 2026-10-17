# Only the agents the reader can drive are listed

**Date:** 2026-10-18
**Branch:** `worktree-agents-report-only`

## What and why

The settings page listed every mainstream agent CLI it could find on the
computer — Gemini CLI, Qwen Code, opencode, Cursor Agent, Kimi CLI, Amp, Goose,
Crush, Droid, Copilot CLI, iFlow and Aider — with a "found, not supported yet"
label. None of them could run a generation: the reader drives only Claude Code,
Codex and Pi. The list advertised twelve tools that did nothing, and the scan
spent a process launch (`--version`) on each of them at startup.

## The change

- `textfold/agents.py` — `REGISTRY` is the three drivable runtimes; the
  `runnable` flag is gone from the registry, the scan rows, the model filter
  and the docstring. Every registered agent is asked for its models.
- `textfold/server.py` — the `/api/models` payload no longer carries `runnable`.
- `textfold/web/app.js`, `textfold/web/i18n.js` — a found agent always shows its
  model count; the "found, not supported yet" branch and string are gone. The
  "Not found" line still names Claude Code, Codex or Pi when one is missing.
- `textfold/web/app.css` — the `.st-dot.warn` rule had no producer left; removed.
- `docs/DEVELOPMENT.md` — the twelve reported tools are no longer promised;
  the page says only the three are scanned and listed.
- `docs/requirements/product-scope.md` — item 1 ticked (the browser check below).
- `tests/test_agents_scope.py` (new, 4 tests) — the registry is exactly the
  three runtimes; a scan returns those three rows with no `runnable` key; a
  found agent is asked for its models and `models()` returns them; the
  `/api/models` payload carries no `runnable` flag.

## Decisions

- Remove the twelve tools rather than keep them behind a label: a row that
  cannot be chosen is noise, and "not supported yet" invites a question the
  reader cannot answer.
- Remove the `runnable` concept itself rather than keep a dormant branch: the
  product rule is that only drivable agents are listed, and a future runtime
  should arrive with its runner.

## Rejected

- Keeping the twelve rows with a "found, not supported yet" label: it
  advertises tools that cannot be chosen.
- Scanning them but hiding them in the UI: the scan still costs a process
  launch and a version call for each at startup.

## How it was verified

- `python .claude/hooks/verify.py` — **175 tests, OK** (7.1 s); the four new
  tests are the registry, the no-model scan, the found-agent model catalog and
  the payload shape.
- `node --check textfold/web/app.js` and `node --check textfold/web/i18n.js` —
  clean.
- `grep` over `textfold/`, `tests/`, `docs/DEVELOPMENT.md`, `README.md` and
  `CLAUDE.md` (excluding `textfold/web/vendor/`) — no report-only name and no
  `runnable` reference remains outside the new test that asserts its absence.
- **In the browser**: the server was started from the worktree against a
  temporary data folder; the landing page in Simplified Chinese → **设置**
  showed **本机的 AGENT** with exactly Claude Code (4 个模型), Codex (5) and
  Pi (21), no "已找到，暂不支持" row. The dialog's headings were 模型 /
  本机的 Agent / API 供应商 / PDF 引擎.
- The independent verifier ran a real scan on this machine: all three were
  found and cataloged (4, 5 and 21 models; 30 ids from `models()`), with no
  errors.

## Not measured

- The settings dialog was checked in Chinese; the English rows use the same
  template and `st_unsupported` is gone from both tables, but the English
  dialog was not opened.
- The changed web code is the settings dialog, not the zoom or render path;
  zoom smoothness stays **unmeasured** on this machine, and no claim is made
  that it is unaffected.
