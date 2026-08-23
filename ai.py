from __future__ import annotations

import logging

from fastapi.encoders import jsonable_encoder
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, SABA_USER_ID, ASSISTANT_NAME, APP_NAME, OMNIROUTE_MODEL
from family_profiles import relevant_context
from memory import get_memories, get_preferences, get_recent_messages, search_memories
from router import execute_named_tool
from tool_schema import TOOL_DECLARATIONS
from omni_router import configured as omniroute_configured, chat_with_tools as omniroute_chat_with_tools

logger = logging.getLogger("saba.ai")

SABA_PERSONA = f"""You are {ASSISTANT_NAME}, the personal AI assistant for {APP_NAME}.
Be warm, intelligent, elegant, engaging, concise, natural, confident, and slightly witty.
You are a family assistant, not a generic chatbot. Use persistent memory and family context when relevant.
Respect the speaker's language and style. If the speaker is the creator/primary user, treat that person with special familiarity and respect, but never invent identity verification.
Never expose hidden reasoning. Never claim an action happened unless a tool call actually confirmed it — this applies just as much here in text chat as it does in voice.
You have the same tools here in text chat as you do in voice, including full home appliance control (LG ThinQ and Samsung SmartThings). Use them; do not pretend to control a device without calling the tool.
For health topics, provide general information and encourage professional care when appropriate.
"""

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Hard cap on chained tool calls per text message so a misbehaving loop (or a
# tool that keeps returning something the model wants to react to with another
# tool call) can't run away.
MAX_TOOL_TURNS = 6


def build_context(conversation_id: int, user_id: int, query: str = "", owner_user_id: int | None = None) -> str:
    owner_user_id = owner_user_id or user_id
    memories = search_memories(user_id, query, 8) if query.strip() else get_memories(user_id, 10)
    history = get_recent_messages(conversation_id, 12)
    prefs = get_preferences(user_id)[:12]
    family = relevant_context(query, 10, owner_user_id)
    blocks = [SABA_PERSONA]
    if family:
        blocks.append(family)
    if memories:
        blocks.append("Relevant memories:\n" + "\n".join(f"- [{m['category']}] {m['memory']}" for m in memories))
    if prefs:
        blocks.append("Preferences:\n" + "\n".join(f"- {p['preference_key']}: {p['preference_value']}" for p in prefs))
    if history:
        blocks.append("Recent conversation:\n" + "\n".join(f"{m['role']}: {m['content']}" for m in history))
    return "\n\n".join(blocks)


def _run_tool(name: str, args: dict, user_id: int, role: str, owner_user_id: int | None = None) -> dict:
    try:
        return execute_named_tool(name, args, user_id=user_id, role=role, owner_user_id=owner_user_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Text-mode tool failed: %s", name)
        return {"ok": False, "error": str(exc)}


def ask_ai(message: str, conversation_id: int, user_id: int = SABA_USER_ID, role: str = "primary_user", owner_user_id: int | None = None) -> str:
    """Text-mode chat. Carries the exact same tool set (memory, notes/tasks, system
    control, and LG ThinQ / SmartThings home control) as the voice path in
    backend/live_voice.py, so typed requests like "turn off the bedroom AC" actually
    call the appliance instead of the model just claiming it happened."""
    # Optional local OmniRoute text path. It is intentionally opt-in via OMNIROUTE_MODEL;
    # Gemini remains the compatibility fallback for the existing voice/live stack.
    if omniroute_configured():
        system_instruction = build_context(conversation_id, user_id, message, owner_user_id)
        try:
            return omniroute_chat_with_tools(
                [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": message},
                ],
                TOOL_DECLARATIONS,
                _run_tool,
                user_id=user_id,
                role=role,
                model=OMNIROUTE_MODEL,
                max_tool_turns=MAX_TOOL_TURNS,
            )
        except Exception as exc:
            logger.warning("OmniRoute tool-capable text path failed: %s", exc)
            if not _client:
                raise RuntimeError(
                    "OmniRoute is configured but this model/gateway did not complete tool calling, "
                    "and no Gemini text fallback is configured."
                ) from exc

    if not _client:
        raise RuntimeError("No text model is configured. Set OMNIROUTE_MODEL or GEMINI_API_KEY in .env.")

    system_instruction = build_context(conversation_id, user_id, message, owner_user_id)
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=message)])
    ]
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        max_output_tokens=900,
        tools=[{"function_declarations": TOOL_DECLARATIONS}],
    )

    for _ in range(MAX_TOOL_TURNS):
        response = _client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=contents,
            config=config,
        )
        candidate = response.candidates[0] if response.candidates else None
        parts = candidate.content.parts if candidate and candidate.content and candidate.content.parts else []
        function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

        if not function_calls:
            return (response.text or "").strip() or "I'm here."

        # Keep the model's own function-call turn in the conversation before
        # answering it, exactly as the Gemini function-calling contract requires.
        contents.append(candidate.content)

        response_parts = []
        for fc in function_calls:
            args = dict(fc.args or {})
            result = jsonable_encoder(_run_tool(fc.name, args, user_id, role, owner_user_id))
            response_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": result})
            )
        contents.append(types.Content(role="user", parts=response_parts))

    return "That took more steps than I could finish in one go — try asking again or breaking it into smaller requests."
