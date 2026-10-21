"""Two easy ways in to a model (as in ThoughtDAG): the ChatGPT plan through a local bridge, and an OpenRouter key made
by one authorisation.

ChatGPT bridge: openai-oauth (npm) serves the ChatGPT plan as an OpenAI-compatible endpoint on 127.0.0.1:10531. It
signs in with Codex's login (~/.codex/auth.json), or opens a browser to sign in when there is none. Started detached,
it outlives this server; `npx openai-oauth stop` stops it.

OpenRouter: OAuth with PKCE, OpenRouter's supported one-click door. No app registration and no secret: this server
makes the verifier, the browser takes the reader to OpenRouter's consent page, OpenRouter sends them back here with a
code, and the code and verifier become a key. The key waits in memory until the reader picks models and saves the
provider (settings, mode 600); it can be revoked on OpenRouter's keys page.
"""
import base64
import hashlib
import json
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import procenv
from .store import HOME

BRIDGE = "http://127.0.0.1:10531/v1"
BRIDGE_PACKAGE = "openai-oauth@2"
AUTH_URL = "https://openrouter.ai/auth"
EXCHANGE_URL = "https://openrouter.ai/api/v1/auth/keys"
_OR = {}   # the authorisation under way: verifier, back (where to return), minted (the key, until saved)
_SEEN = {"at": 0.0, "status": None}   # the bridge's last status, asked for again after a few seconds
_PROBING = threading.Lock()           # one probe at a time, in the background


def _probe():
    try:
        with urllib.request.urlopen(f"{BRIDGE}/models", timeout=2) as r:
            ids = [m.get("id") for m in json.loads(r.read()).get("data", []) if m.get("id")]
        return {"running": True, "models": ids}
    except Exception:
        npx = procenv.which("npx")
        return {"running": False, "node": bool(npx), "codexLogin": (Path.home() / ".codex" / "auth.json").exists()}


def _refresh(started):
    try:
        status = _probe()
        if started >= _SEEN["at"]:   # (a fresh check that finished meanwhile is newer: keep its answer)
            _SEEN.update({"at": time.time(), "status": status})
    finally:
        _PROBING.release()


def bridge_status(fresh=False):
    """Whether the bridge is running and what it serves. An answer a few seconds old is returned at once and the probe
    is made in the background: a probe to a closed local port waits for its whole timeout on some computers (the
    landing page must not wait with it). `fresh` asks now — the settings dialog and a start button need the truth;
    its answer stands even if a slower probe was already on its way."""
    if fresh:
        _SEEN.update({"at": time.time(), "status": _probe()})
        return _SEEN["status"]
    if time.time() - _SEEN["at"] >= 5 and _PROBING.acquire(blocking=False):
        started = time.time()
        try:
            threading.Thread(target=_refresh, args=(started,), daemon=True).start()
        except Exception:
            _PROBING.release()   # (no thread: the last answer stands, and the next call tries again)
    return _SEEN["status"] or {"running": False, "node": bool(procenv.which("npx")),
                               "codexLogin": (Path.home() / ".codex" / "auth.json").exists()}


def bridge_provider(text_only):
    """The running bridge as a provider found on its own (as a running Ollama is): no key, its text models."""
    st = bridge_status()
    if not st.get("running"):
        return None
    ids = [i for i in st["models"] if not text_only.search(i)]
    return {"key": "chatgpt-bridge", "name": "ChatGPT", "protocol": "openai", "base": BRIDGE, "api_key": "none",
            "source": "bridge", "preset": "chatgpt-bridge", "models": [{"id": i, "name": f"{i} (ChatGPT)"} for i in ids]}


def bridge_start():
    """Start the bridge detached (a browser opens to sign in when Codex has no login); the caller polls the status."""
    env = procenv.child_env()
    npx = shutil.which("npx", path=env["PATH"])
    if not npx:
        raise RuntimeError("Node.js (npx) was not found on this computer")
    HOME.mkdir(parents=True, exist_ok=True)
    log = open(HOME / "bridge.log", "a")
    subprocess.Popen([npx, "-y", BRIDGE_PACKAGE, "--detach"], cwd=tempfile.gettempdir(), env=env,
                     stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    return bridge_status(fresh=True)


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def openrouter_start(callback, back, desktop=False):
    """desktop: the consent page opens in the system browser, and the app waits for the key (openrouter_minted)."""
    verifier = _b64(secrets.token_bytes(48))
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    _OR.clear()
    _OR.update({"verifier": verifier, "back": back or "/", "at": time.time(), "desktop": bool(desktop)})
    q = urllib.parse.urlencode({"callback_url": callback, "code_challenge": challenge, "code_challenge_method": "S256"})
    return f"{AUTH_URL}?{q}"


def openrouter_finish(code):
    """The code OpenRouter sent back, and the verifier kept here, exchanged for a key. Returns (key, error, back)."""
    verifier, back = _OR.pop("verifier", None), _OR.get("back", "/")
    if not code or not verifier:
        return None, "no authorisation was under way", back
    body = json.dumps({"code": code, "code_verifier": verifier, "code_challenge_method": "S256"}).encode()
    req = urllib.request.Request(EXCHANGE_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            key = json.loads(r.read()).get("key")
    except Exception as e:
        return None, str(e)[:200], back
    if not key:
        return None, "no key in the reply", back
    _OR["minted"] = key
    return key, None, back


def minted():
    return _OR.get("minted")


def for_desktop():
    return bool(_OR.get("desktop"))


def take_minted():
    return _OR.pop("minted", None)

