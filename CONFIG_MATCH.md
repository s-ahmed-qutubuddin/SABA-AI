# Configuration Match

This release's root `.env.example` intentionally matches the variable set currently provided for this SABA installation. It does not require the extra LG API-key, SmartThings app/token, OmniRoute, or IR endpoint variables that existed in older examples.

The application code still tolerates optional legacy variables when present, but they are not part of the required local configuration.

The HomeMate dual-AC setup is stored under `data/` so the current `.env` does not need new IR variables before the physical transport is verified.
