from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SecurityConfig(BaseModel):
    client_id: str
    client_secret: str  # masked on GET, full on PUT


class SecurityConfigResponse(BaseModel):
    client_id: str
    client_secret: str  # masked: ****xxxx
    configured: bool = True


class SecurityDevice(BaseModel):
    id: str = ""
    name: str = ""
    os: str = ""
    online: bool = False
    profileName: str = ""
    profileState: str = ""
    clientVersion: str = ""
    malwareProtection: str = ""
    updatesStatus: str = ""
    groups: list[str] = []
    ipAddress: str = ""
    registeredAt: str = ""
    subscriptionName: str = ""
    subscriptionKey: str = ""


class SecurityStats(BaseModel):
    total: int = 0
    online: int = 0
    offline: int = 0
    protection_alerts: int = 0
    synced_at: Optional[str] = None


class SyncResponse(BaseModel):
    total: int
    synced_at: str


# ── Cross-reference Parc × WithSecure ─────────────────────

class CrossRefStats(BaseModel):
    total_parc: int = 0
    total_ws: int = 0
    protected: int = 0
    unprotected: int = 0
    unknown: int = 0
    coverage_percent: float = 0.0


class ProtectedDevice(BaseModel):
    hostname: str = ""
    equip_type: str = ""
    os: str = ""
    site_name: str = ""
    ws_name: str = ""
    ws_online: bool = False
    ws_malwareProtection: str = ""
    ws_ipAddress: str = ""


class UnprotectedDevice(BaseModel):
    hostname: str = ""
    equip_type: str = ""
    os: str = ""
    site_name: str = ""
    building_name: str = ""
    serial_number: str = ""


class UnknownDevice(BaseModel):
    ws_name: str = ""
    ws_os: str = ""
    ws_online: bool = False
    ws_ipAddress: str = ""
    ws_profileName: str = ""


class CrossRefResponse(BaseModel):
    stats: CrossRefStats = CrossRefStats()
    protected: list[ProtectedDevice] = []
    unprotected: list[UnprotectedDevice] = []
    unknown: list[UnknownDevice] = []
