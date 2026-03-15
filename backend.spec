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
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
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
