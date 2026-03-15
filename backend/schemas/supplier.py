from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SupplierCreate(BaseModel):
    name: str
    domain: str = ""
    phone: str = ""
    email: str = ""
    contact: str = ""
    notes: str = ""


class SupplierUpdate(SupplierCreate):
    pass


class SupplierResponse(BaseModel):
    id: int
    name: str
    domain: str
    phone: str
    email: str
    contact: str
    notes: str
    logo_path: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class DomainCreate(BaseModel):
    name: str
    color_hex: str = "#64748B"
    icon_key: str = "briefcase"
    sort_order: int = 0


class DomainUpdate(DomainCreate):
    pass


class DomainResponse(BaseModel):
    id: int
    name: str
    color_hex: str
    icon_key: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
