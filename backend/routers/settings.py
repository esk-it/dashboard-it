"""
Router Settings — General settings, theme, RSS feeds, DB info, export, backup.
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])

from ..database import BASE_DIR, DB_PATH

BACKEND_DIR = Path(__file__).resolve().parent.parent
OLD_PROJECT_DIR = Path(r"C:\Users\jdeniel\Documents\Projets\Dashboard - claude code")
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

GENERAL_FILE = BASE_DIR / "general_settings.json"
THEME_FILE = BACKEND_DIR / "settings.json"
RSS_FILE = BACKEND_DIR / "rss_feeds.json"

GENERAL_DEFAULTS = {
    "username": "",
    "auto_refresh_minutes": 5,
    "max_home_tasks": 10,
    "language": "fr",
    "enabled_modules": {},
    "card_order": [],
    "card_layout": [],
    "show_alert_ws": True,
    "show_alert_warranty": True,
}

THEME_DEFAULTS = {
    "theme": "glass",
    "accent": "#06A6C9",
    "brand_icon": "\u26a1",
}

RSS_DEFAULTS = [
    {"name": "CERT-FR", "url": "https://www.cert.ssi.gouv.fr/feed/", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "IT Connect", "url": "https://www.it-connect.fr/feed/", "category": "Infra", "enabled": True},
    {"name": "ZATAZ", "url": "https://www.zataz.com/feed/", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "01net", "url": "https://www.01net.com/rss/info/flux-rss/flux-toutes-les-actualites/", "category": "Tech", "enabled": True},
    {"name": "LeMagIT", "url": "https://www.lemagit.fr/rss/ContentSyndication.xml", "category": "Tech", "enabled": True},
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_file(local: Path, filename: str, defaults) -> Path:
    """Return the settings file path, copying from old project or creating defaults if needed."""
    if local.exists():
        return local
    old = OLD_PROJECT_DIR / filename
    if old.exists():
        shutil.copy2(old, local)
        return local
    local.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
    return local


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── General settings ─────────────────────────────────────────────────────────

@router.get("/general")
async def get_general():
    path = _ensure_file(GENERAL_FILE, "general_settings.json", GENERAL_DEFAULTS)
    return _read_json(path)


@router.put("/general")
async def put_general(payload: dict = Body(...)):
    _ensure_file(GENERAL_FILE, "general_settings.json", GENERAL_DEFAULTS)
    _write_json(GENERAL_FILE, payload)
    return payload


# ── Theme settings ───────────────────────────────────────────────────────────

@router.get("/theme")
async def get_theme():
    path = _ensure_file(THEME_FILE, "settings.json", THEME_DEFAULTS)
    return _read_json(path)


@router.put("/theme")
async def put_theme(payload: dict = Body(...)):
    _ensure_file(THEME_FILE, "settings.json", THEME_DEFAULTS)
    _write_json(THEME_FILE, payload)
    return payload


# ── RSS Feeds ────────────────────────────────────────────────────────────────

@router.get("/rss-feeds")
async def get_rss_feeds():
    path = _ensure_file(RSS_FILE, "rss_feeds.json", RSS_DEFAULTS)
    return _read_json(path)


@router.post("/rss-feeds")
async def add_rss_feed(payload: dict = Body(...)):
    path = _ensure_file(RSS_FILE, "rss_feeds.json", RSS_DEFAULTS)
    feeds = _read_json(path)
    new_feed = {
        "name": payload.get("name", ""),
        "url": payload.get("url", ""),
        "category": payload.get("category", "Autre"),
        "enabled": True,
    }
    feeds.append(new_feed)
    _write_json(path, feeds)
    return feeds


@router.put("/rss-feeds/{idx}")
async def update_rss_feed(idx: int, payload: dict = Body(...)):
    path = _ensure_file(RSS_FILE, "rss_feeds.json", RSS_DEFAULTS)
    feeds = _read_json(path)
    if 0 <= idx < len(feeds):
        feeds[idx].update(payload)
        _write_json(path, feeds)
    return feeds


@router.delete("/rss-feeds/{idx}")
async def delete_rss_feed(idx: int):
    path = _ensure_file(RSS_FILE, "rss_feeds.json", RSS_DEFAULTS)
    feeds = _read_json(path)
    if 0 <= idx < len(feeds):
        feeds.pop(idx)
        _write_json(path, feeds)
    return feeds


# ── Database info ────────────────────────────────────────────────────────────

@router.get("/db-info")
async def db_info():
    info = {
        "path": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "size_bytes": 0,
        "size_human": "0 B",
        "tables": [],
        "journal_mode": "",
    }
    if DB_PATH.exists():
        info["size_bytes"] = DB_PATH.stat().st_size
        sz = info["size_bytes"]
        if sz < 1024:
            info["size_human"] = f"{sz} B"
        elif sz < 1024 * 1024:
            info["size_human"] = f"{sz / 1024:.1f} KB"
        else:
            info["size_human"] = f"{sz / (1024 * 1024):.2f} MB"

        con = sqlite3.connect(str(DB_PATH))
        try:
            cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            info["tables"] = [r[0] for r in cur.fetchall()]
            cur2 = con.execute("PRAGMA journal_mode")
            info["journal_mode"] = cur2.fetchone()[0]
        finally:
            con.close()

    return info


@router.post("/db-integrity")
async def db_integrity():
    if not DB_PATH.exists():
        return {"result": "Base de donn\u00e9es introuvable", "ok": False}
    con = sqlite3.connect(str(DB_PATH))
    try:
        cur = con.execute("PRAGMA integrity_check")
        results = [r[0] for r in cur.fetchall()]
        ok = results == ["ok"]
        return {"result": "\n".join(results), "ok": ok}
    finally:
        con.close()


@router.post("/db-vacuum")
async def db_vacuum():
    if not DB_PATH.exists():
        return {"result": "Base de donn\u00e9es introuvable", "ok": False}
    before = DB_PATH.stat().st_size
    con = sqlite3.connect(str(DB_PATH))
    try:
        con.execute("VACUUM")
    finally:
        con.close()
    after = DB_PATH.stat().st_size
    saved = before - after
    return {
        "result": f"VACUUM termin\u00e9. Taille avant: {before}, apr\u00e8s: {after}, \u00e9conomis\u00e9: {saved} octets",
        "ok": True,
        "before": before,
        "after": after,
        "saved": saved,
    }


@router.post("/db-fk-check")
async def db_fk_check():
    if not DB_PATH.exists():
        return {"result": "Base de donn\u00e9es introuvable", "ok": False, "violations": []}
    con = sqlite3.connect(str(DB_PATH))
    try:
        cur = con.execute("PRAGMA foreign_key_check")
        violations = cur.fetchall()
        if not violations:
            return {"result": "Aucune violation de cl\u00e9 \u00e9trang\u00e8re", "ok": True, "violations": []}
        return {
            "result": f"{len(violations)} violation(s) trouv\u00e9e(s)",
            "ok": False,
            "violations": [{"table": v[0], "rowid": v[1], "parent": v[2], "fkid": v[3]} for v in violations],
        }
    finally:
        con.close()


# ── Export ───────────────────────────────────────────────────────────────────

def _export_table_csv(table_name: str) -> str:
    """Export a DB table to CSV string."""
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(f"SELECT * FROM {table_name}")  # noqa: S608
        rows = cur.fetchall()
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(tuple(row))
        return output.getvalue()
    finally:
        con.close()


@router.post("/export/tasks")
async def export_tasks():
    csv_str = _export_table_csv("tasks")
    if not csv_str:
        csv_str = "Aucune t\u00e2che"
    return StreamingResponse(
        io.BytesIO(csv_str.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks_export.csv"},
    )


@router.post("/export/documents")
async def export_documents():
    csv_str = _export_table_csv("documents")
    if not csv_str:
        csv_str = "Aucun document"
    return StreamingResponse(
        io.BytesIO(csv_str.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=documents_export.csv"},
    )


# ── Backup ───────────────────────────────────────────────────────────────────

@router.post("/backup")
async def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_{timestamp}.zip"
    zip_path = BACKUP_DIR / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, "dashboard.db")
        if GENERAL_FILE.exists():
            zf.write(GENERAL_FILE, "general_settings.json")
        if THEME_FILE.exists():
            zf.write(THEME_FILE, "settings.json")
        if RSS_FILE.exists():
            zf.write(RSS_FILE, "rss_feeds.json")
        # Include logos directory if exists
        logos_dir = BACKEND_DIR / "logos"
        if logos_dir.exists():
            for f in logos_dir.iterdir():
                if f.is_file():
                    zf.write(f, f"logos/{f.name}")

    # Rotation: keep last 10 backups
    backups = sorted(BACKUP_DIR.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[10:]:
        old.unlink()

    return {
        "filename": zip_name,
        "size": zip_path.stat().st_size,
        "timestamp": timestamp,
    }


@router.get("/backups")
async def list_backups():
    backups = sorted(BACKUP_DIR.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for b in backups:
        stat = b.stat()
        sz = stat.st_size
        if sz < 1024:
            size_human = f"{sz} B"
        elif sz < 1024 * 1024:
            size_human = f"{sz / 1024:.1f} KB"
        else:
            size_human = f"{sz / (1024 * 1024):.2f} MB"
        result.append({
            "filename": b.name,
            "size": sz,
            "size_human": size_human,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return result


# ── Danger zone ──────────────────────────────────────────────────────────────

@router.post("/reset-data")
async def reset_data(payload: dict = Body(...)):
    """Reset all data. Requires confirmation='RESET' in body."""
    if payload.get("confirmation") != "RESET":
        return {"ok": False, "message": "Confirmation invalide. Envoyez {\"confirmation\": \"RESET\"}"}

    # Backup first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"pre_reset_{timestamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, "dashboard.db")
        if GENERAL_FILE.exists():
            zf.write(GENERAL_FILE, "general_settings.json")
        if THEME_FILE.exists():
            zf.write(THEME_FILE, "settings.json")
        if RSS_FILE.exists():
            zf.write(RSS_FILE, "rss_feeds.json")

    # Delete DB
    if DB_PATH.exists():
        DB_PATH.unlink()

    # Reset settings to defaults
    _write_json(GENERAL_FILE, GENERAL_DEFAULTS)
    _write_json(THEME_FILE, THEME_DEFAULTS)
    _write_json(RSS_FILE, RSS_DEFAULTS)

    return {"ok": True, "message": f"Donn\u00e9es r\u00e9initialis\u00e9es. Backup de s\u00e9curit\u00e9 cr\u00e9\u00e9: {zip_path.name}"}
