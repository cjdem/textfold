---
name: optimize
description: Optimize a part of TextFold through a confirmed plan, an isolated git worktree, independent verification, a written record, and a local merge. Use when the user asks to optimize, improve, speed up, clean up or refactor something in this repository, or types /optimize. Not for a one-line fix the user has already specified exactly — that needs only the tests and the commit.
argument-hint: what to optimize, and any constraint you already know
---

# Optimizing TextFold

The goal is `$ARGUMENTS`. If it is empty or names nothing in particular, ask what to optimize and stop — an optimization aimed at nothing produces work nobody asked for.

Seven phases. The order is the point: nothing is changed until a plan is confirmed, nothing is merged until it is verified, and both are written down before the branch goes away.

## 0 · Frame

Say back in one sentence what is being optimized and what "better" will mean — faster, smaller, fewer moving parts, a bug gone. If you cannot state it as something measurable or falsifiable, say so now.

Check the ground:
- `git branch --show-current` is `main`, and `git status --short` is empty. If not, stop and ask — an optimization that starts on top of someone's half-finished work cannot be told apart from it. **An empty status is also what puts this workflow's own files into the worktree**: `.claude/`, `CLAUDE.md` and `docs/changes/` have to be committed before the first run, since a worktree is cut from a commit and uncommitted files are not in it.
- Run the suite and keep the numbers: `python .claude/hooks/verify.py`. Expect 85 tests. Record the time.
- Note the version: `python -m textfold --version`.

## 1 · Survey

Send two or three `textfold-scout` agents in parallel, each with a different angle on the same goal — the code path, the constraints, the alternatives. Give each the goal verbatim plus what you already know, so they do not repeat your work.

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

Then these two, whichever apply:

- **If the change touches the reader or anything the zoom runs through**, say plainly: this machine cannot measure smoothness — `tools/zoombench.py` needs a Mac's GPU, and `papers/` is empty. Ask whether to proceed knowing that axis stays unmeasured, or to stop. Never let a plan imply the smoothness rule was checked.
- **If the confirmed plan is bigger than one change**, say which part is being done now and which is left. `CONTRIBUTING.md` asks for one change at a time, and a branch that does three things cannot be verified as one.

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

Make the confirmed change and nothing adjacent to it. Match the code around it — plain names, comments that say why rather than what.

Delegate only work that is genuinely independent: a separate file, a separate question, no shared state with what you are editing. **Do not reach for `isolation: "worktree"` here** — a subagent given its own worktree writes into a throwaway checkout, and its commits do not come back to this one. Since you are already in a worktree, it isolates twice and turns delegation into a manual cherry-pick. Plain subagents inherit this session's directory; keep them read-only, and keep one writer in the tree at a time.

Do not commit yet. The commit comes once the change is verified and recorded, so that the message can describe what was actually done.

## 5 · Verify

Five checks, in this order. A failure sends you back to phase 4; if it cannot be made to pass, abandon the work instead of merging it — `ExitWorktree` with `remove`, and write down why in phase 6.

1. **The suite.** `python .claude/hooks/verify.py` — green, with the numbers recorded. `git diff --check` alongside it, for whitespace and conflict markers the tests do not see.
2. **The plugins, if you touched `plugins/`.** Their tests are not among the 85, and neither runner is set up on this machine as it stands — `plugins/textfold/` has no `package.json` (its tests want `claude plugin test plugins/textfold`, from Claude Code 2.1.287+), and `plugins/pi-textfold/` has a `package.json` but no `node_modules` (`npm install` first, which needs the network). **Run what is available and say plainly what was not.** If you changed the fold engine, both copies must still be byte-identical, and `tests/test_pi_textfold_same_fold.py` is the check that is actually wired up — so run it even when the TypeScript suites cannot run.
3. **An independent adversary.** Send `textfold-verifier` the branch and the claim. It cannot edit code, so it can only report. Act on what it finds, or say why it is wrong.
4. **The invariants.** Walk `references/invariants.md`. Each one is either holding, failing, or unjudgeable from here — there is no fourth answer.
5. **Smoothness, honestly.** If the change touches the reader, zoom or rendering, it stays **unmeasured on this machine**. Write that. "No impact on performance" is a claim nobody made.

## 6 · Record

Two records, both written from the actual diff (`git diff main...HEAD`), never from memory of what you meant to do. Templates: `references/committed-record.md` and `references/local-log.md`.

- **English, committed** — `docs/changes/YYYY-MM-DD-<slug>.md`. Concise: what changed, why, how it was verified, what was measured, what was rejected and what remains unmeasured. This is what a future reader has.
- **Chinese, local** — `notes/YYYY-MM-DD-<slug>.md`, not committed (`notes/` is git-ignored). Detailed: the reasoning, the dead ends, the numbers, the open questions, anything you would want if you came back to this in six months.

The same name in two places, on purpose: the committed one is the record, the local one is the thinking, and finding one should find the other.

## 7 · Merge

1. Commit on the branch. This repository's style: **a single-line, capitalized, prose subject** — no `feat:` prefixes, no bullet points, often a long sentence that says what changed and why it matters. A body only when the subject genuinely cannot carry it. End the message with the `Co-Authored-By: Claude Code <noreply@anthropic.com>` trailer. No `-s`: `CONTRIBUTING.md` asks contributors for a DCO sign-off, but the maintainer's own commits do not carry one, and add it only when preparing a contribution to the upstream project.
2. In the worktree, confirm nothing is left behind: `git status --porcelain` prints nothing, and the records are committed (the Chinese one lives outside the repo and will not appear either way). Then `ExitWorktree` with `keep` — the branch must outlive the worktree.
3. On `main`: `git merge --ff-only <branch>`. Fast-forwarding keeps the history linear — which is what this repository's history already is — *and* keeps the commit you actually wrote, message and all, rather than recreating it.
   - If `main` has moved on and the fast-forward is refused, rebase in the worktree (`git rebase main`), run the suite again there, and retry. Do not force anything.
   - Only if the branch holds several commits you want as one, use `git merge --squash <branch>` and then commit.
4. Clean up: `git worktree remove .claude/worktrees/<name>`, then `git branch -d <branch>` — the lowercase `-d`, which refuses to delete a branch whose work is not in `main`. If it refuses, the merge did not land the way you think it did; that refusal is the last safety net in the sequence, so do not reach for `-D` to get past it without understanding why.
5. Run the suite once more on `main`. The merge is the first moment the change sits where it will live, and this is the cheapest place to find out it does not.
6. **Do not push.** The user pushes on their own terms.
