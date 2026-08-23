from __future__ import annotations

import json
import logging
from typing import Any

import requests

from config import OMNIROUTE_API_KEY, OMNIROUTE_BASE_URL, OMNIROUTE_MODEL

logger = logging.getLogger("saba.omniroute")


def configured() -> bool:
    return bool(OMNIROUTE_BASE_URL and OMNIROUTE_MODEL)


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if OMNIROUTE_API_KEY:
        headers["Authorization"] = f"Bearer {OMNIROUTE_API_KEY}"
    return headers


def _tool_schema(tool_declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert the Gemini-style shared schema into OpenAI-compatible tools."""
    tools: list[dict[str, Any]] = []
    for item in tool_declarations:
        params = item.get("parameters") or {"type": "OBJECT", "properties": {}}

        def normalize(value: Any) -> Any:
            if isinstance(value, dict):
                out = {k: normalize(v) for k, v in value.items()}
                if out.get("type") in {"OBJECT", "STRING", "INTEGER", "NUMBER", "BOOLEAN", "ARRAY"}:
                    out["type"] = out["type"].lower()
                return out
            if isinstance(value, list):
                return [normalize(v) for v in value]
            return value

        tools.append({
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item.get("description", ""),
                "parameters": normalize(params),
            },
        })
    return tools


def chat(messages: list[dict[str, Any]], model: str | None = None, temperature: float = 0.2) -> str:
    if not configured():
        raise RuntimeError("OmniRoute is not configured. Set OMNIROUTE_MODEL (and OMNIROUTE_BASE_URL if needed).")
    response = requests.post(
        f"{OMNIROUTE_BASE_URL}/chat/completions",
        headers=_headers(),
        json={"model": model or OMNIROUTE_MODEL, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OmniRoute {response.status_code}: {response.text[:800]}")
    data: dict[str, Any] = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OmniRoute returned no choices.")
    return str((choices[0].get("message") or {}).get("content") or "").strip()


def chat_with_tools(
    messages: list[dict[str, Any]],
    tool_declarations: list[dict[str, Any]],
    tool_runner,
    *,
    user_id: int,
    role: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tool_turns: int = 6,
) -> str:
    """OpenAI-compatible tool-calling loop for local gateways such as OmniRoute."""
    if not configured():
        raise RuntimeError("OmniRoute is not configured.")

    tools = _tool_schema(tool_declarations)
    working = list(messages)

    for _ in range(max_tool_turns):
        response = requests.post(
            f"{OMNIROUTE_BASE_URL}/chat/completions",
            headers=_headers(),
            json={
                "model": model or OMNIROUTE_MODEL,
                "messages": working,
                "temperature": temperature,
                "tools": tools,
                "tool_choice": "auto",
            },
            timeout=90,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"OmniRoute {response.status_code}: {response.text[:1000]}")

        data: dict[str, Any] = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OmniRoute returned no choices.")

        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        working.append(message)

        if not tool_calls:
            return str(message.get("content") or "").strip() or "I'm here."

        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}

            result = tool_runner(name, args, user_id, role)
            working.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    return "I reached the tool-action safety limit before finishing. Please try the request again."
