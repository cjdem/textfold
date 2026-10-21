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

func TestUpdateStateDismissal(t *testing.T) {
	d := New("1.2.3", "", t.TempDir(), "https://example.com/app", nil)
	if d.UpdateState() != nil {
		t.Fatal("a new app has an update state")
	}
	d.show(UpdateState{Kind: "available", Version: "1.3.0"})
	if s := d.UpdateState(); s == nil || s.Kind != "available" || s.Version != "1.3.0" {
		t.Fatalf("state = %+v", s)
	}
	d.DismissUpdate()
	if s := d.UpdateState(); s == nil || !s.Dismissed {
		t.Fatal("dismissing the toast did not stick")
	}
	d.show(UpdateState{Kind: "downloading", Version: "1.3.0", Percent: 10})
	if s := d.UpdateState(); s == nil || s.Dismissed || s.Kind != "downloading" {
		t.Fatalf("a new phase did not show again: %+v", s)
	}
	d.DismissUpdate()
	d.show(UpdateState{Kind: "downloading", Version: "1.3.0", Percent: 50})
	if s := d.UpdateState(); s == nil || !s.Dismissed {
		t.Fatal("progress reopened a dismissed toast")
	}
	d.show(UpdateState{Kind: "ready", Version: "1.3.0"})
	if s := d.UpdateState(); s == nil || s.Dismissed || s.Kind != "ready" {
		t.Fatalf("ready did not show again: %+v", s)
	}
}

func TestNoteVersionSpeaksOnlyAfterAnUpdate(t *testing.T) {
	data := t.TempDir()
	first := New("1.2.3", "", data, "https://example.com/app", nil)
	first.NoteVersion()
	if s := first.UpdateState(); s != nil {
		t.Fatalf("a first install said it updated: %+v", s)
	}
	next := New("1.2.4", "", data, "https://example.com/app", nil)
	next.NoteVersion()
	s := next.UpdateState()
	if s == nil || s.Kind != "updated" || s.Version != "1.2.4" || s.From != "1.2.3" {
		t.Fatalf("state = %+v", s)
	}
	if s.Notes != "https://example.com/app/releases/tag/v1.2.4" {
		t.Fatalf("notes = %q", s.Notes)
	}
}
