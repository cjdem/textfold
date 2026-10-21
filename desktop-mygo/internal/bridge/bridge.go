package bridge

import (
	"context"
	"errors"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/egoist/mygo"
)

type saveKind struct {
	label string
}

var saveKinds = map[string]saveKind{
	"html": {label: "Web page"},
	"md":   {label: "Markdown"},
	"json": {label: "JSON"},
}

// UpdateState is the subset of the old Electron update contract the page reads.
type UpdateState struct {
	Kind    string `json:"kind"`
	Version string `json:"version,omitempty"`
}

// Desktop is bound to the page as window.desktop through preload.js.
type Desktop struct {
	version   string
	downloads string
}

func New(version, downloads string) *Desktop {
	return &Desktop{version: version, downloads: downloads}
}

func (d *Desktop) OpenExternal(rawURL string) error {
	if !externalURL(rawURL) {
		return errors.New("only http and https links can open in the browser")
	}
	return mygo.Shell.OpenExternal(rawURL)
}

func (d *Desktop) SaveFile(ctx context.Context, name, data string) (string, error) {
	base, kind, err := saveName(name)
	if err != nil {
		return "", err
	}
	defaultPath := base
	if d.downloads != "" {
		defaultPath = filepath.Join(d.downloads, base)
	}
	path, err := mygo.Dialog.Save(mygo.SaveDialogOptions{
		Parent:      mygo.CallerWindow(ctx),
		DefaultPath: defaultPath,
		Filters:     []mygo.FileFilter{{Name: kind.label, Extensions: []string{strings.TrimPrefix(filepath.Ext(base), ".")}}},
	})
	if err != nil || path == "" {
		return "", err
	}
	if err := os.WriteFile(path, []byte(data), 0o644); err != nil {
		return "", err
	}
	return path, nil
}

func (d *Desktop) Version() string { return d.version }

func (d *Desktop) UpdateState() *UpdateState { return nil }

func (d *Desktop) CheckForUpdates(ctx context.Context) UpdateState {
	if !mygo.Updater.Enabled() {
		if mygo.IsDev() {
			return UpdateState{Kind: "dev"}
		}
		return UpdateState{Kind: "disabled", Version: d.version}
	}
	up, err := mygo.Updater.Check(ctx)
	if err != nil {
		return UpdateState{Kind: "check-failed"}
	}
	if up == nil {
		return UpdateState{Kind: "latest", Version: d.version}
	}
	return UpdateState{Kind: "available", Version: up.Version}
}

func (*Desktop) DownloadUpdate() {}
func (*Desktop) InstallUpdate()  {}
func (*Desktop) DismissUpdate()  {}

func externalURL(rawURL string) bool {
	u, err := url.Parse(rawURL)
	return err == nil && u.Host != "" && (u.Scheme == "http" || u.Scheme == "https")
}

func saveName(name string) (string, saveKind, error) {
	base := filepath.Base(strings.TrimSpace(name))
	ext := strings.ToLower(strings.TrimPrefix(filepath.Ext(base), "."))
	kind, ok := saveKinds[ext]
	stem := strings.TrimSuffix(base, filepath.Ext(base))
	if base == "." || base == "" || stem == "" || !ok {
		return "", saveKind{}, errors.New("only .html, .md and .json files can be saved")
	}
	return base, kind, nil
}
