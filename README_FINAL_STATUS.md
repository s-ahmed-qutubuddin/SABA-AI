# SABA — Final Deployable Baseline Status

Selected baseline: **SABA_BEAST_READY(1)**.

This package has been cleaned and hardened from that baseline.

## Verified
- Python compileall: PASS
- Backend smoke test: PASS
- Home integration contract tests: PASS
- SmartThings and LG integrations remain provider-separated.
- LG AC IR integration remains isolated for the HMIR1 integration.
- OmniRoute can now use OpenAI-compatible function/tool calling through the shared SABA tool schema.
- No runtime credentials are packaged.
- Hard-coded LG API-key fallback was removed; configure `LG_THINQ_API_KEY` only when required by the chosen ThinQ contract.
- Creator branding defaults are blank.
- PWA metadata and standalone mode are included.

## Still deployment-specific
- Production DNS/HTTPS/server configuration.
- Real user authentication/account recovery for multi-family-member internet deployment.
- Production secret storage.
- SmartThings OAuth redirect configuration.
- LG credentials/configuration.
- Running OmniRoute gateway/model selection and provider compatibility testing.
- Real iOS installation/testing and Android release signing.
- HMIR1 local/API/firmware integration and two-AC placement verification.
- Real end-to-end acceptance tests on the family's phones and appliances.

## Important
This is the strongest source-tree baseline, **not a claim that a public production deployment is already complete**. The remaining items require the owner's real credentials, infrastructure, mobile signing, and physical devices.
