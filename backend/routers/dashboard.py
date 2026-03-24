from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, Query

from ..database import get_raw_db

logger = logging.getLogger(__name__)
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


# ── Weather (free, no API key) ────────────────────────────────
_weather_cache: dict = {}

@router.get("/weather")
async def weather():
    """Get weather using IP geolocation + Open-Meteo (free, no API key needed)."""
    import time
    # Cache for 30 minutes
    if _weather_cache.get("data") and time.time() - _weather_cache.get("ts", 0) < 1800:
        return _weather_cache["data"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 1. Get location from IP
            geo = await client.get("https://ipapi.co/json/")
            geo_data = geo.json()
            lat = geo_data.get("latitude", 48.86)
            lon = geo_data.get("longitude", 2.35)
            city = geo_data.get("city", "Paris")

            # 2. Get weather from Open-Meteo (free, no key)
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
                f"&daily=temperature_2m_max,temperature_2m_min,weather_code"
                f"&timezone=auto&forecast_days=3"
            )
            resp = await client.get(weather_url)
            data = resp.json()

            current = data.get("current", {})
            daily = data.get("daily", {})

            # WMO weather codes → description + emoji
            wmo = _wmo_code(current.get("weather_code", 0))

            result = {
                "city": city,
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "description": wmo["desc"],
                "emoji": wmo["emoji"],
                "forecast": [],
            }

            # 3-day forecast
            for i in range(min(3, len(daily.get("time", [])))):
                fc_wmo = _wmo_code(daily["weather_code"][i])
                result["forecast"].append({
                    "date": daily["time"][i],
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "description": fc_wmo["desc"],
                    "emoji": fc_wmo["emoji"],
                })

            _weather_cache["data"] = result
            _weather_cache["ts"] = time.time()
            return result

    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
        return {"city": "N/A", "temperature": None, "emoji": "\u2601\uFE0F", "description": "Indisponible", "forecast": []}


def _wmo_code(code: int) -> dict:
    """Convert WMO weather code to description + emoji."""
    mapping = {
        0: ("Ciel d\u00e9gag\u00e9", "\u2600\uFE0F"), 1: ("Peu nuageux", "\u{1F324}\uFE0F"),
        2: ("Partiellement nuageux", "\u26C5"), 3: ("Couvert", "\u2601\uFE0F"),
        45: ("Brouillard", "\u{1F32B}\uFE0F"), 48: ("Brouillard givrant", "\u{1F32B}\uFE0F"),
        51: ("Bruine l\u00e9g\u00e8re", "\u{1F326}\uFE0F"), 53: ("Bruine", "\u{1F326}\uFE0F"), 55: ("Bruine forte", "\u{1F327}\uFE0F"),
        61: ("Pluie l\u00e9g\u00e8re", "\u{1F326}\uFE0F"), 63: ("Pluie", "\u{1F327}\uFE0F"), 65: ("Pluie forte", "\u{1F327}\uFE0F"),
        71: ("Neige l\u00e9g\u00e8re", "\u{1F328}\uFE0F"), 73: ("Neige", "\u2744\uFE0F"), 75: ("Neige forte", "\u2744\uFE0F"),
        80: ("Averses", "\u{1F326}\uFE0F"), 81: ("Averses mod\u00e9r\u00e9es", "\u{1F327}\uFE0F"), 82: ("Averses violentes", "\u{1F327}\uFE0F"),
        85: ("Averses de neige", "\u{1F328}\uFE0F"), 86: ("Averses de neige fortes", "\u{1F328}\uFE0F"),
        95: ("Orage", "\u26C8\uFE0F"), 96: ("Orage gr\u00eale", "\u26C8\uFE0F"), 99: ("Orage gr\u00eale fort", "\u26C8\uFE0F"),
    }
    desc, emoji = mapping.get(code, ("Inconnu", "\u{1F300}"))
    return {"desc": desc, "emoji": emoji}


# ── Recent activity feed ──────────────────────────────────────

@router.get("/activity")
async def recent_activity(limit: int = Query(15, ge=1, le=50), db=Depends(get_raw_db)):
    """Aggregate recent actions across all modules."""
    activities = []

    # Recent tasks (created or completed)
    rows = await db.execute_fetchall(
        "SELECT id, title, done, created_at FROM tasks ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    for r in rows:
        activities.append({
            "type": "task",
            "emoji": "\u2705" if r[2] else "\u{1F4CB}",
            "text": f"{'Termin\u00e9e' if r[2] else 'Cr\u00e9\u00e9e'} : {r[1]}",
            "date": r[3],
        })

    # Recent planning events
    rows = await db.execute_fetchall(
        "SELECT id, title, created_at FROM planning_events ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    for r in rows:
        activities.append({
            "type": "planning",
            "emoji": "\u{1F4C5}",
            "text": f"\u00c9v\u00e9nement : {r[1]}",
            "date": r[2],
        })

    # Recent documents
    rows = await db.execute_fetchall(
        "SELECT id, title, created_at FROM documents ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    for r in rows:
        activities.append({
            "type": "document",
            "emoji": "\u{1F4C4}",
            "text": f"Document : {r[1]}",
            "date": r[2],
        })

    # Recent changelog entries
    rows = await db.execute_fetchall(
        "SELECT id, title, created_at FROM changelog_entries ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    for r in rows:
        activities.append({
            "type": "changelog",
            "emoji": "\u{1F4CB}",
            "text": f"Changelog : {r[1]}",
            "date": r[2],
        })

    # Recent wiki articles
    rows = await db.execute_fetchall(
        "SELECT id, title, updated_at FROM wiki_articles ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    for r in rows:
        activities.append({
            "type": "wiki",
            "emoji": "\u{1F4D6}",
            "text": f"Proc\u00e9dure : {r[1]}",
            "date": r[2],
        })

    # Sort all by date descending
    activities.sort(key=lambda a: a.get("date") or "", reverse=True)
    return activities[:limit]
