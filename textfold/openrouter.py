"""An OpenRouter key made by one authorisation.

OAuth with PKCE, OpenRouter's supported one-click door. No app registration and no secret: this server makes the
verifier, the browser takes the reader to OpenRouter's consent page, OpenRouter sends them back here with a code, and
the code and verifier become a key. The key waits in memory until the reader picks models and saves the provider
(settings, mode 600); it can be revoked on OpenRouter's keys page.
"""
import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request

AUTH_URL = "https://openrouter.ai/auth"
EXCHANGE_URL = "https://openrouter.ai/api/v1/auth/keys"
_OR = {}   # the authorisation under way: verifier, back (where to return), minted (the key, until saved)


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
