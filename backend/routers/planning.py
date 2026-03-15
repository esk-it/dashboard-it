from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..database import get_raw_db

router = APIRouter(prefix="/api/planning", tags=["planning"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlanningEventCreate(BaseModel):
    title: str
    event_type: str = "other"
    date_start: str
    date_end: str
    all_day: bool = True
    time_start: str | None = None
    time_end: str | None = None
    person: str = ""
    notes: str = ""
    task_id: int | None = None


class PlanningEventUpdate(BaseModel):
    title: str
    event_type: str = "other"
    date_start: str
    date_end: str
    all_day: bool = True
    time_start: str | None = None
    time_end: str | None = None
    person: str = ""
    notes: str = ""
    task_id: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_event(r) -> dict:
    return {
        "id": r[0],
        "title": r[1],
        "event_type": r[2] or "other",
        "date_start": r[3],
        "date_end": r[4],
        "all_day": bool(r[5]),
        "time_start": r[6],
        "time_end": r[7],
        "person": r[8] or "",
        "notes": r[9] or "",
        "task_id": r[10],
        "created_at": r[11] or "",
    }


_SELECT_COLS = """id, title, COALESCE(event_type,'other'), date_start, date_end,
                  all_day, time_start, time_end,
                  COALESCE(person,''), COALESCE(notes,''),
                  task_id, COALESCE(created_at,'')"""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/events")
async def list_events(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    db=Depends(get_raw_db),
):
    """Return events whose date range overlaps [start, end]."""
    rows = await db.execute_fetchall(
        f"""SELECT {_SELECT_COLS}
            FROM planning_events
            WHERE date_start <= ? AND date_end >= ?
            ORDER BY date_start ASC, time_start ASC NULLS LAST""",
        (end, start),
    )
    return [_row_to_event(r) for r in rows]


@router.get("/events/{event_id}")
async def get_event(event_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        f"SELECT {_SELECT_COLS} FROM planning_events WHERE id = ?",
        (event_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Event not found")
    return _row_to_event(rows[0])


@router.post("/events", status_code=201)
async def create_event(body: PlanningEventCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO planning_events
           (title, event_type, date_start, date_end, all_day,
            time_start, time_end, person, notes, task_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.title,
            body.event_type,
            body.date_start,
            body.date_end,
            int(body.all_day),
            body.time_start,
            body.time_end,
            body.person,
            body.notes,
            body.task_id,
            now,
        ),
    )
    await db.commit()
    return await get_event(cursor.lastrowid, db)


@router.put("/events/{event_id}")
async def update_event(event_id: int, body: PlanningEventUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id FROM planning_events WHERE id = ?", (event_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.execute(
        """UPDATE planning_events
           SET title=?, event_type=?, date_start=?, date_end=?, all_day=?,
               time_start=?, time_end=?, person=?, notes=?, task_id=?
           WHERE id=?""",
        (
            body.title,
            body.event_type,
            body.date_start,
            body.date_end,
            int(body.all_day),
            body.time_start,
            body.time_end,
            body.person,
            body.notes,
            body.task_id,
            event_id,
        ),
    )
    await db.commit()
    return await get_event(event_id, db)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id FROM planning_events WHERE id = ?", (event_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.execute("DELETE FROM planning_events WHERE id = ?", (event_id,))
    await db.commit()


@router.get("/tasks-for-calendar")
async def tasks_for_calendar(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    db=Depends(get_raw_db),
):
    """Return open tasks with a due_date inside [start, end]."""
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,''), priority, due_date,
                  done, COALESCE(site,'')
           FROM tasks
           WHERE due_date IS NOT NULL
             AND due_date >= ? AND due_date <= ?
             AND done = 0
           ORDER BY due_date ASC, priority ASC""",
        (start, end),
    )
    return [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "priority": r[3],
            "due_date": r[4],
            "done": bool(r[5]),
            "site": r[6],
        }
        for r in rows
    ]
