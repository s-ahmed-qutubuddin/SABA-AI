from __future__ import annotations

from datetime import date, timedelta
from typing import Any
import re

from integrations_lg import (
    configured as lg_configured,
    lg_control_device,
    lg_device_energy_profile,
    lg_device_energy_usage,
    lg_device_profile,
    lg_device_state,
    lg_find_device,
    lg_list_devices,
)

from integrations_smartthings import (
    configured as st_configured,
    smartthings_device,
    smartthings_device_status,
    smartthings_execute,
    smartthings_find_device,
    smartthings_list_devices,
    smartthings_device_controls,
    smartthings_capability_definition,
)


# ---------------------------------------------------------------------------
# Known local device aliases
# ---------------------------------------------------------------------------
#
# These aliases are ONLY local names.
# They are NOT SmartThings credentials or fake provider IDs.
#
# Add more aliases later as devices are added.
#
KNOWN_DEVICE_ALIASES = {
    "samsung ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "samsung air conditioner": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "room air conditioner": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },

    # Local nickname requested by the assistant/device setup.
    "mother room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "mothers room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "mother's room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "samsung room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "samsung room air conditioner": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "mums room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
    "moms room ac": {
        "provider": "smartthings",
        "device_id": "82bc5724-3285-86cd-c8d8-ff7c68b71866",
    },
}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(k): _json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            _json_safe(v)
            for v in value
        ]

    return str(value)


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()

    text = re.sub(
        r"[^a-z0-9\s'-]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _looks_like_uuid(value: str) -> bool:
    if not isinstance(value, str):
        return False

    return bool(
        re.fullmatch(
            r"[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}",
            value.strip(),
        )
    )


def _is_placeholder_device_id(value: str) -> bool:
    if not isinstance(value, str):
        return True

    value = value.strip().lower()

    if not value:
        return True

    bad_tokens = (
        "placeholder",
        "dummy",
        "example",
        "unknown",
        "device_id_here",
        "your_device_id",
        "mother_room_ac_id_placeholder",
    )

    if any(token in value for token in bad_tokens):
        return True

    return False


def _device_id(device: dict) -> str:
    raw = device.get("raw") or {}

    return str(
        device.get("id")
        or device.get("device_id")
        or device.get("deviceId")
        or raw.get("deviceId")
        or ""
    ).strip()


# ---------------------------------------------------------------------------
# Provider normalization
# ---------------------------------------------------------------------------

def _normalize_lg(d: dict) -> dict:
    info = d.get("deviceInfo") or {}

    return {
        "provider": "lg_thinq",
        "id": d.get("deviceId"),
        "name": info.get("alias") or d.get("deviceId"),
        "model": info.get("modelName"),
        "type": info.get("deviceType")
        or info.get("deviceTypeName"),
        "online": d.get("online")
        if "online" in d
        else None,
        "raw": _json_safe(d),
    }


def _normalize_st(d: dict) -> dict:
    return {
        "provider": "smartthings",
        "id": d.get("deviceId"),
        "name": (
            d.get("label")
            or d.get("name")
            or d.get("deviceId")
        ),
        "model": (
            d.get("deviceModel")
            or d.get("deviceManufacturerCode")
        ),
        "type": d.get("deviceTypeName"),
        "manufacturer": d.get("manufacturerName"),
        "location_id": d.get("locationId"),
        "room_id": d.get("roomId"),
        "raw": _json_safe(d),
    }


# ---------------------------------------------------------------------------
# Device listing
# ---------------------------------------------------------------------------

def home_list_devices() -> dict:
    results: list[dict] = []
    provider_status: dict[str, str] = {}
    errors: list[str] = []

    # LG ThinQ
    try:
        if not lg_configured():
            provider_status["lg_thinq"] = "unconfigured"
        else:
            results.extend(
                _normalize_lg(d)
                for d in lg_list_devices().get("devices", [])
            )

            provider_status["lg_thinq"] = "ok"

    except Exception as exc:
        provider_status["lg_thinq"] = "error"
        errors.append(f"LG ThinQ: {exc}")

    # SmartThings
    try:
        if not st_configured():
            provider_status["smartthings"] = "unconfigured"
        else:
            results.extend(
                _normalize_st(d)
                for d in smartthings_list_devices().get(
                    "devices",
                    [],
                )
            )

            provider_status["smartthings"] = "ok"

    except Exception as exc:
        provider_status["smartthings"] = "error"
        errors.append(f"SmartThings: {exc}")

    return {
        "ok": not errors,
        "devices": results,
        "count": len(results),
        "provider_status": provider_status,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def home_get_status(
    provider: str,
    device_id: str,
    query: str | None = None,
) -> dict:
    provider = _normalise_text(provider)

    if provider == "lg_thinq":
        return lg_device_state(device_id)

    if provider == "smartthings":
        resolved_id, resolved_device = _resolve_smartthings_device(
            device_id=device_id,
            query=query,
        )

        result = smartthings_device_status(
            resolved_id,
            include_health=True,
        )

        result["resolved_device"] = {
            "id": resolved_id,
            "name": (
                resolved_device.get("label")
                or resolved_device.get("name")
                or resolved_id
            ),
            "room_id": resolved_device.get("roomId"),
        }

        return result

    raise ValueError("Unknown home provider")


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def home_get_capabilities(
    provider: str,
    device_id: str,
    query: str | None = None,
) -> dict:
    """Return provider capabilities for a real resolved device."""
    provider = _normalise_text(provider)

    if provider == "lg_thinq":
        return lg_device_profile(device_id)

    if provider == "smartthings":
        resolved_id, resolved_device = _resolve_smartthings_device(
            device_id=device_id,
            query=query,
        )

        result = smartthings_device_controls(resolved_id)
        result["resolved_device"] = {
            "id": resolved_id,
            "provider": "smartthings",
            "name": (
                resolved_device.get("label")
                or resolved_device.get("name")
                or resolved_id
            ),
            "device_type": resolved_device.get("deviceTypeName"),
            "room_id": resolved_device.get("roomId"),
        }
        return result

    raise ValueError("Unknown home provider")


# ---------------------------------------------------------------------------
# Device resolution
# ---------------------------------------------------------------------------

def _resolve_smartthings_device(
    device_id: str | None,
    query: str | None = None,
) -> tuple[str, dict]:
    """
    Resolve a real discovered SmartThings device.

    Current deployment has one SmartThings appliance. If the model sends a
    placeholder or invented UUID and exactly one SmartThings device is
    discovered, resolve to that sole real device instead of ever forwarding
    the invented ID to SmartThings.

    If multiple devices are eventually added, semantic matching/aliases are
    required and ambiguous requests are rejected.
    """
    supplied_id = (device_id or "").strip()
    query_text = _normalise_text(query)

    devices = smartthings_list_devices().get("devices", [])

    # Only accept IDs that are both UUID-shaped and actually discovered.
    if (
        supplied_id
        and not _is_placeholder_device_id(supplied_id)
        and _looks_like_uuid(supplied_id)
    ):
        for device in devices:
            if str(device.get("deviceId", "")).strip() == supplied_id:
                return supplied_id, device

        # Do not fail immediately if a semantic query is available.
        if query_text:
            pass
        elif len(devices) == 1:
            # Current home has exactly one SmartThings device.
            sole = devices[0]
            sole_id = str(sole.get("deviceId", "")).strip()
            if _looks_like_uuid(sole_id):
                return sole_id, sole
        else:
            raise ValueError(
                f"SmartThings device {supplied_id} is not currently discovered."
            )

    # Known local aliases.
    if query_text:
        alias = KNOWN_DEVICE_ALIASES.get(query_text)
        if alias and alias.get("provider") == "smartthings":
            alias_id = str(alias.get("device_id", "")).strip()
            for device in devices:
                if str(device.get("deviceId", "")).strip() == alias_id:
                    return alias_id, device

    # Provider-side search.
    if query_text:
        result = smartthings_find_device(query_text)
        matches = [
            d for d in result.get("matches", [])
            if _looks_like_uuid(str(d.get("deviceId", "")).strip())
        ]

        if len(matches) == 1:
            device = matches[0]
            return str(device["deviceId"]).strip(), device

        if len(matches) > 1:
            names = [
                str(
                    item.get("label")
                    or item.get("name")
                    or item.get("deviceId")
                )
                for item in matches[:5]
            ]
            raise ValueError(
                f"Multiple SmartThings devices match '{query}': "
                f"{', '.join(names)}. Specify the room or appliance."
            )

    # If there is exactly one SmartThings device, it is the only safe fallback
    # for this deployment. This also prevents LLM placeholder IDs from leaking.
    if len(devices) == 1:
        sole = devices[0]
        sole_id = str(sole.get("deviceId", "")).strip()
        if _looks_like_uuid(sole_id):
            return sole_id, sole

    raise ValueError(
        "I could not resolve a real SmartThings device. "
        "Specify the appliance name or room."
    )


# ---------------------------------------------------------------------------
# Home control
# ---------------------------------------------------------------------------

def _normalise_command_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _capability_commands(
    device_id: str,
    capability: str,
) -> tuple[dict, list[dict]]:
    """
    Read one capability definition and return normalized command definitions.
    """
    device = smartthings_device(device_id).get("device") or {}

    version = 1
    for component in device.get("components", []) or []:
        if component.get("id", "main") != "main":
            continue
        for cap in component.get("capabilities", []) or []:
            if cap.get("id") == capability:
                version = int(cap.get("version") or 1)
                break

    definition = smartthings_capability_definition(
        capability,
        version,
    ) or {}

    commands = definition.get("commands") or {}

    rows = []

    if isinstance(commands, dict):
        for name, spec in commands.items():
            spec = spec if isinstance(spec, dict) else {}
            rows.append({
                "name": name,
                "arguments": (
                    spec.get("arguments")
                    or spec.get("parameters")
                    or []
                ),
            })
    elif isinstance(commands, list):
        for item in commands:
            if isinstance(item, dict) and item.get("name"):
                rows.append({
                    "name": item["name"],
                    "arguments": (
                        item.get("arguments")
                        or item.get("parameters")
                        or []
                    ),
                })

    return definition, rows


def _coerce_smartthings_arguments(
    command_row: dict,
    args: list[Any],
) -> list[Any]:
    """
    Normalize model/frontend arguments to the exact SmartThings command
    argument shape.

    SmartThings expects `arguments` to be a list whose entries match the
    command's declared parameter schemas. In particular, many Samsung AC
    commands expect a single STRING value, not a JSON object such as
    {"mode": "cool"}.
    """
    declared = command_row.get("arguments") or []
    incoming = list(args or [])

    if not declared:
        # Commands such as switch.on/off and raiseSetpoint take no arguments.
        return []

    # The common model/tool shape may be:
    #   [{"mode": "cool"}]
    # while SmartThings needs:
    #   ["cool"]
    if len(incoming) == 1 and isinstance(incoming[0], dict):
        obj = incoming[0]

        if len(declared) == 1:
            param_name = str(declared[0].get("name") or "").strip()

            if param_name and param_name in obj:
                incoming = [obj[param_name]]
            elif len(obj) == 1:
                incoming = [next(iter(obj.values()))]

    normalized: list[Any] = []

    for index, spec in enumerate(declared):
        if index >= len(incoming):
            if not spec.get("optional", False):
                raise ValueError(
                    f"SmartThings command '{command_row.get('name')}' "
                    f"requires argument '{spec.get('name')}'."
                )
            break

        value = incoming[index]
        schema = spec.get("schema") or {}
        expected_type = schema.get("type")

        if expected_type == "string":
            if isinstance(value, (dict, list)):
                raise ValueError(
                    f"SmartThings argument '{spec.get('name')}' "
                    "must be a string."
                )
            value = str(value)

        elif expected_type == "integer":
            if isinstance(value, bool):
                raise ValueError(
                    f"SmartThings argument '{spec.get('name')}' "
                    "must be an integer."
                )
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"SmartThings argument '{spec.get('name')}' "
                    "must be an integer."
                )

        elif expected_type == "number":
            if isinstance(value, bool):
                raise ValueError(
                    f"SmartThings argument '{spec.get('name')}' "
                    "must be a number."
                )
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"SmartThings argument '{spec.get('name')}' "
                    "must be a number."
                )

        elif expected_type == "boolean":
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    value = True
                elif lowered in {"false", "0", "no", "off"}:
                    value = False

        # Preserve objects/lists when the provider explicitly declares them.
        normalized.append(value)

    if len(incoming) > len(declared):
        raise ValueError(
            f"SmartThings command '{command_row.get('name')}' expects "
            f"{len(declared)} argument(s), received {len(incoming)}."
        )

    return normalized


def _resolve_smartthings_command(
    device_id: str,
    capability: str,
    action: str,
    args: list[Any],
) -> tuple[str, list[Any]]:
    """
    Convert common natural-language/model aliases into a command exposed by
    the real SmartThings capability definition, while validating/coercing
    arguments to the provider's declared schema.
    """
    action_text = _normalise_command_name(action)
    original_args = list(args or [])

    definition, commands = _capability_commands(
        device_id,
        capability,
    )

    command_names = {
        _normalise_command_name(row["name"]): row
        for row in commands
    }

    def finish(row: dict, candidate_args: list[Any] | None = None) -> tuple[str, list[Any]]:
        return row["name"], _coerce_smartthings_arguments(
            row,
            original_args if candidate_args is None else candidate_args,
        )

    # Exact command first.
    if action_text in command_names:
        return finish(command_names[action_text])

    # Common human-language values/actions.
    simple_action_map = {
        "turnon": ("on", []),
        "on": ("on", []),
        "open": ("on", []),
        "start": ("on", []),
        "turnoff": ("off", []),
        "off": ("off", []),
        "close": ("off", []),
        "stop": ("off", []),
    }

    if action_text in simple_action_map:
        candidate, candidate_args = simple_action_map[action_text]

        if candidate in command_names:
            return finish(
                command_names[candidate],
                candidate_args,
            )

    # AC operating mode.
    if capability == "airConditionerMode":
        values = {"auto", "cool", "dry", "fan"}

        if action_text in values and not original_args:
            original_args = [action_text]
            action_text = "setairconditionermode"

    # AC fan mode.
    elif capability == "airConditionerFanMode":
        values = {
            "auto",
            "low",
            "medium",
            "high",
            "turbo",
        }

        if action_text in values and not original_args:
            original_args = [action_text]
            action_text = "setfanmode"

    # Samsung custom optional AC mode.
    elif capability == "custom.airConditionerOptionalMode":
        values = {
            "off",
            "energysaving",
            "windfree",
            "sleep",
            "windfreesleep",
            "speed",
            "smart",
            "quiet",
            "twostep",
            "comfort",
            "dlightcool",
            "drycomfort",
            "cubepurify",
            "longwind",
            "motionindirect",
            "motiondirect",
        }

        if action_text in values and not original_args:
            original_args = [action_text]

        # Provider uses camelCase enum values.
        enum_map = {
            "energysaving": "energySaving",
            "windfree": "windFree",
            "windfreesleep": "windFreeSleep",
            "twostep": "twoStep",
            "dlightcool": "dlightCool",
            "drycomfort": "dryComfort",
            "cubepurify": "cubePurify",
            "longwind": "longWind",
            "motionindirect": "motionIndirect",
            "motiondirect": "motionDirect",
        }

        if original_args and len(original_args) == 1:
            value = original_args[0]
            if isinstance(value, str):
                original_args = [enum_map.get(
                    _normalise_command_name(value),
                    value,
                )]

        if action_text == "setacoptionalmode":
            pass

    # Samsung custom auto-cleaning mode.
    elif capability == "custom.autoCleaningMode":
        values = {"on", "off"}

        if action_text in values and not original_args:
            original_args = [action_text]

    # Try common set-command naming variants.
    candidates: list[tuple[int, dict]] = []

    if action_text.startswith("set") and action_text in command_names:
        candidates.append(
            (1000, command_names[action_text])
        )

    for row in commands:
        normalized = _normalise_command_name(
            row["name"]
        )

        score = 0

        if action_text == normalized:
            score += 1000
        elif action_text in normalized:
            score += 100
        elif normalized in action_text:
            score += 90

        action_tokens = re.findall(
            r"[a-z]+",
            action.lower(),
        )

        for token in action_tokens:
            if len(token) >= 3 and token in normalized:
                score += 10

        if score:
            candidates.append(
                (score, row)
            )

    if candidates:
        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return finish(
            candidates[0][1],
            original_args,
        )

    # Custom setpoint commands take no arguments.
    if capability == "custom.thermostatSetpointControl":
        if action_text in {
            "raise",
            "raisesetpoint",
            "increase",
            "warmer",
            "temperatureup",
        } and "raisesetpoint" in command_names:
            return finish(
                command_names["raisesetpoint"],
                [],
            )

        if action_text in {
            "lower",
            "lowersetpoint",
            "decrease",
            "cooler",
            "temperaturedown",
        } and "lowersetpoint" in command_names:
            return finish(
                command_names["lowersetpoint"],
                [],
            )

    raise ValueError(
        f"SmartThings capability '{capability}' does not expose "
        f"a command matching '{action}'."
    )


def home_control(
    provider: str,
    device_id: str,
    command: dict,
) -> dict:

    provider = _normalise_text(provider)

    if not isinstance(command, dict):
        raise ValueError(
            "Home control command must be an object."
        )

    if provider == "lg_thinq":
        result = lg_control_device(
            device_id,
            command,
        )

        try:
            result["verified_state"] = (
                lg_device_state(device_id).get("state")
            )
        except Exception as exc:
            result["verification_error"] = str(exc)

        return result

    if provider != "smartthings":
        raise ValueError(
            f"Unknown home provider: {provider}"
        )

    capability = command.get("capability")
    action = command.get("command")

    args = command.get("arguments")
    if args is None:
        args = command.get("args")
    if args is None:
        args = []

    if not isinstance(args, list):
        raise ValueError(
            "SmartThings command arguments must be a list."
        )

    if not capability:
        raise ValueError(
            "SmartThings control requires capability."
        )

    if not action:
        raise ValueError(
            "SmartThings control requires command."
        )

    device_query = (
        command.get("device_query")
        or command.get("device_name")
        or command.get("room")
        or command.get("query")
    )

    resolved_id, resolved_device = (
        _resolve_smartthings_device(
            device_id=device_id,
            query=device_query,
        )
    )

    resolved_command, resolved_args = (
        _resolve_smartthings_command(
            resolved_id,
            capability,
            action,
            args,
        )
    )

    # Ask SmartThings for the device's controls so unavailable commands are
    # never intentionally executed.
    try:
        controls = smartthings_device_controls(
            resolved_id
        )
        unavailable = set(
            controls.get("unavailable_commands")
            or []
        )

        if f"{capability}.{resolved_command}" in unavailable:
            raise ValueError(
                f"SmartThings reports {capability}.{resolved_command} "
                "as unavailable on this device."
            )
    except ValueError:
        raise
    except Exception:
        # Capability-control metadata is supplemental. Execution still uses
        # the provider's authoritative command endpoint.
        pass

    result = smartthings_execute(
        resolved_id,
        capability,
        resolved_command,
        resolved_args,
        command.get("component") or "main",
    )

    result["resolved_device"] = {
        "id": resolved_id,
        "provider": "smartthings",
        "name": (
            resolved_device.get("label")
            or resolved_device.get("name")
            or resolved_id
        ),
        "device_type": resolved_device.get(
            "deviceTypeName"
        ),
        "room_id": resolved_device.get(
            "roomId"
        ),
    }

    result["resolved_command"] = {
        "capability": capability,
        "command": resolved_command,
        "arguments": resolved_args,
    }

    # Verify final device state after successful command execution.
    try:
        result["verified_status"] = (
            smartthings_device_status(
                resolved_id,
                include_health=True,
            ).get("status")
        )
    except Exception as exc:
        result["verification_error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Device search
# ---------------------------------------------------------------------------

def home_find(query: str) -> dict:

    matches: list[dict] = []
    errors: list[str] = []

    query = query.strip()

    # LG
    try:
        provider_matches = (
            lg_find_device(
                query
            ).get("matches", [])
        )

        matches.extend(
            _normalize_lg(d)
            for d in provider_matches
        )

    except Exception as exc:
        errors.append(
            f"LG ThinQ: {exc}"
        )

    # SmartThings
    try:
        provider_matches = (
            smartthings_find_device(
                query
            ).get("matches", [])
        )

        matches.extend(
            _normalize_st(d)
            for d in provider_matches
        )

    except Exception as exc:
        errors.append(
            f"SmartThings: {exc}"
        )

    # Local aliases
    normalised_query = _normalise_text(
        query
    )

    alias = KNOWN_DEVICE_ALIASES.get(
        normalised_query
    )

    if alias:
        try:
            devices = (
                smartthings_list_devices()
                .get("devices", [])
            )

            for device in devices:
                if (
                    device.get("deviceId")
                    == alias["device_id"]
                ):
                    matches.append(
                        _normalize_st(device)
                    )

        except Exception as exc:
            errors.append(
                f"SmartThings alias: {exc}"
            )

    # Remove duplicate devices.
    unique: dict[tuple[str, str], dict] = {}

    for item in matches:
        key = (
            item.get("provider", ""),
            item.get("id", ""),
        )

        unique[key] = item

    return {
        "ok": True,
        "matches": _json_safe(
            list(unique.values())
        ),
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Energy helpers
# ---------------------------------------------------------------------------

def _find_energy_values(
    value: Any,
    path: str = "",
) -> list[dict]:

    found: list[dict] = []

    if isinstance(value, dict):

        for key, child in value.items():

            key_path = (
                f"{path}.{key}"
                if path
                else str(key)
            )

            if (
                isinstance(
                    child,
                    (int, float),
                )
                and any(
                    token in str(key).lower()
                    for token in (
                        "energy",
                        "power",
                        "kwh",
                        "watt",
                        "consumption",
                    )
                )
            ):
                found.append(
                    {
                        "path": key_path,
                        "value": child,
                    }
                )

            found.extend(
                _find_energy_values(
                    child,
                    key_path,
                )
            )

    elif isinstance(value, list):

        for idx, child in enumerate(value):

            found.extend(
                _find_energy_values(
                    child,
                    f"{path}[{idx}]",
                )
            )

    return found


def home_get_energy(
    provider: str,
    device_id: str,
    query: str | None = None,
) -> dict:

    provider = _normalise_text(provider)

    if provider == "lg_thinq":
        try:
            profile = lg_device_energy_profile(
                device_id
            )
        except Exception:
            profile = {"profile": {}}

        status = lg_device_state(
            device_id
        )

        values = _find_energy_values(
            {
                "profile": profile,
                "status": status,
            }
        )

        return {
            "ok": True,
            "provider": provider,
            "device_id": device_id,
            "energy_profile": profile.get("profile"),
            "energy_values": values,
        }

    if provider == "smartthings":
        resolved_id, resolved_device = (
            _resolve_smartthings_device(
                device_id=device_id,
                query=query,
            )
        )

        status = smartthings_device_status(
            resolved_id,
            include_health=True,
        )

        values = _find_energy_values(
            status.get("status") or status
        )

        return {
            "ok": True,
            "provider": provider,
            "device_id": resolved_id,
            "device_name": (
                resolved_device.get("label")
                or resolved_device.get("name")
            ),
            "energy_values": values,
            "raw_status": status.get("status"),
        }

    raise ValueError(
        "Unknown home provider"
    )


def home_get_energy_usage(
    provider: str,
    device_id: str,
    energy_property: str,
    period: str = "DAY",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:

    if provider != "lg_thinq":
        return home_get_energy(
            provider,
            device_id,
        )

    end = (
        date.fromisoformat(end_date)
        if end_date
        else date.today()
    )

    start = (
        date.fromisoformat(start_date)
        if start_date
        else end - timedelta(days=1)
    )

    return lg_device_energy_usage(
        device_id,
        energy_property,
        period,
        start.isoformat(),
        end.isoformat(),
    )


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def home_estimate_cost(
    kwh: float,
    tariff_per_kwh: float | None = None,
) -> dict:
    """Estimate a household bill using the configured Telangana schedule.

    tariff_per_kwh is retained only for backwards compatibility. When omitted,
    or when the caller asks for a bill, the configured progressive schedule is used.
    """
    from tariff import estimate_household_bill

    if kwh < 0:
        raise ValueError("kWh must be non-negative")

    result = estimate_household_bill(float(kwh))
    result["legacy_tariff_argument"] = tariff_per_kwh
    return result


def home_estimate_ac_cost(
    ac_kwh: float,
    household_kwh: float,
) -> dict:
    from tariff import estimate_ac_share
    return estimate_ac_share(float(ac_kwh), float(household_kwh))
