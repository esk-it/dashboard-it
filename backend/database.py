from __future__ import annotations

import os
import sys
from pathlib import Path

import aiosqlite
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# When running as PyInstaller bundle, use AppData for persistent storage
if os.environ.get("ITMANAGER_DATA_DIR"):
    BASE_DIR = Path(os.environ["ITMANAGER_DATA_DIR"])
else:
    BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dashboard.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency – yields an async SQLAlchemy session."""
    async with async_session_factory() as session:
        yield session


async def get_raw_db():
    """FastAPI dependency – yields a raw aiosqlite connection.

    Preferred for read/query endpoints to avoid ORM schema mismatch with
    the existing database.
    """
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    try:
        yield db
    finally:
        await db.close()
