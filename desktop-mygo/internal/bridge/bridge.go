package bridge

import (
	"context"
	"errors"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

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

// UpdateState is what the page shows of the app's update: the kinds of
// desktop/main.js, kept so the reader's update toast does not change with
// the shell.
type UpdateState struct {
	Kind      string `json:"kind"`
	Version   string `json:"version,omitempty"`
	Percent   int    `json:"percent,omitempty"`
	From      string `json:"from,omitempty"`
	Notes     string `json:"notes,omitempty"`
	Dismissed bool   `json:"dismissed,omitempty"`
	Transient bool   `json:"transient,omitempty"`
}

// UpdateEvent sends a state to the page's update toast. MyGo queues events
// sent before the page is ready.
var UpdateEvent = mygo.NewEvent[UpdateState]("update")

// Desktop is bound to the page as window.desktop through preload.js.
type Desktop struct {
	version   string
	downloads string
	data      string
	repo      string
	stop      func()

	mu        sync.Mutex
	state     *UpdateState
	pending   *mygo.Update
	dismissed bool
}

func New(version, downloads, data, repo string, stop func()) *Desktop {
	return &Desktop{version: version, downloads: downloads, data: data, repo: repo, stop: stop}
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

// UpdateState returns the state the page shows, or nil. A dismissed state
// stays dismissed until a new phase of the update, or a check by hand.
func (d *Desktop) UpdateState() *UpdateState {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.state == nil {
		return nil
	}
	s := *d.state
	s.Dismissed = d.dismissed
	return &s
}

// CheckForUpdates asks the signed feed for a newer version. It is the
// answer the Settings dialog shows, and the startup and periodic check.
func (d *Desktop) CheckForUpdates(ctx context.Context) UpdateState {
	if mygo.IsDev() {
		return UpdateState{Kind: "dev", Version: d.version}
	}
	if !mygo.Updater.Enabled() {
		return UpdateState{Kind: "disabled", Version: d.version}
	}
	d.mu.Lock()
	if d.state != nil && (d.state.Kind == "downloading" || d.state.Kind == "ready") {
		s := *d.state
		s.Dismissed = d.dismissed
		d.mu.Unlock()
		return s
	}
	d.mu.Unlock()

	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	up, err := mygo.Updater.Check(ctx)
	if err != nil {
		return UpdateState{Kind: "check-failed"}
	}
	if up == nil {
		return UpdateState{Kind: "latest", Version: d.version}
	}
	d.mu.Lock()
	d.pending = up
	d.mu.Unlock()
	s := UpdateState{Kind: "available", Version: up.Version}
	d.show(s)
	return s
}

// CheckByHand is the menu's check: any answer, including "up to date", is
// shown for a moment; a newer version is shown and kept as the toast does.
func (d *Desktop) CheckByHand(ctx context.Context) UpdateState {
	d.mu.Lock()
	d.dismissed = false
	d.mu.Unlock()
	s := d.CheckForUpdates(ctx)
	switch s.Kind {
	case "available", "downloading", "ready", "updated":
	default:
		s.Transient = true
		_ = UpdateEvent.Broadcast(s)
	}
	return s
}

// DownloadUpdate downloads the newer version, checks its signature and
// replaces the app on disk. The new version runs after InstallUpdate.
func (d *Desktop) DownloadUpdate(ctx context.Context) error {
	d.mu.Lock()
	if d.state != nil && d.state.Kind == "downloading" {
		d.mu.Unlock()
		return nil
	}
	up := d.pending
	version := ""
	if d.state != nil {
		version = d.state.Version
	}
	d.mu.Unlock()
	if up == nil {
		s := d.CheckForUpdates(ctx)
		if s.Kind != "available" {
			return nil
		}
		d.mu.Lock()
		up = d.pending
		version = s.Version
		d.mu.Unlock()
	}
	if up == nil {
		return errors.New("no update is available")
	}

	d.show(UpdateState{Kind: "downloading", Version: version})
	last := -1
	// A download is the app's, not the page's: moving to another page in
	// the reader must not cancel it. Closing the app still ends it.
	err := up.Install(context.WithoutCancel(ctx), func(downloaded, total int64) {
		percent := 0
		if total > 0 {
			percent = int(downloaded * 100 / total)
			if percent > 100 {
				percent = 100
			}
		}
		if percent == last {
			return
		}
		last = percent
		d.show(UpdateState{Kind: "downloading", Version: version, Percent: percent})
	})
	d.mu.Lock()
	d.pending = nil
	d.mu.Unlock()
	if err != nil {
		d.show(UpdateState{Kind: "failed", Version: version})
		return err
	}
	d.show(UpdateState{Kind: "ready", Version: version})
	return nil
}

// InstallUpdate restarts the app into the downloaded version. The Python
// server goes first: Windows cannot replace a running process's files
// cleanly, and the new version starts its own.
func (d *Desktop) InstallUpdate() {
	d.mu.Lock()
	ready := d.state != nil && d.state.Kind == "ready"
	d.mu.Unlock()
	if !ready {
		return
	}
	if d.stop != nil {
		d.stop()
	}
	mygo.App.Relaunch()
}

func (d *Desktop) DismissUpdate() {
	d.mu.Lock()
	d.dismissed = true
	d.mu.Unlock()
}

// NoteVersion records the version this launch runs. The first launch after
// an update says so, with a link to what is new; a first install says
// nothing.
func (d *Desktop) NoteVersion() {
	if d.data == "" {
		return
	}
	file := filepath.Join(d.data, "version")
	previous := ""
	if b, err := os.ReadFile(file); err == nil {
		previous = strings.TrimSpace(string(b))
	}
	if err := os.MkdirAll(d.data, 0o755); err != nil {
		return
	}
	_ = os.WriteFile(file, []byte(d.version), 0o644)
	if previous == "" || previous == d.version {
		return
	}
	d.show(UpdateState{Kind: "updated", Version: d.version, From: previous, Notes: d.notesFor(d.version)})
}

func (d *Desktop) notesFor(version string) string {
	if d.repo == "" {
		return ""
	}
	return strings.TrimSuffix(d.repo, "/") + "/releases/tag/v" + version
}

func (d *Desktop) show(s UpdateState) {
	d.mu.Lock()
	if d.state == nil || d.state.Kind != s.Kind {
		d.dismissed = false
	}
	d.state = &s
	dismissed := d.dismissed
	d.mu.Unlock()
	if dismissed {
		s.Dismissed = true
	}
	_ = UpdateEvent.Broadcast(s)
}

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
