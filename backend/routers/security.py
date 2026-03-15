from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..schemas.security import (
    SecurityConfig,
    SecurityConfigResponse,
    SecurityDevice,
    SecurityStats,
    SyncResponse,
)
from ..services.withsecure import (
    delete_config,
    get_masked_config,
    load_cache,
    save_config,
    sync_devices,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security", tags=["security"])


# ── Config ────────────────────────────────────────────────────

@router.get("/config")
async def get_config():
    cfg = get_masked_config()
    if not cfg:
        return {"configured": False, "client_id": "", "client_secret": ""}
    return SecurityConfigResponse(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        configured=True,
    )


@router.put("/config")
async def update_config(body: SecurityConfig):
    if not body.client_id or not body.client_secret:
        raise HTTPException(400, "client_id and client_secret are required")
    save_config(body.client_id, body.client_secret)
    return {"status": "ok"}


@router.delete("/config", status_code=204)
async def remove_config():
    delete_config()


# ── Sync ──────────────────────────────────────────────────────

@router.post("/sync", response_model=SyncResponse)
async def trigger_sync():
    try:
        data = await sync_devices()
        return SyncResponse(total=len(data["devices"]), synced_at=data["synced_at"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("WithSecure sync failed")
        raise HTTPException(502, f"Sync failed: {e}")


# ── Devices ───────────────────────────────────────────────────

def _normalize_device(raw: dict) -> dict:
    """Normalize a raw WithSecure device dict into our schema."""
    props = raw.get("properties", {})
    status = raw.get("status", {})
    return dict(
        id=raw.get("id", ""),
        name=props.get("name", raw.get("name", "")),
        os=props.get("operatingSystem", ""),
        online=status.get("online", False),
        profileName=props.get("profileName", ""),
        clientVersion=props.get("clientOverallVersion", ""),
        malwareProtection=status.get("malwareProtectionStatus", ""),
        updatesStatus=status.get("softwareUpdaterStatus", ""),
        groups=[g.get("name", "") for g in raw.get("groups", [])],
        ipAddress=props.get("ipAddress", ""),
        registeredAt=props.get("registeredAt", ""),
    )


@router.get("/devices", response_model=list[SecurityDevice])
async def list_devices():
    cache = load_cache()
    return [SecurityDevice(**_normalize_device(d)) for d in cache.get("devices", [])]


@router.get("/stats", response_model=SecurityStats)
async def security_stats():
    cache = load_cache()
    devices = cache.get("devices", [])
    total = len(devices)
    online = sum(1 for d in devices if d.get("status", {}).get("online", False))
    offline = total - online
    alerts = sum(
        1 for d in devices
        if d.get("status", {}).get("malwareProtectionStatus", "").lower() not in ("ok", "")
    )
    return SecurityStats(
        total=total, online=online, offline=offline,
        protection_alerts=alerts, synced_at=cache.get("synced_at"),
    )
