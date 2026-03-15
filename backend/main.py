from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import dashboard, tasks, settings, search, planning, documents, changelog, wiki, news, suppliers, parc, security, bastion, tools

app = FastAPI(title="ITManager Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
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
app.include_router(bastion.router)
app.include_router(tools.router)
