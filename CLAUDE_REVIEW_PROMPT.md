# Claude review pass — Saba

Use this ZIP as the current source of truth. **Do not redesign or alter the frontend UI/UX.** Review for functional correctness only.

## Non-negotiable behavior

1. Continuous Gemini Live listening: after every assistant turn, Saba must remain genuinely microphone-live. Pressing Start again after every response is a bug.
2. Recover from suspended/closed AudioContext, stale AudioWorklet, dead MediaStream track, or dead WebSocket without requiring the Start button when the session is still active.
3. Double clap remains a local medium-sensitivity activation and must not stream raw activation audio to Gemini.
4. Memory retrieval must persist and retrieve relevant memories in both text and voice sessions.
5. Existing system tools, internet/web tools, family tools and developer tools must remain functional.
6. LG ThinQ must use the user's already-generated Client ID and PAT. Do not generate a new client ID at runtime. Country is configurable.
7. Samsung SmartThings must use OAuth 2.0 with Client ID, Client Secret and Redirect URI; refresh tokens must survive access-token expiration.
8. Home tools must unify LG and Samsung discovery, status, capabilities, control and energy access.
9. Never put credentials or tokens into source code, logs, UI, Git, or this ZIP.

## Review focus

- Inspect race conditions in the voice state machine and reconnect lifecycle.
- Inspect AudioWorklet registration/recovery behavior.
- Inspect SmartThings OAuth state handling and token refresh.
- Inspect LG ThinQ headers/endpoints against the current ThinQ Connect API contract.
- Inspect capability-aware home control and post-command verification.
- Run Python compile/static tests.
- Run the frontend dependency install and `npm run build` on macOS.
- Do not make cosmetic/UI changes.

Return only concrete bugs found, fixes applied, and test results.
