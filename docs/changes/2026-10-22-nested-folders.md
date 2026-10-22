# Folders go inside folders

**Date:** 2026-10-23
**Branch:** `worktree-nested-folders`

## What and why

R23 of the round is the third of the four parts of upstream `d457cfa`: **folders inside folders**. This fork's sidebar
had one level — a folder held documents, and a document could be in one folder. The reader can now put a folder inside
another as deep as they like (**New folder inside**, **Move up a level**, or by dragging its head onto another
folder), and deleting a folder moves what is in it, documents and folders, up into its parent rather than losing the
structure. R23 is marked optional in the round table; the review has not removed it, so it is done as the last task.

## The change

- `textfold/library.py` — a folder gains `parent` (another folder's id; absent at the top). `load` keeps it only when
  it is a string, and repairs a parent that is gone, or a loop edited by hand, by dropping it (each chain is walked
  with a visited set). `_under(d, fid)` is a folder and every folder inside it, however deep. `change`:
  `new` takes `parent` (which must be a folder that is there); `nest {id, parent}` moves a folder under another, or to
  the top with `parent: null`, and refuses a folder inside itself or inside one it holds; `delete` lifts its children
  and its own documents one level (into its parent, or to the top), a document's folder changing in `of` rather than
  being dropped. The docstring and the file's example carry the new shape.
- `textfold/server.py` — the module docstring lists `nest`; the route already passes the body through and maps
  `ValueError` to 400.
- `textfold/web/app.js` — `kidsOf(id)` and `inside(id)`; the drawing recurses (a folder's folders, then its own
  documents), and a folder's count includes the documents in the folders inside it; a folder's head is draggable
  unless its name is being written; the folder menu has **New folder inside** (which opens the folder and puts the
  field inside it) and **Move up a level** (only when it is inside one); the document and picked menus list the tree
  with how deep each folder is; `within` is the folder a new one is being named inside, cleared on Escape;
  `nestFolder(id, parent)` posts `{op: nest}`; drag and drop handles a folder head, refusing its current parent, itself
  and its descendants, and a folder dropped on the list's end goes to the top; while a folder is dragged the list is
  not redrawn.
- `textfold/web/app.css` — the shut-folder rules take only a folder's own row and items (`>`), so each folder's state
  is its own; the menus' folder rows are indented by `--d`.
- `textfold/web/i18n.js` — `NEST` (en/zh) gives `f_new_sub` and `f_up`; the delete prompt now says that documents and
  folders move up a level and the documents stay in the library.
- `docs/DEVELOPMENT.md` — the library paragraph (inside one another, the two menu items, the count, delete lifting up)
  and the Layout line for `library.py`.
- Tests — `tests/test_nested_folders.py` (a parent kept and validated, nest up and down, refusal of a folder inside
  itself or inside a folder it holds, delete lifting documents and folders, repair of a gone parent and of a loop,
  twelve writers making folders at once, and the sidebar's recursion, menus, drag rules, words, CSS and route);
  `tests/test_app_sidebar_select.py` updated for the array drag and `parent = within`.

## Decisions

- **A parent is one id, not a path.** `library.json` stays something a reader can edit by hand: a folder names its
  parent and nothing else is stored. Materialised paths or ordering keys would have to be rewritten on every rename or
  move, and a hand edit could contradict them; a tree is drawn from one string.
- **Deleting a folder lifts what is in it.** Its documents and folders go up one level, into its parent (or to the
  top), rather than being deleted or all left unfiled: the reader asked to remove a grouping, not its contents. This is
  upstream's choice and the one the delete prompt says.
- **The count includes the folders inside.** A top folder that holds a chapter that holds two documents says 2, the
  number of documents it would take with it if deleted; a count of its own rows only would read as empty.
- **A folder is dragged by its head; documents by their rows.** The row drag of R21b still carries the picked
  documents together; a folder's head is its own handle, and is not draggable while its name is being written.
- **A loop is broken at the edge being read.** The repair is order-dependent: for two folders under each other, the
  first read loses its parent and the second stays under it. No loop remains and every chain ends; the test asserts
  that, not that both come to the top. Upstream behaves the same.
- **Nesting adds no lock.** `change` already takes `library._lock` across its load-modify-save; a parent is written by
  the same path. The two-writer test makes twelve folders under one parent at once.

## Concurrency and locks

`library._lock` still serializes every folder change. Deleting a folder touches `library.json` only: it does not move
any `papers/<id>` folder, so `store.LOCK` and a document's delete/restore are not involved. A document deleted while
its nested folder is deleted comes back through `remember` only if its folder is still there (R21a's rule); if the
folder went in between, the dates and name return and the document is unfiled, which is the same rule one level up.

## How it was verified

- `python .claude/hooks/verify.py` — 436 tests, OK (R22 baseline 421; fifteen new). `node --check` on the scripts and
  `git diff --check` clean.
- A server of its own (temporary data folder, `TEXTFOLD_NO_MODELS=1`, port 3023), two imported Markdown documents:
  - **New folder** made `Thesis`; its menu's **New folder inside** opened it, put the field inside it and made
    `Chapter 2`; the same made a third level. A parent's count showed the documents in its folders (Thesis 2,
    Chapter 2 2, Section 2.1 1); the drawing indented each level.
  - A document's menu listed the tree indented (`--d` 0/1/2 → padding 10/24/38 px) with the document's folder ticked;
    the picked documents' menu listed it too, and moved both into a nested folder.
  - A document dragged onto a nested folder went in; dragged onto the list's end came out.
  - A folder dragged onto another nested it (the target lit); dragging it onto its current parent, onto itself or onto
    a folder it holds lit nothing and dropped nothing; dragging it onto the list's end made it top-level, and back
    into a folder again. **Move up a level** lifted it out of its parent, and the item is absent at the top.
  - Deleting `Section 2.1` (which held both documents) asked "删除文件夹“Section 2.1”？里面的文档和子文件夹会移到上一层，文档仍留在文献库里。"
    and moved both documents into its parent; the counts followed.
  - Collapsing a folder hid its folders and documents and opened again; a search for one document showed the folders
    on its path and hid the other document.
  - Escape on a folder being named inside another left nothing behind, and the next new folder was at the top; a
    nested folder's rename field opened in its own row, filled with its name.
  - No console errors, no failed requests.
  - After the verifier's finding below, in Chrome: with a search ("zzz") that hid the folder, **New folder inside** on
    it cleared the search and showed and focused the field, inside that folder.
- `textfold-verifier` — one pass (~18 minutes, 90 tool uses), **no blocking finding**. It ran the suite and
  `verify.py` (434 at that point), drove the route on a server of its own (nest, self/descendant/missing parent → 400,
  delete lifting, move into a nested folder), and probed the library: all 625 parent assignments over four folders
  repaired to an acyclic, fully reachable tree; 300 random 40-operation sequences kept every parent and `of` entry
  valid; four threads moving, deleting and nesting left the file consistent; `remember` of a nested, lifted and
  deleted place behaved as this record says. Mutations of the new library tests (delete dropping documents, nest
  allowing cycles, delete leaving children, removing the lock) were all killed. Non-blocking, fixed here:
  **a search that hides a folder also hid a new subfolder's name field** (the menu stays open when Ctrl+K is pressed,
  so **New folder inside** rendered an invisible, unfocused field; `editName` now clears the search when it names
  inside a folder); the `inside` traversal and the `up ? … : ''` guard were not pinned by any test (both are now
  asserted, the traversal's exact loop line); `remember` with a nested place and `nest`/`delete` under several
  writers were not tested (both now are); two stale comments (`folders.py`, "New Subfolder") were corrected. Left and
  recorded: `library.json` is serialized by an in-process lock only, so two processes on one data folder can collide
  on the fixed `.tmp` and lose a save (pre-existing; two writers by process were reproduced, two servers were not);
  a hand-edited folder id goes into `data-folder`/`data-to` unescaped (pre-existing, not made worse).

## Measured

| | before | after |
|---|---|---|
| Python tests | 421 | 436 |
| A folder's depth | one level | inside one another, as deep as the reader makes them |
| Deleting a folder | its documents left unfiled | documents and folders move up one level |
| A folder's count | its own documents | its own and those in the folders inside it |
| Moving a folder | — | New folder inside, Move up a level, dragged onto another or to the top |
| The menus' folder list | flat | indented by depth |

## Not measured

- **A real pointer drag**: the browser walk dispatched `DragEvent`s with a `DataTransfer`, as R21b's did; the cursor,
  the native drag image and a drag that leaves the window were not walked.
- **Very deep or very wide trees**: the drawing calls `inside` per folder, and each walk is depth × folders, so a deep
  chain is worst-case cubic in folders; fine at the sizes here, and a library with hundreds of folders was not timed.
- **Two processes on one data folder** (the app and `textfold serve` share `store.DATA`): `library._lock` is in-process,
  and the verifier reproduced a pre-existing collision on the fixed `library.json.tmp` (a `PermissionError`, and a
  save lost) with two child processes. This change neither introduces nor fixes it. Two windows or tabs in one
  process are serialized; the two-writer tests use threads.
- **A folder deleted while a document in it is in the trash** was reasoned through `remember`'s existing rule, not
  walked in a browser.
- **The MyGo shell**, and a hand-edited `library.json` with a parent that is not a string (read as at the top by the
  same validation as the other fields).
- **Zoom smoothness is unmeasured** (it needs `playwright` and `out/compare/`, neither here). The change is in the
  sidebar, not the reader, but it is not reported as unaffected.

## Pitfalls

- A loop edited into `library.json` is repaired at read time, but which edge is dropped depends on the order folders
  are listed: one of the two stays under the other. There is no loop afterwards.
- A folder can be moved into any other folder only by dragging its head; the menu creates one inside and lifts one
  level, so a keyboard-only reader can build a tree downward one menu at a time but cannot move an existing folder
  sideways. Upstream has the same gap.
- Closing a folder hides the folders inside it too; there is no separate "recursive" control.
- A search keeps a folder open (`found`) while it shows what was found; the `>` rules keep a shut inner folder's
  state from leaking out, but the outer folder's open state is the search's, not the reader's.
- Deleting a folder does not delete documents or folders; a reader who expected the whole subtree gone will find it
  one level up.
- `library.json` is serialized within one process only. The app and a `textfold serve` on the same data folder can
  collide on its `.tmp` and lose a save (pre-existing; worst when both write at once).
- A hand-edited folder `id` (any string is accepted) is inserted into the sidebar's `data-folder`/`data-to` attributes
  without escaping; the names are escaped, the ids were not before this change either, and the app never sends one with
  markup.

## Rejected

- **Storing paths or order keys instead of a parent.** Every rename or move would rewrite a subtree, and a hand-edited
  file could carry a path that is not its parent's; one parent id is the smallest fact that makes the tree.
- **Deleting a folder's contents with it.** R23 asks for nesting, not a second, more destructive delete; losing a
  subtree to one confirm would be a data loss.
- **A second folder system for nesting.** The sidebar's existing folders are the library's; a parallel tree would
  split the same documents and confuse the trash's place.
- **Drag-to-reorder within a folder.** This change moves folders between folders; the order inside one stays the order
  they were made, as before.
