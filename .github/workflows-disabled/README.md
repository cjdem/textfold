# Parked workflow

`desktop.yml` and `site.yml` are active in `.github/workflows/`: a `v*` tag
(or Actions › desktop › Run workflow on the tag) builds the Windows app and
publishes its release, and the site is deployed when that run finishes (or by
Actions › site › Run workflow, for the latest release's page). A tag build
needs the `MYGO_UPDATER_PRIVATE_KEY` secret and stops before it leaves a draft
release without it.

Only the PyPI workflow is parked here. GitHub reads only
`.github/workflows/`, so nothing here runs.

- `publish.yml` would publish the `textfold` package to PyPI on a `v*` tag.
  This fork does not publish under that name; keep it parked.

If this fork ever publishes under its own name, move it into place:

    git mv .github/workflows-disabled/publish.yml .github/workflows/publish.yml

The file is kept rather than deleted so the publish steps do not have to be
reconstructed when they are wanted again.
