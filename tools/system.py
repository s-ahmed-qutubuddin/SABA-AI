from __future__ import annotations

import subprocess
from pathlib import Path
from config import SABA_PROJECT_ROOT

APP_ALLOWLIST = {
    "Safari": "/Applications/Safari.app",
    "Google Chrome": "/Applications/Google Chrome.app",
    "Visual Studio Code": "/Applications/Visual Studio Code.app",
    "Terminal": "/System/Applications/Utilities/Terminal.app",
    "Finder": "/System/Library/CoreServices/Finder.app",
    "Music": "/System/Applications/Music.app",
    "Notes": "/System/Applications/Notes.app",
    "Spotify": "/Applications/Spotify.app",
}
MEDIA_ACTIONS = {"play_pause", "next", "previous", "stop"}


def _run_open_app(name: str) -> dict:
    path = APP_ALLOWLIST.get(name)
    if not path or not Path(path).exists():
        raise ValueError("Application not allowed or not installed")
    subprocess.Popen(["open", "-a", name])
    return {"label": f"Opening {name}", "app": name}


def open_app(name: str):
    return _run_open_app(name)


def open_url(url: str):
    url = url.strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError("Only http/https URLs are allowed")
    if any(token in url for token in [";", "|", "`", "$("]):
        raise ValueError("Unsafe URL")
    subprocess.Popen(["open", url])
    return {"label": "Opening website", "url": url}


def set_volume(percent: int):
    p = max(0, min(100, int(percent)))
    subprocess.run(["osascript", "-e", f"set volume output volume {p}"], check=True)
    return {"label": f"Volume set to {p}%", "volume": p}


def get_volume():
    raw = subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"], text=True).strip()
    return {"label": "Current volume", "volume": int(raw)}


def media_control(action: str):
    if action not in MEDIA_ACTIONS:
        raise ValueError("Unsupported media action")
    scripts = {
        "play_pause": 'tell application "Music" to playpause',
        "next": 'tell application "Music" to next track',
        "previous": 'tell application "Music" to previous track',
        "stop": 'tell application "Music" to stop',
    }
    subprocess.run(["osascript", "-e", scripts[action]], check=True)
    return {"label": f"Media {action.replace('_', ' ')}", "action": action}


def battery_status():
    text = subprocess.check_output(["pmset", "-g", "batt"], text=True).strip()
    return {"label": "Battery status", "summary": text.splitlines()[-1] if text else text}


def system_info():
    hostname = subprocess.check_output(["scutil", "--get", "ComputerName"], text=True).strip()
    macos = subprocess.check_output(["sw_vers", "-productVersion"], text=True).strip()
    return {"label": "System information", "computer": hostname, "macos": macos, "summary": f"{hostname}, macOS {macos}."}


def clipboard_read():
    text = subprocess.check_output(["pbpaste"], text=True)
    return {"label": "Clipboard read", "text": text[:10000]}


def clipboard_write(text: str):
    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
    proc.communicate(text[:10000])
    if proc.returncode != 0:
        raise RuntimeError("Clipboard write failed")
    return {"label": "Clipboard updated", "length": len(text[:10000])}


def open_project_folder():
    path = Path(SABA_PROJECT_ROOT).resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError("Project folder is unavailable")
    subprocess.Popen(["open", str(path)])
    return {"label": "Opening Saba project", "path": str(path)}


def list_project_files(limit: int = 80):
    path = Path(SABA_PROJECT_ROOT).resolve()
    if not path.exists():
        raise ValueError("Project folder is unavailable")
    limit = max(1, min(200, int(limit)))
    items = []
    for child in sorted(path.rglob("*")):
        if child.is_dir() and any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in child.parts):
            continue
        if child.is_file():
            items.append(str(child.relative_to(path)))
            if len(items) >= limit:
                break
    return {"label": "Project files", "files": items}
