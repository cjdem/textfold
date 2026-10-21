# Parked workflow

`desktop.yml` and `site.yml` are active in `.github/workflows/`: a `v*` tag
(or Actions › desktop › Run workflow) builds the Windows app, and a push to
`main` that touches `site/**` (or Actions › site › Run workflow) deploys the
website. A tag build needs the `MYGO_UPDATER_PRIVATE_KEY` secret and stops
before it leaves a draft release without it.

Only the PyPI workflow is parked here. GitHub reads only
`.github/workflows/`, so nothing here runs.

- `publish.yml` would publish the `textfold` package to PyPI on a `v*` tag.
  This fork does not publish under that name; keep it parked.

If this fork ever publishes under its own name, move it into place:

    git mv .github/workflows-disabled/publish.yml .github/workflows/publish.yml

The file is kept rather than deleted so the publish steps do not have to be
reconstructed when they are wanted again.
