package server

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestEnvironmentOverridesTextFoldData(t *testing.T) {
	t.Setenv("TEXTFOLD_DATA", "old")
	env := environment(`C:\reading data`)
	found := false
	for _, item := range env {
		if strings.EqualFold(item, `TEXTFOLD_DATA=C:\reading data`) {
			found = true
		}
		if strings.HasPrefix(strings.ToUpper(item), "TEXTFOLD_DATA=") && !strings.EqualFold(item, `TEXTFOLD_DATA=C:\reading data`) {
			t.Fatalf("old TEXTFOLD_DATA survived: %q", item)
		}
	}
	if !found {
		t.Fatal("TEXTFOLD_DATA override is missing")
	}
}

func TestFreePort(t *testing.T) {
	port, err := freePort()
	if err != nil {
		t.Fatal(err)
	}
	if port <= 0 {
		t.Fatalf("port = %d", port)
	}
}

func TestStartRequiresInputs(t *testing.T) {
	if _, err := Start(Config{}); err == nil {
		t.Fatal("Start accepted an empty configuration")
	}
}

func TestStartReportsAMissingPython(t *testing.T) {
	temp := t.TempDir()
	code := filepath.Join(temp, "code")
	if err := os.MkdirAll(code, 0o755); err != nil {
		t.Fatal(err)
	}
	_, err := Start(Config{
		Python:       filepath.Join(temp, "missing-python"),
		Code:         code,
		Data:         filepath.Join(temp, "data"),
		ReadyTimeout: 1,
	})
	if err == nil {
		t.Fatal("Start succeeded without Python")
	}
}
