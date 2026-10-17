"""Coding agents already installed on this computer, ported from ThoughtDAG (runtime/agents/*.cjs).

The server scans for them at startup (and on demand): the three agent CLIs this reader drives are looked for on PATH,
in the usual install directories and under the node version managers, as ThoughtDAG's where.cjs does.
All three run a generation:

  claude-code  claude -p, structured output by --json-schema        models: fable, opus, sonnet, haiku
  codex        codex exec, structured output by --output-schema      models: `codex app-server` model/list
  pi           pi -p --mode json, JSON asked for in the prompt       models: `pi --mode rpc` get_available_models

Only these three are scanned and listed: an agent the reader cannot drive is not offered. A model id is ThoughtDAG's:
`claude/claude-code/opus`, `codex/codex/<model>`, `pi/<provider>/<model>`.
Agents run here only as one-shot text generators: no tools, no session, a scratch working directory.
"""
import glob
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

HOME = Path.home()
# runtime, label, binary, extra directories
REGISTRY = [
    ("claude-code", "Claude Code", "claude", ["~/.claude/local"]),
    ("codex", "Codex", "codex", ["~/.codex/bin"]),
    ("pi", "Pi", "pi", ["~/.pi/bin"]),
]
PREFIX = {"claude-code": "claude/", "codex": "codex/", "pi": "pi/"}
# npm's global folder, Claude Code's own installer (~/.local/bin), Scoop, Node itself
COMMON = [os.path.join(os.environ.get("APPDATA") or "~/AppData/Roaming", "npm"), "~/.local/bin", "~/.bun/bin", "~/scoop/shims",
          os.path.join(os.environ.get("ProgramFiles") or "C:/Program Files", "nodejs")]
WIN = os.name == "nt"
# Windows: a program is claude.exe, or npm's shim claude.cmd (the bare `claude` beside it is a shell script)
EXTS = (".exe", ".cmd", ".bat")


def _version_key(p):
    return [int(x) if x.isdigit() else 0 for x in re.findall(r"\d+", p)]


def search_dirs():
    """PATH, common install dirs, version-manager dirs (ThoughtDAG where.cjs).

    No login shell is asked: the shell this was ported from is a Unix one, and there is none to ask on Windows."""
    dirs = os.environ.get("PATH", "").split(os.pathsep) + COMMON
    managers = sorted(glob.glob(str(HOME / ".nvm/versions/node/*/bin")), key=_version_key, reverse=True)
    for pattern in ["~/.fnm/node-versions/*/installation/bin",
                    "~/.volta/bin", "~/n/bin", "~/.nodenv/shims", "~/.asdf/shims", "~/.local/share/mise/shims", "~/.proto/bin",
                    "~/.local/share/pnpm", "~/.yarn/bin", "~/.config/yarn/global/node_modules/.bin",
                    "~/.deno/bin", "~/.cargo/bin", "~/bin"]:
        managers += sorted(glob.glob(os.path.expanduser(pattern)), key=_version_key, reverse=True)
    out, seen = [], set()
    for d in dirs + managers:
        d = os.path.expanduser(d)
        if d and d not in seen and os.path.isdir(d):
            seen.add(d)
            out.append(d)
    return out


def child_env():
    """Children get the widened PATH, so a node-based CLI finds node.

    The USER/LOGNAME fallback the ported code carried is gone with it: it read the user's name through `pwd`,
    which Windows does not have, and does not need."""
    return {**os.environ, "PATH": os.pathsep.join(search_dirs())}


def locate(binary, extra=()):
    for d in [os.path.expanduser(x) for x in extra] + search_dirs():
        for ext in EXTS:
            f = os.path.join(d, binary + ext)
            if os.path.isfile(f) and os.access(f, os.X_OK):
                return f
    return None


_SHIM = re.compile(r'"%~?dp0%?\\([^"]+\.[cm]?js)"\s+%\*')


def argv(path):
    """The command that runs an agent found at `path`. On Windows npm's shim (claude.cmd) would hand its arguments to
    cmd.exe, which ends a multi-line system prompt at its first line break and reads its quotes and carets: the
    script the shim names is run by node instead."""
    if not (WIN and path.lower().endswith(".cmd")):
        return [path]
    try:
        m = _SHIM.search(Path(path).read_text(**TEXT))
    except OSError:
        m = None
    script = m and Path(path).parent / m.group(1).replace("\\", os.sep)
    if not (script and script.is_file()):
        return [path]
    node = Path(path).parent / "node.exe"
    node = str(node) if node.is_file() else shutil.which("node", path=os.pathsep.join(search_dirs()))
    return [node, str(script)] if node else [path]


# A text-mode pipe with no encoding uses the system's (GBK on a Chinese Windows), and an agent CLI speaks UTF-8: a
# prompt holding ▶ (the outline marks the section being read) dies in subprocess's writer thread before the agent
# sees a byte of it, and a reply holding a typographic quote dies in its reader thread. Every pipe to one is UTF-8;
# errors="replace" keeps one stray byte in a reply from losing the reply.
TEXT = {"encoding": "utf-8", "errors": "replace"}


def _run(args, timeout, **kw):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=child_env(), stdin=subprocess.DEVNULL,
                          **TEXT, **kw)


def _help_levels(path, flag, pattern):
    """Effort or thinking levels as the CLI's own --help lists them."""
    try:
        text = _run([*argv(path), "--help"], 8).stdout
    except Exception:
        return []
    m = re.search(pattern, text, re.S)
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


# ── catalogs ──────────────────────────────────────────────────────────
def _claude_models(path):
    efforts = _help_levels(path, "--effort", r"--effort <level>.*?\(([^)]*)\)")
    efforts = (["off"] + efforts) if efforts else []   # off: no thinking at all (llm.py sets the thinking budget to nothing)
    # (the user's own effortLevel is not the default here: llm.py leaves the user settings out of a call)
    return [{"id": f"claude/claude-code/{a}", "name": f"Claude Code · {a.capitalize()}", "runtime": "claude-code",
             "model": a, "efforts": efforts, "defaultEffort": None}
            for a in ["fable", "opus", "sonnet", "haiku"]]


def _rpc(args, requests, timeout=30, cwd=None):
    """Write JSON lines, collect the replies whose id we asked for."""
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                         env=child_env(), cwd=cwd or str(HOME), **TEXT)
    lines = queue.Queue()   # read by a thread: select() cannot wait on a pipe on Windows

    def read():            # (the thread owns the pipe: it closes it at the end, kill or no kill)
        with p.stdout:
            for line in p.stdout:
                lines.put(line)
        lines.put(None)

    threading.Thread(target=read, daemon=True).start()
    got = {}
    try:
        for r in requests:
            p.stdin.write(json.dumps(r) + "\n")
        p.stdin.flush()
        want = {r["id"] for r in requests if "id" in r}
        t0 = time.time()
        while want - set(got) and time.time() - t0 < timeout:
            try:
                line = lines.get(timeout=0.5)
            except queue.Empty:
                continue
            if line is None:
                break
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("id") in want:
                got[d["id"]] = d
    finally:
        p.kill()
        p.wait()           # (reaped: a killed child left running is a leak, and Windows shows it in the tests)
        try:
            p.stdin.close()
        except OSError:
            pass
    return got


def _codex_models(path):
    got = _rpc([*argv(path), "app-server"], [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"clientInfo": {"name": "textfold", "title": "TextFold", "version": "0.4"}, "capabilities": None}},
        {"jsonrpc": "2.0", "method": "initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "model/list", "params": {}}])
    rows = (got.get(2) or {}).get("result", {}).get("data", [])
    home = Path(os.environ.get("CODEX_HOME", HOME / ".codex"))
    m = re.search(r'^model_reasoning_effort\s*=\s*"([^"]+)"', (home / "config.toml").read_text(**TEXT), re.M) if (home / "config.toml").exists() else None
    out = []
    for r in rows:
        if r.get("hidden"):
            continue
        mid = r.get("model") or r.get("id")
        efforts = [e.get("reasoningEffort") for e in r.get("supportedReasoningEfforts", []) if e.get("reasoningEffort")]
        default = m.group(1) if m and m.group(1) in efforts else r.get("defaultReasoningEffort")
        out.append({"id": f"codex/codex/{mid}", "name": f"Codex · {r.get('displayName') or mid}", "runtime": "codex", "model": mid,
                    "efforts": efforts, "defaultEffort": default, "isDefault": bool(r.get("isDefault"))})
    return out


def _pi_models(path):
    levels = _help_levels(path, "--thinking", r"--thinking <level>\s+Set thinking level:\s*([^\n]*)")
    got = _rpc([*argv(path), "--mode", "rpc", "--no-session"], [{"id": "1", "type": "get_available_models"}])
    data = (got.get("1") or {}).get("data")
    rows = data.get("models", []) if isinstance(data, dict) else (data or [])
    return [{"id": f"pi/{r['provider']}/{r['id']}", "name": f"Pi · {r.get('name') or r['id']}", "runtime": "pi",
             "model": f"{r['provider']}/{r['id']}", "efforts": levels if r.get("reasoning") else [], "defaultEffort": None,
             "vision": "image" in (r.get("input") or [])} for r in rows if r.get("provider") and r.get("id")]


CATALOG = {"claude-code": _claude_models, "codex": _codex_models, "pi": _pi_models}

# ── the scan ──────────────────────────────────────────────────────────
STATE = {"scanned_at": None, "scanning": False, "agents": []}
_lock = threading.Lock()


def scan(log=None):
    """Find every registered agent and ask it for its models. Safe to call from any thread."""
    with _lock:
        STATE["scanning"] = True
        found, seen = [], {}
        for runtime, label, binary, extra in REGISTRY:
            # TEXTFOLD_NO_MODELS=1: none looked for (a test server, a CI run: nothing calls a model by accident)
            path = None if os.environ.get("TEXTFOLD_NO_MODELS") else locate(binary, extra)
            row = {"runtime": runtime, "label": label, "binary": binary, "path": path,
                   "version": None, "models": [], "error": None}
            if path:
                real = os.path.realpath(path)
                if real in seen:  # one program under two names counts once
                    row.update(path=None, error=f"same program as {seen[real]}")
                else:
                    seen[real] = label
                    try:
                        out = _run([*argv(path), "--version"], 8)
                        row["version"] = ((out.stdout or out.stderr).strip().splitlines() or [""])[0][:80]
                    except Exception as e:
                        row["error"] = str(e)[:200]
                    try:
                        row["models"] = CATALOG[runtime](path)
                    except Exception as e:
                        row["error"] = f"model list: {e}"[:200]
            found.append(row)
        STATE.update(agents=found, scanned_at=time.time(), scanning=False)
    if log:
        have = [f"{a['label']} {a['version'] or ''}".strip() + (f" ({len(a['models'])} models)" if a["models"] else "")
                for a in found if a["path"]]
        log("Agents found: " + (", ".join(have) or "none"))
    return STATE


def models():
    return [m for a in STATE["agents"] if a["path"] for m in a["models"]]


def runtime_of(model_id):
    return next((rt for rt, p in PREFIX.items() if model_id.startswith(p)), None)


def path_of(runtime):
    a = next((a for a in STATE["agents"] if a["runtime"] == runtime and a["path"]), None)
    if a:
        return a["path"]
    binary, extra = next((r[2], r[3]) for r in REGISTRY if r[0] == runtime)
    return locate(binary, extra)


# ── one-shot runs ─────────────────────────────────────────────────────
def _strict(schema):
    """OpenAI-style structured output wants every object closed and every property required."""
    if isinstance(schema, dict):
        s = {k: _strict(v) for k, v in schema.items()}
        if s.get("type") == "object" and "properties" in s:
            s["additionalProperties"] = False
            s["required"] = list(s["properties"])
        return s
    if isinstance(schema, list):
        return [_strict(x) for x in schema]
    return schema


def parse_json(text, schema=None):
    """The reply's JSON object, asked for in the prompt: the first object that parses (and has the schema's required
    keys), wherever it starts. A model that is not reasoning sometimes adds a line after the object, or repeats it."""
    text, dec = text or "", json.JSONDecoder()
    need = set((schema or {}).get("required", []))
    first = None
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and need <= set(obj):
            return obj
        first = first if first is not None else obj
    if first is not None and not need:
        return first
    raise RuntimeError("no JSON in reply" if "{" not in text else "the reply's JSON does not parse")


def run_codex(model, prompt, schema, system, effort, timeout):
    path = path_of("codex")
    if not path:
        raise RuntimeError("Codex was not found on this computer")
    with tempfile.TemporaryDirectory() as tmp:  # a scratch cwd: no repository, nothing to edit
        sf, of = Path(tmp) / "schema.json", Path(tmp) / "out.txt"
        sf.write_text(json.dumps(_strict(schema)))
        args = [*argv(path), "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-m", model,
                "--output-schema", str(sf), "-o", str(of)]
        # off is "none" (gpt-5.5 takes it, and refuses "minimal"); a model that refuses "none" runs at "low"
        for level in (["none", "low"] if effort == "off" else [effort]):
            r = subprocess.run(args + (["-c", f"model_reasoning_effort={level}"] if level else []) + ["-"], input=f"{system}\n\n{prompt}",
                               capture_output=True, text=True, timeout=timeout, env=child_env(), cwd=tmp, **TEXT)
            if not r.returncode and of.exists():
                break
        if r.returncode or not of.exists():
            raise RuntimeError(f"codex exec exited {r.returncode}: {(r.stderr or r.stdout)[-800:]}")
        return parse_json(of.read_text(**TEXT)), None   # (codex writes UTF-8)


def run_pi(model, prompt, schema, system, effort, timeout):
    path = path_of("pi")
    if not path:
        raise RuntimeError("Pi was not found on this computer")
    args = [*argv(path), "-p", "--mode", "json", "--no-tools", "--no-session", "--no-context-files", "--no-extensions", "--no-skills",
            "--no-prompt-templates", "--model", model, "--system-prompt", system]
    if effort:
        args += ["--thinking", effort]
    body = f"{prompt}\n\nReply with one JSON object that matches this JSON Schema, and nothing else:\n{json.dumps(schema)}"
    for attempt in (1, 2):   # a reply whose JSON does not parse is asked for once more (it is a sample: the next one parses)
        try:
            return _pi_once(args, body, schema, timeout)
        except ValueError:
            if attempt == 2:
                raise


def _pi_once(args, body, schema, timeout):
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(args, input=body, capture_output=True, text=True, timeout=timeout, env=child_env(), cwd=tmp, **TEXT)
    text, cost = None, None
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "agent_end":
            last = next((m for m in reversed(d.get("messages", [])) if m.get("role") == "assistant"), None)
            if last:
                text = "".join(c.get("text", "") for c in last.get("content", []) if c.get("type") == "text")
                cost = ((last.get("usage") or {}).get("cost") or {}).get("total")
                if last.get("stopReason") == "error" or last.get("errorMessage"):
                    raise RuntimeError(f"pi: {last.get('errorMessage') or 'error'}")
    if text is None:
        raise RuntimeError(f"pi exited {r.returncode}: {(r.stderr or r.stdout)[-800:]}")
    try:
        return parse_json(text, schema), cost
    except RuntimeError as e:
        raise ValueError(str(e))

