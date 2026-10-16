"""The app's Python before it ships: TextFold's tests, three files read without a model, and the server answering
with them listed. The release build (.github/workflows/desktop.yml) runs it with the payload's own Python:

    payload\\python\\python.exe scripts\\smoke.py

A folder of its own stands in for the home and the data folder; nothing calls a model (TEXTFOLD_NO_MODELS)."""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

DESKTOP = Path(__file__).resolve().parent.parent
ROOT = DESKTOP.parent
CODE = DESKTOP / "payload" / "app" if (DESKTOP / "payload" / "app").is_dir() else ROOT
FILES = {
    "notes.md": ("# Folding a text\n\nA text is read at five levels. The first is a topic, the last every word.\n\n"
                 "## Why\n\nA reader decides where to go deeper.\n", "Folding a text"),
    "page.html": ("<html><head><title>A saved page</title></head><body><nav>menu</nav><article><h1>A saved page</h1>"
                  + "<p>This paragraph is the article itself, long enough for the extractor to keep it as the text. </p>" * 6
                  + "</article></body></html>", "A saved page"),
    "table.csv": ("city,people\nMunich,1500000\nBerlin,3700000\n", "CSV · table.csv"),
}


def step(name):
    print(f"\n== {name}", flush=True)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="textfold-smoke-"))
    env = {**os.environ, "HOME": str(tmp), "USERPROFILE": str(tmp), "TEXTFOLD_DATA": str(tmp / "data"),
           "TEXTFOLD_NO_MODELS": "1", "PYTHONNOUSERSITE": "1", "PYTHONIOENCODING": "utf-8"}
    py = [sys.executable, "-s"]
    try:
        step(f"the tests ({sys.executable})")
        subprocess.run(py + ["-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, env=env, check=True)

        for name, (text, want) in FILES.items():
            step(f"read without a model: {name}")
            f = tmp / name
            f.write_text(text, encoding="utf-8")
            r = subprocess.run(py + ["-m", "textfold", "get", str(f), "--no-generate", "--json"], cwd=CODE, env=env,
                               capture_output=True, text=True, encoding="utf-8", timeout=300)
            if r.returncode or want not in r.stdout:
                sys.exit(f"{name}: exit {r.returncode}, {want!r} {'found' if want in r.stdout else 'not found'}\n{r.stderr[-2000:]}")
            print("ok", len(json.loads(r.stdout)), "keys")

        step("the server")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        srv = subprocess.Popen(py + ["-u", "-m", "textfold", "serve", "--port", str(port)], cwd=CODE, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(120):
                try:
                    urllib.request.urlopen(f"{base}/api/models", timeout=2)
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                sys.exit("the server did not answer")
            page = urllib.request.urlopen(f"{base}/", timeout=10).read().decode()
            assert "TextFold" in page, "the landing"
            assert urllib.request.urlopen(f"{base}/static/reader.js", timeout=10).status == 200, "the reader's script"
            papers = json.loads(urllib.request.urlopen(f"{base}/api/papers", timeout=10).read())
            assert len(papers) == len(FILES), f"{len(papers)} documents listed, {len(FILES)} read"
            print("ok: landing, reader, the", len(papers), "documents listed")
        finally:
            srv.kill()
            srv.wait(10)
        print("\nsmoke ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
