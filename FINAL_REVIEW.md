# SABA Final Review — 2026-08-20

## Selected baseline
`SABA_BEAST_READY(1).zip` is the stronger and more complete baseline. `SABA_FINAL_READY.zip` is a sanitized snapshot wrapper whose useful payload is a snapshot document plus the older project tree; it is not the better deployable source tree.

## Fixes applied to the Beast baseline
- Removed the hard-coded LG API key fallback from `config.py`; it is now environment-only.
- Cleared creator-brand/title defaults so the package does not publish personal branding unless explicitly configured.
- Upgraded the local OmniRoute text path to support OpenAI-compatible function/tool calling using the shared SABA tool schema.
- Kept Gemini as an optional fallback for text and the existing Live voice implementation.
- Added this release review and clarified remaining deployment work.

## Verified locally
- Python compileall: PASS
- Backend static smoke test: PASS
- Home integration contract tests: PASS
- No repository file contains the known LG PAT/OAuth/SmartThings token values.
- Frontend source and PWA metadata are included.

## Not claimed as complete
- Real production deployment / DNS / HTTPS
- Production user authentication and account recovery
- Apple App Store signing/distribution
- Android release signing/Play distribution
- Real-world OmniRoute model/tool compatibility (must be tested against the user's running gateway)
- Real LG AC IR adapter integration
- Final two-AC IR placement verification
- Full real-device acceptance testing

## Release rule
Do not label this package production-deployed until the deployment-only items above are tested against the real server, accounts, phone devices, and appliances.
