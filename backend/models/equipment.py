from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from .task import Base


class Equipment(Base):
    __tablename__ = "parc_equipment"

    id = Column(Integer, primary_key=True)
    hostname = Column(String, default="")
    equip_type = Column(String, default="")
    os = Column(String, default="")
    serial_number = Column(String, default="")
    brand = Column(String, default="")
    model = Column(String, default="")
    site_id = Column(Integer, ForeignKey("parc_sites.id"), nullable=True)
    building_id = Column(Integer, ForeignKey("parc_buildings.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("parc_rooms.id"), nullable=True)
    source = Column(String, default="")
    source_ou = Column(String, default="")
    ad_dn = Column(String, default="")
    last_seen_ad = Column(String, default="")
    warranty_end = Column(String, nullable=True)
    purchase_date = Column(String, nullable=True)
    notes = Column(Text, default="")
    manual_location = Column(String, default="")
    created_at = Column(String, default="")
    updated_at = Column(String, default="")


class Site(Base):
    __tablename__ = "parc_sites"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, default="")
    city = Column(String, default="")


class Building(Base):
    __tablename__ = "parc_buildings"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("parc_sites.id"), nullable=False)
    name = Column(String, nullable=False)


class Room(Base):
    __tablename__ = "parc_rooms"

    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("parc_buildings.id"), nullable=False)
    name = Column(String, nullable=False)
    floor = Column(String, default="")
