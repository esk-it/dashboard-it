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
    clientVersion: str = ""
    malwareProtection: str = ""
    updatesStatus: str = ""
    groups: list[str] = []
    ipAddress: str = ""
    registeredAt: str = ""


class SecurityStats(BaseModel):
    total: int = 0
    online: int = 0
    offline: int = 0
    protection_alerts: int = 0
    synced_at: Optional[str] = None


class SyncResponse(BaseModel):
    total: int
    synced_at: str
