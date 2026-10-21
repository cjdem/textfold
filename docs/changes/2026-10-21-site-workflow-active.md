# The site deploy workflow is active again

- Date: 2026-10-21.
- Mode: release follow-up; v0.10.7 is published.
- Decision: bring `site.yml` back now that the download page has a release
  to point at, and keep the PyPI workflow parked.

## What changed

- `.github/workflows-disabled/site.yml` moved back to
  `.github/workflows/site.yml`; a push to `main` that touches `site/**` or the
  workflow deploys the website.
- `.github/workflows-disabled/README.md` says only `publish.yml` remains
  parked.
- `docs/DEVELOPMENT.md` says the site deploys from `site.yml`.

## Not done

- GitHub Pages is not enabled here: the repository must set **Settings ›
  Pages › Build and deployment › Source** to **GitHub Actions** before the
  deploy job can run.
- The site has not been deployed yet.

## Verification

- `python site/build.py` fills both pages, with no `{{...}}` placeholders
  left.
- The download link is
  `https://github.com/cjdem/textfold/releases/latest/download/TextFold-win-x64-setup.exe`,
  and v0.10.7 has that asset.
- The workflow YAML parses.
