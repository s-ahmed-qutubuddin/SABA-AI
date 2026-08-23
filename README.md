# JAMAL-FAMILY-ASSISTANT — Saba

Premium family AI assistant with a MySQL-backed FastAPI backend, Gemini text + Gemini Live voice, persistent memory, family-profile context, controlled web access, safe Mac tools, and an optional local double-clap activation companion.

## Product identity
- App: **JAMAL-FAMILY-ASSISTANT**
- Assistant: **Saba**
- Normal voice activation: the existing frontend Start Listening control remains available.
- Optional hands-free activation: local **double clap** companion → browser activation bridge → persistent Gemini Live session.

## Core behavior
- One voice activation starts a **persistent multi-turn Live session**.
- `turn_complete` returns the assistant to listening; it does not end the session.
- Tool calls temporarily pause microphone forwarding, execute safely, send the function response, and continue the same Live session.
- Voice sessions retrieve recent conversation, relevant memories, preferences, and family-profile context from MySQL.
- New memories are persisted immediately and are available for later retrieval.

## Family profiles
Family-profile infrastructure is database-backed. Because profile names/details are personal data, the repository ships with a **template** rather than hard-coded private identities.

1. Copy/fill `family_profiles.example.json` locally as `family_profiles.json`.
2. Run:
   ```bash
   python scripts/seed_family_profiles.py
   ```
3. The Live and text context layers will automatically retrieve relevant profiles.

## Creator metadata
`CREATOR_BRAND` and `CREATOR_TITLE` are optional environment settings exposed through `/about`. They are intentionally blank in the repository so the owner can choose exactly what to display.

## Local setup
```bash
cd JAMAL-FAMILY-ASSISTANT
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

Second terminal:
```bash
cd frontend
npm install
npm run build
npm run dev
```

## Optional double-clap activation (macOS)
Start the backend first, then in a third terminal:
```bash
source .venv/bin/activate
python companion_clap.py
```

The companion listens locally for a short double-clap pattern. It does **not** send raw microphone audio to Gemini. On detection it posts a local activation event; the frontend activation bridge starts the normal voice pipeline.

## Required environment
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=YOUR_MYSQL_PASSWORD
DB_NAME=assistant_db

GEMINI_API_KEY=YOUR_NEW_KEY
GEMINI_TEXT_MODEL=gemini-3-flash-preview
GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview
GEMINI_VOICE=Kore
SABA_USER_ID=1

CREATOR_BRAND=
CREATOR_TITLE=

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Never commit `.env`, Gemini keys, or DB passwords.

## Production / traffic
The backend now uses a MySQL connection pool, bounded web output, offloaded blocking tool work, deterministic tool allowlists, and structured health diagnostics. For public deployment, run behind a reverse proxy/load balancer, keep WebSocket affinity where required, use a managed MySQL instance, and size Gemini/API quotas separately from server capacity.

## Smart-home integrations
LG ThinQ uses your generated PAT + existing Client ID + country code with the current ThinQ Connect request contract. Samsung SmartThings uses OAuth 2.0 for the durable connection, with App ID retained as app metadata and Client ID/Secret + Redirect URI used for authorization. The backend automatically refreshes access tokens and persists rotated refresh tokens locally.

## Voice reliability
The browser voice pipeline buffers 16 kHz PCM into ~100 ms frames, keeps the same mic/AudioWorklet graph alive across turns, and runs a watchdog that rebuilds a stale graph. Double-clap uses adaptive medium sensitivity with a transient/crest check.

## SABA vNext application layer
- Added a first-class Devices screen with normalized LG ThinQ / SmartThings device discovery and provider health.
- PWA metadata now includes an app icon, installable standalone display, scope and portrait preference.
- Gemini text + Live voice remain the configured AI paths in the current environment. Optional gateway code is retained but is not required.
- The device layer remains provider-separated: SmartThings, LG ThinQ and the HomeMate IR adapter are independent adapters.

## Final unified build
This repository is the canonical SABA build. Run `python3 run.py` from the root to start backend + frontend together.

Home-control providers are normalized behind one SABA surface: LG ThinQ, Samsung SmartThings, and the IR/HomeMate adapter. The IR adapter is a first-class provider with two logical AC remote slots (`ac_1` and `ac_2`). It deliberately does not invent a HomeMate transport endpoint.
