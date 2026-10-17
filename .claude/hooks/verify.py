"""The tests, run before a commit or a merge, so a red suite cannot land.

Wired in `.claude/settings.json` as a PreToolUse hook on Bash. It reads the
hook's JSON on stdin and, only for `git commit` and `git merge`, runs the test
suite in the tree the session is working in. Green lets the command through;
red exits 2, which blocks the command and hands the failures back.

Why a hook and not a Stop hook: a Stop hook can only say "you stopped too
early", so it fires again on every retry and Claude Code caps it at 8 blocks in
a row. This fires exactly once, on the one command that would otherwise record
the change, and it runs the tests rather than asking whether they were run.

Two things it has to get right on a machine where the tests live in a virtual
environment and the work happens in a git worktree:

- *Which interpreter.* The system Python usually has no dependencies installed
  (CONTRIBUTING installs them into the system Python, this machine keeps them
  in `.venv`), so the suite is run by whichever of those has them.
- *Where the worktree is.* A worktree under `.claude/worktrees/` is a checkout
  of this repo and does not carry `.venv`, which git ignores. So when the
  session's tree has no environment of its own, the one in the main checkout
  is used -- `--git-common-dir` is the reliable way to find it from a linked
  worktree, where it points at the main repository's `.git` and not at
  `.git/worktrees/<name>`.

The gate is not absolute. It guards every commit in this repository, so it has
an opt-out — `--no-verify`, git's own word for skipping hooks, or the
TEXTFOLD_SKIP_GATE variable — for commits that have nothing to do with the
optimize workflow. A gate with no door gets taken off the hinges.

Only stdlib: this runs before anything in the project is known to be loadable.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT = 600
# What a failing run's output is trimmed to. unittest puts its summary last, so
# the tail is the part worth handing back.
TAIL = 80

# A `git` that is the command of its own shell segment, optionally behind `-C`
# and `-c` flags and variable assignments. Segments matter: `cd x && git commit`
# is a commit, while `git log --grep commit` is not.
SEGMENT = re.compile(r"(?:^|[;&|])\s*(?:\w+=\S+\s+)*git\s+(?:(?:-C|-c)\s+\S+\s+)*([a-z-]+)")
GATING = {"commit", "merge"}

# This gate guards every commit in this repository, not only the ones the
# optimize workflow makes, so there has to be a way past it: `--no-verify`,
# which is git's own word for skipping hooks, or the variable, for a command
# where typing the flag is awkward. A gate with no door gets removed.
SKIP = "TEXTFOLD_SKIP_GATE"


def gates(command: str) -> bool:
    """Whether this shell command line would record a change."""
    return any(w in GATING for w in SEGMENT.findall(command))


def skipped(command: str) -> bool:
    return os.environ.get(SKIP) == "1" or "--no-verify" in command or f"{SKIP}=1" in command


def run(args, cwd=None, env=None):
    return subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, timeout=TIMEOUT,
    )


def tree(cwd: str) -> Path:
    """The checkout the session is working in -- a worktree, or the clone."""
    try:
        top = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    except (OSError, subprocess.TimeoutExpired):
        return Path(cwd)
    if top.returncode == 0 and top.stdout.strip():
        return Path(top.stdout.strip())
    return Path(cwd)


def environment_for(root: Path):
    """The clone root that holds a virtual environment, if one exists.

    `root` itself when the environment was made there, else the main clone
    behind a worktree -- which is where this machine's `.venv` lives, since a
    worktree is a fresh checkout and git does not copy ignored files into it.
    """
    if (root / ".venv").is_dir():
        return root
    try:
        common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if common.returncode != 0 or not common.stdout.strip():
        return None
    main = Path(common.stdout.strip()).parent
    return main if (main / ".venv").is_dir() else None


def works(exe: str) -> bool:
    """Whether this really is a Python that runs.

    Windows is the reason this is asked at all: `python3` on PATH is commonly
    the Microsoft Store's placeholder, which exits at once with nothing on
    either stream. Trusting it turns a failing suite into a blank report.
    """
    try:
        return run([exe, "-c", "pass"]).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def interpreter(root: Path) -> list[str]:
    """How to run the tests: the virtual environment's Python if there is one,
    else whichever of `python` and `python3` this shell would find that runs,
    which is where a checkout set up the way CONTRIBUTING describes keeps its
    dependencies. `python` leads on Windows and trails elsewhere."""
    with_venv = environment_for(root)
    if with_venv is not None:
        for rel in ("Scripts/python.exe", "bin/python", "bin/python3"):
            exe = with_venv / ".venv" / rel
            if exe.is_file() and works(str(exe)):
                return [str(exe)]
    names = ("python", "python3") if os.name == "nt" else ("python3", "python")
    for name in names:
        found = shutil.which(name)
        if found and works(found):
            return [found]
    return [sys.executable]


def summary(output: str) -> str:
    """unittest's own verdict, out of a stream that warnings and tracebacks
    have collected in: the line that counts the tests, and the line that
    names the outcome. Neither is last, which is why the tail is not used."""
    kept = [line for line in output.splitlines()
            if line.startswith("Ran ") or line.rstrip() in ("OK",) or line.startswith(("FAILED", "ERROR:"))]
    return "\n".join(kept)


def main() -> int:
    # A person running this by hand is asking exactly one question, so the
    # question the hook payload would have answered is not asked.
    if sys.stdin.isatty():
        payload = {}
    else:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            payload = {}

    if payload.get("tool_name") and payload["tool_name"] != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if payload and (not gates(command) or skipped(command)):
        return 0

    root = tree(payload.get("cwd") or os.getcwd())
    tests = root / "tests"
    if not tests.is_dir():
        print(f"no tests/ under {root}: nothing to run", file=sys.stderr)
        return 0

    env = dict(os.environ, TEXTFOLD_NO_MODELS="1")
    try:
        done = run(interpreter(root) + ["-m", "unittest", "discover", "tests"], cwd=root, env=env)
    except subprocess.TimeoutExpired:
        print(f"the tests did not finish in {TIMEOUT}s", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"could not run the tests: {exc}", file=sys.stderr)
        return 2

    output = (done.stderr + done.stdout).strip()
    if done.returncode == 0:
        print(f"tests pass in {root}\n{summary(output)}")
        return 0

    print(f"the tests fail in {root} -- this change is not ready to record.\n", file=sys.stderr)
    tail = "\n".join(output.splitlines()[-TAIL:])
    print(tail or f"and said nothing (exit {done.returncode}); run them by hand to see why", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
