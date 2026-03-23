"""Zabbix API client.

Connects to a Zabbix server to fetch host and problem data.
Cache is stored in backend/data/zabbix_cache.json.
Config (url, api_token) is stored in backend/data/zabbix_config.json.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

if os.environ.get("ITMANAGER_DATA_DIR"):
    DATA_DIR = Path(os.environ["ITMANAGER_DATA_DIR"]) / "data"
else:
    DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "zabbix_config.json"
CACHE_PATH = DATA_DIR / "zabbix_cache.json"


# ── Config ────────────────────────────────────────────────────

def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("url") and data.get("api_token"):
            return data
    except Exception:
        pass
    return None


def save_config(url: str, api_token: str) -> None:
    CONFIG_PATH.write_text(
        json.dumps({"url": url.rstrip("/"), "api_token": api_token}, indent=2),
        encoding="utf-8",
    )


def delete_config() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def get_masked_config() -> dict | None:
    cfg = load_config()
    if not cfg:
        return None
    token = cfg["api_token"]
    masked = "****" + token[-4:] if len(token) > 4 else "****"
    return {"url": cfg["url"], "api_token": masked}


# ── Zabbix API calls ─────────────────────────────────────────

async def _zabbix_api(url: str, token: str, method: str, params: dict | None = None) -> dict:
    """Call a Zabbix JSON-RPC API method."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }
    headers = {
        "Content-Type": "application/json-rpc",
        "Authorization": f"Bearer {token}",
    }
    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        resp = await client.post(f"{url}/api_jsonrpc.php", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ValueError(f"Zabbix API error: {data['error']}")
        return data.get("result", {})


async def fetch_hosts(url: str, token: str) -> list[dict]:
    """Fetch all monitored hosts with their interfaces."""
    return await _zabbix_api(url, token, "host.get", {
        "output": ["hostid", "host", "name", "status", "description"],
        "selectInterfaces": ["ip"],
        "selectGroups": ["name"],
        "sortfield": "name",
    })


async def fetch_problems(url: str, token: str) -> list[dict]:
    """Fetch current active problems (triggers in problem state)."""
    return await _zabbix_api(url, token, "problem.get", {
        "output": ["eventid", "name", "severity", "clock", "acknowledged"],
        "selectHosts": ["name"],
        "recent": True,
        "sortfield": ["eventid"],
        "sortorder": "DESC",
        "limit": 200,
    })


# ── Cache ─────────────────────────────────────────────────────

def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {"hosts": [], "problems": [], "synced_at": None}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"hosts": [], "problems": [], "synced_at": None}


def save_cache(hosts: list[dict], problems: list[dict]) -> dict:
    data = {
        "hosts": hosts,
        "problems": problems,
        "synced_at": datetime.now().isoformat(timespec="seconds"),
    }
    CACHE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return data


async def sync_all() -> dict:
    """Full sync: fetch hosts + problems from Zabbix and cache."""
    cfg = load_config()
    if not cfg:
        raise ValueError("Zabbix credentials not configured")

    hosts = await fetch_hosts(cfg["url"], cfg["api_token"])
    problems = await fetch_problems(cfg["url"], cfg["api_token"])
    return save_cache(hosts, problems)
