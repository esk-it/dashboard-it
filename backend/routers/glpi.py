from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_raw_db
from ..schemas.glpi import (
    GlpiConfig,
    GlpiConfigResponse,
    GlpiStats,
    GlpiSyncResponse,
)
from ..services.glpi import (
    delete_config,
    get_masked_config,
    load_cache,
    save_config,
    sync_to_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/glpi", tags=["glpi"])


# ── Config ────────────────────────────────────────────────────

@router.get("/config")
async def get_config():
    cfg = get_masked_config()
    if not cfg:
        return {"configured": False, "url": "", "app_token": "", "user_token": ""}
    return GlpiConfigResponse(
        url=cfg["url"],
        app_token=cfg["app_token"],
        user_token=cfg["user_token"],
        configured=True,
    )


@router.put("/config")
async def update_config(body: GlpiConfig):
    if not body.url or not body.app_token or not body.user_token:
        raise HTTPException(400, "url, app_token and user_token are required")
    # Normalize URL: remove trailing slash
    url = body.url.rstrip("/")
    save_config(url, body.app_token, body.user_token)
    return {"status": "ok"}


@router.delete("/config", status_code=204)
async def remove_config():
    delete_config()


# ── Sync ──────────────────────────────────────────────────────

@router.post("/sync", response_model=GlpiSyncResponse)
async def trigger_sync(db=Depends(get_raw_db)):
    try:
        result = await sync_to_db(db)
        return GlpiSyncResponse(**result)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("GLPI sync failed")
        raise HTTPException(502, f"Sync failed: {e}")


# ── Stats ─────────────────────────────────────────────────────

@router.get("/stats", response_model=GlpiStats)
async def glpi_stats():
    cache = load_cache()
    return GlpiStats(
        last_sync=cache.get("synced_at"),
        total_items=len(cache.get("items", [])),
        computers=cache.get("computers", 0),
        monitors=cache.get("monitors", 0),
        printers=cache.get("printers", 0),
    )
