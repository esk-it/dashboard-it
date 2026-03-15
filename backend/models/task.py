from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String, default="")
    priority = Column(Integer, default=2)
    due_date = Column(String, nullable=True)
    done = Column(Integer, default=0)
    created_at = Column(String, default="")
    notes = Column(Text, default="")
    site = Column(String, default="")
    recurrence = Column(String, default="")

    checklist = relationship("TaskChecklist", back_populates="task", cascade="all, delete-orphan")


class TaskChecklist(Base):
    __tablename__ = "task_checklist"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    text = Column(String, nullable=False)
    done = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)

    task = relationship("Task", back_populates="checklist")


class TaskTemplate(Base):
    __tablename__ = "task_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    title = Column(String, default="")
    category = Column(String, default="")
    priority = Column(Integer, default=2)
    notes = Column(Text, default="")
    site = Column(String, default="")
    recurrence = Column(String, default="")
    checklist_json = Column(Text, default="[]")


class TaskCategory(Base):
    __tablename__ = "task_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    sort_order = Column(Integer, default=0)
