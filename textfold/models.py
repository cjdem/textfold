"""One catalog of API models this computer can reach, and the settings that choose one.

Provider models come from environment settings, providers added in the reader, or a running local service. Magpie is
first so a shared model id resolves to its local OpenAI-compatible endpoint; the reader's saved choice wins, else its
first model is the default, then the existing ChatGPT and OpenRouter defaults.
"""
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

from . import bridges, providers
from .store import HOME, OLD_HOMES

_SETTINGS_LOCK = threading.RLock()

SETTINGS = HOME / "settings.json"
# How much the model may think, per task, in levels every caller maps onto its own (llm.py). Not a setting: a reader is
# here to read. Measured on one paper (2026-10-04): thinking adds time, not quality, to the levels and the translation.
TASKS = ("ladder", "translate", "ask", "card")
LEVELS = ("default", "off", "low", "medium", "high")
DEFAULT_THINKING = {"ladder": "off", "translate": "off", "ask": "low", "card": "low"}
# the Anthropic API spoken natively (official SDK), offered as one more preset in the settings
ANTHROPIC_PRESET = {"id": "anthropic", "name": "Anthropic", "base": "https://api.anthropic.com", "protocol": "anthropic",
                    "fixed": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"], "keyUrl": "https://console.anthropic.com/settings/keys"}


def _load_settings_locked():
    s = {"model": None, "ask_model": None, "ask_effort": None, "efforts": {}, "providers": [], "use_thoughtdag_env": False,
         "pdf_tier": "fast", "mineru_api_key": "", "zotero": {}}
    old_home = next((h for h in OLD_HOMES if (h / "settings.json").exists()), None)
    if not SETTINGS.exists() and old_home:   # from before the name TextFold: copied, kept
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_home / "settings.json", SETTINGS)
        os.chmod(SETTINGS, 0o600)
    if SETTINGS.exists():
        old = json.loads(SETTINGS.read_text(encoding="utf-8"))
        s.update({k: v for k, v in old.items() if k in s})
        # Older model ids remain in settings; resolve() treats ids outside the provider catalog as unavailable.
        if old.get("use_thoughtdag_env", True):  # still reading ThoughtDAG's .env: copy its providers once, then stop
            import_thoughtdag_env(s)
            _write_settings_locked(s)
    return s


def load_settings():
    with _SETTINGS_LOCK:
        return _load_settings_locked()


def import_thoughtdag_env(s):
    """Until v0.8 the keys in ThoughtDAG's .env (a sibling folder) were read live. The reader now stands on its own:
    the providers found there are copied once into its own settings, keys and model lists included, and the link is cut."""
    have = {p["key"] for p in s["providers"]}
    for p in providers.env_providers(True):
        if p["source"] != "thoughtdag" or p["key"] in have:
            continue
        s["providers"].append({"key": p["key"], "preset": p["key"], "name": p["name"], "base": p["base"], "api_key": p["api_key"],
                               "models": [{"id": m["id"]} for m in p["models"]][:providers.MAX_MODELS]})
    s["use_thoughtdag_env"] = False


def _write_settings_locked(s):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=SETTINGS.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        # ASCII-escaped, UTF-8: provider names may contain characters absent from a Chinese Windows code page.
        tmp.write_text(json.dumps(s, indent=1), encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, SETTINGS)
    finally:
        tmp.unlink(missing_ok=True)   # (the replace consumed it; a failed write leaves nothing behind)
    _clear_provider_cache()


def save_settings(s):
    with _SETTINGS_LOCK:
        _write_settings_locked(s)


def update_settings(change):
    """Apply one settings change to the latest saved version."""
    with _SETTINGS_LOCK:
        settings = _load_settings_locked()
        change(settings)
        _write_settings_locked(settings)
        return settings


_PROVIDERS = {"key": None, "at": 0.0, "rows": []}   # (a page asks more than once; the probes below are not free)


def _clear_provider_cache():
    _PROVIDERS.update(key=None, at=0.0, rows=[])


def provider_list(s, wait=False):
    if os.environ.get("TEXTFOLD_NO_MODELS"):
        return []
    ui = providers.ui_providers(s)
    for p in ui:
        raw = next((x for x in s.get("providers", []) if x["key"] == p["key"] or
                    ((x.get("preset") == "magpie" or x["key"] == "magpie") and p["key"] == "magpie")), {})
        if raw.get("protocol") == "anthropic":
            p["protocol"] = "anthropic"
    manual_magpie = next((p for p in ui if p["key"] == "magpie"), None)
    if manual_magpie:   # a configured Magpie is the one to call: no need to ask the default local port
        magpie, magpie_base, magpie_models = manual_magpie, manual_magpie["base"], manual_magpie["models"]
    else:
        # one snapshot for both the row and the cache key: a probe that answers between two reads would otherwise
        # cache rows that disagree with the key for ten seconds
        magpie_base, magpie_models = providers.magpie_models(wait)
        magpie = ({"key": "magpie", "name": "Magpie", "protocol": "openai", "base": magpie_base, "api_key": "magpie",
                   "source": "local", "preset": "magpie", "models": magpie_models} if magpie_models else None)
    key = json.dumps([s.get("providers"), s.get("use_thoughtdag_env", True),
                      providers.environment(s.get("use_thoughtdag_env", True)), magpie_base, magpie_models,
                      providers.ollama_models(), bridges.bridge_status()], sort_keys=True, default=str)
    if _PROVIDERS["key"] == key and time.time() - _PROVIDERS["at"] < 10:
        return _PROVIDERS["rows"]
    env = providers.env_providers(s.get("use_thoughtdag_env", True), providers.ollama_models())
    # The ChatGPT bridge joins automatically unless it has already been configured by hand.
    bridge = bridges.bridge_provider(providers.NOT_TEXT)
    if bridge and not any(p["base"].rstrip("/") == bridges.BRIDGE for p in ui):
        env.append(bridge)
    rows = ([magpie] if magpie else []) + [p for p in env if p["key"] != "magpie"] + [
        p for p in ui if p["key"] != "magpie"]
    _PROVIDERS.update(key=key, at=time.time(), rows=rows)
    return rows


def catalog(s=None, wait=False):
    s = s or load_settings()
    out, seen = [], set()
    provs = provider_list(s, wait)
    for p in provs:
        for m in p["models"]:
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            out.append({"id": m["id"], "name": m["name"], "kind": "api", "group": p["key"],
                        "efforts": m.get("efforts") or [], "defaultEffort": None})
    return out, provs


def default_model(s=None, cat=None):
    s = s or load_settings()
    cat = cat if cat is not None else catalog(s)[0]
    ids = [m["id"] for m in cat]
    if s.get("model") in ids:
        return s["model"]
    magpie = next((m["id"] for m in cat if m.get("group") == "magpie"), None)
    if magpie:
        return magpie
    for pref in ("gpt-5.5", "openrouter/free"):
        if pref in ids:
            return pref
    return ids[0] if ids else None


def resolve(model_id=None, s=None):
    """A model id to what it takes to call it. A default asks the providers once more if a local probe is under way:
    generation must not begin without the model that a page will show a moment later."""
    s = s or load_settings()
    if not model_id:
        model_id = default_model(s, catalog(s, wait=True)[0])
        if not model_id:
            raise RuntimeError("No model is available: add an API provider in Settings")
    for p in provider_list(s, wait=True):
        if any(m["id"] == model_id for m in p["models"]):
            return {"id": model_id, "kind": "api", "protocol": p["protocol"], "base": p["base"], "api_key": p["api_key"],
                    "provider": p["name"], "model": model_id, "effort": None}
    raise RuntimeError(f"Model {model_id} is not available (its provider is gone)")


def for_task(spec, task, s=None):
    """The spec a task is run with: the reasoning level for the task. A spec that names its own effort keeps it (the
    command line's, the model bench's)."""
    if spec.get("effort") is not None:
        return spec
    level = DEFAULT_THINKING[task]
    return {**spec, "effort": None if level == "default" else level}


def ask_choice(s=None, cat=None):
    """What questions are answered with, as the settings say: (a model of their own or None for the levels' model, a
    reasoning level or None for the questions' default). One no longer there counts as none."""
    s = s or load_settings()
    cat = cat if cat is not None else catalog(s)[0]
    own = next((m for m in cat if m["id"] == s.get("ask_model")), None)
    used = own or next((m for m in cat if m["id"] == default_model(s, cat)), None)
    effort = s.get("ask_effort") if used and s.get("ask_effort") in (used.get("efforts") or []) else None
    return (own["id"] if own else None), effort


def ask_spec(s=None):
    """The model a question is answered with, and how hard it reasons: the settings' own for questions (a stronger
    model, more reasoning), else the one the levels are written with, at the questions' default (DEFAULT_THINKING)."""
    s = s or load_settings()
    model_id, effort = ask_choice(s)
    spec = resolve(model_id, s)
    return {**spec, "effort": effort} if effort else for_task(spec, "ask", s)
