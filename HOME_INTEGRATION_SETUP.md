# Saba Home Integration

## LG ThinQ

Set the exact credentials you already have:

```env
LG_THINQ_PAT=...
LG_THINQ_CLIENT_ID=...
LG_THINQ_COUNTRY=IN
LG_THINQ_LANGUAGE=en-IN
```

The Client ID is the generated UUID-style Client ID from ThinQ Connect. Saba does **not** generate a replacement at runtime. The current ThinQ Connect reference expects a PAT, country code and client ID, and uses the ThinQ Open API endpoints for device list, profile, state and control.

## Samsung SmartThings

For a durable OAuth integration use:

```env
SMARTTHINGS_APP_ID=...
SMARTTHINGS_CLIENT_ID=...
SMARTTHINGS_CLIENT_SECRET=...
SMARTTHINGS_REDIRECT_URI=http://127.0.0.1:8000/oauth/callback
```

Start the backend, open `/integrations/smartthings/connect`, approve access, and Saba stores the access/refresh token locally with `0600` file permissions. The requested scopes are device/location read and device execute.

## What Saba can expose to the AI

- Device discovery across both providers.
- Status and capability inspection.
- Capability-aware control.
- Post-command verification when the vendor API permits it.
- Energy telemetry and LG historical energy usage.
- Unified device search by name, model or type.

Never put PATs, OAuth secrets or tokens in Git.
