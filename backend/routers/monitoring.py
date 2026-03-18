"""Monitoring (Zabbix) router — hosts, problems, stats."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..schemas.monitoring import (
    MonitoringConfig,
    MonitoringConfigResponse,
    MonitoringHost,
    MonitoringProblem,
    MonitoringStats,
    SyncResponse,
)
from ..services.zabbix import (
    delete_config,
    get_masked_config,
    load_cache,
    save_config,
    sync_all,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ── Config ────────────────────────────────────────────────────

@router.get("/config")
async def get_config():
    cfg = get_masked_config()
    if not cfg:
        return {"configured": False, "url": "", "api_token": ""}
    return MonitoringConfigResponse(url=cfg["url"], api_token=cfg["api_token"], configured=True)


@router.put("/config")
async def update_config(body: MonitoringConfig):
    if not body.url or not body.api_token:
        raise HTTPException(400, "url and api_token are required")
    save_config(body.url, body.api_token)
    return {"status": "ok"}


@router.delete("/config", status_code=204)
async def remove_config():
    delete_config()


# ── Sync ──────────────────────────────────────────────────────

@router.post("/sync", response_model=SyncResponse)
async def trigger_sync():
    try:
        data = await sync_all()
        return SyncResponse(
            total_hosts=len(data["hosts"]),
            total_problems=len(data["problems"]),
            synced_at=data["synced_at"],
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Zabbix sync failed")
        raise HTTPException(502, f"Sync failed: {e}")


# ── Hosts ─────────────────────────────────────────────────────

def _normalize_host(raw: dict) -> dict:
    """Map raw Zabbix host to our schema."""
    interfaces = raw.get("interfaces") or []
    ip = interfaces[0].get("ip", "") if interfaces else ""
    groups = [g.get("name", "") for g in (raw.get("groups") or [])]

    # status: 0 = enabled, 1 = disabled
    status = "enabled" if str(raw.get("status")) == "0" else "disabled"

    return dict(
        id=raw.get("hostid", ""),
        name=raw.get("name", ""),
        host=raw.get("host", ""),
        status=status,
        available="",  # availability comes from host.get with selectInterfaces
        groups=groups,
        ip=ip,
        description=raw.get("description", ""),
        last_problem="",
    )


@router.get("/hosts", response_model=list[MonitoringHost])
async def list_hosts():
    cache = load_cache()
    return [MonitoringHost(**_normalize_host(h)) for h in cache.get("hosts", [])]


# ── Problems ──────────────────────────────────────────────────

_SEVERITY_MAP = {
    "0": "non classé",
    "1": "information",
    "2": "avertissement",
    "3": "moyen",
    "4": "élevé",
    "5": "catastrophe",
}


def _normalize_problem(raw: dict) -> dict:
    hosts = raw.get("hosts") or []
    host_name = hosts[0].get("name", "") if hosts else ""
    sev = _SEVERITY_MAP.get(str(raw.get("severity", "0")), "inconnu")

    from datetime import datetime
    ts = raw.get("clock", "")
    try:
        ts = datetime.fromtimestamp(int(ts)).isoformat(timespec="seconds") if ts else ""
    except (ValueError, OSError):
        pass

    return dict(
        id=raw.get("eventid", ""),
        host=host_name,
        severity=sev,
        name=raw.get("name", ""),
        timestamp=ts,
        acknowledged=str(raw.get("acknowledged")) == "1",
    )


@router.get("/problems", response_model=list[MonitoringProblem])
async def list_problems():
    cache = load_cache()
    return [MonitoringProblem(**_normalize_problem(p)) for p in cache.get("problems", [])]


# ── Stats ─────────────────────────────────────────────────────

@router.get("/stats", response_model=MonitoringStats)
async def monitoring_stats():
    cache = load_cache()
    hosts = cache.get("hosts", [])
    problems = cache.get("problems", [])

    enabled = [h for h in hosts if str(h.get("status")) == "0"]
    total = len(enabled)

    return MonitoringStats(
        total_hosts=total,
        available=total,  # refined when availability data is present
        unavailable=0,
        unknown=0,
        active_problems=len(problems),
        synced_at=cache.get("synced_at"),
    )
