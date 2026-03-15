from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from .task import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    domain = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    contact = Column(String, default="")
    notes = Column(Text, default="")
    logo_path = Column(String, default="")
    created_at = Column(String, default="")


class SupplierDomain(Base):
    __tablename__ = "supplier_domains"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    color_hex = Column(String, default="#888888")
    icon_key = Column(String, default="")
    sort_order = Column(Integer, default=0)
