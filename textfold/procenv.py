"""Environment and text encoding for the retained ChatGPT bridge child process."""
import glob
import os
import re
import shutil
from pathlib import Path

HOME = Path.home()


def search_dirs():
    """PATH and common Windows/node-manager locations, newest version-manager installs first."""
    dirs = os.environ.get("PATH", "").split(os.pathsep)
    dirs += [os.path.join(os.environ.get("APPDATA") or "~/AppData/Roaming", "npm"), "~/.local/bin", "~/.bun/bin",
             "~/scoop/shims", os.path.join(os.environ.get("ProgramFiles") or "C:/Program Files", "nodejs")]
    managers = sorted(glob.glob(str(HOME / ".nvm/versions/node/*/bin")), key=_version_key, reverse=True)
    for pattern in ["~/.fnm/node-versions/*/installation/bin", "~/.volta/bin", "~/n/bin", "~/.nodenv/shims",
                    "~/.asdf/shims", "~/.local/share/mise/shims", "~/.proto/bin", "~/.local/share/pnpm", "~/.yarn/bin",
                    "~/.config/yarn/global/node_modules/.bin", "~/.deno/bin", "~/.cargo/bin", "~/bin"]:
        managers += sorted(glob.glob(os.path.expanduser(pattern)), key=_version_key, reverse=True)
    out, seen = [], set()
    for directory in dirs + managers:
        directory = os.path.expanduser(directory)
        if directory and directory not in seen and os.path.isdir(directory):
            seen.add(directory)
            out.append(directory)
    return out


def _version_key(path):
    return [int(part) if part.isdigit() else 0 for part in re.findall(r"\d+", path)]


def child_env():
    """Give bridge tools a PATH that can find node and npx on Windows."""
    return {**os.environ, "PATH": os.pathsep.join(search_dirs())}


TEXT = {"encoding": "utf-8", "errors": "replace"}


def which(name):
    return shutil.which(name, path=child_env()["PATH"])
