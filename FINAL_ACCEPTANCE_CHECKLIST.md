# Saba final acceptance checklist

## Frozen UI
- Existing Saba orb/dashboard/navigation/pages/layout/styles remain unchanged.
- Only functional voice/home/credits changes are allowed.

## Voice
- One Start or creator clap opens one persistent Gemini Live session.
- MediaStream track stays live.
- AudioContext stays running or self-recovers.
- AudioWorklet stays producing PCM frames.
- WebSocket remains open or reconnects automatically.
- 16 kHz PCM is buffered/sent in ~100 ms chunks.
- Automatic Gemini VAD is explicitly configured (low start/end sensitivity, 650 ms silence).
- turn_complete returns to real listening without recreating the session.
- Barge-in stops all scheduled playback sources.
- Tool calls buffer a small amount of incoming audio instead of dropping it.

## Clap
- Local-only companion.
- Medium adaptive sensitivity.
- Double clap/finger-snap-like transient support.
- Refractory/cooldown prevents duplicate activation.
- Valid activation issues one-time creator activation.

## Memory + family
- remember saves.
- recall_memory retrieves JSON-safe records.
- family_context and identify_family_member use the active user id.

## Home
- LG uses LG_THINQ_PAT + the existing generated LG_THINQ_CLIENT_ID + LG_THINQ_COUNTRY; current ThinQ request headers are built by the integration layer.
- Samsung SmartThings uses OAuth 2.0 with Client ID/Secret + Redirect URI; App ID is retained as configuration metadata; access/refresh tokens are persisted and refreshed automatically.
- home_list_devices never asks the user for credentials; unconfigured providers are reported as unconfigured.
- home status/capability/control/energy/cost and historical LG energy usage are exposed through one unified tool layer.

## Creator tools
- Creator role cannot be asserted by browser JSON.
- Developer mode is creator-gated and executes allowlisted macOS actions.

## Credits
- AQUS-AIE -> AHMED QUTUBUDDIN SAAD AI ENGINEER.

## Verification
- Python compile: required.
- Frontend npm build: run on the user's Mac after dependency install.
- Live Gemini/LG/SmartThings integration: verify with real credentials on the user's Mac.
