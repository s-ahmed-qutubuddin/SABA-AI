from __future__ import annotations

import asyncio
import base64
import secrets
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse

from ai import ask_ai
from auth import (
    SessionIdentity,
    clear_auth,
    family_code_configured,
    has_gate,
    identity_from_cookie_header,
    identity_from_request,
    require_identity,
    set_gate,
    set_session,
    verify_family_code,
)
from config import (
    APP_NAME,
    ASSISTANT_NAME,
    CORS_ORIGINS,
    CREATOR_BRAND,
    CREATOR_TITLE,
    GEMINI_LIVE_MODEL,
    GEMINI_TEXT_MODEL,
    HTTP_RATE_LIMIT,
    HTTP_RATE_WINDOW_SECONDS,
    OMNIROUTE_BASE_URL,
    OMNIROUTE_MODEL,
    SABA_ACCESS_CODE,
    SABA_CREATOR_ACTIVATION_SECRET,
    SABA_SESSION_SECRET,
    SABA_USER_ID,
    SMARTTHINGS_APP_ID,
    SMARTTHINGS_CLIENT_ID,
    SMARTTHINGS_CLIENT_SECRET,
    SMARTTHINGS_REDIRECT_URI,
)
from backend.activation import activation_socket, broadcast_activation
from backend.live_voice import get_voice_status, handle_voice_socket
from database import get_connection
from devices.ir_blaster import ir_provider_health, ir_save_learned_command
from family_profiles import (
    ensure_member_user_for_profile,
    get_owner_user_id,
    get_profile_by_id,
    get_profile_for_user,
    list_profiles,
    seed_family_profiles,
)
from home_tools import (
    home_control,
    home_get_capabilities,
    home_get_energy,
    home_get_energy_usage,
    home_get_status,
    home_list_devices,
    home_estimate_cost,
)
from memory import (
    complete_task,
    conversation_belongs_to_user,
    create_conversation,
    delete_memory,
    delete_note,
    delete_task,
    get_conversations,
    get_memories,
    get_messages,
    get_notes,
    get_preferences,
    get_tasks,
    memories,
    notes,
    preferences,
    save_message,
    tasks,
    update_note,
    update_task,
)
from router import route_command
from schema import ensure_runtime_schema

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/login",
    "/auth/session",
    "/auth/members",
    "/oauth/callback",
    "/manifest.webmanifest",
    "/icon.svg",
    "/favicon.ico",
    "/favicon.svg",
}

app = FastAPI(title=f"{APP_NAME} API", version="5.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_lock = asyncio.Lock()
_rate_hits: dict[str, list[float]] = {}
_st_oauth_states: dict[str, float] = {}


def _dev_identity() -> SessionIdentity:
    owner = get_owner_user_id()
    profiles = list_profiles(owner)
    self_profile = next((p for p in profiles if p.get("relationship_to_owner") == "self"), None)
    return SessionIdentity(
        user_id=int((self_profile or {}).get("member_user_id") or owner or SABA_USER_ID),
        owner_user_id=int(owner),
        profile_id=int((self_profile or {}).get("profile_id") or 1),
        role="owner",
        label=str((self_profile or {}).get("label") or CREATOR_BRAND or "Ahmed Qutubuddin"),
        preferred_name=(self_profile or {}).get("preferred_name") or "Boss",
    )


def current_identity(request: Request) -> SessionIdentity:
    identity = identity_from_request(request)
    if identity:
        return identity
    # Local development remains one-click when SABA_ACCESS_CODE is deliberately unset.
    if not family_code_configured():
        return _dev_identity()
    return require_identity(request)


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    if path.startswith("/assets/") or path in PUBLIC_PATHS:
        return await call_next(request)
    if not family_code_configured():
        return await call_next(request)
    # API/UI calls require an authenticated SABA session. The frontend itself is public so it can render the gate.
    if path.startswith("/auth/"):
        return await call_next(request)
    if request.cookies.get("saba_session"):
        return await call_next(request)
    return JSONResponse({"detail": "SABA session required"}, status_code=401)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/assets/"):
        return await call_next(request)
    host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    async with _rate_lock:
        q = _rate_hits.setdefault(host, [])
        window = float(HTTP_RATE_WINDOW_SECONDS)
        q[:] = [stamp for stamp in q if now - stamp <= window]
        if len(q) >= HTTP_RATE_LIMIT:
            return JSONResponse({"detail": "Rate limit exceeded. Try again shortly."}, status_code=429)
        q.append(now)
    return await call_next(request)


@app.on_event("startup")
async def startup():
    await asyncio.to_thread(ensure_runtime_schema)
    # Idempotent seed: existing rows are updated and linked, not duplicated.
    await asyncio.to_thread(seed_family_profiles)
    try:
        import integrations_smartthings as st
        await asyncio.to_thread(st.reload_token_store)
    except Exception:
        pass


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/health")
def health():
    db_status = "ok"
    try:
        conn = get_connection()
        conn.close()
    except Exception:
        db_status = "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "backend": "ok",
        "database": db_status,
        "gemini_text": "configured" if GEMINI_TEXT_MODEL else "missing",
        "gemini_live": "configured" if GEMINI_LIVE_MODEL else "missing",
        "lg_thinq": "configured" if __import__("config").LG_THINQ_PAT else "missing",
        "smartthings": "configured" if __import__("integrations_smartthings").configured() else "missing",
        "smartthings_oauth": "ready" if __import__("integrations_smartthings").oauth_configured() else "missing",
        "assistant": ASSISTANT_NAME,
        "voice": "gemini-live",
        "omniroute": "configured" if OMNIROUTE_BASE_URL else "missing",
        "omniroute_base_url": OMNIROUTE_BASE_URL,
        "omniroute_model": OMNIROUTE_MODEL or None,
        "ir": ir_provider_health(),
        "voice_runtime": get_voice_status(),
        "auth": "family-code" if family_code_configured() else "local-development",
    }


@app.get("/about")
def about():
    return {"app": APP_NAME, "assistant": ASSISTANT_NAME, "creator_brand": CREATOR_BRAND or None, "creator_title": CREATOR_TITLE or None}


@app.get("/auth/session")
def auth_session(request: Request):
    identity = identity_from_request(request)
    return {
        "authenticated": identity is not None,
        "auth_required": family_code_configured(),
        "user": None if identity is None else {
            "user_id": identity.user_id,
            "owner_user_id": identity.owner_user_id,
            "profile_id": identity.profile_id,
            "role": identity.role,
            "label": identity.label,
            "preferred_name": identity.preferred_name,
        },
    }


class LoginIn(__import__("pydantic").BaseModel):
    code: str


@app.post("/auth/login")
def auth_login(body: LoginIn, response: Response):
    if not family_code_configured():
        identity = _dev_identity()
        set_session(response, identity)
        return {"ok": True, "requires_member_selection": False, "user": identity.__dict__}
    if not verify_family_code(body.code):
        raise HTTPException(status_code=401, detail="Incorrect access code")
    set_gate(response)
    return {"ok": True, "requires_member_selection": True}


@app.get("/auth/members")
def auth_members(request: Request):
    if family_code_configured() and not (has_gate(request) or identity_from_request(request)):
        raise HTTPException(status_code=401, detail="Family access code required")
    owner = get_owner_user_id()
    return {
        "owner_user_id": owner,
        "members": [
            {
                "profile_id": p["profile_id"],
                "user_id": p.get("member_user_id"),
                "label": p["label"],
                "preferred_name": p.get("preferred_name"),
                "relationship_to_owner": p["relationship_to_owner"],
                "role_title": p.get("role_title"),
                "role": "owner" if p["relationship_to_owner"] == "self" else "family_member",
            }
            for p in list_profiles(owner)
        ],
    }


class SelectMemberIn(__import__("pydantic").BaseModel):
    profile_id: int


@app.post("/auth/select-member")
def select_member(body: SelectMemberIn, request: Request, response: Response):
    if family_code_configured() and not (has_gate(request) or identity_from_request(request)):
        raise HTTPException(status_code=401, detail="Family access code required")
    owner = get_owner_user_id()
    profile = get_profile_by_id(body.profile_id, owner)
    if not profile:
        raise HTTPException(status_code=404, detail="Family member not found")
    user_id = ensure_member_user_for_profile(body.profile_id, owner)
    role = "owner" if profile["relationship_to_owner"] == "self" else "family_member"
    identity = SessionIdentity(
        user_id=user_id,
        owner_user_id=owner,
        profile_id=int(profile["profile_id"]),
        role=role,
        label=profile["label"],
        preferred_name=profile.get("preferred_name"),
    )
    set_session(response, identity)
    return {"ok": True, "user": identity.__dict__}


@app.post("/auth/logout")
def logout(response: Response):
    clear_auth(response)
    return {"ok": True}



@app.get("/manifest.webmanifest")
def manifest():
    path = FRONTEND_DIST / "manifest.webmanifest"
    if path.exists():
        return FileResponse(path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="Manifest not found")


@app.get("/icon.svg")
def icon():
    path = FRONTEND_DIST / "icon.svg"
    if path.exists():
        return FileResponse(path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Icon not found")

@app.get("/")
def root():
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"app": APP_NAME, "assistant": ASSISTANT_NAME, "status": "ok"}


@app.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    if family_code_configured() and not identity_from_cookie_header(websocket.headers.get("cookie")):
        await websocket.close(code=1008, reason="SABA session required")
        return
    await handle_voice_socket(websocket)


@app.websocket("/ws/activation")
async def ws_activation(websocket: WebSocket):
    if family_code_configured() and not identity_from_cookie_header(websocket.headers.get("cookie")):
        await websocket.close(code=1008, reason="SABA session required")
        return
    await activation_socket(websocket)


class ActivationIn(__import__("pydantic").BaseModel):
    role: str = "creator"


@app.post("/activation/clap")
async def clap_activation(body: ActivationIn, request: Request):
    identity = current_identity(request)
    host = request.client.host if request.client else None
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Clap activation is local-only.")
    if body.role != "creator" or not identity.is_owner:
        raise HTTPException(status_code=403, detail="Creator activation is owner-only.")
    supplied = request.headers.get("X-Bridge-Secret", "")
    if not SABA_CREATOR_ACTIVATION_SECRET or supplied != SABA_CREATOR_ACTIVATION_SECRET:
        raise HTTPException(status_code=401, detail="Invalid activation bridge secret.")
    if get_voice_status().get("active_sessions", 0) > 0:
        return {"ok": True, "activated_role": None, "ignored": "voice_active"}
    await broadcast_activation("creator")
    return {"ok": True, "activated_role": "creator"}


@app.get("/integrations/smartthings/connect")
def smartthings_connect(request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="SmartThings setup is owner-only.")
    if not (SMARTTHINGS_CLIENT_ID and SMARTTHINGS_REDIRECT_URI):
        raise HTTPException(status_code=503, detail="SmartThings OAuth is not configured yet.")
    state = secrets.token_urlsafe(24)
    _st_oauth_states[state] = time.time() + 600
    scopes = "r:locations:* r:devices:* x:devices:*"
    query = urllib.parse.urlencode({"client_id": SMARTTHINGS_CLIENT_ID, "scope": scopes, "response_type": "code", "redirect_uri": SMARTTHINGS_REDIRECT_URI, "state": state})
    return {"ok": True, "authorization_url": f"https://api.smartthings.com/v1/oauth/authorize?{query}"}


@app.get("/oauth/callback")
def smartthings_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if not state or state not in _st_oauth_states or _st_oauth_states[state] < time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    _st_oauth_states.pop(state, None)
    if error:
        raise HTTPException(status_code=400, detail=f"SmartThings authorization failed: {error}")
    if not code or not (SMARTTHINGS_CLIENT_ID and SMARTTHINGS_CLIENT_SECRET and SMARTTHINGS_REDIRECT_URI):
        raise HTTPException(status_code=503, detail="SmartThings OAuth credentials are not configured.")
    basic = base64.b64encode(f"{SMARTTHINGS_CLIENT_ID}:{SMARTTHINGS_CLIENT_SECRET}".encode()).decode()
    response = requests.post(
        "https://api.smartthings.com/v1/oauth/token",
        headers={"Authorization": f"Basic {basic}", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code, "client_id": SMARTTHINGS_CLIENT_ID, "redirect_uri": SMARTTHINGS_REDIRECT_URI},
        timeout=15,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"SmartThings token exchange failed: {response.text[:800]}")
    import integrations_smartthings as st
    st.set_oauth_tokens(response.json())
    return {"ok": True, "message": "SmartThings connected."}


@app.post("/smartthings/webhook")
async def smartthings_webhook(payload: dict):
    return {"ok": True}


@app.get("/home/devices")
def home_devices(request: Request):
    current_identity(request)
    return home_list_devices()


@app.get("/home/summary")
def home_summary(request: Request):
    current_identity(request)
    data = home_list_devices()
    return {"count": data.get("count", 0), "providers": data.get("provider_status", {}), "errors": data.get("errors", []), "devices": [{k: d.get(k) for k in ("provider", "id", "name", "model", "type", "manufacturer", "online")} for d in data.get("devices", [])]}


@app.get("/home/status")
def home_status(request: Request, provider: str, device_id: str):
    current_identity(request)
    return home_get_status(provider, device_id)


@app.get("/home/capabilities")
def home_capabilities(request: Request, provider: str, device_id: str):
    current_identity(request)
    return home_get_capabilities(provider, device_id)


class HomeControlIn(__import__("pydantic").BaseModel):
    provider: str
    device_id: str
    command: dict


@app.post("/home/control")
def home_control_route(body: HomeControlIn, request: Request):
    current_identity(request)
    return home_control(body.provider, body.device_id, body.command)


@app.get("/home/energy")
def home_energy(request: Request, provider: str, device_id: str):
    current_identity(request)
    return home_get_energy(provider, device_id)


@app.get("/home/energy/usage")
def home_energy_usage(request: Request, provider: str, device_id: str, energy_property: str, period: str = "DAY", start_date: str | None = None, end_date: str | None = None):
    current_identity(request)
    return home_get_energy_usage(provider, device_id, energy_property, period, start_date, end_date)


@app.get("/home/cost")
def home_cost(request: Request, kwh: float, tariff_per_kwh: float):
    current_identity(request)
    return home_estimate_cost(kwh, tariff_per_kwh)


class IRLearnIn(__import__("pydantic").BaseModel):
    name: str
    payload: dict
    appliance: str | None = None


@app.post("/home/ir/learn")
def home_ir_learn(body: IRLearnIn, request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="IR learning is owner-only.")
    return ir_save_learned_command(body.name, body.payload, body.appliance)


@app.get("/voice/status")
def voice_status(request: Request):
    current_identity(request)
    return get_voice_status()


@app.get("/me")
def me(request: Request):
    identity = current_identity(request)
    profile = get_profile_for_user(identity.user_id, identity.owner_user_id)
    return {"user": identity.__dict__, "profile": profile}


@app.get("/conversations")
def conversations(request: Request):
    identity = current_identity(request)
    return get_conversations(identity.user_id)


@app.post("/conversations")
def new_conversation(request: Request, title: str = "Saba Session"):
    identity = current_identity(request)
    return {"conversation_id": create_conversation(identity.user_id, title)}


@app.get("/conversations/{conversation_id}/messages")
def messages(conversation_id: int, request: Request):
    identity = current_identity(request)
    return get_messages(identity.user_id, conversation_id)


class ChatRequest(__import__("pydantic").BaseModel):
    conversation_id: Optional[int] = None
    message: str


@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    identity = current_identity(request)
    conversation_id = req.conversation_id or create_conversation(identity.user_id, "Saba Family Chat")
    if req.conversation_id and not conversation_belongs_to_user(conversation_id, identity.user_id):
        raise HTTPException(status_code=403, detail="Conversation does not belong to this family member.")
    save_message(conversation_id, req.message, "user")
    events: list[tuple[str, dict]] = []
    local = route_command(req.message, emit=lambda t, p: events.append((t, p)), user_id=identity.user_id, role=identity.role, owner_user_id=identity.owner_user_id)
    answer = local.get("speak", "Done.") if local.get("handled") else ask_ai(req.message, conversation_id, identity.user_id, identity.role, identity.owner_user_id)
    save_message(conversation_id, answer, "assistant")
    return {"response": answer, "handled": bool(local.get("handled")), "conversation_id": conversation_id, "events": events}


@app.get("/memories")
def memory_list(request: Request):
    return get_memories(current_identity(request).user_id)


class MemoryIn(__import__("pydantic").BaseModel):
    memory: str
    category: str = "general"
    importance: int = 5


@app.post("/memories")
def add_memory(body: MemoryIn, request: Request):
    return {"memory_id": memories(current_identity(request).user_id, body.memory, body.category, body.importance)}


@app.delete("/memories/{memory_id}")
def del_memory(memory_id: int, request: Request):
    return {"deleted": delete_memory(current_identity(request).user_id, memory_id) > 0}


@app.get("/notes")
def note_list(request: Request):
    return get_notes(current_identity(request).user_id)


class NoteIn(__import__("pydantic").BaseModel):
    title: str
    content: str


@app.post("/notes")
def add_note(body: NoteIn, request: Request):
    return {"note_id": notes(current_identity(request).user_id, body.title, body.content)}


@app.put("/notes/{note_id}")
def edit_note(note_id: int, body: NoteIn, request: Request):
    return {"updated": update_note(current_identity(request).user_id, note_id, body.title, body.content) > 0}


@app.delete("/notes/{note_id}")
def del_note(note_id: int, request: Request):
    return {"deleted": delete_note(current_identity(request).user_id, note_id) > 0}


@app.get("/tasks")
def task_list(request: Request):
    return get_tasks(current_identity(request).user_id)


class TaskIn(__import__("pydantic").BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None


@app.post("/tasks")
def add_task(body: TaskIn, request: Request):
    return {"task_id": tasks(current_identity(request).user_id, body.title, body.description, body.due_date)}


class TaskUpdate(__import__("pydantic").BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "pending"


@app.put("/tasks/{task_id}")
def edit_task(task_id: int, body: TaskUpdate, request: Request):
    return {"updated": update_task(current_identity(request).user_id, task_id, body.title, body.description, body.due_date, body.status) > 0}


@app.post("/tasks/{task_id}/complete")
def complete(task_id: int, request: Request):
    return {"updated": complete_task(current_identity(request).user_id, task_id) > 0}


@app.delete("/tasks/{task_id}")
def del_task(task_id: int, request: Request):
    return {"deleted": delete_task(current_identity(request).user_id, task_id) > 0}


@app.get("/preferences")
def preference_list(request: Request):
    return get_preferences(current_identity(request).user_id)


class PreferenceIn(__import__("pydantic").BaseModel):
    value: str


@app.put("/preferences/{key}")
def set_preference(key: str, body: PreferenceIn, request: Request):
    preferences(current_identity(request).user_id, key, body.value)
    return {"ok": True}


@app.get("/family/profiles")
def family_list(request: Request):
    identity = current_identity(request)
    return list_profiles(identity.owner_user_id)


class FamilyProfileIn(__import__("pydantic").BaseModel):
    label: str
    relationship_to_owner: str
    preferred_name: Optional[str] = None
    languages: Optional[str] = None
    role_title: Optional[str] = None
    occupation: Optional[str] = None
    interests: Optional[str] = None
    notes: Optional[str] = None


@app.post("/family/profiles")
def family_upsert(body: FamilyProfileIn, request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can edit family profiles.")
    from family_profiles import upsert_profile
    return {"profile_id": upsert_profile(**body.model_dump(), user_id=identity.owner_user_id)}


@app.delete("/family/profiles/{profile_id}")
def family_delete(profile_id: int, request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can delete family profiles.")
    from family_profiles import delete_profile
    return {"deleted": delete_profile(profile_id, identity.owner_user_id)}


@app.get("/family/context")
def family_context(request: Request, q: str = ""):
    from family_profiles import relevant_context
    identity = current_identity(request)
    return {"context": relevant_context(q, 20, identity.owner_user_id)}


@app.get("/system/allowed")
def system_allowed(request: Request):
    identity = current_identity(request)
    common = ["Open URL", "Search Web", "Get Weather", "Get News"]
    if identity.is_owner:
        common += ["Open Safari", "Open Google Chrome", "Open Visual Studio Code", "Open Terminal", "Open Finder", "Open Music", "Open Notes", "Open Spotify", "Set volume", "Get volume", "Play/pause media", "Next track", "Previous track", "Stop media", "Battery status", "System info", "Read clipboard", "Write clipboard"]
    return {"actions": common, "role": identity.role}


class OpenAppIn(__import__("pydantic").BaseModel):
    name: str


@app.post("/system/open-app")
def system_open_app(body: OpenAppIn, request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="OS app control is owner-only until this device is paired.")
    from tools.system import open_app
    try:
        return open_app(body.name)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


class VolumeIn(__import__("pydantic").BaseModel):
    percent: int


@app.post("/system/volume")
def system_volume(body: VolumeIn, request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="OS volume control is owner-only until this device is paired.")
    from tools.system import set_volume
    try:
        return set_volume(body.percent)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/system/volume")
def system_volume_get(request: Request):
    identity = current_identity(request)
    if not identity.is_owner:
        raise HTTPException(status_code=403, detail="OS volume control is owner-only until this device is paired.")
    from tools.system import get_volume
    return get_volume()


class UrlIn(__import__("pydantic").BaseModel):
    url: str


@app.post("/system/open-url")
def system_open_url(body: UrlIn, request: Request):
    current_identity(request)
    from tools.system import open_url
    try:
        return open_url(body.url)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/weather")
def weather(city: str, request: Request):
    current_identity(request)
    from tools.weather import get_weather
    return get_weather(city)


@app.get("/news")
def news(request: Request, q: str = "technology"):
    current_identity(request)
    from tools.news import get_news
    return get_news(q)


@app.get("/web/search")
def web_search(q: str, request: Request):
    current_identity(request)
    from tools.web import search_web
    return search_web(q)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not Found")
