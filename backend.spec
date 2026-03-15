# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ITManager Dashboard backend."""

import os
from pathlib import Path

block_cipher = None
project_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(project_dir, 'run_backend.py')],
    pathex=[project_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        # FastAPI / Uvicorn
        'uvicorn',
        'uvicorn.config',
        'uvicorn.main',
        'uvicorn.server',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # FastAPI internals
        'fastapi',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.responses',
        'starlette.requests',
        'starlette.datastructures',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'h11',
        # SQLAlchemy async
        'aiosqlite',
        'sqlalchemy.ext.asyncio',
        # Backend modules
        'backend',
        'backend.main',
        'backend.database',
        'backend.routers',
        'backend.routers.dashboard',
        'backend.routers.tasks',
        'backend.routers.settings',
        'backend.routers.search',
        'backend.routers.planning',
        'backend.routers.documents',
        'backend.routers.changelog',
        'backend.routers.wiki',
        'backend.routers.news',
        'backend.routers.suppliers',
        'backend.routers.parc',
        'backend.routers.security',
        'backend.routers.bastion',
        'backend.routers.tools',
        'backend.schemas',
        'backend.schemas.bastion',
        'backend.schemas.changelog',
        'backend.schemas.dashboard',
        'backend.schemas.document',
        'backend.schemas.parc',
        'backend.schemas.security',
        'backend.schemas.settings',
        'backend.schemas.supplier',
        'backend.schemas.task',
        'backend.schemas.wiki',
        # RSS feeds
        'feedparser',
        'sgmllib',
        # Paramiko for SSH
        'paramiko',
        # System info
        'psutil',
        # HTTP client
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        # Multipart
        'multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console for backend logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
