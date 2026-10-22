package main

import (
	"os"
	"path/filepath"
	"regexp"
	"testing"
)

// The app's Settings offer the Anthropic API, and an installed copy offers no way to run pip: the payload must install
// the SDK into the Python it ships, and its own check must import it from the app folder, without the user's
// site-packages (a build machine's own Python could otherwise satisfy the import and the payload still ship without
// it).
func TestPayloadShipsTheAnthropicSDK(t *testing.T) {
	script, err := os.ReadFile(filepath.Join("scripts", "prepare-payload.mjs"))
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []struct {
		what string
		re   *regexp.Regexp
	}{
		{"the SDK's version range", regexp.MustCompile(`APP_ONLY\s*=\s*\[\s*['"]anthropic>=1\.15,<2['"]`)},
		{"the SDK in the pip install", regexp.MustCompile(`\.\.\.APP_ONLY`)},
		{"the payload check's -s -c", regexp.MustCompile(`['"]-s['"]\s*,\s*['"]-c['"]`)},
		{"the payload check run in app/", regexp.MustCompile(`cwd:\s*app\b`)},
		{"the SDK imported by the payload check", regexp.MustCompile(`import [^;\n]*\banthropic\b`)},
	} {
		if !want.re.Match(script) {
			t.Errorf("scripts/prepare-payload.mjs no longer ships the Anthropic SDK: %s is missing", want.what)
		}
	}
}
