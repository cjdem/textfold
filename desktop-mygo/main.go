package main

import (
	_ "embed"
	"fmt"
	"html"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"

	"github.com/chenxiachan/textfold/desktop-mygo/internal/bridge"
	"github.com/chenxiachan/textfold/desktop-mygo/internal/locator"
	textserver "github.com/chenxiachan/textfold/desktop-mygo/internal/server"
	"github.com/egoist/mygo"
)

const version = "0.10.7"

//go:embed preload.js
var preload string

var (
	stateMu sync.Mutex
	server  *textserver.Server
	win     *mygo.Window
)

func main() {
	app := mygo.App
	app.SetName("TextFold")
	app.SetVersion(version)

	if !app.RequestSingleInstanceLock() {
		return
	}
	app.OnSecondInstance(func(_ []string, _ string) {
		stateMu.Lock()
		current := win
		stateMu.Unlock()
		if current != nil {
			current.Restore()
			current.Focus()
		}
	})

	data, err := textfoldDataDir()
	if err != nil {
		log.Fatal(err)
	}
	downloads, _ := app.Path(mygo.PathDownloads)
	mygo.Bind(bridge.New(version, downloads))

	app.WhenReady(func() {
		app.SetMenu(mygo.NewMenu([]*mygo.MenuItem{
			{Role: mygo.RoleAppMenu},
			{Role: mygo.RoleEditMenu},
			{Role: mygo.RoleViewMenu},
			{Role: mygo.RoleWindowMenu},
			{Role: mygo.RoleHelp},
		}))
		go launch(data)
	})
	app.OnWillQuit(func(*mygo.QuitEvent) { stopServer() })

	if err := app.Run(); err != nil {
		log.Fatal(err)
	}
}

func launch(data string) {
	resources, err := mygo.App.Path(mygo.PathResources)
	if err != nil {
		showFailure(err)
		return
	}
	layout, err := resolveLayout(resources)
	if err != nil {
		showFailure(err)
		return
	}

	srv, err := textserver.Start(textserver.Config{
		Python: layout.Python,
		Code:   layout.Code,
		Data:   data,
		Log:    filepath.Join(data, "server.log"),
	})
	if err != nil {
		showFailure(err)
		return
	}
	stateMu.Lock()
	server = srv
	stateMu.Unlock()

	current := openWindow(srv.URL)
	stateMu.Lock()
	win = current
	stateMu.Unlock()
}

func openWindow(rawURL string) *mygo.Window {
	origin := originOf(rawURL)
	w := mygo.NewWindow(mygo.WindowOptions{
		Title:           "TextFold",
		URL:             rawURL,
		Width:           1360,
		Height:          900,
		MinWidth:        720,
		MinHeight:       520,
		AutoHideMenuBar: true,
		BackgroundColor: "light-dark(#FAF9F7, #1B1915)",
		StateKey:        "main",
		Page: mygo.PageOptions{
			PreloadScript: preload,
			TrustedOrigins: []string{
				origin,
			},
			UserAgentSuffix: "TextFold/" + version,
		},
	})
	w.Page().SetWindowOpenHandler(func(req mygo.WindowOpenRequest) *mygo.WindowOptions {
		if isExternalHTTP(req.URL) {
			go mygo.Shell.OpenExternal(req.URL)
		}
		return nil
	})
	w.Page().OnWillNavigate(func(e *mygo.NavigateEvent) {
		if sameOrigin(e.URL, rawURL) || e.URL == "about:blank" {
			return
		}
		e.PreventDefault()
		if isExternalHTTP(e.URL) {
			go mygo.Shell.OpenExternal(e.URL)
		}
	})
	return w
}

func showFailure(err error) {
	log.Print(err)
	page := failurePage(err)
	w := mygo.NewWindow(mygo.WindowOptions{
		Title:           "TextFold",
		Width:           900,
		Height:          520,
		MinWidth:        600,
		MinHeight:       360,
		BackgroundColor: "light-dark(#FAF9F7, #1B1915)",
	})
	w.Page().LoadHTML(page, "")
	stateMu.Lock()
	win = w
	stateMu.Unlock()
}

func failurePage(err error) string {
	logPath := "server.log"
	if data, dataErr := textfoldDataDir(); dataErr == nil {
		logPath = filepath.Join(data, "server.log")
	}
	return fmt.Sprintf(`<!doctype html><meta charset="utf-8">
<title>TextFold could not start</title>
<style>
:root{color-scheme:light dark;font:16px/1.55 "Segoe UI",sans-serif}
body{margin:0;background:#faf9f7;color:#24211d;padding:48px}
@media(prefers-color-scheme:dark){body{background:#1b1915;color:#f3efe8}}
pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:18px;border-radius:12px;background:color-mix(in srgb,currentColor 7%%,transparent)}
code{font:14px/1.5 ui-monospace,monospace}
</style>
<h1>TextFold could not start its Python server</h1>
<p>%s</p>
<p>The server log is:</p><pre><code>%s</code></pre>`,
		html.EscapeString(err.Error()), html.EscapeString(logPath))
}

func stopServer() {
	stateMu.Lock()
	srv := server
	server = nil
	stateMu.Unlock()
	if srv != nil {
		srv.Stop()
	}
}

func resolveLayout(resources string) (locator.Layout, error) {
	if !mygo.IsDev() {
		return locator.Packaged(resources)
	}
	return locator.Development(sourceRoot())
}

func sourceRoot() string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return ""
	}
	return filepath.Dir(filepath.Dir(file))
}

func originOf(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return ""
	}
	return u.Scheme + "://" + u.Host
}

func sameOrigin(a, b string) bool {
	ua, errA := url.Parse(a)
	ub, errB := url.Parse(b)
	return errA == nil && errB == nil && ua.Scheme == ub.Scheme && ua.Host == ub.Host
}

func isExternalHTTP(rawURL string) bool {
	u, err := url.Parse(rawURL)
	return err == nil && (u.Scheme == "http" || u.Scheme == "https") && u.Host != ""
}

func textfoldDataDir() (string, error) {
	if named := strings.TrimSpace(os.Getenv("TEXTFOLD_DATA")); named != "" {
		return filepath.Abs(named)
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	if runtime.GOOS == "windows" {
		base := os.Getenv("LOCALAPPDATA")
		if base == "" {
			base = filepath.Join(home, "AppData", "Local")
		}
		return filepath.Join(base, "TextFold"), nil
	}
	base, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(base, "TextFold"), nil
}
