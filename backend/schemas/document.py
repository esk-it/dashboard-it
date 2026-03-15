from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    title: str
    doc_type: str = ""
    supplier_id: int | None = None
    doc_date: str | None = None
    reference: str = ""
    file_path: str = ""
    file_hash: str = ""
    notes: str = ""
    tag_ids: list[int] = []


class DocumentUpdate(DocumentCreate):
    pass


class DocumentResponse(BaseModel):
    id: int
    title: str
    doc_type: str
    supplier_id: int | None
    supplier_name: str
    doc_date: str | None
    reference: str
    file_path: str
    file_hash: str
    notes: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TagResponse(BaseModel):
    id: int
    name: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class DocumentLinkResponse(BaseModel):
    id: int
    source_id: int
    target_id: int
    link_type: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class DocumentLinkCreate(BaseModel):
    target_id: int
    link_type: str = "related"


class DocumentDetailResponse(DocumentResponse):
    tags: list[TagResponse] = []
    links: list[DocumentLinkResponse] = []
