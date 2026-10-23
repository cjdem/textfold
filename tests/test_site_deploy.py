"""The website goes up when the desktop workflow finishes a release, not when a push touches site/**: its download
button offers releases/latest, so a page published before the installer exists promises capabilities the downloadable
app does not have. The release is published with the repository's GITHUB_TOKEN, which starts no `release` event, so the
site waits on the desktop run that publishes it. The page states its version, and that version must be the release's
and the app's; a manual run may publish only the latest release's page. There is no site build in the suite, so this
holds the workflow's trigger, its guards, its version checks, and the files they depend on.

Run from the repo root:
    python -m unittest discover tests
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"


class SiteDeploy(unittest.TestCase):
    def setUp(self):
        self.yml = (WF / "site.yml").read_text(encoding="utf-8")
        self.on = self.yml[self.yml.index("\non:"):self.yml.index("\npermissions:")]

    def test_the_site_waits_for_the_release_run_and_a_push_does_not_publish_it(self):
        self.assertIn("workflow_run:", self.on)
        self.assertIn("workflows: ['desktop']", self.on)
        self.assertIn("types: [completed]", self.on)
        self.assertIn("workflow_dispatch:", self.on)   # (a site-only change, after the release it belongs to)
        self.assertNotIn("push:", self.on)
        self.assertNotIn("branches:", self.on)   # (any branch trigger would bring the push back)
        self.assertNotIn("release:", self.on)    # (the GITHUB_TOKEN that publishes it starts none)
        self.assertNotIn("schedule:", self.on)   # (it would publish whatever is on main)

    def test_only_a_successful_v_tag_run_publishes_it(self):
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.yml)
        self.assertIn("startsWith(github.event.workflow_run.head_branch, 'v')", self.yml)
        # A dispatch on the tag publishes the release too (desktop.yml keys on refs/tags), so the event is not the test.
        self.assertNotIn("github.event.workflow_run.event == 'push'", self.yml)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha || github.sha }}", self.yml)   # (the tag's commit, not main)

    def test_the_run_it_waits_on_is_the_one_that_publishes_the_release(self):
        desk = (WF / "desktop.yml").read_text(encoding="utf-8")
        name = re.search(r"^name: (\S+)$", desk, re.M).group(1)
        self.assertIn(f"workflows: ['{name}']", self.on)   # (a renamed workflow would silently stop the site)
        self.assertIn('gh release edit "$TAG" -R "$REPO" --draft=false --latest', desk)   # (the last step publishes it)

    def test_the_deployment_follows_a_build_that_ran(self):
        self.assertIn("  deploy:\n    needs: build", self.yml)   # (a skipped build deploys nothing)

    def test_every_publish_path_checks_the_version_before_building(self):
        build_at = self.yml.index("- run: python3 site/build.py")
        self.assertLess(self.yml.index("The page states the release it is published with"), build_at)
        self.assertLess(self.yml.index("A manual run publishes the latest release's page, not a newer one"), build_at)
        self.assertIn('test "v$code" = "$TAG"', self.yml)   # (the release run: the page is the tag's)
        self.assertIn('gh api "repos/$REPO/releases/latest" --jq .tag_name', self.yml)
        self.assertIn('test "v$code" = "$latest"', self.yml)   # (a manual run: the page is the latest release's)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", self.yml)

    def test_the_page_the_app_and_the_desktop_manifest_state_one_version(self):
        def stated(path, pattern):
            return re.search(pattern, (ROOT / path).read_text(encoding="utf-8"), re.M).group(1)
        site = stated("site/strings.py", r'^VERSION = "([^"]+)"')
        app = stated("textfold/__init__.py", r'^__version__ = "([^"]+)"')
        desk = stated("desktop-mygo/mygo.json", r'^  "version": "([^"]+)"')
        self.assertEqual({site, app, desk}, {site})


if __name__ == "__main__":
    unittest.main()
