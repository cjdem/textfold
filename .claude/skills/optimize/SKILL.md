---
name: optimize
description: Change TextFold through a confirmed plan, an isolated git worktree, independent verification, a written record, and a local merge — in optimize mode for something faster, smaller or cleaner, in feature mode for a new capability. Use when the user asks to optimize, improve, speed up, clean up or refactor, asks for a feature, or types /optimize or /feature. Not for a one-line fix the user has already specified exactly — that needs only the tests and the commit.
argument-hint: what to change, and any constraint you already know; for a feature, its requirements document under docs/requirements/
---

# Changing TextFold

The goal is `$ARGUMENTS`. If it is empty or names nothing in particular, ask what to change and stop — an optimization or feature aimed at nothing produces work nobody asked for.

This workflow serves two modes:

- **optimize** — an existing behaviour should be faster, smaller, simpler, or a bug gone.
- **feature** — a new capability, usually from a requirements document under `docs/requirements/`. `/feature` enters here directly.

State the mode in your first reply, in one sentence, and say which phase you are entering. The seven phases are the same; what the feature mode adds is marked **Feature mode**.

Seven phases. The order is the point: nothing is changed until a plan is confirmed, nothing is merged until it is verified, and both are written down before the branch goes away.

## 0 · Frame

Say back in one sentence what is being changed, which mode this is (**optimize** or **feature**), and what "better" will mean — for an optimization, faster, smaller, fewer moving parts, a bug gone; for a feature, the acceptance criteria its requirements document states. If you cannot state it as something measurable or falsifiable, say so now.

**Feature mode:** read the requirements document in full (`docs/requirements/<name>.md`). If there is none, ask for it before planning — a feature built from memory of a conversation cannot be verified against it.

Check the ground:
- `git branch --show-current` is `main`, and `git status --short` is empty. If not, stop and ask — a change that starts on top of someone's half-finished work cannot be told apart from it. **An empty status is also what puts this workflow's own files into the worktree**: `.claude/`, `CLAUDE.md` and `docs/changes/` have to be committed before the first run, since a worktree is cut from a commit and uncommitted files are not in it.
- Run the suite and keep the numbers: `python .claude/hooks/verify.py`. Record the count and time it prints; do not expect a fixed count — it grows with every feature.
- Note the version: `python -m textfold --version`.

## 1 · Survey

Send two or three `textfold-scout` agents in parallel, each with a different angle on the same goal — the code path, the constraints, the alternatives. Give each the goal verbatim plus what you already know, so they do not repeat your work. In feature mode, give one scout the requirements document verbatim and the data it will write, one the states and failure paths, and one the existing code it should reuse.

If `claude` offers the saved workflow `survey`, it does this fan-out in one call; use it when the goal sprawls across modules. Fall back to plain subagents whenever it is unavailable.

Collect their candidates into one ranked list. Do not add candidates of your own that nobody investigated.

## 2 · Confirm — the hard gate

**Change nothing yet. Do not create a worktree, do not touch a file, until the user approves.**

Put the plan in front of them with `AskUserQuestion` — the candidates as options, so the choice is theirs and not yours:

- the goal restated in one sentence
- the chosen change, and **exactly which files it touches**
- how it will be verified, concretely
- what could go wrong, and what it would break if it did
- what is deliberately **not** being done

**Feature mode also states in the plan:**

- the data contract — the files, schemas and versions this writes, and every reader of them;
- the states and transitions, including partial, cancelled and failed states;
- each failure path and what the reader sees;
- every writer of shared state, the lock or single-writer rule that serializes them, and what happens when a document is deleted, re-converted, or a generation finishes while a save is in flight;
- each acceptance item tagged `[test]`, `[manual]` or `[unmeasured]`; the manual and unmeasured ones are named in the record.

Then these, whichever apply:

- **If the change touches the reader or anything the zoom runs through**, say plainly: this machine cannot measure smoothness — `tools/zoombench.py` drives Windows' Direct3D 11 backend but needs `playwright` and exported comparison pages, and neither is installed here. Ask whether to proceed knowing that axis stays unmeasured, or to stop. Never let a plan imply the smoothness rule was checked.
- **If the confirmed plan is bigger than one change**, say which part is being done now and which is left. `CONTRIBUTING.md` asks for one change at a time, and a branch that does three things cannot be verified as one.
- **A feature and the tests, UI and docs that make it verifiable are one change.** Say so in the record; splitting them would leave no way to verify the end-to-end behaviour.

## 3 · Isolate

`EnterWorktree` with a short kebab-case name taken from the goal. The branch is cut from **local** `HEAD` — `.claude/settings.json` sets `worktree.baseRef: "head"` for exactly this reason, since work merged locally and not yet pushed would otherwise be invisible here.

Then **prove the base is what you think it is**, because getting this wrong is silent — you would work from an older tree and only find out at the merge:

```
git rev-parse --show-toplevel                       # under .claude/worktrees/<name>
git merge-base --is-ancestor main HEAD; echo $?     # 0 means local main is behind you
```

A non-zero answer means the worktree was cut from `origin/main` and does not contain work that is already on local `main`. Stop and say so rather than continuing on the wrong base.

The worktree is a fresh checkout: `papers/`, `out/` and `.venv` are git-ignored and therefore absent. Run the tests with `python .claude/hooks/verify.py`, which finds the environment in the main clone and runs it against this tree.

The branch is named by Claude Code after the worktree, and `git worktree list` shows both.

## 4 · Implement

Make the confirmed change and nothing adjacent to it. Match the code around it — plain names, comments that say why rather than what. For a feature, the tests, UI and documentation that make it verifiable are part of the confirmed change, not a follow-up.

Delegate only work that is genuinely independent: a separate file, a separate question, no shared state with what you are editing. **Do not reach for `isolation: "worktree"` here** — a subagent given its own worktree writes into a throwaway checkout, and its commits do not come back to this one. Since you are already in a worktree, it isolates twice and turns delegation into a manual cherry-pick. Plain subagents inherit this session's directory; keep them read-only, and keep one writer in the tree at a time.

Do not commit yet. The commit comes once the change is verified and recorded, so that the message can describe what was actually done.

## 5 · Verify

Six checks, in this order. A failure sends you back to phase 4; if it cannot be made to pass, abandon the work instead of merging it — `ExitWorktree` with `remove`, and write down why in phase 6.

1. **The suite.** `python .claude/hooks/verify.py` — green, with the numbers recorded. `git diff --check` alongside it, for whitespace and conflict markers the tests do not see.
2. **Persistence and interleavings.** If the change writes files or shared state, it needs at least one regression test with two writers interleaving: a save during a generation or candidate write, a save during a PDF re-conversion, a save crossing the move to the trash. A green suite that never runs two writers has not tested this; tell the verifier (check 3) to construct those interleavings too.
3. **An independent adversary.** Send `textfold-verifier` the branch and the claim. It cannot edit code, so it can only report. Act on what it finds, or say why it is wrong.
4. **The invariants.** Walk `references/invariants.md`. Each one is either holding, failing, or unjudgeable from here — there is no fourth answer.
5. **Text on a Chinese Windows.** If the change reads or writes text or runs a subprocess, run a Chinese title and Chinese card or notes content through import, parse, save, export and the static page build; look for `UnicodeDecodeError` and `UnicodeEncodeError`. Files are read as UTF-8, stored caches and settings are ASCII-escaped, and pipes are UTF-8 both ways.
6. **Smoothness, honestly.** If the change touches the reader, zoom or rendering, it stays **unmeasured on this machine**. Write that. "No impact on performance" is a claim nobody made.

## 6 · Record

Two records, both written from the actual diff (`git diff main...HEAD`), never from memory of what you meant to do. Templates: `references/committed-record.md` and `references/local-log.md`. The local log is written in the worktree's ignored `notes/`; phase 7 copies it to the main checkout before the worktree is removed.

- **English, committed** — `docs/changes/YYYY-MM-DD-<slug>.md`. Concise: what changed, why, the decisions the diff cannot show, how it was verified, what was measured, the concurrency and locks, what was rejected and what remains unmeasured. This is what a future reader has.
- **Chinese, local** — `notes/YYYY-MM-DD-<slug>.md`, not committed (`notes/` is git-ignored). Detailed: the reasoning, the dead ends, the numbers, the open questions, anything you would want if you came back to this in six months.

The same name in two places, on purpose: the committed one is the record, the local one is the thinking, and finding one should find the other.

## 7 · Merge

1. Commit on the branch. This repository's style: **a single-line, capitalized, prose subject** — no `feat:` prefixes, no bullet points, often a long sentence that says what changed and why it matters. A body only when the subject genuinely cannot carry it. End the message with the `Co-Authored-By: Claude Code <noreply@anthropic.com>` trailer. No `-s`: `CONTRIBUTING.md` asks contributors for a DCO sign-off, but the maintainer's own commits do not carry one, and add it only when preparing a contribution to the upstream project.
2. **Carry the local log out first.** `notes/` is git-ignored, so `git worktree remove` deletes it with the worktree. Copy `notes/YYYY-MM-DD-<slug>.md` to the main checkout's `notes/` and confirm it is there. Then, in the worktree, confirm nothing is left behind: `git status --porcelain` prints nothing, and the records are committed (the Chinese one lives outside the repo and will not appear either way). Then `ExitWorktree` with `keep` — the branch must outlive the worktree.
3. On `main`: `git merge --ff-only <branch>`. Fast-forwarding keeps the history linear — which is what this repository's history already is — *and* keeps the commit you actually wrote, message and all, rather than recreating it.
   - If `main` has moved on and the fast-forward is refused, rebase in the worktree (`git rebase main`), run the suite again there, and retry. Do not force anything.
   - Only if the branch holds several commits you want as one, use `git merge --squash <branch>` and then commit.
4. Clean up: `git worktree remove .claude/worktrees/<name>`, then `git branch -d <branch>` — the lowercase `-d`, which refuses to delete a branch whose work is not in `main`. If it refuses, the merge did not land the way you think it did; that refusal is the last safety net in the sequence, so do not reach for `-D` to get past it without understanding why.
5. Run the suite once more on `main`. The merge is the first moment the change sits where it will live, and this is the cheapest place to find out it does not.
6. **Re-read the project instructions from the main checkout.** This session's `CLAUDE.md` was read from the worktree; after the merge it names a path that no longer exists and may carry stale counts. Start a fresh session, or re-read `D:\Code\textfold\CLAUDE.md` and this skill before continuing.
7. **Do not push.** The user pushes on their own terms.
