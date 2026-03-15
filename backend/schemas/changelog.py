from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChangelogEntryCreate(BaseModel):
    title: str
    description: str = ""
    category: str = ""
    impact: str = "low"
    author: str = ""
    event_date: str | None = None
    tags: str = ""


class ChangelogEntryUpdate(ChangelogEntryCreate):
    pass


class ChangelogEntryResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    impact: str
    author: str
    event_date: str | None
    created_at: str
    tags: str

    model_config = ConfigDict(from_attributes=True)


class ChangelogCategoryResponse(BaseModel):
    id: int
    name: str
    color_hex: str
    icon_key: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ChangelogStatCategory(BaseModel):
    category: str
    count: int


class ChangelogStatMonth(BaseModel):
    month: str
    count: int


class ChangelogStatsResponse(BaseModel):
    by_category: list[ChangelogStatCategory]
    by_month: list[ChangelogStatMonth]
