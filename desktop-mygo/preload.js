(() => {
  const call = (method, ...args) => window.mygo.call(method, ...args);

  Object.defineProperty(window, "desktop", {
    configurable: false,
    enumerable: true,
    value: Object.freeze({
      openExternal: (url) => call("Desktop.OpenExternal", String(url)),
      saveFile: (name, data) => call("Desktop.SaveFile", String(name), String(data)),
      version: () => call("Desktop.Version"),
      updateState: () => call("Desktop.UpdateState"),
      checkForUpdates: () => call("Desktop.CheckForUpdates"),
      downloadUpdate: () => call("Desktop.DownloadUpdate"),
      installUpdate: () => call("Desktop.InstallUpdate"),
      dismissUpdate: () => call("Desktop.DismissUpdate"),
      onUpdate: (listener) => (typeof listener === "function" ? window.mygo.on("update", listener) : () => {}),
    }),
  });
})();
