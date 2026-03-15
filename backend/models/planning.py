from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from .task import Base


class PlanningEvent(Base):
    __tablename__ = "planning_events"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    event_type = Column(String, default="")
    date_start = Column(String, default="")
    date_end = Column(String, nullable=True)
    all_day = Column(Integer, default=0)
    time_start = Column(String, nullable=True)
    time_end = Column(String, nullable=True)
    person = Column(String, default="")
    notes = Column(Text, default="")
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(String, default="")
