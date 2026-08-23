# Saba App Phase

This package is intended to be the near-ready local Mac application baseline.

## One-click start
Double-click `START_SABA_APP.command`.

It will create the Python environment if needed, install backend dependencies, install frontend dependencies if needed, start FastAPI, start the local clap companion, and launch the Vite frontend.

## Required secrets
Keep real secrets only in `.env`.

- `GEMINI_API_KEY`
- MySQL credentials
- `SABA_CREATOR_ACTIVATION_SECRET`
- `LG_THINQ_PAT` plus LG developer client headers when required
- `SMARTTHINGS_ACCESS_TOKEN` for testing, or SmartThings OAuth refresh credentials for unattended use
