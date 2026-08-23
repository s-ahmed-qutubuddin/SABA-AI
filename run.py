#!/usr/bin/env python3
"""Single-command SABA launcher for macOS/Linux development."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / "bin" / "python"
PIP = VENV / "bin" / "pip"
FRONTEND = ROOT / "frontend"
NPM = shutil.which("npm") or "npm"

processes: list[subprocess.Popen] = []


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_env() -> None:
    if not VENV.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    run([str(PIP), "install", "-q", "-r", "requirements.txt"])
    if not (ROOT / ".env").exists():
        shutil.copy2(ROOT / ".env.example", ROOT / ".env")
        raise SystemExit("Created .env from .env.example. Add your local secrets/config, then run python run.py again.")
    if not (FRONTEND / "node_modules").exists():
        run([NPM, "install"], FRONTEND)


def wait_http(url: str, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if 200 <= r.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Service did not become ready: {url}")


def stop_all(*_args) -> None:
    for proc in reversed(processes):
        if proc.poll() is None:
            proc.terminate()
    for proc in reversed(processes):
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def main() -> None:
    ensure_env()
    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    backend_log = open(ROOT / "saba_backend.log", "a")
    backend = subprocess.Popen([
        str(PYTHON), "-m", "uvicorn", "backend.api:app", "--host", "127.0.0.1", "--port", "8000"
    ], cwd=ROOT, stdout=backend_log, stderr=subprocess.STDOUT)
    processes.append(backend)
    wait_http("http://127.0.0.1:8000/health")

    env = os.environ.copy()
    frontend = subprocess.Popen([NPM, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], cwd=FRONTEND, env=env)
    processes.append(frontend)
    wait_http("http://127.0.0.1:5173")

    print("SABA is running: http://127.0.0.1:5173")
    print("Backend health: http://127.0.0.1:8000/health")
    print("Press Ctrl+C to stop all SABA services.")
    if shutil.which("open"):
        subprocess.Popen(["open", "http://127.0.0.1:5173"])
    try:
        while True:
            if backend.poll() is not None:
                raise RuntimeError("SABA backend exited. Check saba_backend.log.")
            if frontend.poll() is not None:
                raise RuntimeError("SABA frontend exited.")
            time.sleep(1)
    finally:
        stop_all()


if __name__ == "__main__":
    main()
