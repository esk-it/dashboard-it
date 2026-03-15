from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_raw_db
from ..schemas.changelog import (
    ChangelogCategoryResponse,
    ChangelogEntryCreate,
    ChangelogEntryResponse,
    ChangelogEntryUpdate,
    ChangelogStatCategory,
    ChangelogStatMonth,
    ChangelogStatsResponse,
)

router = APIRouter(prefix="/api/changelog", tags=["changelog"])


def _row_to_entry(r) -> dict:
    return {
        "id": r[0],
        "title": r[1],
        "description": r[2] or "",
        "category": r[3] or "",
        "impact": r[4] or "low",
        "author": r[5] or "",
        "event_date": r[6],
        "created_at": r[7] or "",
        "tags": r[8] or "",
    }


@router.get("/categories", response_model=list[ChangelogCategoryResponse])
async def list_categories(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, name, COALESCE(color_hex,''), COALESCE(icon_key,''), sort_order
           FROM changelog_categories
           ORDER BY sort_order ASC, name ASC"""
    )
    return [
        ChangelogCategoryResponse(
            id=r[0], name=r[1], color_hex=r[2], icon_key=r[3], sort_order=r[4]
        )
        for r in rows
    ]


@router.get("/stats", response_model=ChangelogStatsResponse)
async def stats(db=Depends(get_raw_db)):
    # Count by category
    cat_rows = await db.execute_fetchall(
        """SELECT COALESCE(category,'') as cat, COUNT(*) as cnt
           FROM changelog_entries
           GROUP BY cat
           ORDER BY cnt DESC"""
    )
    by_category = [ChangelogStatCategory(category=r[0] or "Sans catégorie", count=r[1]) for r in cat_rows]

    # Count by month
    month_rows = await db.execute_fetchall(
        """SELECT strftime('%Y-%m', COALESCE(event_date, created_at)) as month, COUNT(*) as cnt
           FROM changelog_entries
           GROUP BY month
           ORDER BY month DESC
           LIMIT 12"""
    )
    by_month = [ChangelogStatMonth(month=r[0] or "", count=r[1]) for r in month_rows]

    return ChangelogStatsResponse(by_category=by_category, by_month=by_month)


@router.get("", response_model=list[ChangelogEntryResponse])
async def list_entries(
    category: str = Query(""),
    impact: str = Query(""),
    search: str = Query(""),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db=Depends(get_raw_db),
):
    query = """SELECT id, title, COALESCE(description,''), COALESCE(category,''),
                      COALESCE(impact,'low'), COALESCE(author,''),
                      event_date, COALESCE(created_at,''), COALESCE(tags,'')
               FROM changelog_entries
               WHERE 1=1"""
    params: list = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if impact:
        query += " AND impact = ?"
        params.append(impact)

    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    query += " ORDER BY COALESCE(event_date, created_at) DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows = await db.execute_fetchall(query, params)
    return [ChangelogEntryResponse(**_row_to_entry(r)) for r in rows]


@router.get("/{entry_id}", response_model=ChangelogEntryResponse)
async def get_entry(entry_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(description,''), COALESCE(category,''),
                  COALESCE(impact,'low'), COALESCE(author,''),
                  event_date, COALESCE(created_at,''), COALESCE(tags,'')
           FROM changelog_entries WHERE id = ?""",
        (entry_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Changelog entry not found")
    return ChangelogEntryResponse(**_row_to_entry(rows[0]))


@router.post("", response_model=ChangelogEntryResponse, status_code=201)
async def create_entry(body: ChangelogEntryCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO changelog_entries (title, description, category, impact, author, event_date, created_at, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.title,
            body.description,
            body.category,
            body.impact,
            body.author,
            body.event_date,
            now,
            body.tags,
        ),
    )
    await db.commit()
    entry_id = cursor.lastrowid
    return await get_entry(entry_id, db)


@router.put("/{entry_id}", response_model=ChangelogEntryResponse)
async def update_entry(entry_id: int, body: ChangelogEntryUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM changelog_entries WHERE id = ?", (entry_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Changelog entry not found")

    await db.execute(
        """UPDATE changelog_entries SET title=?, description=?, category=?, impact=?, author=?, event_date=?, tags=?
           WHERE id=?""",
        (
            body.title,
            body.description,
            body.category,
            body.impact,
            body.author,
            body.event_date,
            body.tags,
            entry_id,
        ),
    )
    await db.commit()
    return await get_entry(entry_id, db)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM changelog_entries WHERE id = ?", (entry_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Changelog entry not found")

    await db.execute("DELETE FROM changelog_entries WHERE id = ?", (entry_id,))
    await db.commit()
