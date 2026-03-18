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


async def init_db():
    """Create all tables if they don't exist (fresh install)."""
    db = await aiosqlite.connect(str(DB_PATH))
    await db.execute("PRAGMA journal_mode=WAL")

    statements = [
        # --- Tasks ---
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 2,
            due_date TEXT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            site TEXT NOT NULL DEFAULT '',
            recurrence TEXT NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS task_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 100
        )""",
        """CREATE TABLE IF NOT EXISTS task_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS task_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 2,
            notes TEXT NOT NULL DEFAULT '',
            site TEXT NOT NULL DEFAULT '',
            recurrence TEXT NOT NULL DEFAULT '',
            checklist_json TEXT NOT NULL DEFAULT '[]'
        )""",
        # --- Planning ---
        """CREATE TABLE IF NOT EXISTS planning_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            event_type  TEXT NOT NULL DEFAULT 'other',
            date_start  TEXT NOT NULL,
            date_end    TEXT NOT NULL,
            all_day     INTEGER NOT NULL DEFAULT 1,
            time_start  TEXT NULL,
            time_end    TEXT NULL,
            person      TEXT NOT NULL DEFAULT '',
            notes       TEXT NOT NULL DEFAULT '',
            task_id     INTEGER NULL,
            created_at  TEXT NOT NULL
        )""",
        # --- Documents ---
        """CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            supplier_id INTEGER NULL,
            doc_date TEXT NULL,
            reference TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS document_tags (
            document_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (document_id, tag_id),
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS document_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            link_type TEXT NOT NULL DEFAULT 'AUTRE',
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES documents(id) ON DELETE CASCADE,
            UNIQUE(source_id, target_id)
        )""",
        # --- Changelog ---
        """CREATE TABLE IF NOT EXISTS changelog_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            category    TEXT NOT NULL DEFAULT '',
            impact      TEXT NOT NULL DEFAULT 'info',
            author      TEXT NOT NULL DEFAULT '',
            event_date  TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            tags        TEXT NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS changelog_categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            color_hex  TEXT NOT NULL DEFAULT '#64748B',
            icon_key   TEXT NOT NULL DEFAULT 'fa5s.clipboard-list',
            sort_order INTEGER NOT NULL DEFAULT 100
        )""",
        # --- Wiki ---
        """CREATE TABLE IF NOT EXISTS wiki_articles (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT '',
            content    TEXT NOT NULL DEFAULT '',
            tags       TEXT NOT NULL DEFAULT '',
            pinned     INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source_path TEXT NOT NULL DEFAULT '',
            content_format TEXT NOT NULL DEFAULT 'html'
        )""",
        """CREATE TABLE IF NOT EXISTS wiki_categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            color_hex  TEXT NOT NULL DEFAULT '#64748B',
            icon_key   TEXT NOT NULL DEFAULT 'fa5s.folder',
            sort_order INTEGER NOT NULL DEFAULT 100
        )""",
        # --- Suppliers ---
        """CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            domain TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            contact TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            logo_path TEXT NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS supplier_domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color_hex TEXT NOT NULL DEFAULT '#AAB3C5',
            icon_key  TEXT NOT NULL DEFAULT 'fa5s.address-book',
            sort_order INTEGER NOT NULL DEFAULT 100,
            color TEXT NOT NULL DEFAULT '#AAB3C5',
            icon TEXT NOT NULL DEFAULT 'fa5s.address-book'
        )""",
        # --- Parc ---
        """CREATE TABLE IF NOT EXISTS parc_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS parc_buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL REFERENCES parc_sites(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(site_id, name)
        )""",
        """CREATE TABLE IF NOT EXISTS parc_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL REFERENCES parc_buildings(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            floor TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(building_id, name)
        )""",
        """CREATE TABLE IF NOT EXISTS parc_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL DEFAULT '',
            equip_type TEXT NOT NULL DEFAULT 'PC',
            os TEXT NOT NULL DEFAULT '',
            serial_number TEXT NOT NULL DEFAULT '',
            brand TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            site_id INTEGER REFERENCES parc_sites(id) ON DELETE SET NULL,
            building_id INTEGER REFERENCES parc_buildings(id) ON DELETE SET NULL,
            room_id INTEGER REFERENCES parc_rooms(id) ON DELETE SET NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            source_ou TEXT NOT NULL DEFAULT '',
            ad_dn TEXT NOT NULL DEFAULT '',
            last_seen_ad TEXT,
            warranty_end TEXT,
            purchase_date TEXT,
            notes TEXT NOT NULL DEFAULT '',
            manual_location INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS parc_site_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            pattern TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(site_id, pattern),
            FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
        )""",
        # --- Security (WithSecure) ---
        """CREATE TABLE IF NOT EXISTS ws_endpoints (
            hostname TEXT PRIMARY KEY,
            online INTEGER,
            os_name TEXT,
            profile TEXT,
            client_version TEXT,
            malware_protection TEXT,
            sw_updates_state TEXT,
            groups_text TEXT,
            tags_text TEXT,
            ip_addrs TEXT,
            uuid TEXT,
            enrolled_at TEXT,
            updated_at TEXT,
            last_imported_at TEXT NOT NULL,
            dns_address TEXT,
            wins_address TEXT,
            status_update_ts TEXT,
            ws_recent INTEGER,
            serial_number TEXT,
            state TEXT,
            protection_overview TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS ws_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TEXT NOT NULL,
            file_name TEXT NOT NULL,
            row_count INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS ws_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
        # --- AD ---
        """CREATE TABLE IF NOT EXISTS ad_computers (
            hostname TEXT NOT NULL,
            dnshostname TEXT,
            enabled INTEGER NOT NULL,
            source TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            last_logon_date TEXT,
            PRIMARY KEY (hostname, source)
        )""",
        """CREATE TABLE IF NOT EXISTS ad_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TEXT NOT NULL,
            source TEXT NOT NULL,
            file_name TEXT NOT NULL,
            row_count INTEGER NOT NULL
        )""",
        # --- Bastion ---
        """CREATE TABLE IF NOT EXISTS bastion_groups (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            color_hex  TEXT    NOT NULL DEFAULT '#4B8BFF',
            sort_order INTEGER NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS bastion_servers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            hostname     TEXT    NOT NULL,
            port         INTEGER NOT NULL DEFAULT 22,
            username     TEXT    NOT NULL DEFAULT '',
            protocol     TEXT    NOT NULL DEFAULT 'SSH',
            group_name   TEXT    NOT NULL DEFAULT '',
            notes        TEXT    NOT NULL DEFAULT '',
            ssh_key_path TEXT    NOT NULL DEFAULT '',
            created_at   TEXT    NOT NULL DEFAULT '',
            updated_at   TEXT    NOT NULL DEFAULT ''
        )""",
        # --- Misc (sites, buildings, rooms for old parc) ---
        """CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )""",
        """CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(site_id, name),
            FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            floor TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            UNIQUE(building_id, floor, name),
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL UNIQUE,
            scope TEXT NOT NULL DEFAULT 'ADMIN',
            site_id INTEGER NULL,
            building_id INTEGER NULL,
            room_id INTEGER NULL,
            location_source TEXT NOT NULL DEFAULT 'UNKNOWN',
            status TEXT NOT NULL DEFAULT 'ACTIF',
            device_type TEXT NOT NULL DEFAULT 'FIXE',
            os TEXT NOT NULL DEFAULT '',
            primary_user TEXT NOT NULL DEFAULT '',
            purchase_date TEXT NULL,
            warranty_end TEXT NULL,
            last_seen_ad TEXT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE SET NULL,
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE SET NULL,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS machine_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            at TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE
        )""",
    ]

    for stmt in statements:
        await db.execute(stmt)
    await db.commit()

    # --- Migrations for existing databases ---
    await _run_migrations(db)
    await db.commit()

    # --- Insert default data if tables are empty ---
    await _seed_defaults(db)

    await db.commit()
    await db.close()


async def _run_migrations(db):
    """Apply schema migrations for existing databases."""
    # Check if content_format column exists in wiki_articles
    cursor = await db.execute("PRAGMA table_info(wiki_articles)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "content_format" not in columns:
        await db.execute(
            "ALTER TABLE wiki_articles ADD COLUMN content_format TEXT NOT NULL DEFAULT 'html'"
        )

    # GLPI integration columns on parc_equipment
    cursor = await db.execute("PRAGMA table_info(parc_equipment)")
    parc_cols = [row[1] for row in await cursor.fetchall()]
    if "glpi_id" not in parc_cols:
        await db.execute("ALTER TABLE parc_equipment ADD COLUMN glpi_id INTEGER")
    if "glpi_location" not in parc_cols:
        await db.execute(
            "ALTER TABLE parc_equipment ADD COLUMN glpi_location TEXT NOT NULL DEFAULT ''"
        )
    if "last_user" not in parc_cols:
        await db.execute(
            "ALTER TABLE parc_equipment ADD COLUMN last_user TEXT NOT NULL DEFAULT ''"
        )


async def _seed_defaults(db):
    """Insert default data into empty tables (first launch only)."""

    # Default task categories
    row = await db.execute("SELECT COUNT(*) FROM task_categories")
    count = (await row.fetchone())[0]
    if count == 0:
        categories = [
            "Administration", "Réseau", "Pédagogique",
            "Sécurité", "Serveurs", "Maintenance", "Support",
        ]
        for i, name in enumerate(categories):
            await db.execute(
                "INSERT INTO task_categories (name, sort_order) VALUES (?, ?)",
                (name, 100),
            )

    # Default supplier domains
    row = await db.execute("SELECT COUNT(*) FROM supplier_domains")
    count = (await row.fetchone())[0]
    if count == 0:
        domains = [
            ("Réseau",        "#2D6CDF", "fa5s.network-wired",  10),
            ("Wi-Fi",         "#FF55FF", "fa5s.wifi",           20),
            ("Fibre/Internet","#55007F", "fa5s.project-diagram",30),
            ("Téléphonie",    "#00FF00", "fa5s.phone",          40),
            ("Imprimantes",   "#AA5500", "fa5s.print",          50),
            ("Sécurité",      "#EF4444", "fa5s.shield-alt",     60),
            ("Support",       "#FF5500", "fa5s.tools",          70),
            ("Logiciels",     "#22C55E", "fa5s.puzzle-piece",   80),
            ("Matériel",      "#AAB3C5", "fa5s.toolbox",        90),
        ]
        for name, color, icon, order in domains:
            await db.execute(
                "INSERT INTO supplier_domains (name, color_hex, icon_key, sort_order, color, icon) VALUES (?, ?, ?, ?, ?, ?)",
                (name, color, icon, order, color, icon),
            )
