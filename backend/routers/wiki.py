from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_raw_db
from ..schemas.wiki import (
    WikiArticleCreate,
    WikiArticleListResponse,
    WikiArticleResponse,
    WikiArticleUpdate,
    WikiCategoryResponse,
)

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/categories", response_model=list[WikiCategoryResponse])
async def list_categories(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, name, COALESCE(color_hex,''), COALESCE(icon_key,''), sort_order
           FROM wiki_categories
           ORDER BY sort_order ASC, name ASC"""
    )
    return [
        WikiCategoryResponse(
            id=r[0], name=r[1], color_hex=r[2], icon_key=r[3], sort_order=r[4]
        )
        for r in rows
    ]


@router.get("", response_model=list[WikiArticleListResponse])
async def list_articles(
    category: str = Query(""),
    search: str = Query(""),
    pinned: bool | None = Query(None),
    db=Depends(get_raw_db),
):
    query = """SELECT id, title, COALESCE(category,''), pinned,
                      COALESCE(tags,''), COALESCE(updated_at,''),
                      COALESCE(content_format,'html')
               FROM wiki_articles
               WHERE 1=1"""
    params: list = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    if pinned is not None:
        query += " AND pinned = ?"
        params.append(1 if pinned else 0)

    query += " ORDER BY pinned DESC, updated_at DESC"

    rows = await db.execute_fetchall(query, params)
    return [
        WikiArticleListResponse(
            id=r[0], title=r[1], category=r[2], pinned=bool(r[3]),
            tags=r[4], updated_at=r[5], content_format=r[6],
        )
        for r in rows
    ]


@router.get("/{article_id}", response_model=WikiArticleResponse)
async def get_article(article_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,''), COALESCE(content,''),
                  COALESCE(tags,''), pinned, COALESCE(created_at,''),
                  COALESCE(updated_at,''), COALESCE(source_path,''),
                  COALESCE(content_format,'html')
           FROM wiki_articles WHERE id = ?""",
        (article_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Wiki article not found")
    r = rows[0]
    return WikiArticleResponse(
        id=r[0], title=r[1], category=r[2], content=r[3], tags=r[4],
        pinned=bool(r[5]), created_at=r[6], updated_at=r[7], source_path=r[8],
        content_format=r[9],
    )


@router.post("", response_model=WikiArticleResponse, status_code=201)
async def create_article(body: WikiArticleCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO wiki_articles (title, category, content, tags, pinned, created_at, updated_at, source_path, content_format)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.title,
            body.category,
            body.content,
            body.tags,
            1 if body.pinned else 0,
            now,
            now,
            body.source_path,
            body.content_format,
        ),
    )
    await db.commit()
    article_id = cursor.lastrowid
    return await get_article(article_id, db)


@router.put("/{article_id}", response_model=WikiArticleResponse)
async def update_article(article_id: int, body: WikiArticleUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM wiki_articles WHERE id = ?", (article_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Wiki article not found")

    now = datetime.now().isoformat(timespec="seconds")
    await db.execute(
        """UPDATE wiki_articles SET title=?, category=?, content=?, tags=?, pinned=?, updated_at=?, source_path=?, content_format=?
           WHERE id=?""",
        (
            body.title,
            body.category,
            body.content,
            body.tags,
            1 if body.pinned else 0,
            now,
            body.source_path,
            body.content_format,
            article_id,
        ),
    )
    await db.commit()
    return await get_article(article_id, db)


@router.delete("/{article_id}", status_code=204)
async def delete_article(article_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM wiki_articles WHERE id = ?", (article_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Wiki article not found")

    await db.execute("DELETE FROM wiki_articles WHERE id = ?", (article_id,))
    await db.commit()
