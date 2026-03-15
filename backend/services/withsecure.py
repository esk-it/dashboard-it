"""WithSecure Elements API client.

Uses OAuth2 client credentials to fetch device inventory.
Cache is stored in backend/data/withsecure_cache.json.
Config (client_id, client_secret) is stored in backend/data/withsecure_config.json.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "withsecure_config.json"
CACHE_PATH = DATA_DIR / "withsecure_cache.json"

TOKEN_URL = "https://api.connect.withsecure.com/as/token.oauth2"
DEVICES_URL = "https://api.connect.withsecure.com/devices/v1/devices"


# ── Config ────────────────────────────────────────────────────

def load_config() -> dict | None:
    """Load saved credentials. Returns dict with client_id/client_secret or None."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("client_id") and data.get("client_secret"):
            return data
    except Exception:
        pass
    return None


def save_config(client_id: str, client_secret: str) -> None:
    CONFIG_PATH.write_text(
        json.dumps({"client_id": client_id, "client_secret": client_secret}, indent=2),
        encoding="utf-8",
    )


def delete_config() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def get_masked_config() -> dict | None:
    """Return config with secret masked (only last 4 chars visible)."""
    cfg = load_config()
    if not cfg:
        return None
    secret = cfg["client_secret"]
    masked = "****" + secret[-4:] if len(secret) > 4 else "****"
    return {"client_id": cfg["client_id"], "client_secret": masked}


# ── OAuth2 token ──────────────────────────────────────────────

async def _get_token(client_id: str, client_secret: str) -> str:
    """Obtain OAuth2 access token using client credentials grant."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


# ── Fetch devices ─────────────────────────────────────────────

async def fetch_devices(client_id: str, client_secret: str) -> list[dict]:
    """Fetch all devices from WithSecure API with pagination."""
    token = await _get_token(client_id, client_secret)

    all_devices: list[dict] = []
    anchor: str | None = None

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params: dict = {"limit": 100}
            if anchor:
                params["anchor"] = anchor

            resp = await client.get(
                DEVICES_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            all_devices.extend(items)

            anchor = data.get("nextAnchor")
            if not anchor or len(items) == 0:
                break

    return all_devices


# ── Cache ─────────────────────────────────────────────────────

def load_cache() -> dict:
    """Load cached devices. Returns {devices: [...], synced_at: '...'}."""
    if not CACHE_PATH.exists():
        return {"devices": [], "synced_at": None}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"devices": [], "synced_at": None}


def save_cache(devices: list[dict]) -> dict:
    """Save devices to cache with timestamp."""
    data = {
        "devices": devices,
        "synced_at": datetime.now().isoformat(timespec="seconds"),
    }
    CACHE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return data


async def sync_devices() -> dict:
    """Full sync: fetch from API and save to cache. Returns cache data."""
    cfg = load_config()
    if not cfg:
        raise ValueError("WithSecure credentials not configured")

    devices = await fetch_devices(cfg["client_id"], cfg["client_secret"])
    return save_cache(devices)
