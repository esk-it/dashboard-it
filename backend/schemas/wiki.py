from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WikiArticleCreate(BaseModel):
    title: str
    category: str = ""
    content: str = ""
    tags: str = ""
    pinned: bool = False
    source_path: str = ""


class WikiArticleUpdate(WikiArticleCreate):
    pass


class WikiArticleListResponse(BaseModel):
    id: int
    title: str
    category: str
    pinned: bool
    tags: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class WikiArticleResponse(BaseModel):
    id: int
    title: str
    category: str
    content: str
    tags: str
    pinned: bool
    created_at: str
    updated_at: str
    source_path: str

    model_config = ConfigDict(from_attributes=True)


class WikiCategoryResponse(BaseModel):
    id: int
    name: str
    color_hex: str
    icon_key: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
