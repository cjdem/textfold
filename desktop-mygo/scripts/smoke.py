"""Start the Python app from a prepared payload and wait for /api/models.

Run after desktop-mygo/scripts/prepare-payload.mjs:
    python desktop-mygo/scripts/smoke.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PAYLOAD = HERE / "resources" / "payload"
PYTHON = PAYLOAD / "python" / "python.exe"
APP = PAYLOAD / "app"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    if not PYTHON.is_file() or not (APP / "textfold").is_dir():
        raise SystemExit("prepare desktop-mygo/resources/payload first")
    with tempfile.TemporaryDirectory(prefix="textfold-mygo-") as data:
        port = free_port()
        env = {
            **os.environ,
            "TEXTFOLD_DATA": data,
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
        }
        log = Path(data) / "server.log"
        with log.open("wb") as out:
            proc = subprocess.Popen(
                [str(PYTHON), "-s", "-u", "-m", "textfold", "serve", "--port", str(port)],
                cwd=APP,
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        try:
            url = f"http://127.0.0.1:{port}/api/models"
            deadline = time.time() + 90
            while time.time() < deadline:
                if proc.poll() is not None:
                    raise SystemExit(f"server exited with {proc.returncode}; see {log}\n{log.read_text('utf-8', 'replace')}")
                try:
                    with urllib.request.urlopen(url, timeout=3) as reply:
                        payload = json.load(reply)
                        if reply.status == 200:
                            print(json.dumps({"ok": True, "port": port, "models": len(payload.get("models", []))}))
                            return
                except OSError:
                    time.sleep(0.25)
            raise SystemExit(f"server did not answer; see {log}\n{log.read_text('utf-8', 'replace')}")
        finally:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True) if os.name == "nt" else proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
