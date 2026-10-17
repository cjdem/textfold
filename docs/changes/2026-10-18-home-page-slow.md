# Returning to the home page no longer takes sixteen seconds

**Date:** 2026-10-18
**Branch:** `worktree-home-slow`

## What and why

From a paper's reader, clicking the sidebar's mark (or the top bar's) goes
to `/`. On this machine that took **16.3 seconds** — measured with `curl`:
`GET /` 16.28–16.31 s, while `GET /p/<id>` took 0.25 s and `/api/jobs` 0.23 s.
The reader itself was never slow; the landing page was.

`landing_page` built `models.catalog` four times: once for
`models.default_model`, once for `models.ask_choice`, and once per
`models.label` call (the chosen model's name and the ask model's). Each
build calls `models.provider_list`, which probes the computer's own model
servers: Ollama and the ChatGPT bridge. When nothing answers, each probe
waits for its whole timeout — on this computer a closed local port is
dropped, not refused (`socket.connect` to 127.0.0.1 measured 2.0 s at a 2 s
timeout) — and `localhost` costs one timeout per address family. Measured
pieces of a cold catalog: `ollama_models` 3.0 s, `bridge_provider` 2.0 s;
four builds with the bridge's 5 s cache overlapping give 5 + 3 + 3 + 5 = 16 s.

## The change

- `textfold/server.py`, `landing_page`: the model catalog is built **once**;
  the default model, the ask model and both display names come from it
  (the same "name from the catalog" expression `models_payload` uses).
- `textfold/bridges.py`: `bridge_status` returns the last answer **at once**
  and probes in a background thread when that answer is older than five
  seconds. The probe keeps its 2 s timeout, so the busy bridge an earlier
  draft cut off (answering `/models` in 1–2 s) is found; one slower than 2 s
  is still reported absent until a later probe. `fresh=True` (the settings
  dialog, the start button) probes synchronously, and its answer stands even
  if a slower probe was already on its way (the probe compares its start with
  the answer's time). A second background probe never runs at once.
- `textfold/providers.py`: `ollama_models` works the same way — the last
  answer at once, a background probe every ten seconds at `localhost` (so a
  daemon on either loopback address is found, as before) with a 1.5 s
  timeout, long enough for a busy Ollama. One probe at a time; the lock is
  released even when the probe fails, and a thread that cannot start leaves
  the last answer for the next call to retry.
- `textfold/models.py`: `provider_list` keeps its rows for ten seconds, and
  its cache key includes the settings' providers, `use_thoughtdag_env`, the
  environment (`.env` files and the process environment, so a key added to
  one appears at once), and the live Ollama and bridge answers — a background
  probe that changes either makes the next request rebuild immediately.
  `save_settings` clears the cache. `models.label` is removed —
  `landing_page` was its last caller, and the catalog expression replaces it.
- `tests/test_landing_page.py` (new, 7 tests) — the landing builds the
  catalog once and names both models from it (the ask model, and no second
  name when it is the same one); the provider list is reused within the cache
  window, rebuilt when a live answer changes, and rebuilt after ten seconds;
  saving the settings probes again; an older background probe does not
  overwrite a newer fresh answer. The provider tests clear
  `TEXTFOLD_NO_MODELS` themselves, so they also pass in the suite's no-model
  mode. `CLAUDE.md` — 130 tests.

## How it was verified

- `GET /` on a server of this build (`--port 3018`): **0.24, 0.23, 0.21,
  0.21 s** — first request, an immediate one, one after 6 s and one after
  11 s (the "click after reading" case). The previous build measured 16.28,
  16.28 and 16.31 s on the same requests; `/api/jobs`, the floor for a
  request on this machine, is 0.23 s.
- `landing_page` called directly: 37 ms first (the probes are still running
  in the background), then 4, 1 and 2 ms — including after 11 s.
- `python .claude/hooks/verify.py` — **130 tests, OK**. Also
  `TEXTFOLD_NO_MODELS=1 python -m unittest discover tests` — 130, OK. (The
  hook builds that variable's environment but does not pass it to its test
  run — a pre-existing bug outside this change, which is why the mode was
  also run by hand.)
- `textfold-verifier`, two passes. The first reviewed an earlier design (a
  1 s synchronous bridge timeout plus caches) and found that a busy bridge
  answering in 1–2 s was reported absent, that the settings check was
  affected too (the record then claimed otherwise), and that the click after
  reading still paid a probe whenever the caches expired; it also found the
  landing test unpinned to a data folder, its ask-model branch untested, and
  `models.label` left dead. The background-probe design above answers the
  first three; the rest are fixed.
- The second pass, on the final design, reproduced the result: direct
  `landing_page` 36/4/1/2 ms, a real server 55/29/2/3 ms with an isolated
  profile, 130 tests OK, and the old cost's arithmetic (3.0 + 2.0 s per
  catalog, four catalogs). It then found, and these are fixed here:
  - probing `127.0.0.1` no longer found an Ollama answering only on IPv6
    loopback, and the 0.5 s timeout cut off a busy Ollama that answers in
    0.5–1.5 s. The probe is back on `localhost` at 1.5 s; because it now runs
    in the background, that costs no request time.
  - a background probe already in flight could overwrite a newer
    `fresh=True` answer; the start-time guard (and its test) prevents it.
  - the two new provider tests failed under `TEXTFOLD_NO_MODELS=1`, the
    suite's documented mode (the hook's env bug hid it); they now clear the
    variable, and the mode was run by hand.
  - the cache-hit comment described the old synchronous probes; the record's
    "appears in 0.5 s / 2 s" figures were probe durations, not waits, and its
    "the 2 s timeout means no false negative" claim was too strong; the
    dangling verifier line is replaced by this account. Also: the Ollama
    probe released its lock outside `finally` and an unstartable thread could
    hold it; the cache key did not include the environment; and the
    background mechanism itself (a changed live answer, the ten-second
    expiry, an older probe versus a fresh one) had no tests. All addressed.
- The second pass's remaining latent points are kept as bounds below:
  provider rows are shared by reference (no caller mutates them), and
  `ollama_models` accepts a base but keeps one cache (no caller passes one).

## Bounds

- **The provider list can be up to ten seconds old.** A provider that has
  just stopped can still be chosen in that window — its call then fails at
  the transport instead of "model not available". A model server that has
  just started appears on the first request after the next probe: up to ten
  seconds plus the probe's 1.5 s for Ollama, five seconds plus 2 s for the
  bridge. In the first seconds after the server starts, a non-fresh call
  returns "not running" until the first background probe answers. Saving the
  settings clears the provider cache, so a provider added or removed there
  shows at once; the Ollama probe keeps its own ten-second clock.

## Not measured

- **No browser was driven.** The fix is measured at the HTTP layer, which is
  where the delay was; the click path itself (the sidebar link is a plain
  `<a href="/">`) was not exercised.
- **The previous build's 16.28–16.31 s was not re-run** by the verifier; it
  verified the components and the four-build arithmetic instead. The HTTP
  figures above are from this branch's build.
- **Smoothness: unmeasured.** No file the reader loads changed, but
  `tools/zoombench.py` needs `playwright` and an exported page under
  `out/compare/`, neither on this machine, so the axis is not reported as
  unaffected.
- A large library's effect on `listed()` (it reads every paper's `meta.json`)
  is pre-existing and unmeasured here.
