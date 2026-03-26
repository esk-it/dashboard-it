from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import dashboard, tasks, settings, search, planning, documents, changelog, wiki, news, suppliers, parc, security, monitoring, tools, glpi, launcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup (handles fresh installs)."""
    await init_db()
    yield


app = FastAPI(title="ITManager Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(search.router)
app.include_router(planning.router)
app.include_router(documents.router)
app.include_router(changelog.router)
app.include_router(wiki.router)
app.include_router(news.router)
app.include_router(suppliers.router)
app.include_router(parc.router)
app.include_router(security.router)
app.include_router(monitoring.router)
app.include_router(tools.router)
app.include_router(glpi.router)
app.include_router(launcher.router)
