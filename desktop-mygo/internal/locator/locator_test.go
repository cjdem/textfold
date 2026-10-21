package locator

import (
	"os"
	"path/filepath"
	"testing"
)

func checkout(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "textfold"), 0o755); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"server.py", "__main__.py"} {
		if err := os.WriteFile(filepath.Join(root, "textfold", name), []byte("# test\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func TestDevelopmentFindsTheCheckoutVirtualenv(t *testing.T) {
	root := checkout(t)
	t.Setenv("TEXTFOLD_PYTHON", "")
	python := filepath.Join(root, ".venv", "Scripts", "python.exe")
	if err := os.MkdirAll(filepath.Dir(python), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(python, []byte("test"), 0o644); err != nil {
		t.Fatal(err)
	}
	got, err := Development(root)
	if err != nil {
		t.Fatal(err)
	}
	if got.Python != python || got.Code != root {
		t.Fatalf("Development = %+v", got)
	}
}

func TestDevelopmentFindsTheMainCheckoutVirtualenvFromAWorktree(t *testing.T) {
	main := checkout(t)
	python := filepath.Join(main, ".venv", "Scripts", "python.exe")
	if err := os.MkdirAll(filepath.Dir(python), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(python, []byte("test"), 0o644); err != nil {
		t.Fatal(err)
	}
	worktree := checkout(t)
	gitdir := filepath.Join(main, ".git", "worktrees", "test")
	if err := os.MkdirAll(gitdir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(gitdir, "commondir"), []byte("../..\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(worktree, ".git"), []byte("gitdir: "+gitdir+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Setenv("TEXTFOLD_PYTHON", "")
	t.Setenv("VIRTUAL_ENV", "")
	got, err := Development(worktree)
	if err != nil {
		t.Fatal(err)
	}
	if got.Python != python {
		t.Fatalf("Python = %q, want %q", got.Python, python)
	}
}

func TestPackagedRequiresThePayload(t *testing.T) {
	resources := t.TempDir()
	if _, err := Packaged(resources); err == nil {
		t.Fatal("Packaged accepted an empty resources folder")
	}
	app := filepath.Join(resources, "payload", "app")
	if err := os.MkdirAll(filepath.Join(app, "textfold"), 0o755); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"server.py", "__main__.py"} {
		if err := os.WriteFile(filepath.Join(app, "textfold", name), []byte("# test\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	python := filepath.Join(resources, "payload", "python", "python.exe")
	if err := os.MkdirAll(filepath.Dir(python), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(python, []byte("test"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Packaged(resources); err != nil {
		t.Fatal(err)
	}
}
