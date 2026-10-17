# Settings shows the connection, the default model and two one-click entries; the rest is under Advanced

**Date:** 2026-10-18
**Branch:** `worktree-settings-simple`

## What and why

Item 6a of the confirmed product scope. The settings dialog opened on every provider, agent row, ask
model, reasoning level and engine control at once. A reader who only wants to read needs the
connection, the default model, a test, and the two one-click ways in; the rest is for setting up
or repairing a connection. The advanced controls are hidden behind one disclosure, not removed.

## The change

- `textfold/web/app.js` — the settings dialog now opens with:
  - the current connection (the selected model, with its agent or provider when the model name
    does not already say it) and an **OpenRouter in one click** button;
  - the ChatGPT plan's local bridge row, with its state and a start button (it was previously
    hidden once a bridge provider had been saved, so a stopped bridge could not be restarted
    without editing the provider);
  - the default model select and its connection test.
  Under a native `<details class="st-adv">` **Advanced settings**: the questions' model and
  reasoning, the agents on this computer and Rescan, the API providers with Add/Edit/Remove and
  the provider form, and the PDF engine's install/remove and conversion tier.
- The advanced disclosure's open state survives each re-render (selecting a model, switching the
  interface language, a finished test); adding or editing a provider, and returning from
  OpenRouter, open it and scroll its form into view. The dialog's scroll position and the
  provider form's saved values survive a re-render; text typed into the form but not yet kept is
  discarded if a language switch re-renders it (as before this change).
- `textfold/web/i18n.js` — `st_current`, `st_advanced` and `st_or` added in English and Chinese;
  the generation model's label is now **Default model** / **默认模型**, and the answer model's
  fallback is **Same as the default** / **与默认相同**.
- `textfold/web/app.css` — the disclosure row, its sections and the OpenRouter button.
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md` — the paths to Add provider and the
  questions' model now go through **Advanced**.

## Decisions

- Use a native `<details>` rather than a modal, a second page or a toggle button: it is one click,
  keyboard-accessible, collapses without JavaScript, and the content stays in the DOM so the
  existing wiring, selectors and form state keep working.
- Keep every control reachable and unchanged. This is a hierarchy change, not a removal: provider
  setup, the ask model, agents, the engine and both connection tests still exist.
- Put the bridge row in the main view instead of only in the provider list. The old row disappeared
  once a bridge provider existed, which hid the restart action exactly when it was needed; the
  main row now shows running/stopped and the start button whenever Node is available.
- Add OpenRouter to the main view as well as the provider form. It is the same OAuth flow; the
  main button saves the reader from finding the provider form first.
- No server change: `models_payload`, `/api/models`, `/api/settings`, `/api/providers/*` and the
  settings file are untouched, so the caching, encoding and last-writer behaviour stay as they
  were.

## Rejected

- A separate "simple" and "advanced" settings dialog: two code paths to render the same controls
  and keep in sync.
- CSS-only hiding without a disclosure: the controls would be invisible and unreachable.
- Removing the ask model, provider form, agent rescan or engine controls: they are capabilities,
  and the scope only moves them.
- Changing the payload or adding a setting for "advanced": the hierarchy is a view concern.

## What is lost

- Provider setup, the ask model and reasoning, agents and the PDF engine are one click deeper.
  Nothing is removed, and no stored setting, model or provider changes.
- The main view no longer shows the ask model's separate test until Advanced is opened; the
  default model's test remains visible.

## How it was verified

- `python .claude/hooks/verify.py` — **188 tests, OK**; `node --check textfold/web/app.js` — clean.
- In the browser, Chinese and English:
  - the closed dialog shows the language, the current connection ("Claude Code · Sonnet"), the
    OpenRouter button, the bridge row with its state and start button, the default model and its
    test, and the **Advanced settings** disclosure;
  - opening Advanced shows the ask model, agents, providers and engine; the disclosure stays open
    across an interface-language re-render and closes cleanly;
  - the labels switch with the interface language (`Advanced settings` / `高级设置`,
    `Answering questions` / `回答问题`).
- An independent verifier drove the real `app.js` in headless Chrome against a stubbed API. It
  found that the new main OpenRouter button could discard a just-minted key on return (the button
  is now hidden while the minted form is open), that the minted form's fetched model list and
  Save button were below the visible body (the fetch now scrolls them into view), and that the
  main and provider-form bridge start buttons could both call `/api/bridge/start` (the main one is
  hidden while the bridge form is open). Its second pass verified those fixes at 800×600 and
  360×740 and found no functional break.
- `git diff --check` is clean; no server route, payload, test or stored data changed.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** no parser or renderer change; every dynamic
  settings value is still escaped with `esc()`.
- **Parser change renumbers atoms:** not applicable.
- **Persistent writes serialized per document:** no writer added or changed. The dialog only calls
  the existing settings and provider routes.
- **UTF-8 on a Chinese Windows:** the new Chinese strings are UTF-8 in `i18n.js` and rendered
  correctly in the browser; no file or subprocess encoding path changed.
- **No new dependencies:** none.

## Not measured

- Zoom smoothness: **unmeasured** on this machine (no `playwright`, no exported pages under
  `out/compare/`). The change is in the settings dialog, not the reader or the zoom, but no claim
  is made that it is unaffected.
- A real connection test, a provider save, an agent rescan and an engine install were not run in
  the browser (they would call a model, write the user's settings, or start a long install); they
  are unchanged and covered by reading the existing wiring.
- The OpenRouter consent round trip and the bridge start were not completed; both reuse the
  existing flows, and only their new entry points were checked.
- A phone-width layout of the new disclosure was not checked separately.
- The settings UI has no automated regression test: the suite is Python-only, so the browser
  checks above are the evidence for the DOM, the disclosure state and the minted-key guard. A
  change that removed those guards would leave the suite green.
