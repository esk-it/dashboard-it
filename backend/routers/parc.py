from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_raw_db
from ..schemas.parc import (
    BuildingCreate,
    BuildingResponse,
    BuildingUpdate,
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
    ParcStats,
    RoomCreate,
    RoomResponse,
    RoomUpdate,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
)

router = APIRouter(prefix="/api/parc", tags=["parc"])


# ── Helpers ─────────────────────────────────────────────────

_EQ_COLS = """
    e.id, e.hostname, COALESCE(e.equip_type,''), COALESCE(e.os,''),
    COALESCE(e.serial_number,''), COALESCE(e.brand,''), COALESCE(e.model,''),
    e.site_id, e.building_id, e.room_id,
    COALESCE(e.source,''), COALESCE(e.source_ou,''), COALESCE(e.ad_dn,''),
    COALESCE(e.last_seen_ad,''), e.warranty_end, e.purchase_date,
    COALESCE(e.notes,''), COALESCE(e.manual_location,''),
    COALESCE(e.created_at,''), COALESCE(e.updated_at,''),
    e.glpi_id, COALESCE(e.glpi_location,''), COALESCE(e.last_user,''),
    COALESCE(s.name,''), COALESCE(b.name,''), COALESCE(r.name,'')
"""

_EQ_FROM = """
    FROM parc_equipment e
    LEFT JOIN parc_sites s ON s.id = e.site_id
    LEFT JOIN parc_buildings b ON b.id = e.building_id
    LEFT JOIN parc_rooms r ON r.id = e.room_id
"""


def _row_to_equipment(r) -> dict:
    return dict(
        id=r[0], hostname=r[1], equip_type=r[2], os=r[3],
        serial_number=r[4], brand=r[5], model=r[6],
        site_id=r[7], building_id=r[8], room_id=r[9],
        source=r[10], source_ou=r[11], ad_dn=r[12],
        last_seen_ad=r[13], warranty_end=r[14], purchase_date=r[15],
        notes=r[16], manual_location=str(r[17]) if r[17] is not None else "",
        created_at=r[18], updated_at=r[19],
        glpi_id=r[20], glpi_location=r[21], last_user=r[22],
        site_name=r[23], building_name=r[24], room_name=r[25],
    )


# ── Equipment CRUD ──────────────────────────────────────────

@router.get("/equipment", response_model=list[EquipmentResponse])
async def list_equipment(
    site_id: int | None = Query(None),
    building_id: int | None = Query(None),
    room_id: int | None = Query(None),
    equip_type: str = Query(""),
    source: str = Query(""),
    search: str = Query(""),
    db=Depends(get_raw_db),
):
    query = f"SELECT {_EQ_COLS} {_EQ_FROM} WHERE 1=1"
    params: list = []

    if site_id is not None:
        query += " AND e.site_id = ?"
        params.append(site_id)
    if building_id is not None:
        query += " AND e.building_id = ?"
        params.append(building_id)
    if room_id is not None:
        query += " AND e.room_id = ?"
        params.append(room_id)
    if equip_type:
        query += " AND e.equip_type = ?"
        params.append(equip_type)
    if source:
        query += " AND e.source = ?"
        params.append(source)
    if search:
        query += " AND (e.hostname LIKE ? OR e.serial_number LIKE ? OR e.brand LIKE ? OR e.model LIKE ?)"
        params += [f"%{search}%"] * 4

    query += " ORDER BY e.hostname ASC"
    rows = await db.execute_fetchall(query, params)
    return [EquipmentResponse(**_row_to_equipment(r)) for r in rows]


@router.get("/equipment/{equip_id}", response_model=EquipmentResponse)
async def get_equipment(equip_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        f"SELECT {_EQ_COLS} {_EQ_FROM} WHERE e.id = ?", (equip_id,)
    )
    if not rows:
        raise HTTPException(404, "Equipment not found")
    return EquipmentResponse(**_row_to_equipment(rows[0]))


@router.post("/equipment", response_model=EquipmentResponse, status_code=201)
async def create_equipment(body: EquipmentCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO parc_equipment
           (hostname, equip_type, os, serial_number, brand, model,
            site_id, building_id, room_id, source, notes,
            warranty_end, purchase_date, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (body.hostname, body.equip_type, body.os, body.serial_number,
         body.brand, body.model, body.site_id, body.building_id,
         body.room_id, body.source, body.notes,
         body.warranty_end, body.purchase_date, now, now),
    )
    await db.commit()
    return await get_equipment(cursor.lastrowid, db)


@router.put("/equipment/{equip_id}", response_model=EquipmentResponse)
async def update_equipment(equip_id: int, body: EquipmentUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM parc_equipment WHERE id=?", (equip_id,))
    if not rows:
        raise HTTPException(404, "Equipment not found")
    now = datetime.now().isoformat(timespec="seconds")
    await db.execute(
        """UPDATE parc_equipment SET hostname=?, equip_type=?, os=?, serial_number=?,
           brand=?, model=?, site_id=?, building_id=?, room_id=?, source=?,
           notes=?, warranty_end=?, purchase_date=?, updated_at=?
           WHERE id=?""",
        (body.hostname, body.equip_type, body.os, body.serial_number,
         body.brand, body.model, body.site_id, body.building_id,
         body.room_id, body.source, body.notes,
         body.warranty_end, body.purchase_date, now, equip_id),
    )
    await db.commit()
    return await get_equipment(equip_id, db)


@router.delete("/equipment/{equip_id}", status_code=204)
async def delete_equipment(equip_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM parc_equipment WHERE id=?", (equip_id,))
    if not rows:
        raise HTTPException(404, "Equipment not found")
    await db.execute("DELETE FROM parc_equipment WHERE id=?", (equip_id,))
    await db.commit()


# ── Stats ───────────────────────────────────────────────────

@router.get("/stats", response_model=ParcStats)
async def parc_stats(db=Depends(get_raw_db)):
    total = (await db.execute_fetchall("SELECT COUNT(*) FROM parc_equipment"))[0][0]

    type_rows = await db.execute_fetchall(
        "SELECT equip_type, COUNT(*) FROM parc_equipment GROUP BY equip_type ORDER BY COUNT(*) DESC"
    )
    by_type = {r[0] or "Inconnu": r[1] for r in type_rows}

    site_rows = await db.execute_fetchall(
        """SELECT COALESCE(s.code, 'Non affecté'), COUNT(*)
           FROM parc_equipment e LEFT JOIN parc_sites s ON s.id = e.site_id
           GROUP BY s.code ORDER BY COUNT(*) DESC"""
    )
    by_site = {r[0] or "Non affecté": r[1] for r in site_rows}

    source_rows = await db.execute_fetchall(
        "SELECT source, COUNT(*) FROM parc_equipment GROUP BY source ORDER BY COUNT(*) DESC"
    )
    by_source = {r[0] or "Inconnu": r[1] for r in source_rows}

    return ParcStats(total=total, by_type=by_type, by_site=by_site, by_source=by_source)


# ── Audit — Smart rules-based audit ─────────────────────────

DEFAULT_AUDIT_RULES = {
    "PC":          {"site": True, "building": True, "room": True, "os": True, "user": False},
    "Portable":    {"site": True, "building": True, "room": True, "os": True, "user": False},
    "Chromebook":  {"site": True, "building": False, "room_or_user": True, "os": False, "user": False},
    "Imprimante":  {"site": True, "building": True, "room": False, "os": False, "user": False},
    "Switch":      {"site": True, "building": True, "room": False, "os": False, "user": False},
    "AP Wi-Fi":    {"site": True, "building": True, "room": False, "os": False, "user": False},
    "Serveur":     {"site": True, "building": True, "room": True, "os": True, "user": False},
    "_default":    {"site": True, "building": False, "room": False, "os": False, "user": False},
}

if os.environ.get("ITMANAGER_DATA_DIR"):
    _AUDIT_RULES_PATH = Path(os.environ["ITMANAGER_DATA_DIR"]) / "data" / "audit_rules.json"
else:
    _AUDIT_RULES_PATH = Path(__file__).parent.parent / "data" / "audit_rules.json"


def _load_audit_rules() -> dict:
    if _AUDIT_RULES_PATH.exists():
        try:
            return json.loads(_AUDIT_RULES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_AUDIT_RULES


def _save_audit_rules(rules: dict):
    _AUDIT_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _AUDIT_RULES_PATH.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")


def _check_equipment(eq: dict, rules: dict) -> list[str]:
    """Return list of missing required fields for an equipment based on its type rules."""
    equip_type = eq.get("equip_type", "")
    rule = rules.get(equip_type, rules.get("_default", {}))
    missing = []

    if rule.get("site") and not eq.get("site_id"):
        missing.append("site")
    if rule.get("building") and not eq.get("building_id"):
        missing.append("building")
    if rule.get("room") and not eq.get("room_id"):
        missing.append("room")
    if rule.get("os") and not eq.get("os", "").strip():
        missing.append("os")
    if rule.get("user") and not eq.get("last_user", "").strip():
        missing.append("user")

    # Special: room_or_user — need at least one of room or user
    if rule.get("room_or_user"):
        has_room = bool(eq.get("room_id"))
        has_user = bool(eq.get("last_user", "").strip())
        if not has_room and not has_user:
            missing.append("room_or_user")

    return missing


@router.get("/audit")
async def audit_smart(db=Depends(get_raw_db)):
    """Smart audit: check each equipment against type-specific rules."""
    rules = _load_audit_rules()
    rows = await db.execute_fetchall(
        f"SELECT {_EQ_COLS} {_EQ_FROM} ORDER BY e.hostname"
    )

    issues = []
    by_type: dict[str, dict] = {}
    total_checked = len(rows)

    for r in rows:
        eq = _row_to_equipment(r)
        etype = eq["equip_type"] or "_default"

        if etype not in by_type:
            by_type[etype] = {"total": 0, "issues": 0}
        by_type[etype]["total"] += 1

        missing = _check_equipment(eq, rules)
        if missing:
            severity = "critical" if len(missing) >= 2 else "warning"
            by_type[etype]["issues"] += 1
            issues.append({
                "id": eq["id"],
                "hostname": eq["hostname"],
                "equip_type": etype,
                "site_name": eq.get("site_name", ""),
                "building_name": eq.get("building_name", ""),
                "room_name": eq.get("room_name", ""),
                "last_user": eq.get("last_user", ""),
                "missing": missing,
                "severity": severity,
            })

    n_critical = sum(1 for i in issues if i["severity"] == "critical")
    n_warning = len(issues) - n_critical
    compliant = total_checked - len(issues)
    pct = round(compliant / total_checked * 100, 1) if total_checked > 0 else 100.0

    return {
        "rules": rules,
        "issues": issues,
        "summary": {
            "total_checked": total_checked,
            "compliant": compliant,
            "warnings": n_warning,
            "critical": n_critical,
            "compliance_percent": pct,
            "by_type": by_type,
        },
    }


@router.get("/audit/rules")
async def get_audit_rules():
    return _load_audit_rules()


@router.put("/audit/rules")
async def set_audit_rules(rules: dict):
    _save_audit_rules(rules)
    return {"status": "ok"}


# ── Sites CRUD ──────────────────────────────────────────────

@router.get("/sites", response_model=list[SiteResponse])
async def list_sites(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id, name, COALESCE(code,''), COALESCE(city,'') FROM parc_sites ORDER BY name")
    return [SiteResponse(id=r[0], name=r[1], code=r[2], city=r[3]) for r in rows]


@router.post("/sites", response_model=SiteResponse, status_code=201)
async def create_site(body: SiteCreate, db=Depends(get_raw_db)):
    cursor = await db.execute(
        "INSERT INTO parc_sites (name, code, city) VALUES (?,?,?)",
        (body.name, body.code, body.city),
    )
    await db.commit()
    return SiteResponse(id=cursor.lastrowid, name=body.name, code=body.code, city=body.city)


@router.put("/sites/{site_id}", response_model=SiteResponse)
async def update_site(site_id: int, body: SiteUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM parc_sites WHERE id=?", (site_id,))
    if not rows:
        raise HTTPException(404, "Site not found")
    await db.execute(
        "UPDATE parc_sites SET name=?, code=?, city=? WHERE id=?",
        (body.name, body.code, body.city, site_id),
    )
    await db.commit()
    return SiteResponse(id=site_id, name=body.name, code=body.code, city=body.city)


# ── Buildings CRUD ──────────────────────────────────────────

@router.get("/sites/{site_id}/buildings", response_model=list[BuildingResponse])
async def list_buildings(site_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, site_id, name FROM parc_buildings WHERE site_id=? ORDER BY name", (site_id,)
    )
    return [BuildingResponse(id=r[0], site_id=r[1], name=r[2]) for r in rows]


@router.post("/buildings", response_model=BuildingResponse, status_code=201)
async def create_building(body: BuildingCreate, db=Depends(get_raw_db)):
    cursor = await db.execute(
        "INSERT INTO parc_buildings (site_id, name) VALUES (?,?)",
        (body.site_id, body.name),
    )
    await db.commit()
    return BuildingResponse(id=cursor.lastrowid, site_id=body.site_id, name=body.name)


@router.put("/buildings/{building_id}", response_model=BuildingResponse)
async def update_building(building_id: int, body: BuildingUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT site_id FROM parc_buildings WHERE id=?", (building_id,))
    if not rows:
        raise HTTPException(404, "Building not found")
    await db.execute("UPDATE parc_buildings SET name=? WHERE id=?", (body.name, building_id))
    await db.commit()
    return BuildingResponse(id=building_id, site_id=rows[0][0], name=body.name)


# ── Rooms CRUD ──────────────────────────────────────────────

@router.get("/buildings/{building_id}/rooms", response_model=list[RoomResponse])
async def list_rooms(building_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, building_id, name, COALESCE(floor,'') FROM parc_rooms WHERE building_id=? ORDER BY name",
        (building_id,),
    )
    return [RoomResponse(id=r[0], building_id=r[1], name=r[2], floor=r[3]) for r in rows]


@router.post("/rooms", response_model=RoomResponse, status_code=201)
async def create_room(body: RoomCreate, db=Depends(get_raw_db)):
    cursor = await db.execute(
        "INSERT INTO parc_rooms (building_id, name, floor) VALUES (?,?,?)",
        (body.building_id, body.name, body.floor),
    )
    await db.commit()
    return RoomResponse(id=cursor.lastrowid, building_id=body.building_id, name=body.name, floor=body.floor)


@router.put("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, body: RoomUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT building_id FROM parc_rooms WHERE id=?", (room_id,))
    if not rows:
        raise HTTPException(404, "Room not found")
    await db.execute("UPDATE parc_rooms SET name=?, floor=? WHERE id=?", (body.name, body.floor, room_id))
    await db.commit()
    return RoomResponse(id=room_id, building_id=rows[0][0], name=body.name, floor=body.floor)
