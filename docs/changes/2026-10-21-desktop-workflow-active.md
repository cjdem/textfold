# The Windows release workflow is active again

- Date: 2026-10-21.
- Mode: release preparation; not pushed as a tag.
- Decision: activate `desktop.yml` for the first MyGo release, and keep the
  PyPI and site workflows parked.

## What changed

- `.github/workflows-disabled/desktop.yml` moved back to
  `.github/workflows/desktop.yml`. It runs on a `v*` tag or by hand; a push
  to `main` does not build it.
- The `prepare` job now checks for `MYGO_UPDATER_PRIVATE_KEY` before it
  creates the draft release, so a tag without the secret fails without
  leaving an empty draft. The `build` job keeps its own check.
- `.github/workflows-disabled/README.md` and `docs/DEVELOPMENT.md` say which
  workflows are active and which remain parked.

## Not done

- The `MYGO_UPDATER_PRIVATE_KEY` secret is not added here: the private key is
  on the maintainer's machine at
  `%APPDATA%\mygo\update-keys\mygo-update.key`.
- No `v0.10.7` tag was created or pushed.
- `publish.yml` stays parked; this fork does not publish `textfold` to PyPI.
- `site.yml` stays parked until the first release is out, so the download
  button has a file to point at.

## Release order

1. Add `MYGO_UPDATER_PRIVATE_KEY` to the repository secrets.
2. `git tag v0.10.7 && git push origin v0.10.7`.
3. The workflow builds the app, the signed update manifest and archive, and
   publishes the release.
4. Move `site.yml` back, enable GitHub Pages, and deploy the site.

## Verification

- The workflow YAML parses.
- `git diff --check`.
- The moved file is the only change under `.github/workflows/`; no tag was
  pushed, so no build ran.
