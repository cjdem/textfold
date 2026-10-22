# The app's payload ships the Anthropic SDK

**Date:** 2026-10-22
**Branch:** `worktree-anthropic-sdk-payload`

## What and why

The app's Settings offer the Anthropic API, and `textfold/llm.py` imports the SDK only when that provider is used
(`import anthropic`, else "The Anthropic API needs the SDK: pip install anthropic"). In a development checkout that is
fine: `requirements.txt` lists `anthropic` commented out, for those who want it. An installed app offers no way to run
pip and no requirements file to read (the payload does ship pip, but nothing in the app runs it), so a reader who
picks Anthropic there gets the error instead of a working provider. This
change ports the payload part of upstream `f260244`: the MyGo payload's CPython installs the Anthropic SDK alongside
TextFold's packages, and the payload build's own import check now proves the SDK is there.

## The change

- `desktop-mygo/scripts/prepare-payload.mjs` — `APP_ONLY = ['anthropic>=1.15,<2']`, installed with
  `pip install -r requirements.txt ...APP_ONLY` into the payload's Python; the header comment says the SDK ships; the
  payload's `app/requirements.txt` note says what is installed there; the final import check (run from `app/` with
  the payload's Python, `-s`) imports `anthropic` too, so a build without it fails instead of shipping a Settings
  option that cannot work.
- `desktop-mygo/README.md` — the packaged app needs the SDK as well, and why.
- `docs/DEVELOPMENT.md` — the app paragraph names the SDK among the packages it ships.
- `desktop-mygo/payload_script_test.go` — a Go test that reads the build script and fails if the SDK's version range,
  its spread into the pip install, its import in the payload check, or that check's `-s`/`app` isolation goes away.

## Docs checked

- `desktop-mygo/README.md` — updated (as above).
- `docs/DEVELOPMENT.md` — updated (the app paragraph).
- `requirements.txt` — not changed: the SDK stays optional for a development checkout, as upstream has it.
- `.github/workflows/desktop.yml` — not changed: it runs this script and then `desktop-mygo/scripts/smoke.py`; the
  script's import check is where the payload proves the SDK is installed.
- `site/`, `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no format, command
  or page changes.
- `desktop-mygo/scripts/smoke.py` — not changed: it starts the server and asks `/api/models`, which does not import
  the SDK; the build-time check covers it.

## Decisions

- **The SDK is app-only, not a requirements.txt entry.** `APP_ONLY` is installed into the payload's Python, as
  upstream does. Putting it in `requirements.txt` would make every development and CI install pull the SDK and its
  dependencies (pydantic, httpx2, …) for a provider most of them never use; the app cannot opt out, because it offers
  no way to run pip.
- **The payload's import check imports it.** A build that somehow loses the SDK fails loudly at the payload step,
  rather than at a reader's first Anthropic call in the app.
- **The generated `app/requirements.txt` says what is installed.** It is a note, not read by pip; it now names
  TextFold's packages and the SDK, so the file inside a shipped payload is not misleading.
- **The version range is upstream's `anthropic>=1.15,<2`.** This fork's `_anthropic` is the same code upstream pinned
  it for (beta message streams, `output_config`, server-side fallbacks); a `pip install --dry-run` on the payload's
  own CPython 3.12.15 resolves `anthropic 1.17.0`, inside the range.
- **The MyGo script, not the Electron one.** The upstream diff changes `desktop/scripts/prepare-payload.mjs`, which this
  fork no longer has; the MyGo script is its Windows-only equivalent, and only the SDK parts were ported.

## Concurrency and locks

None added. The change is a build-time dependency in a script that rebuilds `desktop-mygo/resources/payload` from
scratch; it writes no stored documents and touches no runtime path.

## How it was verified

- `python .claude/hooks/verify.py` — 282 tests, OK (unchanged: no Python code changed).
- `go -C desktop-mygo test ./...` — all four packages OK, including the new `TestPayloadShipsTheAnthropicSDK`.
- `node --check desktop-mygo/scripts/prepare-payload.mjs`.
- `desktop-mygo/resources/payload/python/python.exe -m pip install --dry-run --no-cache-dir "anthropic>=1.15,<2"` on
  the existing payload's CPython 3.12.15: would install `anthropic-1.17.0` and its dependencies (pydantic, httpx2,
  anyio, …), so the pin resolves on the interpreter the app ships.
- `textfold-verifier` — no blocking findings. It ran the exact install and check against a copy of the shipped,
  pruned payload Python: the SDK landed in that copy's `Lib/site-packages`, and `python -s -c "... anthropic ..."` from
  `app/` printed `payload ok 1.17.0`, with `pydantic_core`'s native module. It also checked that a payload without the
  SDK fails the build, that Node passes `anthropic>=1.15,<2` to `python.exe` intact on Windows (no shell), and that
  anthropic 1.15.0, 1.16.0, 1.17.0 and 2.1.0 all have the beta stream surface `_anthropic` uses. Its findings on the
  test's brittleness, the payload's shipped pip, and the size/package count are fixed below.

## Measured

| | before | after |
|---|---|---|
| Python tests | 282 | 282 |
| MyGo packages (`go test ./...`) | 4 OK | 4 OK, one new test |
| payload `Lib/site-packages` | 86 MB | 128 MB (the verifier's install into a copy of the shipped payload) |

## Not measured

- **The payload was not rebuilt here.** `prepare-payload.mjs` downloads a CPython build and installs all packages; that
  was not run, so no fresh payload, app installer or update archive was made. The verifier installed the exact command
  into a copy of the existing payload and ran the exact check, which covers the install and the import but not a fresh
  interpreter or MyGo's packaging.
- No real Anthropic API call was made (no key), so the SDK's own request path in an installed app is not exercised.
- The `>=1.15` lower bound was not installed by this change's run; the verifier extracted 1.15.0 and confirmed it has
  the beta stream surface, so the range is not merely taken from upstream's pin. The dry-run itself resolves 1.17.0.
- The installer's size and update delta were not measured; only the payload's site-packages growth (about +42 MB).

## Pitfalls

- A development checkout still needs `pip install anthropic` for the Anthropic API; `requirements.txt` keeps it
  commented. The app payload is the only place it is installed for a reader.
- The SDK draws in pydantic, httpx2, anyio and others (fifteen packages in all); the payload's pruning only removes
  CPython's test suite, IDLE and Tk, not site-packages, so all of them ship. The payload's site-packages grows by
  about 42 MB (86 → 128 MB in the verifier's copy).
- `TestPayloadShipsTheAnthropicSDK` pins the version range and the install/check shape with regular expressions:
  bumping the SDK's range means updating the test too. That is deliberate — the range is the contract that the
  server's calls were written for.
- The build's import check runs `python -s -c …` from `app/`; a user site-packages (`-s` disables it) cannot mask a
  missing SDK. The Go test pins both, so removing them is a test failure, not a silent weakening.
- `pyproject.toml`'s development extra is still `anthropic = ["anthropic"]`, unpinned, while the payload pins
  `>=1.15,<2`: a `pip install .[anthropic]` in a checkout can get 2.x. That drift predates this change (2.1.0 still
  has the beta stream surface), but a future SDK 3 could break the checkout without failing the payload.

## Rejected

- **Adding `anthropic` to `requirements.txt`.** Every development and CI install would carry the SDK and its
  dependencies for a provider most of them do not use; the app's payload has to add it separately anyway.
- **Only writing it into the payload's `app/requirements.txt`.** That file is a note; nothing installs from it.
- **Copying upstream's Electron `prepare-payload.mjs`.** The fork has no Electron shell; paths, targets and pruning
  differ in the MyGo script.
- **Leaving the payload's import check unchanged.** A build could silently lose the SDK, and the failure would surface
  only when a reader picks Anthropic in the app.
