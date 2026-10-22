"""API providers, ported from ThoughtDAG (server.mjs `.env` registry, src/lib/runtime-providers.ts presets).

Two sources, as in ThoughtDAG:
  env   keys in the environment or a .env file; the model list is a fixed default or <PREFIX>_MODELS
  ui    providers added in the settings: an OpenAI-compatible base URL and key; its /models is probed
        and the reader picks which models to offer
One difference: ThoughtDAG keeps UI keys in the browser and sends them with each request; here generation
runs in the background on the server, so they are kept in ~/.textfold/settings.json (mode 600).
Every provider except Anthropic is spoken to through the OpenAI-compatible protocol (llm_openai.py).
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

from .store import HOME, OLD_HOMES, ROOT

THOUGHTDAG_ENV = ROOT.parent / "thoughtdag-main" / ".env"
ENV_FILES = [ROOT / ".env", HOME / ".env"] + [h / ".env" for h in OLD_HOMES]

# ThoughtDAG server.mjs:70-179. Anthropic's defaults are the current models (ThoughtDAG still lists sonnet-5).
ENV_PROVIDERS = [
    {"key": "zhipu", "name": "Zhipu", "env": ["ZHIPU_API_KEY"], "base": "https://open.bigmodel.cn/api/paas/v4",
     "models": ["glm-5.3-flash", "glm-4v-flash"], "names": {"glm-5.3-flash": "GLM-5.3 Flash · free"}},
    {"key": "qwen", "name": "Qwen", "env": ["DASHSCOPE_API_KEY"], "base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
     "models": ["qwen-plus", "qwen-vl-plus"]},
    {"key": "openai", "name": "OpenAI", "env": ["OPENAI_API_KEY"], "list": "OPENAI_MODELS", "base": "https://api.openai.com/v1",
     "models": ["gpt-5.1", "gpt-5-mini"]},
    {"key": "anthropic", "name": "Anthropic", "env": ["ANTHROPIC_API_KEY"], "list": "ANTHROPIC_MODELS", "protocol": "anthropic",
     "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"]},
    {"key": "google", "name": "Google", "env": ["GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"], "list": "GOOGLE_MODELS",
     "base": "https://generativelanguage.googleapis.com/v1beta/openai", "models": ["gemini-2.5-pro", "gemini-2.5-flash"]},
    {"key": "deepseek", "name": "DeepSeek", "env": ["DEEPSEEK_API_KEY"], "list": "DEEPSEEK_MODELS", "base": "https://api.deepseek.com/v1",
     "models": ["deepseek-v4-flash", "deepseek-v4-pro"]},
    {"key": "moonshot", "name": "Kimi", "env": ["MOONSHOT_API_KEY"], "list": "MOONSHOT_MODELS", "base_env": "MOONSHOT_BASE_URL",
     "base": "https://api.moonshot.cn/v1", "models": ["kimi-k2-turbo-preview", "kimi-latest"]},
    {"key": "openrouter", "name": "OpenRouter", "env": ["OPENROUTER_API_KEY"], "list": "OPENROUTER_MODELS", "base": "https://openrouter.ai/api/v1",
     "models": ["openrouter/auto"]},
    # Ollama needs no key; ThoughtDAG registers it only when OLLAMA_MODELS is set, here a running Ollama is also asked
    {"key": "ollama", "name": "Ollama", "env": [], "list": "OLLAMA_MODELS", "base_env": "OLLAMA_BASE_URL",
     "base": "http://localhost:11434", "suffix": "/v1", "models": [], "nokey": True},
]

# ThoughtDAG runtime-providers.ts:39-83
PRESETS = [
    {"id": "openrouter", "name": "OpenRouter", "base": "https://openrouter.ai/api/v1", "keyUrl": "https://openrouter.ai/keys",
     "recommend": ["openrouter/auto", "anthropic/claude-sonnet-5", "openai/gpt-5.5", "google/gemini-3.1-pro-preview",
                   "deepseek/deepseek-v4-pro", "z-ai/glm-5", "qwen/qwen3.7-max", "moonshotai/kimi-k2.6"]},
    {"id": "zai", "name": "Z.ai GLM", "region": "en", "base": "https://api.z.ai/api/paas/v4", "recommend": ["glm-5.3-flash", "glm-5"]},
    {"id": "zhipu", "name": "智谱 GLM", "region": "zh", "base": "https://open.bigmodel.cn/api/paas/v4", "recommend": ["glm-5.3-flash", "glm-4v-flash", "glm-5"]},
    {"id": "glm-coding", "name": "GLM Coding Plan", "region": "zh", "base": "https://open.bigmodel.cn/api/coding/paas/v4", "recommend": ["glm-5"]},
    {"id": "glm-coding-intl", "name": "GLM Coding Plan", "region": "en", "base": "https://api.z.ai/api/coding/paas/v4", "recommend": ["glm-5"]},
    {"id": "kimi-code", "name": "Kimi Code", "region": "zh", "base": "https://api.kimi.com/coding/v1", "recommend": ["k3-256k", "kimi-for-coding"]},
    {"id": "kimi-code-intl", "name": "Kimi Code", "region": "en", "base": "https://api.kimi.com/coding/v1", "recommend": ["k3-256k", "kimi-for-coding"]},
    {"id": "minimax-intl", "name": "MiniMax", "region": "en", "base": "https://api.minimax.io/v1",
     "fixed": ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5"]},
    {"id": "minimax", "name": "MiniMax", "region": "zh", "base": "https://api.minimaxi.com/v1",
     "fixed": ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5"]},
    {"id": "deepseek", "name": "DeepSeek", "base": "https://api.deepseek.com/v1"},
    {"id": "openai", "name": "OpenAI", "base": "https://api.openai.com/v1"},
    {"id": "google", "name": "Google AI Studio", "base": "https://generativelanguage.googleapis.com/v1beta/openai",
     "recommend": ["gemini-2.5-flash", "gemini-2.5-flash-lite"]},
    {"id": "moonshot-intl", "name": "Moonshot", "region": "en", "base": "https://api.moonshot.ai/v1"},
    {"id": "moonshot", "name": "Moonshot", "region": "zh", "base": "https://api.moonshot.cn/v1"},
    {"id": "magpie", "name": "Magpie", "base": "http://127.0.0.1:3425/v1", "nokey": True},
    {"id": "ollama", "name": "Ollama", "base": "http://localhost:11434/v1", "nokey": True},
    {"id": "custom", "name": "", "base": ""},
]
MAX_PROVIDERS, MAX_MODELS = 12, 60


def _read_env_file(f):
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([\w.]+)\s*=\s*(.*?)\s*$", line)
            if m and not line.lstrip().startswith("#"):
                out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def environment(use_thoughtdag=True):
    """The variables providers read: .env files fill in, a variable already set in the shell wins (as in ThoughtDAG)."""
    env = {}
    files = ENV_FILES + ([THOUGHTDAG_ENV] if use_thoughtdag else [])
    for f in reversed(files):  # earlier files take precedence
        env.update(_read_env_file(f))
    env.update({k: v for k, v in os.environ.items()})
    return env


def short(mid):
    """ThoughtDAG's display id: a vendor prefix (anthropic/claude-sonnet-5) is dropped."""
    return mid.split("/", 1)[1] if "/" in mid else mid


def _ids(env, p):
    raw = env.get(p.get("list", ""), "")
    return [s.strip() for s in raw.split(",") if s.strip()] if raw else list(p["models"])


def env_providers(use_thoughtdag=True, ollama_live=None):
    env = environment(use_thoughtdag)
    out = []
    for p in ENV_PROVIDERS:
        key = next((env[k] for k in p["env"] if env.get(k)), "")
        base = (env.get(p.get("base_env", ""), "") or p.get("base", "")).rstrip("/") + p.get("suffix", "")
        ids = _ids(env, p)
        if p["key"] == "ollama":
            ids = ids or list(ollama_live or [])
            if not ids:
                continue
        elif not key:
            continue
        source = "thoughtdag" if use_thoughtdag and any(k in _read_env_file(THOUGHTDAG_ENV) for k in p["env"] + [p.get("list", "")]) \
            and not any(os.environ.get(k) for k in p["env"]) else "env"
        out.append({"key": p["key"], "name": p["name"], "protocol": p.get("protocol", "openai"), "base": base,
                    "api_key": key or ("ollama" if p.get("nokey") else ""), "source": source,
                    "models": [{"id": i, "name": p.get("names", {}).get(i) or f"{short(i)} ({p['name']})"} for i in ids]})
    return out


def ui_providers(settings):
    out = []
    for p in (settings.get("providers") or [])[:MAX_PROVIDERS]:
        magpie = p.get("preset") == "magpie" or p["key"] == "magpie"
        out.append({"key": "magpie" if magpie else p["key"], "name": p.get("name") or p["key"], "protocol": "openai",
                    "base": p["base"].rstrip("/"), "api_key": p.get("api_key") or ("magpie" if magpie else "none"),
                    "source": "ui", "preset": p.get("preset", "custom"),
                    "models": [{"id": m["id"], "name": f"{short(m['id'])} ({p.get('name') or p['key']})"}
                               for m in (p.get("models") or [])[:MAX_MODELS]]})
    return out


_OLLAMA = {"at": 0.0, "ids": []}
_OLLAMA_PROBING = threading.Lock()


def _ollama_probe(base):
    try:
        try:
            with urllib.request.urlopen(f"{base.rstrip('/')}/api/tags", timeout=1.5) as r:
                ids = [m["name"] for m in json.loads(r.read()).get("models", [])]
        except Exception:
            ids = []
        _OLLAMA.update(at=time.time(), ids=ids)
    finally:
        _OLLAMA_PROBING.release()


def ollama_models(base="http://localhost:11434"):
    """What a running Ollama has pulled ([] when it is not running, and [] until the first background probe answers).
    A probe to a closed local port is not instant on every computer (a firewall may drop it rather than refuse it), so
    a page gets the last answer at once and the probe is made in the background; `localhost` finds a daemon on either
    loopback address, and 1.5 s is long enough for one that is busy."""
    if time.time() - _OLLAMA["at"] >= 10 and _OLLAMA_PROBING.acquire(blocking=False):
        try:
            threading.Thread(target=_ollama_probe, args=(base,), daemon=True).start()
        except Exception:
            _OLLAMA_PROBING.release()   # (no thread: the last answer stands, and the next call tries again)
    return list(_OLLAMA["ids"])


MAGPIE = {"base": None, "at": 0.0, "models": []}
_MAGPIE_LOCK = threading.Lock()       # one background probe at a time
_MAGPIE_STATE = threading.Lock()      # publishes and reads the answer as one
_MAGPIE_DONE = threading.Event()      # set when no probe is in flight
_MAGPIE_DONE.set()


def _magpie_snapshot():
    with _MAGPIE_STATE:
        return MAGPIE["base"], MAGPIE["at"], list(MAGPIE["models"])


def _magpie_set(base, at=None, models=None):
    with _MAGPIE_STATE:
        MAGPIE.update(base=base, at=time.time() if at is None else at,
                      models=list(MAGPIE["models"]) if models is None else models)


MAGPIE_BASE = "http://127.0.0.1:3425/v1"


def _magpie_config():
    env = environment(False)
    base = (env.get("MAGPIE_BASE_URL") or MAGPIE_BASE).rstrip("/")
    override = [m.strip() for m in env.get("MAGPIE_MODELS", "").split(",") if m.strip()]
    return base, override


def _magpie_probe(base):
    models = []
    try:
        req = urllib.request.Request(f"{base}/models", headers={"Authorization": "Bearer magpie"})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            body = json.loads(r.read())
        rows = body.get("data")
        models = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict) or not row.get("id"):
                    continue
                mid = str(row["id"])
                name = row.get("display_name") or row.get("magpie_label") or mid
                levels = row.get("supported_reasoning_levels") or row.get("reasoning_levels") or []
                efforts = [x.get("effort") or x.get("name") for x in levels if isinstance(x, dict)] if isinstance(levels, list) else []
                model = {"id": mid, "name": str(name)}
                if efforts:
                    model["efforts"] = [e for e in efforts if e]
                models.append(model)
    except Exception:
        models = []
    finally:
        try:
            current_base, override = _magpie_config()
            if current_base == base and not override:   # (the address or an override changed while this probe ran)
                _magpie_set(base, models=models)
        finally:
            _MAGPIE_LOCK.release()
            _MAGPIE_DONE.set()


def magpie_models(wait=False):
    """A running local Magpie, checked in the background so a closed port never holds up a page. A caller that needs
    a model now (`wait=True`) waits for a probe already under way, at most its 1.5 s timeout plus a moment."""
    base, override = _magpie_config()
    if override:
        found = [{"id": mid, "name": f"{short(mid)} (Magpie)"} for mid in override]
        old_base, _, old = _magpie_snapshot()
        if old_base != base or old != found:
            _magpie_set(base, models=found)
        return base, found
    known_base, at, found = _magpie_snapshot()
    if known_base != base:
        _magpie_set(base, at=0.0, models=[])
        at, found = 0.0, []
    if time.time() - at >= 10 and _MAGPIE_LOCK.acquire(blocking=False):
        _MAGPIE_DONE.clear()
        try:
            threading.Thread(target=_magpie_probe, args=(base,), daemon=True).start()
        except Exception:
            _MAGPIE_LOCK.release()
            _MAGPIE_DONE.set()
    if wait and not _MAGPIE_DONE.is_set():
        _MAGPIE_DONE.wait(2.0)
        known_base, at, found = _magpie_snapshot()
        if known_base != base:
            return base, []
    return base, found


def probe(base, api_key, timeout=15):
    """GET {base}/models (ThoughtDAG server.mjs:799-824): [{id, created?, vision?, contextLength?}]."""
    req = urllib.request.Request(f"{base.rstrip('/')}/models", headers={"Authorization": f"Bearer {api_key or 'none'}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}")
    except urllib.error.URLError as e:
        raise RuntimeError(str(e.reason))
    rows = body.get("data") or body.get("models") or []
    out = []
    for m in rows:
        mid = str(m.get("id") or m.get("name") or "")
        if not mid:
            continue
        mid = mid[len("models/"):] if mid.startswith("models/") else mid  # Google's compatible layer
        mods = (m.get("architecture") or {}).get("input_modalities")
        price = m.get("pricing") or {}
        free = mid.endswith(":free") or mid == "openrouter/free" or (
            bool(price) and all(str(price.get(k, "1")).strip() in ("0", "0.0") for k in ("prompt", "completion")))
        out.append({"id": mid, **({"created": m["created"]} if m.get("created") else {}),
                    **({"vision": "image" in mods} if isinstance(mods, list) else {}),
                    **({"contextLength": m["context_length"]} if m.get("context_length") else {}),
                    **({"free": True} if free else {}), **({"other": True} if NOT_TEXT.search(mid) else {})})
    # free models first (OpenRouter's router to one, then the known makers, then the newest), then the rest as listed
    return sorted(out, key=lambda m: (not m.get("free"), bool(m.get("other"))) + (_free_rank(m) if m.get("free") else (0, 0, 0)))


# ids that are not text models (images, music, speech, embeddings, safety classifiers): listed, never picked for you
NOT_TEXT = re.compile(r"image|lyria|music|audio|tts|whisper|embed|safety|guard|moderation|clip-preview", re.I)
FREE_PICKS = 5
# makers whose free models are offered first, in this order; anonymous ("stealth") models never by default
FREE_MAKERS = ["deepseek", "qwen", "z-ai", "moonshotai", "google", "nvidia", "meta-llama", "mistralai", "openai", "thinkingmachines"]


def _free_rank(m):
    maker = m["id"].split("/")[0]
    return (m["id"] != "openrouter/free", FREE_MAKERS.index(maker) if maker in FREE_MAKERS else len(FREE_MAKERS), -(m.get("created") or 0))


def preselect(models, preset=None, current=None, free_first=False):
    """Which probed models to offer (ThoughtDAG ApiKeyModal): the current picks on a refresh; free models first where
    the endpoint has them and a new connection is being made (OpenRouter's router to a free model, then the newest free
    text models); else the recommended ones that exist; else the 8 newest; else everything when there are at most 12."""
    ids = [m["id"] for m in models]
    if current:
        return [i for i in ids if i in set(current)]
    if free_first:
        free = sorted((m for m in models if m.get("free") and not m.get("other") and not m["id"].startswith("stealth/")), key=_free_rank)
        if free:
            return [m["id"] for m in free][:FREE_PICKS]
    models = [m for m in models if not m.get("other")]
    ids = [m["id"] for m in models]
    rec = [i for i in (preset or {}).get("recommend", []) if i in ids]
    if rec:
        return rec
    dated = sorted((m for m in models if m.get("created")), key=lambda m: -m["created"])
    if dated:
        return [m["id"] for m in dated[:8]]
    return ids if len(ids) <= 12 else ids[:12]
