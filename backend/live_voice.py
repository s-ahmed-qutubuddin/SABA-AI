from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from google import genai
from google.genai import types

from config import ASSISTANT_NAME, GEMINI_API_KEY, GEMINI_LIVE_MODEL, GEMINI_VOICE, SABA_USER_ID, MAX_VOICE_CONNECTIONS, VOICE_MAX_AUDIO_BYTES, VOICE_MAX_TEXT_BYTES
from family_profiles import relevant_context
from identity import Identity, identify_family_member, resolve_voice_identity, issue_creator_session
from auth import identity_from_cookie_header
from memory import conversation_belongs_to_user, create_conversation, get_memories, get_preferences, get_recent_messages, save_message
from router import execute_named_tool
from tool_schema import TOOL_DECLARATIONS

logger = logging.getLogger("saba.live")

_voice_slots = asyncio.Semaphore(MAX_VOICE_CONNECTIONS)
_active_sessions: dict[str, dict[str, Any]] = {}
_sessions_lock = asyncio.Lock()

LIVE_REALTIME_INPUT_CONFIG = {
    "automatic_activity_detection": {
        "disabled": False,
        "start_of_speech_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
        "end_of_speech_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        "prefix_padding_ms": 120,
        "silence_duration_ms": 650,
    }
}


def _tool(name: str, args: Dict[str, Any], user_id: int, role: str, owner_user_id: int) -> Dict[str, Any]:
    try:
        return execute_named_tool(name, args, user_id=user_id, role=role, owner_user_id=owner_user_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool failed: %s", name)
        return {"ok": False, "error": str(exc)}


def _session_context(conversation_id: int, owner_user_id: int, active_user_id: int, identity: Identity) -> str:
    memories = __import__("memory").get_memories(active_user_id, 12)
    history = get_recent_messages(conversation_id, 16)
    preferences = get_preferences(active_user_id)[:16]
    family = relevant_context("", 20, owner_user_id)
    lines = [
        f"You are {ASSISTANT_NAME}, the personal AI assistant for the Jamal family.",
        "Be warm, natural, elegant, concise, engaging, confident, respectful and slightly witty.",
        "You are a persistent assistant. Use stored memory and family context instead of guessing.",
        "The current speaker identity was established by the backend; never claim biometric certainty.",
        f"Current speaker role: {identity.role}. Profile: {identity.profile_label}.",
        "No wake word is required inside an active voice session. Keep the session alive across turns; do not treat turn_complete as session_complete.",
        "Never claim an external/system action happened unless its tool returned success. If the authenticated creator says developer mode, go developer mode, or ready to build, use activate_developer_mode.",
        "Never reveal hidden reasoning or secrets.",
    ]
    if identity.is_creator:
        lines += [
            "The current speaker is the authenticated creator/originator of this local assistant session.",
            "Address the creator with warmth, respect and familiarity. They are authorized for creator-only developer tools.",
        ]
    if family:
        lines.append(family)
    if memories:
        lines.append("Relevant persistent memories:\n" + "\n".join(f"- [{m['category']}] {m['memory']}" for m in memories))
    if preferences:
        lines.append("Persistent preferences:\n" + "\n".join(f"- {p['preference_key']}: {p['preference_value']}" for p in preferences))
    if history:
        lines.append("Recent conversation:\n" + "\n".join(f"{m['role']}: {m['content']}" for m in history))
    return "\n\n".join(lines)


def get_voice_status() -> dict[str, Any]:
    if not _active_sessions:
        return {"state": "stopped", "conversation_id": None, "connected": False, "active_sessions": 0}
    latest = next(reversed(_active_sessions.values()))
    return {
        "state": latest.get("state", "listening"),
        "conversation_id": latest.get("conversation_id"),
        "connected": True,
        "active_sessions": len(_active_sessions),
        "role": latest.get("role"),
        "user_id": latest.get("user_id"),
    }


async def handle_voice_socket(websocket: WebSocket) -> None:
    client_host = getattr(websocket.client, "host", None)
    query = websocket.query_params
    activation_hint = query.get("activation_id")
    creator_session_token = query.get("creator_session_token")
    requested_conversation_id = query.get("conversation_id")
    if _voice_slots.locked() and getattr(_voice_slots, "_value", 0) <= 0:
        await websocket.close(code=1013, reason="Voice capacity reached")
        return
    async with _voice_slots:
        await websocket.accept()
        socket_key = f"{client_host}:{id(websocket)}"
        error_sent = False
        error_lock = asyncio.Lock()

        async def send_error(message: str, code: str = "voice_error"):
            nonlocal error_sent
            async with error_lock:
                if error_sent:
                    return
                error_sent = True
                try:
                    await websocket.send_json({"type": "error", "code": code, "message": message})
                except Exception:
                    pass

        conversation_id = None
        stop_event = asyncio.Event()
        tool_busy = asyncio.Event()
        pending_tool_audio: deque[bytes] = deque(maxlen=16)
        tool_audio_lock = asyncio.Lock()
        explicit_stop = False
        client = None
        auth_identity = identity_from_cookie_header(websocket.headers.get("cookie"))
        identity = auth_identity or resolve_voice_identity(
            client_host=client_host,
            activation_hint=activation_hint,
            creator_session_token=creator_session_token,
        )
        active_user_id = identity.user_id
        owner_user_id = identity.owner_user_id if auth_identity else SABA_USER_ID

        try:
            if not GEMINI_API_KEY:
                await send_error("Gemini is not configured.", "gemini_not_configured")
                return

            client = genai.Client(api_key=GEMINI_API_KEY)
            requested_id = int(requested_conversation_id) if requested_conversation_id and requested_conversation_id.isdigit() else None
            if requested_id and await asyncio.to_thread(conversation_belongs_to_user, requested_id, active_user_id):
                conversation_id = requested_id
            else:
                conversation_id = await asyncio.to_thread(create_conversation, active_user_id, "Saba Voice Session")
            context = await asyncio.to_thread(_session_context, conversation_id, owner_user_id, active_user_id, identity)
            live_config = {
                "response_modalities": ["AUDIO"],
                "realtime_input_config": LIVE_REALTIME_INPUT_CONFIG,
                "input_audio_transcription": {},
                "output_audio_transcription": {},
                "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": GEMINI_VOICE}}},
                "system_instruction": context,
                "tools": [{"function_declarations": TOOL_DECLARATIONS}],
            }

            async with _sessions_lock:
                _active_sessions[socket_key] = {"state": "connecting", "conversation_id": conversation_id, "role": identity.role, "user_id": active_user_id, "started_at": time.time()}
            await websocket.send_json({"type": "state", "state": "connecting", "conversation_id": conversation_id})

            async with client.aio.live.connect(model=GEMINI_LIVE_MODEL, config=live_config) as live:
                async with _sessions_lock:
                    _active_sessions[socket_key]["state"] = "listening"
                ready_payload = {"type": "ready", "conversation_id": conversation_id, "voice": GEMINI_VOICE, "role": identity.role}
                if identity.is_creator:
                    ready_payload["creator_session_token"] = issue_creator_session()
                await websocket.send_json(ready_payload)
                await websocket.send_json({"type": "state", "state": "listening"})

                if identity.is_creator and identity.source == "local_clap":
                    await live.send_realtime_input(text="The creator has just activated you. Respond exactly: Systems are online, Boss. Ready to build.")

                async def client_to_gemini():
                    nonlocal explicit_stop, active_user_id, identity
                    try:
                        while not stop_event.is_set():
                            msg = await websocket.receive()
                            if msg.get("bytes") is not None:
                                payload = msg["bytes"]
                                if len(payload) > VOICE_MAX_AUDIO_BYTES:
                                    await send_error("Audio frame too large.", "audio_frame_too_large")
                                    continue
                                if tool_busy.is_set():
                                    async with tool_audio_lock:
                                        pending_tool_audio.append(payload)
                                    continue
                                await live.send_realtime_input(audio=types.Blob(data=payload, mime_type="audio/pcm;rate=16000"))
                            elif msg.get("text"):
                                raw = msg["text"]
                                if len(raw.encode("utf-8")) > VOICE_MAX_TEXT_BYTES:
                                    await send_error("Voice command too large.", "voice_message_too_large")
                                    continue
                                try:
                                    data = json.loads(raw)
                                except json.JSONDecodeError:
                                    await send_error("Malformed voice message.", "malformed_voice_message")
                                    continue
                                action = data.get("action")
                                if action == "start":
                                    # Ignore arbitrary client role claims. Creator elevation only comes from local clap activation.
                                    await websocket.send_json({"type": "state", "state": "listening"})
                                elif action == "stop":
                                    explicit_stop = True
                                    stop_event.set()
                                    break
                                elif action == "text":
                                    await live.send_realtime_input(text=str(data.get("text", ""))[:VOICE_MAX_TEXT_BYTES])
                    except WebSocketDisconnect:
                        explicit_stop = True
                        stop_event.set()
                    except Exception as exc:
                        logger.exception("Client->Gemini loop failed")
                        await send_error(str(exc), "client_gemini_error")
                        stop_event.set()

                async def gemini_to_client():
                    nonlocal active_user_id, identity
                    user_buf: list[str] = []
                    assistant_buf: list[str] = []
                    try:
                        async for response in live.receive():
                            if response.tool_call:
                                tool_busy.set()
                                await websocket.send_json({"type": "state", "state": "tool_running"})
                                calls = []
                                try:
                                    for fc in response.tool_call.function_calls:
                                        args = dict(fc.args or {})
                                        await websocket.send_json({"type": "tool_start", "name": fc.name, "args": args})
                                        result = await asyncio.to_thread(_tool, fc.name, args, active_user_id, identity.role, owner_user_id)
                                        result = jsonable_encoder(result)
                                        await websocket.send_json({"type": "tool_result", "name": fc.name, "result": result})
                                        if fc.name == "identify_family_member" and result.get("ok"):
                                            active_user_id = int(result["user_id"])
                                            identity = Identity(user_id=active_user_id, role="family_member", source="voice_identification", profile_label=result["profile_label"])
                                            async with _sessions_lock:
                                                _active_sessions[socket_key]["user_id"] = active_user_id
                                                _active_sessions[socket_key]["role"] = identity.role
                                        calls.append(types.FunctionResponse(name=fc.name, id=fc.id, response={"result": result}))
                                    if calls:
                                        await live.send_tool_response(function_responses=calls)
                                    async with tool_audio_lock:
                                        buffered = list(pending_tool_audio)
                                        pending_tool_audio.clear()
                                    for buffered_audio in buffered:
                                        await live.send_realtime_input(audio=types.Blob(data=buffered_audio, mime_type="audio/pcm;rate=16000"))
                                    await websocket.send_json({"type": "state", "state": "thinking"})
                                finally:
                                    tool_busy.clear()

                            content = response.server_content
                            if not content:
                                continue
                            if content.input_transcription:
                                chunk = content.input_transcription.text or ""
                                if chunk:
                                    user_buf.append(chunk)
                                    await websocket.send_json({"type": "transcript", "role": "user", "text": chunk})
                                    async with _sessions_lock:
                                        _active_sessions[socket_key]["state"] = "thinking"
                                    await websocket.send_json({"type": "state", "state": "thinking"})
                            if content.output_transcription:
                                chunk = content.output_transcription.text or ""
                                if chunk:
                                    assistant_buf.append(chunk)
                                    await websocket.send_json({"type": "response", "role": "assistant", "text": chunk})
                            if content.model_turn:
                                for part in content.model_turn.parts or []:
                                    if part.inline_data and part.inline_data.data:
                                        await websocket.send_bytes(part.inline_data.data)
                                        async with _sessions_lock:
                                            _active_sessions[socket_key]["state"] = "speaking"
                                        await websocket.send_json({"type": "state", "state": "speaking"})
                            if getattr(response, "go_away", None) is not None:
                                await websocket.send_json({"type": "state", "state": "thinking"})
                            if content.interrupted:
                                await websocket.send_json({"type": "interrupted"})
                            if getattr(content, "generation_complete", False) and not content.turn_complete:
                                async with _sessions_lock:
                                    if socket_key in _active_sessions:
                                        _active_sessions[socket_key]["state"] = "listening"
                                await websocket.send_json({"type": "state", "state": "listening"})
                            if content.turn_complete:
                                if user_buf:
                                    text = "".join(user_buf).strip()
                                    if text:
                                        await asyncio.to_thread(save_message, conversation_id, text, "user")
                                if assistant_buf:
                                    text = "".join(assistant_buf).strip()
                                    if text:
                                        await asyncio.to_thread(save_message, conversation_id, text, "assistant")
                                user_buf.clear(); assistant_buf.clear()
                                async with _sessions_lock:
                                    _active_sessions[socket_key]["state"] = "listening"
                                await websocket.send_json({"type": "state", "state": "listening", "session_alive": True})
                    except Exception as exc:
                        logger.exception("Gemini->client loop failed")
                        await send_error(str(exc), "gemini_live_error")
                        stop_event.set()

                # Run both loops as real tasks and race them against stop_event. Without
                # this, sending {"action": "stop"} only ends client_to_gemini(); the
                # gemini_to_client() loop has no way to learn the session should end and
                # blocks forever on live.receive(), so the "async with ... as live:" block
                # (and its voice slot / semaphore) never releases until Gemini itself drops
                # the socket. Repeated stop/start cycles would then slowly exhaust
                # MAX_VOICE_CONNECTIONS.
                task_in = asyncio.create_task(client_to_gemini())
                task_out = asyncio.create_task(gemini_to_client())
                task_stop = asyncio.create_task(stop_event.wait())
                try:
                    done, pending = await asyncio.wait(
                        {task_in, task_out, task_stop},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    for task in (task_in, task_out):
                        if task.done() and not task.cancelled():
                            exc = task.exception()
                            if exc:
                                raise exc
                finally:
                    for task in (task_in, task_out, task_stop):
                        if not task.done():
                            task.cancel()
        except Exception as exc:
            logger.exception("Live session failed")
            await send_error(str(exc), "live_session_error")
        finally:
            async with _sessions_lock:
                _active_sessions.pop(socket_key, None)
            if explicit_stop:
                try:
                    await websocket.send_json({"type": "state", "state": "stopped"})
                except Exception:
                    pass
            elif not error_sent:
                try:
                    await websocket.send_json({"type": "state", "state": "disconnected"})
                except Exception:
                    pass
            try:
                await websocket.close()
            except Exception:
                pass
