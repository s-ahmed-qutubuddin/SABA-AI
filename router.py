from __future__ import annotations

import os
import re
import subprocess
import sys
from dateparser.search import search_dates

from config import SABA_USER_ID
from family_profiles import list_profiles, relevant_context
from identity import identify_family_member
from memory import memories, notes, tasks, preferences, search_memories, get_preferences
from tools.system import (
    open_app, open_url, set_volume, get_volume, media_control,
    battery_status, system_info, clipboard_read, clipboard_write, open_project_folder, list_project_files,
)
from tools.weather import get_weather
from home_tools import home_list_devices, home_get_status, home_get_capabilities, home_control, home_find, home_get_energy, home_get_energy_usage, home_estimate_cost, home_estimate_ac_cost
from tools.news import get_news
from tools.web import search_web
from tools.calculator import calculate
from tools.music import open_music


def parse_task(text):
    clean = text.strip()
    found = search_dates(clean, settings={"PREFER_DATES_FROM": "future"})
    if not found:
        return clean, None
    phrase, dt = found[-1]
    due_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    title = clean.replace(phrase, "").strip(" ,.-")
    return title or clean, due_date


def route_command(text, emit=None, user_id=SABA_USER_ID, role="primary_user", owner_user_id=None):
    emit = emit or (lambda *_: None)
    original = text.strip()
    low = original.lower()

    if low.startswith("remember"):
        memory = original[len("remember"):].strip()
        if not memory:
            return {"handled": True, "speak": "What would you like me to remember?"}
        memories(user_id, memory, "general")
        emit("memory_saved", {"text": memory})
        return {"handled": True, "speak": "I'll remember that."}

    if low.startswith(("what do you remember", "recall", "remembered")):
        query = original.replace("what do you remember", "").replace("recall", "").strip() or "general"
        rows = search_memories(user_id, query, 6)
        if not rows:
            return {"handled": True, "speak": "I don't have a matching stored memory yet."}
        answer = "; ".join(row["memory"] for row in rows[:4])
        emit("memory_retrieved", {"results": rows})
        return {"handled": True, "speak": answer}

    identify = re.fullmatch(r"(?:i am|i'm|this is|switch to|talk as)\s+(.+)", original, flags=re.IGNORECASE)
    if identify:
        try:
            identity = identify_family_member(identify.group(1), user_id)
            emit("identity_switched", {"user_id": identity.user_id, "label": identity.profile_label})
            return {"handled": True, "speak": f"Understood. I’ll use the {identity.profile_label} profile from now on."}
        except Exception:
            pass

    if low.startswith("note"):
        content = original[len("note"):].strip()
        if not content:
            return {"handled": True, "speak": "What should I put in the note?"}
        notes(user_id, "Note", content)
        emit("note_saved", {"text": content})
        return {"handled": True, "speak": "Note saved."}

    if low.startswith("task"):
        payload = original[len("task"):].strip()
        if not payload:
            return {"handled": True, "speak": "What task should I create?"}
        title, due = parse_task(payload)
        tasks(user_id, title, payload, due)
        emit("task_saved", {"text": title, "due_date": due})
        return {"handled": True, "speak": "Task saved."}

    if low.startswith("preference"):
        payload = original[len("preference"):].strip()
        if ":" not in payload:
            return {"handled": True, "speak": "Give me a preference like theme: dark."}
        key, value = payload.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            return {"handled": True, "speak": "I need both a preference key and a value."}
        preferences(user_id, key, value)
        emit("preference_saved", {"key": key, "value": value})
        return {"handled": True, "speak": "Preference updated."}

    app_match = re.fullmatch(r"open (safari|chrome|google chrome|vs code|visual studio code|terminal|finder|music|notes|spotify)", low)
    if app_match:
        raw = app_match.group(1)
        app = {"safari":"Safari","chrome":"Google Chrome","google chrome":"Google Chrome","vs code":"Visual Studio Code","visual studio code":"Visual Studio Code","terminal":"Terminal","finder":"Finder","music":"Music","notes":"Notes","spotify":"Spotify"}[raw]
        result = open_app(app); emit("system_action", result)
        return {"handled": True, "speak": f"Opening {app}."}

    volume_match = re.fullmatch(r"(?:set )?volume(?: to)?\s+(\d{1,3})%?", low)
    if volume_match:
        result = set_volume(int(volume_match.group(1))); emit("system_action", result)
        return {"handled": True, "speak": f"Volume set to {result['volume']} percent."}

    if low in {"what is my volume", "current volume", "volume"}:
        result = get_volume(); emit("system_action", result)
        return {"handled": True, "speak": f"The output volume is {result['volume']} percent."}

    if low in {"yt", "youtube", "open youtube", "go to youtube", "open yt"}:
        result = open_url("https://www.youtube.com"); emit("system_action", result)
        return {"handled": True, "speak": "Opening YouTube."}

    if low in {"google", "open google", "go to google"}:
        result = open_url("https://www.google.com"); emit("system_action", result)
        return {"handled": True, "speak": "Opening Google."}

    if low in {"play music", "open music"}:
        result = open_music(); emit("system_action", result)
        return {"handled": True, "speak": "Opening Music."}

    url_match = re.fullmatch(r"(?:open|go to)\s+(https?://\S+)", original, flags=re.IGNORECASE)
    if url_match:
        result = open_url(url_match.group(1)); emit("system_action", result)
        return {"handled": True, "speak": "Opening website."}

    if low in {"battery", "battery status", "how much battery"}:
        result = battery_status(); emit("system_action", result)
        return {"handled": True, "speak": result.get("summary", "Battery status retrieved.")}

    if low in {"system info", "computer info", "mac info"}:
        result = system_info(); emit("system_action", result)
        return {"handled": True, "speak": result.get("summary", "System information retrieved.")}

    calc_match = re.fullmatch(r"(?:calculate|what is)\s+(.+)", original, flags=re.IGNORECASE)
    if calc_match:
        try:
            value = calculate(calc_match.group(1))
            return {"handled": True, "speak": str(value)}
        except Exception:
            pass

    weather_match = re.fullmatch(r"weather(?: in)?\s+(.+)", original, flags=re.IGNORECASE)
    if weather_match:
        data = get_weather(weather_match.group(1)); emit("weather_result", data)
        return {"handled": True, "speak": f"In {data['city']}, it's {data['temperature_c']} degrees Celsius, with wind at {data['wind_kmh']} kilometers per hour."}

    search_match = re.fullmatch(r"(?:search|look up)\s+(.+)", original, flags=re.IGNORECASE)
    if search_match:
        results = search_web(search_match.group(1)); emit("web_result", {"results": results})
        return {"handled": True, "speak": results[0]["title"] if results else "I found no results."}

    news_match = re.fullmatch(r"news(?: about)?\s+(.+)", original, flags=re.IGNORECASE)
    if news_match:
        results = get_news(news_match.group(1)); emit("news_result", {"results": results})
        return {"handled": True, "speak": results[0]["title"] if results else "I found no news results."}

    return {"handled": False}


def _dev_tool_allowed(role: str) -> bool:
    return role in {"creator", "owner"}




def activate_developer_mode(role: str):
    """Creator-only developer-mode activation. Opens the primary dev tools on macOS."""
    if not _dev_tool_allowed(role):
        return {"ok": False, "error": "Creator-only developer mode."}
    opened = []
    errors = []
    for app in ("Visual Studio Code", "Terminal", "Notes"):
        try:
            result = open_app(app)
            opened.append(app)
        except Exception as exc:
            errors.append(f"{app}: {exc}")
    try:
        project = open_project_folder()
        opened.append("Jamal Family Assistant project")
    except Exception as exc:
        errors.append(f"Project: {exc}")
    return {
        "ok": not errors,
        "label": "Developer mode active",
        "message": "Systems are online, Boss. Ready to build.",
        "opened": opened,
        "errors": errors,
        "developer_mode": True,
    }

def developer_diagnostics(role: str):
    if not _dev_tool_allowed(role):
        return {"ok": False, "error": "Creator-only developer tool."}
    return {
        "ok": True,
        "app": os.getenv("APP_NAME", "JAMAL-FAMILY-ASSISTANT"),
        "python": subprocess.check_output([sys.executable, "--version"], text=True).strip(),
        "cwd": os.getcwd(),
        "pid": os.getpid(),
    }


def open_project(role: str):
    if not _dev_tool_allowed(role):
        return {"ok": False, "error": "Creator-only developer tool."}
    return open_project_folder()


def list_project(role: str):
    if not _dev_tool_allowed(role):
        return {"ok": False, "error": "Creator-only developer tool."}
    return list_project_files()


def git_status(role: str):
    if not _dev_tool_allowed(role):
        return {"ok": False, "error": "Creator-only developer tool."}
    try:
        result = subprocess.run(["git", "status", "--short", "--branch"], text=True, capture_output=True, timeout=5, check=False)
        return {"ok": result.returncode == 0, "output": result.stdout[:12000], "error": result.stderr[:2000]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def execute_named_tool(name, args, user_id=SABA_USER_ID, role="primary_user", owner_user_id=None):
    if name == "activate_developer_mode":
        return activate_developer_mode(role)
    if name == "remember":
        memory_id = memories(user_id, args["memory"], args.get("category", "general"))
        return {"ok": True, "memory_id": memory_id, "stored": args["memory"]}
    if name == "recall_memory":
        rows = search_memories(user_id, args.get("query", ""), args.get("limit", 8))
        return {"ok": True, "memories": [{"memory_id": r.get("memory_id"), "memory": r.get("memory"), "category": r.get("category"), "importance": r.get("importance")} for r in rows]}
    if name == "family_context":
        q = args.get("query", "")
        family_owner = owner_user_id or user_id
        return {"ok": True, "context": relevant_context(q, args.get("limit", 10), family_owner), "profiles": list_profiles(family_owner)[:10]}
    if name == "identify_family_member":
        identity = identify_family_member(args.get("name", ""), owner_user_id or user_id)
        return {"ok": True, "user_id": identity.user_id, "role": identity.role, "profile_label": identity.profile_label}
    if name == "create_note":
        note_id = notes(user_id, args["title"], args["content"])
        return {"ok": True, "note_id": note_id}
    if name == "create_task":
        title, due = parse_task(args.get("title", ""))
        due = args.get("due_date") or due
        task_id = tasks(user_id, title, args.get("description"), due)
        return {"ok": True, "task_id": task_id, "due_date": due}
    if name == "set_preference":
        preferences(user_id, args["key"], args["value"])
        return {"ok": True}
    if name == "open_allowed_app":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local OS app control requires the owner account and a paired local device agent."}
        return open_app(args["name"])
    if name == "set_volume":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local OS control requires the owner account and a paired local device agent."}
        return set_volume(args["percent"])
    if name == "get_volume":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local OS control requires the owner account and a paired local device agent."}
        return get_volume()
    if name == "media_control":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local device control requires the owner account and a paired local device agent."}
        return media_control(args["action"])
    if name == "battery_status":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local device control requires the owner account and a paired local device agent."}
        return battery_status()
    if name == "system_info":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local device control requires the owner account and a paired local device agent."}
        return system_info()
    if name == "clipboard_read":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local device control requires the owner account and a paired local device agent."}
        return clipboard_read()
    if name == "clipboard_write":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local device control requires the owner account and a paired local device agent."}
        return clipboard_write(args["text"])
    if name == "open_url":
        if role not in {"creator", "owner"}:
            return {"ok": False, "error": "Local device control requires the owner account and a paired local device agent."}
        return open_url(args["url"])
    if name == "search_web":
        return {"ok": True, "results": search_web(args["query"])}
    if name == "get_weather":
        return {"ok": True, "weather": get_weather(args["city"])}
    if name == "get_news":
        return {"ok": True, "news": get_news(args["query"])}
    if name == "calculate":
        return {"ok": True, "result": calculate(args["expression"])}
    if name == "developer_diagnostics":
        return developer_diagnostics(role)
    if name == "open_project":
        return open_project(role)
    if name == "list_project":
        return list_project(role)
    if name == "git_status":
        return git_status(role)
    if name == "home_list_devices":
        return home_list_devices()

    if name == "home_find_device":
        return home_find(
            args.get("query")
            or args.get("device_name")
            or args.get("room")
            or ""
        )

    if name == "home_get_status":
        return home_get_status(
            args["provider"],
            args.get("device_id", ""),
            args.get("query")
            or args.get("device_name")
            or args.get("room"),
        )

    if name == "home_get_capabilities":
        return home_get_capabilities(
            args["provider"],
            args.get("device_id", ""),
            args.get("query")
            or args.get("device_name")
            or args.get("room"),
        )

    if name == "home_control_device":
        command = dict(args.get("command") or {})

        # Carry semantic device information into home_tools even when the
        # model does not put it inside the nested command object.
        if not command.get("device_query"):
            command["device_query"] = (
                args.get("query")
                or args.get("device_name")
                or args.get("room")
            )

        # Normalize alternate argument field names used by different models.
        if "arguments" not in command and "args" not in command:
            if "arguments" in args:
                command["arguments"] = args["arguments"]
            elif "args" in args:
                command["args"] = args["args"]

        for key in (
            "value",
            "mode",
            "fan_mode",
            "temperature",
            "direction",
            "level",
        ):
            if key in args and key not in command:
                command[key] = args[key]

        return home_control(
            args["provider"],
            args.get("device_id", ""),
            command,
        )

    if name == "home_get_energy":
        return home_get_energy(
            args["provider"],
            args.get("device_id", ""),
            args.get("query")
            or args.get("device_name")
            or args.get("room"),
        )

    if name == "home_get_energy_usage":
        return home_get_energy_usage(
            args["provider"],
            args.get("device_id", ""),
            args.get("energy_property", "total_energy"),
            args.get("period", "DAY"),
            args.get("start_date"),
            args.get("end_date"),
        )
    if name == "home_estimate_cost":
        return home_estimate_cost(args["kwh"], args.get("tariff_per_kwh"))
    if name == "home_estimate_ac_cost":
        return home_estimate_ac_cost(args["ac_kwh"], args["household_kwh"])
    return {"ok": False, "error": f"Unknown tool: {name}"}
