# Parked workflows

The repository's GitHub Actions workflows lived in `.github/workflows/`.
They were moved here on 2026-10-18 so that a push builds nothing. GitHub
reads only `.github/workflows/`, so nothing here runs.

To bring one back, move it into place:

    git mv .github/workflows-disabled/desktop.yml .github/workflows/desktop.yml

- `desktop.yml` and `publish.yml` run on a `v*` tag (or by hand, Actions ›
  desktop › Run workflow): the Windows app into a draft release, and the
  package to PyPI.
- `site.yml` runs on a push to `main` that touches `site/**`,
  `docs/assets/**` or the workflow itself, and deploys the website.

The files are kept rather than deleted so the build and release steps do not
have to be reconstructed when they are wanted again.
