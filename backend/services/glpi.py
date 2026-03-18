"""GLPI REST API client.

Uses App-Token + User-Token authentication to fetch equipment inventory
(computers, monitors, printers).
Config stored in backend/data/glpi_config.json.
Cache stored in backend/data/glpi_cache.json.
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

CONFIG_PATH = DATA_DIR / "glpi_config.json"
CACHE_PATH = DATA_DIR / "glpi_cache.json"

PAGE_SIZE = 50


# ── Config ────────────────────────────────────────────────────

def load_config() -> dict | None:
    """Load saved credentials. Returns dict with url/app_token/user_token or None."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("url") and data.get("app_token") and data.get("user_token"):
            return data
    except Exception:
        pass
    return None


def save_config(url: str, app_token: str, user_token: str) -> None:
    CONFIG_PATH.write_text(
        json.dumps({"url": url, "app_token": app_token, "user_token": user_token}, indent=2),
        encoding="utf-8",
    )


def delete_config() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def get_masked_config() -> dict | None:
    """Return config with tokens masked (only last 4 chars visible)."""
    cfg = load_config()
    if not cfg:
        return None

    def _mask(val: str) -> str:
        return "****" + val[-4:] if len(val) > 4 else "****"

    return {
        "url": cfg["url"],
        "app_token": _mask(cfg["app_token"]),
        "user_token": _mask(cfg["user_token"]),
    }


# ── Session management ────────────────────────────────────────

async def _init_session(client: httpx.AsyncClient, url: str, app_token: str, user_token: str) -> str:
    """POST initSession → returns session_token."""
    resp = await client.get(
        f"{url}/apirest.php/initSession",
        headers={
            "App-Token": app_token,
            "Authorization": f"user_token {user_token}",
        },
    )
    resp.raise_for_status()
    return resp.json()["session_token"]


async def _kill_session(client: httpx.AsyncClient, url: str, app_token: str, session_token: str) -> None:
    """GET killSession."""
    try:
        await client.get(
            f"{url}/apirest.php/killSession",
            headers={
                "App-Token": app_token,
                "Session-Token": session_token,
            },
        )
    except Exception:
        pass  # best effort


def _api_headers(app_token: str, session_token: str) -> dict:
    return {
        "App-Token": app_token,
        "Session-Token": session_token,
        "Content-Type": "application/json",
    }


# ── Paginated fetch ───────────────────────────────────────────

async def _fetch_items(
    client: httpx.AsyncClient,
    url: str,
    app_token: str,
    session_token: str,
    item_type: str,
) -> list[dict]:
    """Fetch all items of a given type with range-based pagination.

    GLPI may return fewer items than requested (server-side limit),
    so we use the Content-Range header to know when we've fetched everything.
    """
    all_items: list[dict] = []
    offset = 0
    headers = _api_headers(app_token, session_token)
    total = None

    while True:
        end = offset + PAGE_SIZE - 1

        resp = await client.get(
            f"{url}/apirest.php/{item_type}",
            headers=headers,
            params={"range": f"{offset}-{end}"},
        )

        # 200 or 206 = data; 416 = range not satisfiable (no more data)
        if resp.status_code == 416:
            break
        resp.raise_for_status()

        # Parse Content-Range to get total count (e.g. "0-49/449")
        content_range = resp.headers.get("Content-Range", "")
        if "/" in content_range:
            try:
                total = int(content_range.split("/")[1])
            except (ValueError, IndexError):
                pass

        data = resp.json()
        if isinstance(data, list):
            all_items.extend(data)
            offset += len(data)
            # Stop if we've reached the total or got no data
            if len(data) == 0 or (total and offset >= total):
                break
        else:
            break

    logger.info("Fetched %d %s items (total reported: %s)", len(all_items), item_type, total)
    return all_items


# ── FK resolution (batch) ─────────────────────────────────────

async def _resolve_fk_names(
    client: httpx.AsyncClient,
    url: str,
    app_token: str,
    session_token: str,
    item_type: str,
    ids: set[int],
) -> dict[int, str]:
    """Batch-resolve FK IDs to names. Returns {id: name}."""
    if not ids:
        return {}

    result: dict[int, str] = {}
    headers = _api_headers(app_token, session_token)

    # Fetch all at once (GLPI usually has < 1000 entries per type)
    headers["Range"] = "0-9999"
    try:
        resp = await client.get(
            f"{url}/apirest.php/{item_type}",
            headers=headers,
        )
        if resp.status_code in (200, 206):
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    item_id = item.get("id")
                    if item_id in ids:
                        result[item_id] = item.get("name", item.get("completename", ""))
    except Exception as e:
        logger.warning("Failed to resolve %s: %s", item_type, e)

    return result


# ── Mapping ───────────────────────────────────────────────────

_TYPE_MAP = {
    "Computer": "PC",
    "Monitor": "Moniteur",
    "Printer": "Imprimante",
}

_MODEL_TYPE_MAP = {
    "Computer": "ComputerModel",
    "Monitor": "MonitorModel",
    "Printer": "PrinterModel",
}


def _map_item(raw: dict, item_type: str, lookups: dict) -> dict:
    """Map a GLPI item to parc_equipment fields.

    If expand_dropdowns=true was used, FK fields may already be strings.
    Otherwise we fall back to the lookup tables.
    """
    def _resolve(field: str, lookup_name: str) -> str:
        val = raw.get(field, "")
        if isinstance(val, str) and val:
            return val
        if isinstance(val, int) and val > 0:
            return lookups.get(lookup_name, {}).get(val, "")
        return ""

    name = raw.get("name", "")
    serial = raw.get("serial", "")

    # OS — resolved via Item_OperatingSystem lookup (populated in fetch_all)
    os_val = ""
    if item_type == "Computer":
        os_val = _resolve("operatingsystems_id", "OperatingSystem")
        if not os_val:
            os_val = lookups.get("_os_by_computer", {}).get(raw.get("id"), "")

    brand = _resolve("manufacturers_id", "Manufacturer")
    model_key = _MODEL_TYPE_MAP.get(item_type, "ComputerModel")
    model_field = {
        "Computer": "computermodels_id",
        "Monitor": "monitormodels_id",
        "Printer": "printermodels_id",
    }.get(item_type, "computermodels_id")
    model = _resolve(model_field, model_key)

    location = _resolve("locations_id", "Location")

    # Keep raw locations_id for DB location mapping
    locations_id = raw.get("locations_id")
    if isinstance(locations_id, str):
        locations_id = None  # expand_dropdowns turned it into a string

    # User — resolved via Users lookup
    user_val = ""
    users_id = raw.get("users_id")
    if isinstance(users_id, int) and users_id > 0:
        user_val = lookups.get("_users", {}).get(users_id, "")

    return {
        "hostname": name,
        "equip_type": _TYPE_MAP.get(item_type, "PC"),
        "os": os_val,
        "serial_number": serial,
        "brand": brand,
        "model": model,
        "source": "glpi",
        "glpi_id": raw.get("id"),
        "glpi_location": location,
        "glpi_locations_id": locations_id if isinstance(locations_id, int) and locations_id > 0 else None,
        "last_user": user_val,
    }


# ── Full fetch ────────────────────────────────────────────────

async def fetch_all(url: str, app_token: str, user_token: str) -> dict:
    """Fetch computers, monitors and printers from GLPI.

    Returns {"computers": [...], "monitors": [...], "printers": [...], "mapped": [...]}
    where mapped contains parc_equipment-ready dicts.
    """
    async with httpx.AsyncClient(timeout=60, verify=False) as client:
        session_token = await _init_session(client, url, app_token, user_token)

        try:
            # Fetch raw items
            computers = await _fetch_items(client, url, app_token, session_token, "Computer")
            monitors = await _fetch_items(client, url, app_token, session_token, "Monitor")
            printers = await _fetch_items(client, url, app_token, session_token, "Printer")

            # Collect FK IDs that need resolution (only if expand_dropdowns didn't work)
            # We try expand_dropdowns=true first, but build fallback lookups
            all_items = (
                [(i, "Computer") for i in computers]
                + [(i, "Monitor") for i in monitors]
                + [(i, "Printer") for i in printers]
            )

            # Check if we need FK resolution (if any FK field is still an int)
            needs_resolution = False
            fk_ids: dict[str, set[int]] = {
                "Manufacturer": set(),
                "OperatingSystem": set(),
                "ComputerModel": set(),
                "MonitorModel": set(),
                "PrinterModel": set(),
                "Location": set(),
            }
            for item, itype in all_items:
                for field, fk_type in [
                    ("manufacturers_id", "Manufacturer"),
                    ("operatingsystems_id", "OperatingSystem"),
                    ("locations_id", "Location"),
                ]:
                    val = item.get(field)
                    if isinstance(val, int) and val > 0:
                        fk_ids[fk_type].add(val)
                        needs_resolution = True

                model_field = {
                    "Computer": "computermodels_id",
                    "Monitor": "monitormodels_id",
                    "Printer": "printermodels_id",
                }.get(itype, "computermodels_id")
                model_type = _MODEL_TYPE_MAP.get(itype, "ComputerModel")
                val = item.get(model_field)
                if isinstance(val, int) and val > 0:
                    fk_ids[model_type].add(val)
                    needs_resolution = True

            lookups: dict[str, dict[int, str]] = {}
            if needs_resolution:
                for fk_type, ids in fk_ids.items():
                    if ids:
                        lookups[fk_type] = await _resolve_fk_names(
                            client, url, app_token, session_token, fk_type, ids
                        )

            # Fetch Item_OperatingSystem → build computer_id → OS name lookup
            item_os_list = await _fetch_items(client, url, app_token, session_token, "Item_OperatingSystem")
            os_id_set: set[int] = set()
            for ios in item_os_list:
                os_id = ios.get("operatingsystems_id")
                if isinstance(os_id, int) and os_id > 0:
                    os_id_set.add(os_id)
            # Resolve OS names
            os_names = {}
            if os_id_set:
                os_names = await _resolve_fk_names(
                    client, url, app_token, session_token, "OperatingSystem", os_id_set
                )
            # Map computer_id → OS name
            os_by_computer: dict[int, str] = {}
            for ios in item_os_list:
                comp_id = ios.get("items_id")
                os_id = ios.get("operatingsystems_id")
                if comp_id and isinstance(os_id, int) and os_id > 0:
                    os_by_computer[comp_id] = os_names.get(os_id, "")
            lookups["_os_by_computer"] = os_by_computer

            # Fetch Users → build user_id → "Prénom NOM" lookup
            users_list = await _fetch_items(client, url, app_token, session_token, "User")
            users_lookup: dict[int, str] = {}
            for u in users_list:
                uid = u.get("id")
                if uid:
                    firstname = (u.get("firstname") or "").strip()
                    realname = (u.get("realname") or "").strip()
                    if firstname and realname:
                        users_lookup[uid] = f"{firstname} {realname}"
                    elif realname:
                        users_lookup[uid] = realname
                    elif firstname:
                        users_lookup[uid] = firstname
                    else:
                        users_lookup[uid] = u.get("name", "")
            lookups["_users"] = users_lookup

            # Fetch all locations for site/building/room mapping
            locations = await _fetch_items(client, url, app_token, session_token, "Location")
            locations_by_id: dict[int, dict] = {}
            for loc in locations:
                loc_id = loc.get("id")
                if loc_id:
                    locations_by_id[loc_id] = {
                        "id": loc_id,
                        "name": loc.get("name", ""),
                        "completename": loc.get("completename", ""),
                        "level": loc.get("level", 0),
                    }

            # Map all items
            mapped = []
            for item, itype in all_items:
                mapped.append(_map_item(item, itype, lookups))

        finally:
            await _kill_session(client, url, app_token, session_token)

    return {
        "computers": computers,
        "monitors": monitors,
        "printers": printers,
        "mapped": mapped,
        "locations": locations_by_id,
    }


# ── Cache ─────────────────────────────────────────────────────

def load_cache() -> dict:
    """Load cached GLPI data."""
    if not CACHE_PATH.exists():
        return {"items": [], "synced_at": None, "computers": 0, "monitors": 0, "printers": 0}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"items": [], "synced_at": None, "computers": 0, "monitors": 0, "printers": 0}


def save_cache(data: dict) -> dict:
    """Save GLPI fetch results to cache."""
    cache = {
        "items": data.get("mapped", []),
        "computers": len(data.get("computers", [])),
        "monitors": len(data.get("monitors", [])),
        "printers": len(data.get("printers", [])),
        "synced_at": datetime.now().isoformat(timespec="seconds"),
    }
    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str), encoding="utf-8")
    return cache


# ── Sync to database ─────────────────────────────────────────

async def sync_to_db(db) -> dict:
    """Fetch from GLPI API and upsert into parc_equipment.

    Returns {total, created, updated, unchanged, synced_at}.
    """
    cfg = load_config()
    if not cfg:
        raise ValueError("GLPI credentials not configured")

    # Fetch all from GLPI
    data = await fetch_all(cfg["url"], cfg["app_token"], cfg["user_token"])
    cache = save_cache(data)

    mapped_items = data["mapped"]
    locations_by_id = data.get("locations", {})
    now = datetime.now().isoformat(timespec="seconds")

    # ── Build location mapping: GLPI location → parc site/building/room ──
    # GLPI completename format: "Site > Building > Room"
    # We parse this and create parc_sites / parc_buildings / parc_rooms as needed.
    location_cache: dict[int, dict] = {}  # glpi_locations_id → {site_id, building_id, room_id}

    async def _get_or_create_site(name: str) -> int:
        cur = await db.execute("SELECT id FROM parc_sites WHERE name = ?", (name,))
        row = await cur.fetchone()
        if row:
            return row[0]
        # Generate a code from the name (first 3 letters uppercase)
        code = "".join(c for c in name if c.isalnum())[:6].upper() or "SITE"
        # Ensure unique code
        cur2 = await db.execute("SELECT id FROM parc_sites WHERE code = ?", (code,))
        if await cur2.fetchone():
            code = code + str(hash(name) % 1000)
        await db.execute(
            "INSERT INTO parc_sites (name, code, city, created_at) VALUES (?, ?, '', ?)",
            (name, code, now),
        )
        cur3 = await db.execute("SELECT last_insert_rowid()")
        return (await cur3.fetchone())[0]

    async def _get_or_create_building(site_id: int, name: str) -> int:
        cur = await db.execute(
            "SELECT id FROM parc_buildings WHERE site_id = ? AND name = ?", (site_id, name)
        )
        row = await cur.fetchone()
        if row:
            return row[0]
        await db.execute(
            "INSERT INTO parc_buildings (site_id, name, created_at) VALUES (?, ?, ?)",
            (site_id, name, now),
        )
        cur2 = await db.execute("SELECT last_insert_rowid()")
        return (await cur2.fetchone())[0]

    async def _get_or_create_room(building_id: int, name: str) -> int:
        cur = await db.execute(
            "SELECT id FROM parc_rooms WHERE building_id = ? AND name = ?", (building_id, name)
        )
        row = await cur.fetchone()
        if row:
            return row[0]
        await db.execute(
            "INSERT INTO parc_rooms (building_id, name, floor, created_at) VALUES (?, ?, '', ?)",
            (building_id, name, now),
        )
        cur2 = await db.execute("SELECT last_insert_rowid()")
        return (await cur2.fetchone())[0]

    async def _resolve_location(glpi_loc_id: int | None) -> dict:
        """Resolve a GLPI locations_id into site_id/building_id/room_id."""
        if not glpi_loc_id or glpi_loc_id not in locations_by_id:
            return {"site_id": None, "building_id": None, "room_id": None}

        if glpi_loc_id in location_cache:
            return location_cache[glpi_loc_id]

        loc = locations_by_id[glpi_loc_id]
        completename = loc.get("completename", "")
        parts = [p.strip() for p in completename.split(">") if p.strip()]

        result = {"site_id": None, "building_id": None, "room_id": None}

        if len(parts) >= 1:
            result["site_id"] = await _get_or_create_site(parts[0])
        if len(parts) >= 2 and result["site_id"]:
            result["building_id"] = await _get_or_create_building(result["site_id"], parts[1])
        if len(parts) >= 3 and result["building_id"]:
            result["room_id"] = await _get_or_create_room(result["building_id"], parts[2])

        location_cache[glpi_loc_id] = result
        return result

    created = 0
    updated = 0
    unchanged = 0
    seen_glpi_ids: set[int] = set()

    for item in mapped_items:
        glpi_id = item.get("glpi_id")
        if glpi_id:
            seen_glpi_ids.add(glpi_id)

        # Resolve GLPI location → site/building/room
        loc_ids = await _resolve_location(item.get("glpi_locations_id"))
        site_id = loc_ids["site_id"]
        building_id = loc_ids["building_id"]
        room_id = loc_ids["room_id"]

        # Try to find existing by glpi_id first
        existing = None
        if glpi_id:
            cursor = await db.execute(
                "SELECT id, hostname, equip_type, os, serial_number, brand, model, "
                "glpi_location, site_id, building_id, room_id, COALESCE(last_user,'') "
                "FROM parc_equipment WHERE glpi_id = ? AND source = 'glpi'",
                (glpi_id,),
            )
            existing = await cursor.fetchone()

        # Fallback: match by serial_number
        if not existing and item.get("serial_number"):
            cursor = await db.execute(
                "SELECT id, hostname, equip_type, os, serial_number, brand, model, "
                "glpi_location, site_id, building_id, room_id, COALESCE(last_user,'') "
                "FROM parc_equipment WHERE serial_number = ? AND serial_number != ''",
                (item["serial_number"],),
            )
            existing = await cursor.fetchone()

        if existing:
            # Check if anything changed
            ex_dict = {
                "hostname": existing[1], "equip_type": existing[2], "os": existing[3],
                "serial_number": existing[4], "brand": existing[5], "model": existing[6],
                "glpi_location": existing[7],
                "site_id": existing[8], "building_id": existing[9], "room_id": existing[10],
                "last_user": existing[11],
            }
            new_dict = {
                "hostname": item["hostname"], "equip_type": item["equip_type"], "os": item["os"],
                "serial_number": item["serial_number"], "brand": item["brand"], "model": item["model"],
                "glpi_location": item["glpi_location"],
                "site_id": site_id, "building_id": building_id, "room_id": room_id,
                "last_user": item.get("last_user", ""),
            }
            if ex_dict != new_dict:
                await db.execute(
                    """UPDATE parc_equipment SET
                        hostname = ?, equip_type = ?, os = ?, serial_number = ?,
                        brand = ?, model = ?, source = 'glpi', glpi_id = ?,
                        glpi_location = ?, site_id = ?, building_id = ?, room_id = ?,
                        last_user = ?, updated_at = ?
                    WHERE id = ?""",
                    (
                        item["hostname"], item["equip_type"], item["os"], item["serial_number"],
                        item["brand"], item["model"], glpi_id,
                        item["glpi_location"], site_id, building_id, room_id,
                        item.get("last_user", ""), now, existing[0],
                    ),
                )
                updated += 1
            else:
                unchanged += 1
        else:
            # Insert new
            await db.execute(
                """INSERT INTO parc_equipment
                    (hostname, equip_type, os, serial_number, brand, model,
                     source, glpi_id, glpi_location, site_id, building_id, room_id,
                     last_user, notes, source_ou, ad_dn, manual_location, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'glpi', ?, ?, ?, ?, ?, ?, '', '', '', 0, ?, ?)""",
                (
                    item["hostname"], item["equip_type"], item["os"], item["serial_number"],
                    item["brand"], item["model"], glpi_id, item["glpi_location"],
                    site_id, building_id, room_id, item.get("last_user", ""), now, now,
                ),
            )
            created += 1

    # Flag items previously from GLPI that are no longer present
    if seen_glpi_ids:
        placeholders = ",".join("?" for _ in seen_glpi_ids)
        await db.execute(
            f"""UPDATE parc_equipment
                SET notes = CASE
                    WHEN notes = '' THEN '[GLPI] Disparu du GLPI le {now}'
                    WHEN notes NOT LIKE '%Disparu du GLPI%' THEN notes || ' | [GLPI] Disparu du GLPI le {now}'
                    ELSE notes
                END,
                updated_at = ?
            WHERE source = 'glpi' AND glpi_id IS NOT NULL
                AND glpi_id NOT IN ({placeholders})""",
            (now, *seen_glpi_ids),
        )

    await db.commit()

    return {
        "total": len(mapped_items),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "synced_at": cache["synced_at"],
    }
