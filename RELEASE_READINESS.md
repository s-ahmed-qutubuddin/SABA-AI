# SABA Release Readiness

## Included
- Premium responsive React UI with command center and PWA metadata.
- Device hub for normalized SmartThings and LG ThinQ discovery.
- Provider separation: SmartThings, LG ThinQ, and future IR/Tuya adapter.
- MySQL-backed conversations, memory, notes, tasks, preferences, family profiles.
- Voice session + local clap bridge reliability improvements from the hardened build.
- Optional local OmniRoute text routing through an OpenAI-compatible gateway.
- Production-oriented health endpoint and integration status.

## Deployment-only work
1. Provision a production server and database.
2. Set secrets/environment variables on the server.
3. Configure HTTPS + DNS and production CORS origins.
4. Configure SmartThings OAuth redirect and LG credentials/connection.
5. Configure the OmniRoute gateway/model available in production.
6. Install and pair the IR blaster; then add the `ir_blaster` adapter and verify both ACs.
7. Add production Android/iOS packaging/signing and store distribution as desired.
8. Run end-to-end acceptance tests with real family accounts/devices.

## Important
The package is intentionally not marked "production deployed": provider credentials, physical devices, infrastructure, and store signing are environment-specific and must be verified outside this build environment.
