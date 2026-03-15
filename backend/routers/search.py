from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..database import get_raw_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def global_search(q: str = Query("", min_length=1), db=Depends(get_raw_db)):
    """Search across tasks, suppliers and documents."""
    if not q.strip():
        return []

    pattern = f"%{q}%"
    results: list[dict] = []

    # Tasks
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,'') as subtitle
           FROM tasks WHERE title LIKE ? OR notes LIKE ? LIMIT 20""",
        (pattern, pattern),
    )
    for r in rows:
        results.append({"type": "task", "id": r[0], "title": r[1], "subtitle": r[2]})

    # Suppliers
    rows = await db.execute_fetchall(
        """SELECT id, name, COALESCE(domain,'') as subtitle
           FROM suppliers WHERE name LIKE ? OR contact LIKE ? OR email LIKE ? LIMIT 20""",
        (pattern, pattern, pattern),
    )
    for r in rows:
        results.append({"type": "supplier", "id": r[0], "title": r[1], "subtitle": r[2]})

    # Documents
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(doc_type,'') as subtitle
           FROM documents WHERE title LIKE ? OR reference LIKE ? OR notes LIKE ? LIMIT 20""",
        (pattern, pattern, pattern),
    )
    for r in rows:
        results.append({"type": "document", "id": r[0], "title": r[1], "subtitle": r[2]})

    return results
