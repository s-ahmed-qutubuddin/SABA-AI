from __future__ import annotations

import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect

from identity import issue_local_creator_activation
from config import MAX_ACTIVATION_CONNECTIONS
import time

ACTIVATION_TTL_SECONDS = 12.0
_last_activation: dict | None = None

logger = logging.getLogger("saba.activation")
_clients: set[WebSocket] = set()
_lock = asyncio.Lock()
_slots = asyncio.Semaphore(MAX_ACTIVATION_CONNECTIONS)


async def activation_socket(websocket: WebSocket):
    async with _slots:
        await websocket.accept()
        async with _lock:
            _clients.add(websocket)
            pending = dict(_last_activation) if _last_activation else None
        try:
            if pending and time.monotonic() - pending.get("issued_at", 0) <= ACTIVATION_TTL_SECONDS:
                payload = {k: v for k, v in pending.items() if k != "issued_at"}
                await websocket.send_json(payload)

            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("Activation websocket failure")
        finally:
            async with _lock:
                _clients.discard(websocket)


async def broadcast_activation(role: str = "creator"):
    global _last_activation
    nonce = issue_local_creator_activation() if role == "creator" else None
    payload = {"type": "clap_detected", "role": "creator", "activation_id": nonce}
    _last_activation = {**payload, "issued_at": time.monotonic()}
    async with _lock:
        clients = list(_clients)
    for ws in clients:
        try:
            await ws.send_json(payload)
        except Exception:
            async with _lock:
                _clients.discard(ws)
