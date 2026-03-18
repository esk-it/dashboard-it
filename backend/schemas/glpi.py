from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class GlpiConfig(BaseModel):
    url: str  # e.g. "https://glpi.example.com"
    app_token: str
    user_token: str


class GlpiConfigResponse(BaseModel):
    url: str
    app_token: str  # masked
    user_token: str  # masked
    configured: bool = True


class GlpiSyncResponse(BaseModel):
    total: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    synced_at: str = ""


class GlpiStats(BaseModel):
    last_sync: Optional[str] = None
    total_items: int = 0
    computers: int = 0
    monitors: int = 0
    printers: int = 0
