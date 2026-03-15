from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    category: str = ""
    priority: int = 2
    due_date: str | None = None
    notes: str = ""
    site: str = ""
    recurrence: str = ""


class TaskUpdate(TaskCreate):
    pass


class TaskResponse(BaseModel):
    id: int
    title: str
    category: str
    priority: int
    due_date: str | None
    done: bool
    created_at: str
    notes: str
    site: str
    recurrence: str

    model_config = ConfigDict(from_attributes=True)


class ChecklistItemCreate(BaseModel):
    text: str
    sort_order: int = 0


class ChecklistItemResponse(BaseModel):
    id: int
    task_id: int
    text: str
    done: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class TemplateCreate(BaseModel):
    name: str
    title: str = ""
    category: str = ""
    priority: int = 2
    notes: str = ""
    site: str = ""
    recurrence: str = ""
    checklist_json: str = "[]"


class TemplateResponse(BaseModel):
    id: int
    name: str
    title: str
    category: str
    priority: int
    notes: str
    site: str
    recurrence: str
    checklist_json: str

    model_config = ConfigDict(from_attributes=True)


class TemplateUse(BaseModel):
    due_date: str | None = None
