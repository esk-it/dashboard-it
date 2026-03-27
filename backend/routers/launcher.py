"""Quick Links / Launcher module — manage and display shortcut links."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..database import get_raw_db

logger = logging.getLogger(__name__)

# Icons storage directory
if os.environ.get("ITMANAGER_DATA_DIR"):
    ICONS_DIR = Path(os.environ["ITMANAGER_DATA_DIR"]) / "data" / "launcher_icons"
else:
    ICONS_DIR = Path(__file__).parent.parent / "data" / "launcher_icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/launcher", tags=["launcher"])


class QuickLinkCreate(BaseModel):
    name: str
    url: str
    description: str = ""
    category: str = ""
    icon_type: str = "emoji"  # 'emoji' | 'url' (for favicon/logo URL)
    icon_value: str = "🔗"
    color: str = "#6C63FF"
    favorite: bool = False
    sort_order: int = 100


class QuickLinkResponse(BaseModel):
    id: int
    name: str
    url: str
    description: str = ""
    category: str = ""
    icon_type: str = "emoji"
    icon_value: str = "🔗"
    color: str = "#6C63FF"
    favorite: bool = False
    sort_order: int = 100
    created_at: str = ""


@router.get("", response_model=list[QuickLinkResponse])
async def list_links(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, name, url, description, category, icon_type, icon_value, color, favorite, sort_order, created_at "
        "FROM quick_links ORDER BY sort_order ASC, name ASC"
    )
    return [
        QuickLinkResponse(
            id=r[0], name=r[1], url=r[2], description=r[3], category=r[4],
            icon_type=r[5], icon_value=r[6], color=r[7], favorite=bool(r[8]),
            sort_order=r[9], created_at=r[10],
        )
        for r in rows
    ]


@router.post("", response_model=QuickLinkResponse, status_code=201)
async def create_link(body: QuickLinkCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        "INSERT INTO quick_links (name, url, description, category, icon_type, icon_value, color, favorite, sort_order, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (body.name, body.url, body.description, body.category,
         body.icon_type, body.icon_value, body.color, int(body.favorite), body.sort_order, now),
    )
    await db.commit()
    return QuickLinkResponse(
        id=cursor.lastrowid, name=body.name, url=body.url, description=body.description,
        category=body.category, icon_type=body.icon_type, icon_value=body.icon_value,
        color=body.color, favorite=body.favorite, sort_order=body.sort_order, created_at=now,
    )


@router.put("/{link_id}", response_model=QuickLinkResponse)
async def update_link(link_id: int, body: QuickLinkCreate, db=Depends(get_raw_db)):
    await db.execute(
        "UPDATE quick_links SET name=?, url=?, description=?, category=?, icon_type=?, icon_value=?, color=?, favorite=?, sort_order=? WHERE id=?",
        (body.name, body.url, body.description, body.category,
         body.icon_type, body.icon_value, body.color, int(body.favorite), body.sort_order, link_id),
    )
    await db.commit()
    rows = await db.execute_fetchall("SELECT created_at FROM quick_links WHERE id=?", (link_id,))
    return QuickLinkResponse(
        id=link_id, name=body.name, url=body.url, description=body.description,
        category=body.category, icon_type=body.icon_type, icon_value=body.icon_value,
        color=body.color, favorite=body.favorite, sort_order=body.sort_order,
        created_at=rows[0][0] if rows else "",
    )


@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: int, db=Depends(get_raw_db)):
    await db.execute("DELETE FROM quick_links WHERE id=?", (link_id,))
    await db.commit()


@router.get("/categories")
async def list_categories(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT DISTINCT category FROM quick_links WHERE category != '' ORDER BY category")
    return [r[0] for r in rows]


# ── Icon management (local storage) ──────────────────────────

@router.post("/{link_id}/icon")
async def download_icon(link_id: int, body: dict, db=Depends(get_raw_db)):
    """Download an icon from a URL and store it locally."""
    icon_url = body.get("url", "").strip()
    if not icon_url:
        raise HTTPException(400, "url required")

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(icon_url)
            resp.raise_for_status()
            content = resp.content
            # Detect extension from content-type
            ct = resp.headers.get("content-type", "")
            if "svg" in ct:
                ext = ".svg"
            elif "png" in ct:
                ext = ".png"
            elif "jpeg" in ct or "jpg" in ct:
                ext = ".jpg"
            elif "webp" in ct:
                ext = ".webp"
            elif "ico" in ct:
                ext = ".ico"
            else:
                ext = ".png"  # default

            icon_path = ICONS_DIR / f"{link_id}{ext}"
            icon_path.write_bytes(content)

            # Update DB to use local icon
            await db.execute(
                "UPDATE quick_links SET icon_type='local', icon_value=? WHERE id=?",
                (f"{link_id}{ext}", link_id),
            )
            await db.commit()

            return {"status": "ok", "icon_file": f"{link_id}{ext}"}
    except Exception as e:
        logger.warning(f"Failed to download icon: {e}")
        raise HTTPException(502, f"Failed to download icon: {e}")


@router.get("/{link_id}/icon")
async def get_icon(link_id: int, db=Depends(get_raw_db)):
    """Serve a locally stored icon."""
    # Find the icon file
    for ext in [".svg", ".png", ".jpg", ".webp", ".ico"]:
        icon_path = ICONS_DIR / f"{link_id}{ext}"
        if icon_path.exists():
            media = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
                     ".webp": "image/webp", ".ico": "image/x-icon"}
            return FileResponse(icon_path, media_type=media.get(ext, "image/png"))
    raise HTTPException(404, "Icon not found")
