from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_raw_db
from ..schemas.security import (
    CrossRefResponse,
    CrossRefStats,
    ProtectedDevice,
    SecurityConfig,
    SecurityConfigResponse,
    SecurityDevice,
    SecurityStats,
    SyncResponse,
    UnknownDevice,
    UnprotectedDevice,
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

def _is_valid_device(raw: dict) -> bool:
    """Filter out empty/invalid entries from the API."""
    return bool(raw.get("id") and raw.get("name"))


def _normalize_device(raw: dict) -> dict:
    """Normalize a raw WithSecure device dict into our schema.

    The WS API returns a flat structure with fields like:
    name, os: {name, version}, online, profileName, clientVersion,
    malwareState, patchOverallState, ipAddresses, registrationTimestamp, etc.
    """
    os_info = raw.get("os") or {}
    os_str = os_info.get("name", "") if isinstance(os_info, dict) else str(os_info)
    os_version = os_info.get("version", "") if isinstance(os_info, dict) else ""
    if os_version:
        os_str = f"{os_str} {os_version}"

    # Subscription info
    sub = raw.get("subscription") or {}
    sub_name = sub.get("name", "") if isinstance(sub, dict) else ""
    sub_key = sub.get("key", "") if isinstance(sub, dict) else ""

    return dict(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        os=os_str,
        online=raw.get("online", False),
        profileName=raw.get("profileName", ""),
        profileState=raw.get("profileState", ""),
        clientVersion=raw.get("clientVersion", ""),
        malwareProtection=raw.get("protectionStatusOverview", raw.get("protectionStatus", "")),
        updatesStatus=raw.get("patchOverallState", ""),
        groups=[],
        ipAddress=raw.get("ipAddresses", raw.get("publicIpAddress", "")),
        registeredAt=raw.get("registrationTimestamp", ""),
        subscriptionName=sub_name,
        subscriptionKey=sub_key,
    )


@router.get("/devices", response_model=list[SecurityDevice])
async def list_devices():
    cache = load_cache()
    return [
        SecurityDevice(**_normalize_device(d))
        for d in cache.get("devices", [])
        if _is_valid_device(d)
    ]


@router.get("/stats", response_model=SecurityStats)
async def security_stats():
    cache = load_cache()
    devices = [d for d in cache.get("devices", []) if _is_valid_device(d)]
    total = len(devices)
    online = sum(1 for d in devices if d.get("online", False))
    offline = total - online
    alerts = sum(
        1 for d in devices
        if d.get("protectionStatus", "").lower() not in ("protected", "")
    )
    return SecurityStats(
        total=total, online=online, offline=offline,
        protection_alerts=alerts, synced_at=cache.get("synced_at"),
    )


# ── Cross-reference Parc × WithSecure ────────────────────────

@router.get("/crossref", response_model=CrossRefResponse)
async def cross_reference(db=Depends(get_raw_db)):
    """Compare Parc equipment with WithSecure devices to find coverage gaps."""
    # 1. Load WithSecure devices from cache
    cache = load_cache()
    ws_devices = [_normalize_device(d) for d in cache.get("devices", []) if _is_valid_device(d)]

    # 2. Load Parc computers (PC-type equipment only)
    cursor = await db.execute(
        """SELECT e.hostname, e.equip_type, e.os, e.serial_number,
                  COALESCE(s.name,'') as site_name,
                  COALESCE(b.name,'') as building_name
           FROM parc_equipment e
           LEFT JOIN parc_sites s ON s.id = e.site_id
           LEFT JOIN parc_buildings b ON b.id = e.building_id
           WHERE e.equip_type IN ('PC', 'Portable', 'Laptop', 'Serveur')
             AND LOWER(COALESCE(e.os,'')) NOT LIKE '%chromeos%'"""
    )
    parc_computers = [dict(row) for row in await cursor.fetchall()]

    # 3. Build lookup maps (case-insensitive hostname)
    parc_by_hostname: dict[str, dict] = {}
    for pc in parc_computers:
        key = (pc["hostname"] or "").strip().upper()
        if key:
            parc_by_hostname[key] = pc

    ws_by_hostname: dict[str, dict] = {}
    ws_by_ip: dict[str, dict] = {}
    for dev in ws_devices:
        key = (dev["name"] or "").strip().upper()
        if key:
            ws_by_hostname[key] = dev
        ip = (dev.get("ipAddress") or "").strip()
        if ip:
            ws_by_ip[ip] = dev

    # 4. Classify
    protected_list: list[ProtectedDevice] = []
    unprotected_list: list[UnprotectedDevice] = []
    matched_ws_keys: set[str] = set()

    for hostname_upper, pc in parc_by_hostname.items():
        ws_match = ws_by_hostname.get(hostname_upper)

        if ws_match:
            matched_ws_keys.add((ws_match["name"] or "").strip().upper())
            protected_list.append(ProtectedDevice(
                hostname=pc["hostname"],
                equip_type=pc["equip_type"],
                os=pc["os"],
                site_name=pc["site_name"],
                ws_name=ws_match["name"],
                ws_online=ws_match.get("online", False),
                ws_malwareProtection=ws_match.get("malwareProtection", ""),
                ws_ipAddress=ws_match.get("ipAddress", ""),
                ws_profileName=ws_match.get("profileName", ""),
            ))
        else:
            unprotected_list.append(UnprotectedDevice(
                hostname=pc["hostname"],
                equip_type=pc["equip_type"],
                os=pc["os"],
                site_name=pc["site_name"],
                building_name=pc["building_name"],
                serial_number=pc["serial_number"],
            ))

    # Unknown: in WithSecure but not in Parc
    unknown_list: list[UnknownDevice] = []
    for dev in ws_devices:
        key = (dev["name"] or "").strip().upper()
        if key and key not in parc_by_hostname:
            unknown_list.append(UnknownDevice(
                ws_name=dev["name"],
                ws_os=dev.get("os", ""),
                ws_online=dev.get("online", False),
                ws_ipAddress=dev.get("ipAddress", ""),
                ws_profileName=dev.get("profileName", ""),
            ))

    total_parc = len(parc_by_hostname)
    n_protected = len(protected_list)
    coverage = (n_protected / total_parc * 100) if total_parc > 0 else 0.0

    return CrossRefResponse(
        stats=CrossRefStats(
            total_parc=total_parc,
            total_ws=len(ws_devices),
            protected=n_protected,
            unprotected=len(unprotected_list),
            unknown=len(unknown_list),
            coverage_percent=round(coverage, 1),
        ),
        protected=protected_list,
        unprotected=unprotected_list,
        unknown=unknown_list,
    )
