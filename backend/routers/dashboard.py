from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from ..database import get_raw_db
from ..schemas.dashboard import (
    CategoryStatItem,
    CompletionResponse,
    KpiResponse,
    SystemMonitorResponse,
    TopTaskResponse,
    WeeklyStatItem,
)
from ..services.system_monitor import get_system_stats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=KpiResponse)
async def kpis(db=Depends(get_raw_db)):
    today = date.today().isoformat()
    # End of week (Sunday)
    week_end = (date.today() + timedelta(days=(6 - date.today().weekday()))).isoformat()

    row = await db.execute_fetchall(
        "SELECT COUNT(*) FROM tasks WHERE done = 0"
    )
    open_tasks = row[0][0]

    row = await db.execute_fetchall(
        "SELECT COUNT(*) FROM tasks WHERE done = 0 AND due_date IS NOT NULL AND due_date != '' AND due_date < ?",
        (today,),
    )
    overdue_tasks = row[0][0]

    row = await db.execute_fetchall(
        "SELECT COUNT(*) FROM tasks WHERE done = 0 AND due_date IS NOT NULL AND due_date != '' AND due_date >= ? AND due_date <= ?",
        (today, week_end),
    )
    week_tasks = row[0][0]

    row = await db.execute_fetchall("SELECT COUNT(*) FROM documents")
    documents = row[0][0]

    row = await db.execute_fetchall("SELECT COUNT(*) FROM parc_equipment")
    equipment = row[0][0]

    return KpiResponse(
        open_tasks=open_tasks,
        overdue_tasks=overdue_tasks,
        week_tasks=week_tasks,
        documents=documents,
        equipment=equipment,
    )


@router.get("/sysmon", response_model=SystemMonitorResponse)
async def sysmon():
    return SystemMonitorResponse(**get_system_stats())


@router.get("/stats/weekly", response_model=list[WeeklyStatItem])
async def stats_weekly(db=Depends(get_raw_db)):
    """Tasks completed per week for the last 8 weeks."""
    results: list[WeeklyStatItem] = []
    today = date.today()
    for i in range(7, -1, -1):
        week_start = today - timedelta(weeks=i, days=today.weekday())
        week_end = week_start + timedelta(days=6)
        row = await db.execute_fetchall(
            "SELECT COUNT(*) FROM tasks WHERE done = 1 AND created_at >= ? AND created_at <= ?",
            (week_start.isoformat(), week_end.isoformat() + "T23:59:59"),
        )
        label = f"S{week_start.isocalendar()[1]}"
        results.append(WeeklyStatItem(label=label, count=row[0][0]))
    return results


@router.get("/stats/categories", response_model=list[CategoryStatItem])
async def stats_categories(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT COALESCE(category, '') as cat, COUNT(*) as cnt FROM tasks WHERE done = 0 GROUP BY cat ORDER BY cnt DESC"
    )
    return [CategoryStatItem(category=r[0] or "Sans catégorie", count=r[1]) for r in rows]


@router.get("/stats/completion", response_model=CompletionResponse)
async def stats_completion(db=Depends(get_raw_db)):
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    month_end = today.isoformat() + "T23:59:59"

    row = await db.execute_fetchall(
        "SELECT COUNT(*) FROM tasks WHERE created_at >= ? AND created_at <= ?",
        (month_start, month_end),
    )
    created = row[0][0]

    row = await db.execute_fetchall(
        "SELECT COUNT(*) FROM tasks WHERE done = 1 AND created_at >= ? AND created_at <= ?",
        (month_start, month_end),
    )
    done = row[0][0]

    rate = round((done / created * 100) if created > 0 else 0, 1)
    return CompletionResponse(created=created, done=done, rate=rate)


@router.get("/top-tasks", response_model=list[TopTaskResponse])
async def top_tasks(limit: int = Query(5, ge=1, le=50), db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, title, COALESCE(category,'') as category, priority,
                  due_date, COALESCE(site,'') as site
           FROM tasks
           WHERE done = 0
           ORDER BY priority ASC, due_date ASC NULLS LAST
           LIMIT ?""",
        (limit,),
    )
    return [
        TopTaskResponse(
            id=r[0], title=r[1], category=r[2], priority=r[3], due_date=r[4], site=r[5]
        )
        for r in rows
    ]
