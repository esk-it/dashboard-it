from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_raw_db
from ..schemas.task import (
    ChecklistItemCreate,
    ChecklistItemResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TemplateCreate,
    TemplateResponse,
    TemplateUse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _row_to_task(r) -> dict:
    return {
        "id": r[0],
        "title": r[1],
        "category": r[2] or "",
        "priority": r[3],
        "due_date": r[4],
        "done": bool(r[5]),
        "created_at": r[6] or "",
        "notes": r[7] or "",
        "site": r[8] or "",
        "recurrence": r[9] or "",
    }


@router.get("/categories")
async def list_categories(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, name, sort_order FROM task_categories ORDER BY sort_order ASC, name ASC"
    )
    return [{"id": r[0], "name": r[1], "sort_order": r[2]} for r in rows]


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status: str = Query("all"),
    search: str = Query(""),
    site: str = Query(""),
    category: str = Query(""),
    db=Depends(get_raw_db),
):
    query = """SELECT id, title, COALESCE(category,''), priority, due_date,
                      done, COALESCE(created_at,''), COALESCE(notes,''),
                      COALESCE(site,''), COALESCE(recurrence,'')
               FROM tasks WHERE 1=1"""
    params: list = []

    if status == "open":
        query += " AND done = 0"
    elif status == "done":
        query += " AND done = 1"

    if search:
        query += " AND (title LIKE ? OR notes LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    if site:
        query += " AND site = ?"
        params.append(site)

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY priority ASC, due_date ASC NULLS LAST, created_at DESC"

    rows = await db.execute_fetchall(query, params)
    return [TaskResponse(**_row_to_task(r)) for r in rows]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,''), priority, due_date,
                  done, COALESCE(created_at,''), COALESCE(notes,''),
                  COALESCE(site,''), COALESCE(recurrence,'')
           FROM tasks WHERE id = ?""",
        (task_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**_row_to_task(rows[0]))


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO tasks (title, category, priority, due_date, done, created_at, notes, site, recurrence)
           VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)""",
        (
            body.title,
            body.category,
            body.priority,
            body.due_date,
            now,
            body.notes,
            body.site,
            body.recurrence,
        ),
    )
    await db.commit()
    task_id = cursor.lastrowid
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,''), priority, due_date,
                  done, COALESCE(created_at,''), COALESCE(notes,''),
                  COALESCE(site,''), COALESCE(recurrence,'')
           FROM tasks WHERE id = ?""",
        (task_id,),
    )
    return TaskResponse(**_row_to_task(rows[0]))


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, body: TaskUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.execute(
        """UPDATE tasks SET title=?, category=?, priority=?, due_date=?, notes=?, site=?, recurrence=?
           WHERE id=?""",
        (
            body.title,
            body.category,
            body.priority,
            body.due_date,
            body.notes,
            body.site,
            body.recurrence,
            task_id,
        ),
    )
    await db.commit()
    return await get_task(task_id, db)


@router.patch("/{task_id}/done", response_model=TaskResponse)
async def toggle_done(task_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT done FROM tasks WHERE id = ?", (task_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    new_done = 0 if rows[0][0] else 1
    await db.execute("UPDATE tasks SET done = ? WHERE id = ?", (new_done, task_id))
    await db.commit()
    return await get_task(task_id, db)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.execute("DELETE FROM task_checklist WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    await db.commit()


# ---------------------------------------------------------------------------
# Checklist endpoints
# ---------------------------------------------------------------------------

@router.get("/{task_id}/checklist", response_model=list[ChecklistItemResponse])
async def list_checklist(task_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, task_id, text, done, sort_order FROM task_checklist WHERE task_id = ? ORDER BY sort_order ASC, id ASC",
        (task_id,),
    )
    return [
        ChecklistItemResponse(id=r[0], task_id=r[1], text=r[2], done=bool(r[3]), sort_order=r[4])
        for r in rows
    ]


@router.post("/{task_id}/checklist", response_model=ChecklistItemResponse, status_code=201)
async def add_checklist_item(task_id: int, body: ChecklistItemCreate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    cursor = await db.execute(
        "INSERT INTO task_checklist (task_id, text, done, sort_order) VALUES (?, ?, 0, ?)",
        (task_id, body.text, body.sort_order),
    )
    await db.commit()
    item_id = cursor.lastrowid
    return ChecklistItemResponse(id=item_id, task_id=task_id, text=body.text, done=False, sort_order=body.sort_order)


@router.patch("/checklist/{item_id}/toggle", response_model=ChecklistItemResponse)
async def toggle_checklist_item(item_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, task_id, text, done, sort_order FROM task_checklist WHERE id = ?", (item_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    r = rows[0]
    new_done = 0 if r[3] else 1
    await db.execute("UPDATE task_checklist SET done = ? WHERE id = ?", (new_done, item_id))
    await db.commit()
    return ChecklistItemResponse(id=r[0], task_id=r[1], text=r[2], done=bool(new_done), sort_order=r[4])


@router.delete("/checklist/{item_id}", status_code=204)
async def delete_checklist_item(item_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM task_checklist WHERE id = ?", (item_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    await db.execute("DELETE FROM task_checklist WHERE id = ?", (item_id,))
    await db.commit()


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, name, title, COALESCE(category,''), priority, COALESCE(notes,''), COALESCE(site,''), COALESCE(recurrence,''), COALESCE(checklist_json,'[]') FROM task_templates ORDER BY name ASC"
    )
    return [
        TemplateResponse(
            id=r[0], name=r[1], title=r[2], category=r[3], priority=r[4],
            notes=r[5], site=r[6], recurrence=r[7], checklist_json=r[8],
        )
        for r in rows
    ]


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(body: TemplateCreate, db=Depends(get_raw_db)):
    cursor = await db.execute(
        """INSERT INTO task_templates (name, title, category, priority, notes, site, recurrence, checklist_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (body.name, body.title, body.category, body.priority, body.notes, body.site, body.recurrence, body.checklist_json),
    )
    await db.commit()
    tid = cursor.lastrowid
    return TemplateResponse(
        id=tid, name=body.name, title=body.title, category=body.category,
        priority=body.priority, notes=body.notes, site=body.site,
        recurrence=body.recurrence, checklist_json=body.checklist_json,
    )


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM task_templates WHERE id = ?", (template_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.execute("DELETE FROM task_templates WHERE id = ?", (template_id,))
    await db.commit()


@router.post("/templates/{template_id}/use", response_model=TaskResponse, status_code=201)
async def use_template(template_id: int, body: TemplateUse | None = None, db=Depends(get_raw_db)):
    import json as _json

    rows = await db.execute_fetchall(
        "SELECT id, name, title, COALESCE(category,''), priority, COALESCE(notes,''), COALESCE(site,''), COALESCE(recurrence,''), COALESCE(checklist_json,'[]') FROM task_templates WHERE id = ?",
        (template_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Template not found")
    t = rows[0]

    due_date = body.due_date if body and body.due_date else None
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO tasks (title, category, priority, due_date, done, created_at, notes, site, recurrence)
           VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)""",
        (t[2], t[3], t[4], due_date, now, t[5], t[6], t[7]),
    )
    await db.commit()
    task_id = cursor.lastrowid

    # Insert checklist items from template
    try:
        items = _json.loads(t[8])
    except Exception:
        items = []
    for idx, item_text in enumerate(items):
        text = item_text if isinstance(item_text, str) else str(item_text)
        await db.execute(
            "INSERT INTO task_checklist (task_id, text, done, sort_order) VALUES (?, ?, 0, ?)",
            (task_id, text, idx),
        )
    if items:
        await db.commit()

    task_rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,''), priority, due_date,
                  done, COALESCE(created_at,''), COALESCE(notes,''),
                  COALESCE(site,''), COALESCE(recurrence,'')
           FROM tasks WHERE id = ?""",
        (task_id,),
    )
    return TaskResponse(**_row_to_task(task_rows[0]))
