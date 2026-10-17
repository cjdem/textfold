# The reader offers two languages: English and Simplified Chinese

**Date:** 2026-10-17
**Branch:** `worktree-languages-en-zh`

## What and why

The reader offered twelve interface and reading languages. Asked for: keep
English and Simplified Chinese, remove the other ten (Traditional Chinese,
Japanese, Korean, Spanish, French, German, Portuguese, Italian, Russian,
Hindi) from the product.

## The change

- `textfold/langs.py` — `LANGS` is English and Simplified Chinese. The hangul
  budget and the per-language punctuation cases for the removed languages go
  with them; `budget`, `cjk`, `stop` and `punctuation_rule` keep the two
  scripts that remain.
- `textfold/store.py` — `languages(pid)` lists only the translations in
  `langs.LANGS`. **A translation in a removed language stays on disk** (no
  file is deleted) but is no longer listed, offered in the menu or read;
  `assemble` and the sidebar follow from it.
- `textfold/web/i18n.js` — every language-keyed table trimmed to `en` and
  `zh`: the main strings (`S`), Zotero (`Z`), updates (`U`), folders (`F`),
  questions (`Q`), model settings (`M`), the short sort labels (`BY`), the
  move menu (`MV`), the document-question words (`DOCS`), `NATIVE`,
  `HTML_LANG`, and the browser-language guess (a `zh-*` browser now gets
  Simplified Chinese, not Traditional).
- `textfold/web/tutorial.js` — the tutorial's words table (`W`) trimmed to
  the two; its `pick` maps any `zh-*` page to `zh`; the two remaining
  tutorials no longer say "twelve languages".
- `textfold/web/app.js` — the sidebar's short language chips (`SHORT`) keep
  `en` and `zh`.
- `desktop/main.js` — the menu's "Check for Updates…" has English and
  Chinese; a `zh-*` system gets the Chinese one.
- `textfold/__main__.py` — a language outside `langs.LANGS` is refused with
  `unknown language …` (exit 2) instead of failing deep in a translation;
  the help text no longer names removed languages.
- `textfold/pipeline.py` — `generate` refuses a language outside `langs.LANGS`
  at its first line (`unknown language ja: en, zh`), the guard behind every
  caller: a launch, an `/api/convert` request, a conversion a reloaded
  upload sidecar still names.
- `textfold/server.py` — the two paths the verifier found that carried an
  old language into a job are coerced to English: `/api/convert`'s `lang`,
  and the language a reloaded `uploads/*.json` sidecar holds (written before
  the trim, while the engine was missing).
- `textfold/notes.py` — a note whose stored language is no longer offered
  (an anchor or a turn written before the trim) is answered in English
  rather than failing on `langs.name`; `prompt` and `ask` both coerce.
- `tools/gallery.json`, `tools/gallery.py` — the gallery's languages are
  `en` and `zh`; the German paper copy (field, title, why) and the German
  site strings are deleted.
- `site/strings.py`, `site/build.py` — the website says "Two languages" and
  lists `LANGS_NATIVE = "English, 简体中文"`; the page metadata's
  `inLanguage` is `["en", "zh-CN"]`.
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md` — the language lists
  and examples say English and Simplified Chinese; the doc notes that a
  translation of a removed language stays on disk, unread.
- `tests/test_languages.py` (new, 5 tests) — the list is `en`/`zh`; a stored
  `tr-ja`/`tr-de` is not offered while `tr-zh` is; the command line refuses
  `--lang ja`; `pipeline.generate` refuses it too; a note stored in a
  removed language is answered in English. `CLAUDE.md` — 123 tests.

## What goes with the removed languages

- Reading and generating those ten languages; their interface translations;
  the German gallery copy; the website's claim to them. Existing layer files
  in those languages are neither deleted nor read — they can be removed by
  hand (or by a later change) if the space matters; nothing in the product
  offers them again until a language is added back to `langs.LANGS` (and its
  table to `i18n.js`).

## How it was verified

- `python .claude/hooks/verify.py` — **123 tests, OK**.
- `node --check` on `i18n.js`, `tutorial.js`, `app.js`, `desktop/main.js`;
  `py_compile` on `site/build.py`, `site/strings.py`; `json.load` on
  `gallery.json`.
- A sweep for the removed language names and codes in `textfold/`, `site/`,
  `tools/`, `desktop/`, `README*` and `docs/DEVELOPMENT.md`: no hits left
  outside historical change records and the one gallery meta description the
  verifier found (now "English and Chinese").
- `textfold-verifier`: no flow the app offers breaks; it found two unguarded
  entry points that could still carry a removed language into a job
  (`/api/convert`, a reloaded upload sidecar) and one note path
  (`/api/ask` without `ui`, a stored note language), all now coerced, with
  the `pipeline.generate` guard behind them; the gallery's meta description
  still said "German"; and this record had a dangling verifier reference and
  a sweep claim its own tree contradicted. All fixed above. It also
  confirmed en/zh lost no interface key (289 keys each, compared with
  main), the merge loops and helper arities survived the trim, the stored
  ja/zh/export paths behave, and the CLI/API entry points validate.

## Not measured

- **No browser was driven.** The interface change is checked by parsing the
  JavaScript and by the table structure; no page was loaded.
- **Smoothness: unmeasured.** `i18n.js`, `tutorial.js` and `app.js` are files
  the reader loads; `tools/zoombench.py` needs `playwright` and an exported
  page under `out/compare/`, neither on this machine, so the axis is not
  reported as unaffected.
