from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from .task import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    doc_type = Column(String, default="")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    doc_date = Column(String, default="")
    reference = Column(String, default="")
    file_path = Column(String, default="")
    file_hash = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(String, default="")


class DocumentLink(Base):
    __tablename__ = "document_links"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    link_type = Column(String, default="")
    created_at = Column(String, default="")
