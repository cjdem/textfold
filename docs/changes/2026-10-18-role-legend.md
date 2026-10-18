# The paragraph-role legend opens from a Legend button instead of filling the bar

**Date:** 2026-10-18
**Branch:** `worktree-legend-on-demand`

## What and why

Item 6d of the confirmed product scope: the roles stay; the full legend expands on demand. At
Topic, Takeaway and Key the legend used to put every role the document uses in the top bar. The
bar now carries a small **Legend** button at those levels, and the full list opens under it on a
click. Hovering a role still lights its paragraphs and map chips, clicking still pins it, and
Escape or an outside click closes the list and drops the pin.

## The change

- `textfold/web/template.html` — the bare `#legend` div becomes `.legendpick`: a `#legendbtn`
  button (`aria-expanded`, `aria-controls`) that starts `hidden`, and the `#legend` popover, placed
  just after the header so its `position: fixed` is the window's (inside the top bar's
  `backdrop-filter` it would be measured against the bar).
- `textfold/web/reader.js` —
  - `legendShow(open)` opens or closes the popover and clears a pinned role when it closes;
    `setLegendShown(near)` shows the button at levels 0–2 when the document has roles and the
    window is wider than 640 px, and hides and closes it otherwise. It runs wherever the level or
    the window changes: the zoom stage's level crossings, `prepare`, `revert`, `setLevelAttr`,
    `applyLang` and the resize handler.
  - `legendPlace()` puts the fixed popover under its button, clamped to 8 px inside the visible
    area (`documentElement.clientWidth`) on both sides, and runs on opening, on resize, on a
    language change and when the fonts are ready.
  - The button's click toggles the popover; an outside click (heard in the capture phase, so a
    button that stops propagation still closes it) or Escape closes it. The old CSS-driven
    visibility is gone.
  - `applyLang` fills the popover with a **Paragraph roles** heading and the roles the document
    uses, and labels the button **Legend** / **图例**.
- `textfold/web/reader.css` — the `.legend` rules become a fixed popover placed by the reader; the
  level-based display rules and the now-dead `container: topbar` declaration are removed; print
  and widths under 640 px hide the button and the popover.
- `textfold/web/i18n.js` — `legend` and `legend_title` in English and Chinese.
- `docs/requirements/product-scope.md` — item 6d ticked.

## Decisions

- A button and a popover instead of an inline `<details>`: the popover does not reflow the bar,
  and it matches the language and export menus beside it.
- Keep showing the roles the document uses, not all eight: the legend explains what the reader
  sees, and unused role names would add noise. The heading makes the list self-explanatory.
- Closing drops a pinned role: a pin changes the page's emphasis, and with the list closed it
  would be an unexplained state.
- Keep the role hover, click and beat behavior exactly; only the container changes.
- Show the button at the same levels the legend used to show (Topic, Takeaway, Key) and hide it at
  Brief and Full, as before.
- The outside-click listener runs in the capture phase so buttons that stop propagation close the
  legend; the export menu uses the same pattern.
- The popover is fixed and placed by the reader rather than anchored to the button in CSS: at
  641–700 px, where the button sits left of the other controls, a 420 px popover anchored to it
  ran off the left edge of the window. The fixed box is clamped to the window, and it lives
  outside the top bar because that bar's `backdrop-filter` would otherwise make it the fixed
  element's containing block.
- Under 640 px the button was hidden by the phone rule; the same rule closes the popover and
  clears the pin in JS, so a window narrowed while the list is open does not leave a filtered page
  with no visible control.
- Drop `aria-haspopup` from the button: the popover is a disclosure of role labels, not an ARIA
  menu (its items are not focusable), so `aria-expanded` and `aria-controls` are the accurate
  attributes.

## Rejected

- Keeping the legend inline and adding a "more" link: the bar would still carry every role label.
- A hover-only flyout: not discoverable on touch and not what "on demand" means here.
- Showing all eight roles, including ones the document does not use.
- Closing without clearing the pin: the page would stay filtered with no visible control.

## What is lost

- The role names are one click away at Topic, Takeaway and Key instead of always visible; a reader
  who wants the legend must open it.
- Hovering a paragraph still lights its role in the list, but with the list closed that
  confirmation is not visible; the paragraph dots and map chips still respond.
- Zooming through Brief while the list is open closes it and drops the pin, even if the zoom
  returns to Key; the list does not reopen by itself.
- No role, color or focus behavior is removed.
- At narrow widths the legend no longer takes a row of its own; the popover overlays the page.
- Under 640 px the button and the popover are hidden, as the old legend was; the roles are not
  available there.

## How it was verified

- `python .claude/hooks/verify.py` — **188 tests, OK**; `node --check` on `reader.js` and
  `i18n.js` is clean; `git diff --check` is clean.
- Headless Chrome, on a temporary Markdown paper with one local role (removed afterwards):
  - at Full the pick is hidden and the tagline shown; at Topic and Key the pick shows;
  - clicking it opens the popover with the **Paragraph roles** heading and the role the document
    uses, and `aria-expanded` is true;
  - hovering a role sets `#doc[data-role]`; clicking pins it; Escape closes the popover, clears
    the pin and removes the attribute; an outside click does the same;
  - zooming to Brief hides the pick and closes the popover;
  - `setUi('en')` changes the button to **Legend** and the heading to **Paragraph roles**;
  - the popover sits under the button (top 44 px, 194 px wide at a 1254 px viewport), and a
    screenshot at Key shows it between the brand and the reading-card button.
- An independent verifier drove the real reader in headless Chrome with a synthetic document
  using all eight roles. It found that the popover, anchored to a button left of the other
  controls, ran off the left edge at 641–700 px (it is now a fixed box placed and clamped by the
  reader, outside the top bar, whose `backdrop-filter` would capture a fixed child); that the
  phone rule hid only the button, leaving an open popover and a pin behind when the window was
  narrowed (the resize handler and the 640 px check now close both); that the record claimed a
  print rule that did not exist (one now hides the button and the popover); that the
  `container: topbar` declaration was dead (removed); that `aria-haspopup` named a menu the
  popover is not (removed); and that a zoom comment still described the old attribute-driven
  legend (updated).
- After those fixes, with all eight roles injected to make the popover its full 420 px: at
  1280 px it sits at 821–1241; at 641 px at 182–602; at 620 px the button is hidden, the popover
  closed and a pinned role cleared; at 700 px the button returns, closed. Print media hides both.
- A second verifier pass found that the placement ran before `notesForLang` relabelled the notes
  and Export buttons, so a language switch while the list was open left the popover 25 px off its
  button (the placement now runs last in `applyLang`; driving zh→en leaves an offset of 0). It
  also found that the right clamp used `innerWidth` while the visible area ends at
  `documentElement.clientWidth`, so the border went under a classic Windows scrollbar (now
  clamped to `clientWidth`); that a font swap could reflow the bar after placement (the
  fonts-ready handler now re-places it); and that two bindings pointed at the same element (now
  one).
- The temporary paper's title and the Chinese interface strings rendered without encoding errors;
  the interface was switched to English and back.
- Zoom smoothness: **not measured** (no `playwright` and no `out/compare/` pages on this machine).
  The change adds a hidden popover and one state update per level crossing, not per frame; no
  claim is made about the measured smoothness.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** not applicable; no parser or renderer change.
- **Parser change renumbers atoms:** not applicable.
- **Persistent writes serialized per document:** no writer added or changed.
- **UTF-8 on a Chinese Windows:** the new Chinese strings are UTF-8 in `i18n.js` and rendered in
  the browser. No new file or subprocess encoding path.
- **No new dependencies:** none.

## Not measured

- Phone widths and print were checked with viewport and media emulation in headless Chrome
  (641, 620 and 700 px; print), not on a real phone or printer; touch input and the app shell
  were not exercised. The scrollbar case was reasoned from `clientWidth`, not seen with a real
  classic scrollbar in the driven window.
- A font swap while the list is open was not forced; the fonts-ready re-placement is in place but
  only reasoned about, not observed.
- Keyboard movement inside the popover: the button is focusable and Enter opens it, but the role
  spans are not focusable, as before; lighting a role needs a pointer.
- The UI has no automated test (the suite is Python-only), so a future regression in the opening,
  the level visibility or the pin clearing would leave the suite green.
