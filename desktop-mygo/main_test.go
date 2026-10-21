package main

import (
	"strings"
	"testing"
)

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
