# SABA Dual-AC IR Setup

The project now treats the HomeMate blaster as one physical IR device with two logical remote slots:

- `ac_1` — AC 1 Remote
- `ac_2` — AC 2 Remote

This does **not** assume that either AC uses the same IR code set. Each remote keeps its own learned-command namespace in `data/ir_commands.json`.

## Current state

- The two remote slots are present in the repository.
- The AI/device layer can identify `AC 1` and `AC 2` separately.
- Learned commands are stored separately for each remote.
- The current `.env` does not need additional IR variables.
- Direct command delivery stays disabled until the exact HomeMate network transport for this physical unit is verified.

## Learning model

When a verified transport is available, save commands with the existing endpoint:

`POST /home/ir/learn`

Example body:

```json
{
  "appliance": "ac_1",
  "name": "power_on",
  "payload": {"transport_specific": "learned data"}
}
```

Use `ac_2` for the second AC. Never copy AC 1's learned data to AC 2 unless the physical remote codes have been independently confirmed identical.

## Physical placement

A single IR blaster can control both ACs only when its IR output has adequate line-of-sight to both indoor units. A central placement is a practical option, but the final position must be validated from the actual room geometry.
