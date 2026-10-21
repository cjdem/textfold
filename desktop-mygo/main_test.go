package main

import (
	"bytes"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

func TestConfigVersionMatchesThePackage(t *testing.T) {
	version, err := configVersion()
	if err != nil {
		t.Fatal(err)
	}
	source, err := os.ReadFile(filepath.Join("..", "textfold", "__init__.py"))
	if err != nil {
		t.Fatal(err)
	}
	m := regexp.MustCompile(`(?m)^__version__ = "([^"]+)"`).FindSubmatch(source)
	if m == nil {
		t.Fatal("textfold/__init__.py has no __version__")
	}
	if version != string(m[1]) {
		t.Fatalf("mygo.json says %s, textfold says %s", version, m[1])
	}
}

func TestShippedLicensesMatchTheRepository(t *testing.T) {
	for _, name := range []string{"LICENSE", "NOTICE"} {
		want, err := os.ReadFile(filepath.Join("..", name))
		if err != nil {
			t.Fatal(err)
		}
		got, err := os.ReadFile(filepath.Join("resources", name+".txt"))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(got, want) {
			t.Errorf("desktop-mygo/resources/%s.txt has drifted from %s; copy it again", name, name)
		}
	}
}

func TestSameOrigin(t *testing.T) {
	base := "http://127.0.0.1:31917/"
	if !sameOrigin("http://127.0.0.1:31917/p/paper?lang=zh", base) {
		t.Fatal("a reader page was treated as another origin")
	}
	for _, raw := range []string{
		"http://localhost:31917/",
		"http://127.0.0.1:31918/",
		"https://127.0.0.1:31917/",
	} {
		if sameOrigin(raw, base) {
			t.Errorf("sameOrigin(%q, %q) = true", raw, base)
		}
	}
}

func TestFailurePageEscapesTheError(t *testing.T) {
	page := failurePage(assertError("<script>alert(1)</script>"))
	if strings.Contains(page, "<script>alert(1)</script>") {
		t.Fatal("failure page contains unescaped HTML")
	}
	if !strings.Contains(page, "&lt;script&gt;alert(1)&lt;/script&gt;") {
		t.Fatal("failure page does not show the error")
	}
}

type assertError string

func (e assertError) Error() string { return string(e) }
