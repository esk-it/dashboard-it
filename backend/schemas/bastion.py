"""Pydantic schemas for the Bastion module (SSH/RDP server management)."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ── Groups ────────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    color_hex: str = "#4B8BFF"

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    color_hex: Optional[str] = None
    sort_order: Optional[int] = None

class GroupResponse(BaseModel):
    id: int
    name: str
    color_hex: str
    sort_order: int
    server_count: int = 0


# ── Servers ───────────────────────────────────────────────────────────────────

class ServerCreate(BaseModel):
    name: str
    hostname: str
    port: int = 22
    username: str = ""
    protocol: str = "SSH"
    group_name: str = ""
    notes: str = ""
    ssh_key_path: str = ""

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    protocol: Optional[str] = None
    group_name: Optional[str] = None
    notes: Optional[str] = None
    ssh_key_path: Optional[str] = None

class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    port: int
    username: str
    protocol: str
    group_name: str
    notes: str
    ssh_key_path: str
    created_at: str
    updated_at: str


# ── Ping ──────────────────────────────────────────────────────────────────────

class PingResult(BaseModel):
    server_id: int
    alive: bool
    latency_ms: int = 0

class PingRequest(BaseModel):
    server_ids: list[int]


# ── Stats ─────────────────────────────────────────────────────────────────────

class BastionStats(BaseModel):
    total: int
    ssh_count: int
    rdp_count: int
    groups_count: int
    by_group: dict[str, int]
