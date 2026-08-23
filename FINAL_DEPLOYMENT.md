# SABA Final Deployment

This package is the canonical cloud-ready build of the working Mac SABA project.

## Architecture

- FastAPI backend + React/Vite frontend served from one web service.
- Browser voice uses WebSocket + Gemini Live; the cloud build does not require PyAudio.
- Shared family access code followed by per-family-member selection.
- Each member receives a separate persistent database user, so conversations, memories, notes, tasks and preferences are isolated.
- Family profiles are seeded idempotently from `family_profiles.json` at backend startup.
- The owner profile (`relationship_to_owner: self`) receives owner-level privileges.
- SmartThings remains provider-isolated and capability-aware; OAuth tokens prefer MySQL persistence with a local-file fallback.

## Required Render environment variables

- `SABA_ACCESS_CODE` — 10-digit family access code.
- `SABA_SESSION_SECRET` — long random secret (Render can generate it).
- `GEMINI_API_KEY` — Gemini API key.
- Database variables already required by the project (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).
- SmartThings variables when SmartThings is enabled.
- LG ThinQ variables when LG is enabled.

Never commit `.env`, SmartThings tokens, or machine-specific secrets.

## Build

```bash
python -m pip install -r requirements-cloud.txt && cd frontend && npm ci && npm run build
```

## Start

```bash
uvicorn backend.api:app --host 0.0.0.0 --port $PORT
```

## Cross-device note

The SABA web/PWA UI is same-origin and responsive across iPhone/iPad/Android/macOS/Windows browsers. OS-level actions such as launching arbitrary local apps or changing the local computer's volume require a paired local device agent; the cloud service never pretends those actions happened remotely.
