# TextFold

A reader that zooms any text from every word to a one-screen map. Python
server in `textfold/`, reader in plain JavaScript under `textfold/web/`, the
Electron app in `desktop/`, the website in `site/`.

`docs/DEVELOPMENT.md` is the authority on how this is built — its **Layout**
section is the module map, and its other sections state the constraints that
are easy to break by accident. Read it before changing anything structural.
`CONTRIBUTING.md` has the rules for a change.

## This fork

`origin` is `cjdem/textfold`, a fork of `chenxiachan/textfold`, and it is being
made Windows-only. Two things that the obvious way of doing that gets wrong:

- **`tools/zoombench.py` is a capability.** It is the only way to
  check "Smoothness is a rule"; it now launches Chromium on Windows' Direct3D
  11 backend (`--use-angle=d3d11`). Deleting it removes the ability to
  check the project's first rule on *any* machine, and `docs/DEVELOPMENT.md`
  says the cheap substitute (headless rAF intervals) reports healthy while the
  reader drops frames. If a task would remove it, say what is being given up
  and ask, rather than treating it as cleanup. Running it end to end still needs
  `playwright` and exported comparison pages under `out/compare/`, neither of
  which is installed here; its numbers are Windows numbers and cannot be
  compared with the Metal ones recorded before.
- **The `sys_platform` markers in `pyproject.toml` and `requirements.txt` are
  for pip, not for runtime** — they keep a dependency from being installed
  where no prebuilt wheel exists (elsewhere it would have to build from source,
  needing Rust). Simplifying them for Windows is fine; making a dependency
  uninstallable is not.

Being Windows-only is a goal, not a licence to delete: a change that removes
platform code should say what functionality goes with it.

## Working here

- **Tests:** `python -m unittest discover tests` — 104 tests, about seven
  seconds, needing nothing beyond `requirements.txt` and touching none of your
  papers. `python .claude/hooks/verify.py` runs the same suite, finding the right
  interpreter (this machine keeps its dependencies in `.venv`, not in the system
  Python) and setting `TEXTFOLD_NO_MODELS=1`.
- **Run it:** `python -m textfold serve`, then `http://localhost:3017`.
- **One change at a time.** `CONTRIBUTING.md` asks for one change per pull
  request: what it changes, why, and how you checked it.
- **Commits** are single-line, capitalized, prose — no `feat:` prefixes. A long
  sentence that says what changed and why it matters is the house style.
- **Papers and keys stay out of commits.** `papers/`, `out/` and `~/.textfold/`
  are git-ignored; if one of them shows up in `git status`, something is wrong.

## Optimizing

`/optimize <goal>` runs the full workflow — a confirmed plan, an isolated
worktree, independent verification, a written record, and a local merge. The
rules that are easiest to get wrong live in
`.claude/skills/optimize/references/invariants.md`; the short version:

- The two fold engines (`plugins/pi-textfold/extension/fold.ts` and
  `plugins/textfold/hooks/fold.ts`) must stay byte-identical.
- Parsed HTML passes through `textfold/semantic.py`, and nothing renders around it.
- A parser change renumbers atoms, so previously generated layers go stale.
- **No change may make the zoom less smooth** — `tools/zoombench.py` measures it
  on Windows' Direct3D 11 backend, but running it end to end needs `playwright`
  and exported comparison pages, so on this machine that axis stays unmeasured.
  Say so; never report it as unaffected.
