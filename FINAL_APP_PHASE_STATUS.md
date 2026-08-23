# Saba Final App-Phase Status

This package keeps the existing Saba frontend design and adds reliability/integration work without redesigning the UI.

## Voice
- Continuous multi-turn Live session is preserved.
- Input PCM is buffered into ~100 ms / 16 kHz chunks.
- An AudioWorklet watchdog detects a stale microphone graph and rebuilds it.
- The input AudioContext is resumed when suspended.
- Unexpected WebSocket closes trigger reconnect attempts while the session is active.
- Tool calls pause incoming microphone forwarding and then return to the same Live session.
- Interruption events return the UI to listening.

## Clap
- Local macOS companion only; raw microphone audio is not sent to Gemini.
- Adaptive medium sensitivity; designed to tolerate quieter claps/finger snaps while reducing false triggers.
- Double-hit refractory period prevents one physical clap from becoming two activations.
- Creator activation is bridged into the existing voice session.

## Creator / Developer mode
- Creator-only developer tool is already exposed by the backend.
- It opens VS Code, Terminal, Notes, and the project folder.
- Other diagnostic/project tools remain creator-gated.

## Memory / family
- Durable memory save + recall tools are present.
- Current voice session context includes recent conversation, memories, preferences, and family context.
- A local `family_profiles.json` is included with the family details supplied by the owner; run the seed script once against your database.

## Home integrations
- LG ThinQ: PAT supported; optional developer headers supported when your LG account/app requires them.
- Samsung SmartThings: PAT supported for testing. OAuth 2.0 refresh credentials are supported for unattended use, with access-token refresh and rotated refresh-token persistence.
- The unified home layer provides device discovery, status/capability lookup, control, energy inspection and estimated cost.

## Important credential note
SmartThings PATs are intentionally short-lived. Automatic long-term refresh is only possible after OAuth 2.0 linking supplies a refresh token. The backend cannot manufacture a refresh token from a PAT.

## Build validation
- Python compileall: PASS
- Frontend design files are preserved; final browser build must be run on the user's Mac after `npm install`.
- Gemini Live and appliance APIs require the user's real credentials and are not exercised in this sandbox.


## Build contract locked
- Frontend visual design frozen; only minimal functional voice/home/auth changes allowed.
- Continuous audio requires an actually live MediaStream, AudioContext, AudioWorklet, WebSocket, and Gemini Live session.
- Barge-in stops queued playback and relies on Gemini Live interruption.
- Double clap is medium-sensitivity adaptive local detection.
- LG requires only LG_THINQ_PAT for the current PAT flow; optional client headers stay optional.
- Samsung OAuth 2.0 is isolated and includes automatic refresh; registration remains pending with SmartThings.
