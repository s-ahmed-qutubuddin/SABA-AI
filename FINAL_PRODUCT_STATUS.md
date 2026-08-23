# SABA — Final Product Baseline

## Master build
`SABA_FINAL_DEPLOYABLE` is now the single canonical SABA repository.

## Runtime
Use one command from the repository root:

```bash
python3 run.py
```

The launcher creates/uses `.venv`, installs backend dependencies, installs frontend dependencies, starts FastAPI, starts Vite, waits for readiness, opens the browser, and tears down child processes on exit.

## Unified device architecture
All home control now passes through one normalized surface in `home_tools.py`:

- LG ThinQ
- Samsung SmartThings
- IR / HomeMate transport

The UI and AI call provider-neutral actions. Provider-specific protocols stay inside adapters.

## IR status
The IR adapter is intentionally real but transport-neutral. It supports:

- configurable HTTP/webhook control transport
- named learned-command storage in `data/ir_commands.json`
- appliance aliases through `data/ir_devices.json`
- optional status verification endpoint
- explicit unconfigured / unverifiable states

Do not set `IR_BACKEND` to a made-up endpoint. First verify the actual HomeMate/Tuya transport for the physical blaster, then configure `IR_BASE_URL` and paths. Current Tuya documentation exposes universal-IR cloud APIs and current community reverse-engineering shows local IR command/keydata flows, but the exact HomeMate hardware revision and local endpoint must still be verified before SABA can claim direct control. 

## Truthfulness rule
SABA never reports a device command as successfully executed merely because the AI requested it. A provider adapter must return a successful transport response. Where a fresh status read is available, SABA also reports verification; otherwise it explicitly says the appliance state could not be independently verified.

## Production boundary
This is the canonical application baseline, not a claim that every physical appliance is already wired. The remaining hardware task is the verified HomeMate/IR transport. Once that transport is confirmed, its endpoint/command mapping belongs in the IR adapter and the same SABA device layer is reused.
