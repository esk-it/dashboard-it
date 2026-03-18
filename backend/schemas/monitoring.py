"""Pydantic models for Zabbix monitoring module."""
from __future__ import annotations

from pydantic import BaseModel


class MonitoringConfig(BaseModel):
    url: str
    api_token: str


class MonitoringConfigResponse(BaseModel):
    configured: bool = False
    url: str = ""
    api_token: str = ""  # masked


class MonitoringHost(BaseModel):
    id: str = ""
    name: str = ""
    host: str = ""           # technical name
    status: str = ""         # enabled / disabled
    available: str = ""      # available / unavailable / unknown
    groups: list[str] = []
    ip: str = ""
    description: str = ""
    last_problem: str = ""


class MonitoringProblem(BaseModel):
    id: str = ""
    host: str = ""
    severity: str = ""       # not_classified / information / warning / average / high / disaster
    name: str = ""           # problem description
    timestamp: str = ""
    acknowledged: bool = False


class MonitoringStats(BaseModel):
    total_hosts: int = 0
    available: int = 0
    unavailable: int = 0
    unknown: int = 0
    active_problems: int = 0
    synced_at: str | None = None


class SyncResponse(BaseModel):
    total_hosts: int = 0
    total_problems: int = 0
    synced_at: str = ""
