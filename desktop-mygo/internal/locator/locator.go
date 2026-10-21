package locator

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

type Layout struct {
	Python string
	Code   string
}

func Development(root string) (Layout, error) {
	if root == "" {
		return Layout{}, errors.New("the TextFold checkout could not be located")
	}
	code := filepath.Clean(root)
	if !hasServer(code) {
		return Layout{}, errors.New("textfold/server.py is missing from the TextFold checkout")
	}
	if named := os.Getenv("TEXTFOLD_PYTHON"); named != "" {
		return Layout{Python: named, Code: code}, nil
	}
	roots := []string{code}
	if common := commonCheckout(code); common != "" && !samePath(common, code) {
		roots = append(roots, common) // a linked worktree borrows the main checkout's virtualenv
	}
	if virtual := os.Getenv("VIRTUAL_ENV"); virtual != "" {
		roots = append([]string{virtual, code}, roots[1:]...)
	}
	for _, root := range roots {
		if python := virtualenvPython(root); python != "" {
			return Layout{Python: python, Code: code}, nil
		}
	}
	if runtime.GOOS == "windows" {
		return Layout{Python: "python.exe", Code: code}, nil
	}
	return Layout{Python: "python3", Code: code}, nil
}

func Packaged(resources string) (Layout, error) {
	payload := filepath.Join(resources, "payload")
	if named := os.Getenv("TEXTFOLD_PAYLOAD"); named != "" {
		payload = named
	}
	python := filepath.Join(payload, "python", "python.exe")
	if runtime.GOOS != "windows" {
		python = filepath.Join(payload, "python", "bin", "python3")
	}
	code := filepath.Join(payload, "app")
	if info, err := os.Stat(python); err != nil || info.IsDir() {
		return Layout{}, errors.New("the bundled Python runtime is missing; prepare the payload before building")
	}
	if !hasServer(code) {
		return Layout{}, errors.New("the bundled TextFold code is missing from the payload")
	}
	return Layout{Python: python, Code: code}, nil
}

func hasServer(code string) bool {
	for _, rel := range [][]string{{"textfold", "server.py"}, {"textfold", "__main__.py"}} {
		if info, err := os.Stat(filepath.Join(append([]string{code}, rel...)...)); err != nil || info.IsDir() {
			return false
		}
	}
	return true
}

func virtualenvPython(root string) string {
	for _, candidate := range []string{
		filepath.Join(root, "Scripts", "python.exe"),
		filepath.Join(root, "bin", "python3"),
		filepath.Join(root, "bin", "python"),
		filepath.Join(root, ".venv", "Scripts", "python.exe"),
		filepath.Join(root, ".venv", "bin", "python3"),
		filepath.Join(root, ".venv", "bin", "python"),
	} {
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
			return candidate
		}
	}
	return ""
}

func commonCheckout(root string) string {
	dotGit := filepath.Join(root, ".git")
	info, err := os.Stat(dotGit)
	if err != nil || info.IsDir() {
		return ""
	}
	data, err := os.ReadFile(dotGit)
	if err != nil {
		return ""
	}
	line := strings.TrimSpace(string(data))
	if !strings.HasPrefix(strings.ToLower(line), "gitdir:") {
		return ""
	}
	gitdir := strings.TrimSpace(line[len("gitdir:"):])
	if !filepath.IsAbs(gitdir) {
		gitdir = filepath.Join(root, gitdir)
	}
	commonDir, err := os.ReadFile(filepath.Join(gitdir, "commondir"))
	if err != nil {
		return ""
	}
	commonGit := strings.TrimSpace(string(commonDir))
	if !filepath.IsAbs(commonGit) {
		commonGit = filepath.Join(gitdir, commonGit)
	}
	return filepath.Dir(filepath.Clean(commonGit))
}

func samePath(a, b string) bool {
	aa, errA := filepath.Abs(a)
	bb, errB := filepath.Abs(b)
	if errA != nil || errB != nil {
		return a == b
	}
	if runtime.GOOS == "windows" {
		return strings.EqualFold(aa, bb)
	}
	return aa == bb
}
