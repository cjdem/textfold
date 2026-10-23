# The website is published by a release, not by a push

**Date:** 2026-10-23
**Branch:** `worktree-site-release-deploy`

## What and why

`.github/workflows/site.yml` built and deployed the site on every push to `main` that touched `site/**`. Its download
button offers `releases/latest`, and the newest installer is the `v0.10.7` release built on a tag. The pending push
changes `site/strings.py` — the page would describe connecting API providers and Magpie while the downloadable app is
still 0.10.7 and lacks them. Now the site is deployed by the desktop workflow's successful run for a `v*` tag, which
is the run that publishes the release and its installer; the build fails unless the page's stated version is that tag,
and a manual site run may publish only the latest release's page.

## The change

- `.github/workflows/site.yml` — the trigger is `workflow_run: workflows: ['desktop'], types: [completed]` plus
  `workflow_dispatch`; the push trigger is gone. The build job runs for a `workflow_run` of a `v*` tag that succeeded
  (whether the tag was pushed or dispatched; `desktop.yml` keys its release steps on `refs/tags`, so a dispatch on the
  tag publishes too), or for a manual site run. It checks out `workflow_run.head_sha` — the tagged commit, not `main`.
  A release run compares `site/strings.py`'s `VERSION` with `head_branch` (the tag); a manual run compares it with
  `releases/latest`. Either check stops the build before a page that names another version. The header comment says
  why.
- `tests/test_site_deploy.py` — new: no push/branch/release/schedule trigger; the success-and-`v*` guard and the
  tagged-commit checkout; the workflow name it waits on is the one `desktop.yml` declares, and that workflow's last
  step publishes the release; `deploy` needs `build`; both version checks come before the site build; and
  `site/strings.py`, `textfold/__init__.py` and `desktop-mygo/mygo.json` state one version.
- `.github/workflows-disabled/README.md` — it described the removed push trigger; it now says the site follows the
  desktop run, or a manual run for the latest release's page.
- `docs/DEVELOPMENT.md` — the deployment sentence says the site goes up when the desktop run finishes a release.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: how the website is deployed.
- `.github/workflows-disabled/README.md` — updated: it described the old push trigger.
- `README.md` / `README.zh-CN.md` — not needed: no reader or install step changes.
- `site/` — no page text or version changes; this is how it is published, not what it says.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no data format change.
- `docs/requirements/` — none covers deployment.
- `pyproject.toml`, `requirements.txt` — not needed: no dependency; the test uses the standard library only.
- `NOTICE`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md`,
  `desktop-mygo/README.md`, `.claude/agents/`, `CLAUDE.md`, `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no
  attribution, licence, security, contribution, desktop or process change.

## Decisions

- Trigger on the desktop run, not `release: published`: `desktop.yml` creates the draft and publishes it with
  `${{ secrets.GITHUB_TOKEN }}` (`gh release edit --draft=false --latest`), and events caused by the repository's
  `GITHUB_TOKEN` do not start workflows (only `workflow_dispatch` and `repository_dispatch` do). A workflow waiting on
  the `release` event would never run. Waiting on the run that publishes the release needs no new secret or
  permission.
- The guard is `conclusion == 'success'` and `head_branch` starting with `v`, not the upstream event: a dispatch on a
  branch builds artifacts and publishes no release, and a failed run publishes nothing, so both are excluded; a
  dispatch on the tag *does* publish (the release steps test `refs/tags`), so requiring `event == 'push'` would drop a
  real release from the site.
- `workflow_run.head_sha`, not the default checkout ref: on a `workflow_run` the checkout defaults to the default
  branch, and the page must be built from the tagged commit.
- A manual site run compares its version with `releases/latest` instead of publishing "what it is given": otherwise a
  typo fix dispatched from `main` after a version bump would publish a page naming a version whose installer is not
  out — the mismatch this change exists to prevent. It also keeps an old tag's page from being dispatched over a newer
  one.
- `workflow_dispatch` stays: a site-only change (a typo) can still be published by hand once the release it belongs to
  is out. The push trigger does not stay, because "remember to release first" is exactly the failure being fixed.
- The version checks live in the workflow, not in `site/build.py`: `desktop.yml` already checks its own version
  against the tag with a shell step, and this keeps the site build usable by hand from any checkout.
- The three-way version test is a test-only guard: it catches drift before a release and changes no file's version.

## Concurrency and locks

Not applicable: this changes CI configuration, documentation and a test; no data is read or written. The Pages
deployment keeps its `concurrency: group: pages` so two runs do not deploy over each other.

## How it was verified

- `python .claude/hooks/verify.py` — 463 tests, OK (30.4 s); `git diff --check` clean.
- `tests.test_site_deploy` — 6 tests, deterministic; run against a scratch tree made from `HEAD`, 3 fail and 1 errors
  (the two checks cannot even find their markers), so they pin the workflow rather than describing it.
- Not verified by a run: GitHub Actions cannot be run from here, and `actionlint` and a YAML parser are not installed
  (none was installed). The version shell snippets were run locally against the repo root: `v0.10.7` passes and
  `v0.10.8` fails.

## Not measured

- A real release publishing the site: not exercised. The claims that `workflow_run` fires for the tag run, carries
  `head_branch` as the tag and `head_sha` as the tagged commit, and that the installer is published by the time the
  desktop run completes rest on GitHub's documented behaviour and `desktop.yml`'s step order, not on a run.
- Zoom smoothness: unchanged by this change and still unmeasured on this machine (`tools/zoombench.py` needs
  `playwright` and exported comparison pages, neither installed).

## Pitfalls

- `workflow_run` only starts a workflow whose file is on the default branch: the change must be on `origin/main` (the
  push, not merely the local merge) before the tag is pushed, or the release's completion matches nothing.
- On a `workflow_run`, `actions/checkout` defaults to the default branch. The explicit `head_sha` is what makes the
  built page the released one.
- The checks compare `v$code` with the tag, so the page's `VERSION` must carry no `v`. A release published without
  bumping `site/strings.py` fails the site build instead of publishing a page that names the wrong version; a manual
  run on `main` with an unreleased version fails the same way.
- `on:` is a YAML 1.1 boolean for some parsers; the tests slice it as text rather than parsing the file, and GitHub
  reads the key as `on`.
- If a job is ever added to `desktop.yml` after `publish` and that job fails, the desktop run is not a success and the
  site does not deploy — the release is out, and the site waits for the next release or a manual run. Keeping
  `publish` last is what makes the coupling exact.

## Rejected

- Waiting on `release: published`: the publisher is the repository's `GITHUB_TOKEN`, which starts no such workflow.
- Requiring the upstream event to be `push`: a dispatch on the tag publishes the release too, and would leave the site
  behind.
- Deploying on a tag push: the draft release is not public yet, so the page could still offer the old installer, and
  the site would build before the app is known to build.
- Polling `gh release view` for the draft to disappear: runner-minutes spent waiting on a build whose length is not
  bounded here, and a timeout that fails the page.
- Publishing the release with a personal access token so the `release` event fires: a new secret and broader
  permissions for the same result.
- Deploying on a schedule: it would publish whatever is on `main`, which is the same mismatch with extra steps.
