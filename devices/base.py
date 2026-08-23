from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass
class DeviceCommandResult:
    ok: bool
    provider: str
    device_id: str
    command: dict[str, Any]
    verified: bool = False
    verification_error: str | None = None
    response: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class DeviceAdapter(Protocol):
    provider: str
    def configured(self) -> bool: ...
    def list_devices(self) -> dict[str, Any]: ...
    def get_status(self, device_id: str) -> dict[str, Any]: ...
    def get_capabilities(self, device_id: str) -> dict[str, Any]: ...
    def control(self, device_id: str, command: dict[str, Any]) -> dict[str, Any]: ...
