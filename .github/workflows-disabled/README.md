# Parked workflows

`desktop.yml` is active again in `.github/workflows/`: a `v*` tag (or
Actions › desktop › Run workflow) builds the Windows app. A tag build needs
the `MYGO_UPDATER_PRIVATE_KEY` secret and stops before it leaves a draft
release without it.

The PyPI and site workflows are parked here. GitHub reads only
`.github/workflows/`, so nothing here runs.

- `publish.yml` would publish the `textfold` package to PyPI on a `v*` tag.
  This fork does not publish under that name; keep it parked.
- `site.yml` deploys the website on a push to `main` that touches `site/**`
  or the workflow itself. Bring it back once the first release is out.

To bring one back, move it into place:

    git mv .github/workflows-disabled/site.yml .github/workflows/site.yml

The files are kept rather than deleted so the build and release steps do not
have to be reconstructed when they are wanted again.
