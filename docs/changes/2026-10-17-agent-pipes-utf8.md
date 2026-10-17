# What the reader and a coding agent exchange is UTF-8

**Date:** 2026-10-17
**Branch:** `worktree-gbk-agent-pipes`

## What and why

Started from the terminal on a Chinese Windows machine, the server printed
two families of tracebacks: at startup, `UnicodeDecodeError: 'gbk' codec
can't decode byte 0x93` in a `_readerthread` while scanning the agents; and
when a generation began ("正在生成 · 简体中文"), four
`UnicodeEncodeError: 'gbk' codec can't encode character '▶'` in
`_writerthread`s.

Both are the same defect, and it runs past the pipes. Text that crosses
between this Python and an agent is UTF-8 — the CLI output, the reply file
`codex exec -o` writes, `~/.codex/config.toml`, the cache — while every
`subprocess` text pipe and `read_text()`/`write_text()` without an encoding
uses the system's, GBK here:

- **Writer side (the generation).** The translation prompt contains `▶`
  (`translate.py:68`, "Outline (▶ marks this section)"), which GBK cannot
  encode. `subprocess.run(input=prompt, text=True)` dies in its writer thread
  before the agent has read a full prompt; the child then waits for an input
  end that never closes. Every section's model call hangs or fails with no
  trace of what was asked.
- **Reader side (the scan).** An agent's `--help` output holds a typographic
  quote (`“`, bytes `E2 80 9C`); decoding those bytes as GBK raises in the
  reader thread, so that agent's catalog came back empty or partial. Codex's
  `config.toml` read the same way lost its whole model list.
- **After the pipes (the verifier's finds).** With the pipes fixed, the first
  translated reply dies at the cache write: `⟦a1⟧` markers (U+27E6) are not
  in GBK, and `json.dumps(..., ensure_ascii=False)` encoded them in the
  locale. The failed write also left an empty cache file that every retry
  then failed to parse. The same shape lurked further along: the saved
  layers (`store.write`), a note's answer (`notes.py`) and the settings
  (`models.py`) all wrote `ensure_ascii=False` in the locale, so a Korean or
  Hindi generation — both offered languages, neither in GBK — answers,
  caches, and then dies at the final save.

## The change

- `textfold/agents.py` — `TEXT = {"encoding": "utf-8", "errors": "replace"}`
  with a comment saying why; used by `_run` (the scan's `--version`/`--help`),
  `_rpc` (the scan's JSON-RPC to `codex app-server` and `pi --mode rpc`), the
  three places an agent's own files are read (`~/.codex/config.toml`, codex's
  `-o` reply file, npm's `.cmd` shim), `run_codex` and `_pi_once`.
- `textfold/llm.py` — both `claude -p` calls in `_claude` take `**agents.TEXT`.
  The reply cache is written ASCII-escaped (`json.dumps(rec, indent=1)`), so
  the file is readable in any locale, and read through `_read_cache`: ASCII is
  the new form; any file with bytes outside ASCII was written before this
  with `ensure_ascii=False`, in the system's encoding or in UTF-8 (another
  machine's) with no marker to tell them apart — so it is a miss, made again
  once, never returned as mojibake (`一` in GBK is `d2 bb`, valid UTF-8: both
  heuristics that pick an encoding are silently wrong for one of the two
  cases). A cache a failed write left empty or partial is a miss the same
  way: the call is made again and the file rewritten.
- `textfold/store.py`, `textfold/notes.py`, `textfold/models.py` — the saved
  layers, the notes file and the settings are written ASCII-escaped as UTF-8
  for the same reason: Korean or Hindi (offered languages) and a provider
  named in either are not in GBK, and the save failed outright. Reading is
  unchanged, so a file written before this still opens.
- `textfold/agents.py`, `_rpc` cleanup found by the new tests: after
  `p.kill()` the child is now reaped (`p.wait()`) and the pipes closed — the
  old code left a killed-but-unreaped process and open pipe handles per
  scan (ResourceWarning on this Python).
- `tests/test_agent_encoding.py` (new, 13 tests) — a child's UTF-8 reply is
  read; a prompt holding `▶ “quoted”` survives the exact pipe shape every
  model call uses; a JSON-RPC line with UTF-8 is read; the `claude -p`,
  `codex exec` and `pi -p` calls each send UTF-8 text (their real functions,
  with the process stubbed); a codex config holding a typographic quote
  keeps its default effort; a cache reply holding `⟦` is written
  (ASCII-escaped, so a GBK machine can read it) and read back; an empty cache
  file is made again; a cache from before ASCII replies, in either the
  system's encoding or UTF-8, is remade rather than read as mojibake; a
  layer, a note and the settings holding Korean are saved and read back. The
  children write UTF-8 bytes themselves, since their own stdout would
  otherwise use the system's encoding too.
- `docs/DEVELOPMENT.md` — a paragraph after the Layout: everything exchanged
  with a model CLI is UTF-8, why, that a failed cache write is redone, and
  that layers, notes and settings are written the same way. `CLAUDE.md` —
  102 tests.

## How it was verified

- Reproduced both reported failures on this machine before changing
  anything: a text-mode pipe writing `x` × 134 + `▶` hangs (the writer
  thread dies at position 134; a timeout is what the server's model call
  would hit), and a child writing `“` in UTF-8 makes the reader thread raise
  the same `'gbk' ... 0x9d` error as the startup scan.
- Captured Claude Code's own bytes: `claude -p` writes `\xc2\xb7` for `·` —
  valid UTF-8 — confirming the agents' output is UTF-8 and the reader side of
  the fix is the right direction.
- Ran the real scan after the fix: Claude Code 4 models, Codex **5** (0
  before — its `config.toml` read failed), Pi 21, no errors.
- `python .claude/hooks/verify.py` — **102 tests, OK**. On pristine `main`
  the new tests fail for the real reasons: the reader thread's
  `UnicodeDecodeError`, `UnicodeEncodeError` at the old cache write, the
  config's GBK decode, `AttributeError` for `agents.TEXT`, and the claude
  pipe test's missing `encoding`; on a UTF-8 CI runner the locale-dependent
  ones would pass on main too — inherent to a locale bug.
- `textfold-verifier`, three passes. The first found the cache write, the
  codex config read, the codex `-o` read, the untested writer-side wiring,
  and the over-broad docs sentence; all addressed. The second confirmed
  those and found the next unguarded saves — layers, notes, settings — and
  the UTF-8-first ambiguity in `_read_cache`; all addressed. The third
  confirmed those and found the converse of the ambiguity: an old UTF-8
  cache on a GBK machine was returned as a mojibake hit, so `_read_cache`
  now treats any non-ASCII cache as a miss (the third pass's outcome is
  written here from its report; it was not re-run after this last
  one-function change). Its remaining notes (the `_rpc` cleanup has no test
  of its own; POSIX was not run) are recorded here rather than hidden.

## Not measured

- **A full generation was not run through the app on this machine.** A
  `claude -p` spawned from inside this session inherits this session's
  `CLAUDE_CODE_*` host-auth variables and answers "Not logged in"; the user's
  own terminal, where the server runs, has none of them. The pipe is verified
  down to the bytes, the cache round-trip without a model, and the claude
  call's own kwargs; the model call behind them was not observed end to end.
- **Smoothness: unmeasured.** No file the reader loads was changed — this is
  a Python-side fix — but `tools/zoombench.py` needs `playwright` and an
  exported page, which this machine does not have, so the axis stays
  unmeasured rather than reported as unaffected.
