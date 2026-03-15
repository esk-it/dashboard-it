from __future__ import annotations

from pydantic import BaseModel


class KpiResponse(BaseModel):
    open_tasks: int
    overdue_tasks: int
    week_tasks: int
    documents: int
    equipment: int


class SystemMonitorResponse(BaseModel):
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    ram_free_gb: float
    disk_free_gb: float


class WeeklyStatItem(BaseModel):
    label: str
    count: int


class CategoryStatItem(BaseModel):
    category: str
    count: int


class CompletionResponse(BaseModel):
    created: int
    done: int
    rate: float


class TopTaskResponse(BaseModel):
    id: int
    title: str
    category: str
    priority: int
    due_date: str | None
    site: str
