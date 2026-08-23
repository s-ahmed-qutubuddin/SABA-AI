# Saba — Project Ready Build

This ZIP preserves the existing Saba frontend design and existing features while hardening the runtime and home integrations.

## Included

- Continuous Gemini Live listening across turns.
- Microphone/audio-worklet recovery after a completed response.
- Fresh AudioWorklet processor registration on every recovery to avoid dead input graphs.
- Automatic voice WebSocket reconnection.
- Medium-sensitivity local double-clap activation bridge.
- Persistent MySQL memory, notes, tasks and preferences.
- Relevance-aware memory retrieval for text and voice.
- Existing macOS system tools, calculator, weather, news and web search.
- LG ThinQ integration using the existing PAT + generated Client ID + country code model.
- Samsung SmartThings OAuth 2.0 integration using App ID / Client ID / Client Secret / Redirect URI.
- SmartThings access/refresh token persistence and refresh handling.
- Unified home-device discovery, search, status, capabilities, control and energy tools.
- Post-command state verification when supported.
- LG historical energy usage endpoint.
- No UI/UX redesign.

## Credentials

Copy `.env.example` to `.env` and fill in your local values. Never commit `.env`.

For LG use the PAT and **your already-generated Client ID**. Do not create a new Client ID unless LG requires it.

For SmartThings use the OAuth app's Client ID, Client Secret and registered Redirect URI. The App ID is retained as configuration metadata.

## Run

### Backend

Use your existing Python environment. The project does not ship a virtual environment.

```bash
source .venv/bin/activate
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Double clap companion

With the backend running and `SABA_CREATOR_ACTIVATION_SECRET` configured:

```bash
python companion_clap.py
```

The companion keeps microphone audio local to the Mac and only sends an activation event to the local backend after a detected double clap.

## SmartThings connection

Open:

```text
http://127.0.0.1:8000/integrations/smartthings/connect
```

Authorize Saba in SmartThings. The callback stores the access and refresh token locally in a file with restricted permissions. The same local token store is reused by the home tools.

## Home commands

Saba exposes one unified home tool layer. It discovers LG and Samsung devices, inspects capabilities before control when necessary, executes commands through the correct provider, and attempts a post-command verification read.

## Important limitation

Vendor API availability, device model capabilities, network connectivity, account permissions and current Gemini Live service availability cannot be proven from a static ZIP. The included tests validate code contracts locally, but the final acceptance test must be run against your real LG and SmartThings accounts and appliances.
