package bridge

import "testing"

func TestExternalURL(t *testing.T) {
	for _, raw := range []string{"https://example.com/a", "http://127.0.0.1:3017/"} {
		if !externalURL(raw) {
			t.Errorf("externalURL(%q) = false", raw)
		}
	}
	for _, raw := range []string{"file:///C:/Windows/win.ini", "javascript:alert(1)", "https://", ""} {
		if externalURL(raw) {
			t.Errorf("externalURL(%q) = true", raw)
		}
	}
}

func TestSaveName(t *testing.T) {
	for _, name := range []string{"paper.html", "notes.MD", "../reading.json"} {
		if _, _, err := saveName(name); err != nil {
			t.Errorf("saveName(%q): %v", name, err)
		}
	}
	for _, name := range []string{"paper.exe", "notes", ".md", ""} {
		if _, _, err := saveName(name); err == nil {
			t.Errorf("saveName(%q) succeeded", name)
		}
	}
}
