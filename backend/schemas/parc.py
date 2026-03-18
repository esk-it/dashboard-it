from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Equipment ───────────────────────────────────────────────

class EquipmentCreate(BaseModel):
    hostname: str = ""
    equip_type: str = "PC"
    os: str = ""
    serial_number: str = ""
    brand: str = ""
    model: str = ""
    site_id: Optional[int] = None
    building_id: Optional[int] = None
    room_id: Optional[int] = None
    source: str = "manual"
    notes: str = ""
    warranty_end: Optional[str] = None
    purchase_date: Optional[str] = None
    glpi_id: Optional[int] = None
    glpi_location: str = ""
    last_user: str = ""


class EquipmentUpdate(EquipmentCreate):
    pass


class EquipmentResponse(BaseModel):
    id: int
    hostname: str
    equip_type: str
    os: str
    serial_number: str
    brand: str
    model: str
    site_id: Optional[int]
    building_id: Optional[int]
    room_id: Optional[int]
    source: str
    source_ou: str
    ad_dn: str
    last_seen_ad: str
    warranty_end: Optional[str]
    purchase_date: Optional[str]
    notes: str
    manual_location: str
    created_at: str
    updated_at: str
    glpi_id: Optional[int] = None
    glpi_location: str = ""
    last_user: str = ""
    # Joined names (filled by router)
    site_name: str = ""
    building_name: str = ""
    room_name: str = ""

    model_config = ConfigDict(from_attributes=True)


# ── Sites / Buildings / Rooms ───────────────────────────────

class SiteCreate(BaseModel):
    name: str
    code: str = ""
    city: str = ""


class SiteUpdate(SiteCreate):
    pass


class SiteResponse(BaseModel):
    id: int
    name: str
    code: str
    city: str

    model_config = ConfigDict(from_attributes=True)


class BuildingCreate(BaseModel):
    site_id: int
    name: str


class BuildingUpdate(BaseModel):
    name: str


class BuildingResponse(BaseModel):
    id: int
    site_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoomCreate(BaseModel):
    building_id: int
    name: str
    floor: str = ""


class RoomUpdate(BaseModel):
    name: str
    floor: str = ""


class RoomResponse(BaseModel):
    id: int
    building_id: int
    name: str
    floor: str

    model_config = ConfigDict(from_attributes=True)


# ── Stats ───────────────────────────────────────────────────

class ParcStats(BaseModel):
    total: int = 0
    by_type: dict[str, int] = {}
    by_site: dict[str, int] = {}
    by_source: dict[str, int] = {}
