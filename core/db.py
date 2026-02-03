# core/db.py
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List


# -----------------------------
# Tasks
# -----------------------------
@dataclass(frozen=True)
class Task:
    id: int
    title: str
    category: str
    priority: int
    due_date: Optional[str]
    done: bool
    created_at: str


class TaskRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    priority INTEGER NOT NULL DEFAULT 2,
                    due_date TEXT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
            con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);")

    def add_task(self, title: str, category: str = "", priority: int = 2, due_date: Optional[str] = None) -> int:
        title = title.strip()
        if not title:
            raise ValueError("title is empty")

        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as con:
            cur = con.execute(
                """
                INSERT INTO tasks(title, category, priority, due_date, done, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (title, category.strip(), int(priority), due_date, created_at),
            )
            return int(cur.lastrowid)

    def list_tasks(self, status: str = "all", search: str = "") -> List[Task]:
        where = []
        params: list = []

        if status == "open":
            where.append("done = 0")
        elif status == "done":
            where.append("done = 1")

        s = search.strip()
        if s:
            where.append("(title LIKE ? OR category LIKE ?)")
            like = f"%{s}%"
            params += [like, like]

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
            SELECT id, title, category, priority, due_date, done, created_at
            FROM tasks
            {where_sql}
            ORDER BY
                done ASC,
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,
                due_date ASC,
                created_at DESC;
        """

        with self._connect() as con:
            rows = con.execute(sql, params).fetchall()

        return [
            Task(
                id=int(r["id"]),
                title=str(r["title"]),
                category=str(r["category"] or ""),
                priority=int(r["priority"] or 2),
                due_date=r["due_date"],
                done=bool(r["done"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def count_tasks(self) -> tuple[int, int]:
        with self._connect() as con:
            open_count = con.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0]
            done_count = con.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        return int(open_count), int(done_count)

    def top_open_tasks(self, limit: int = 5) -> list[Task]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, title, category, priority, due_date, done, created_at
                FROM tasks
                WHERE done = 0
                ORDER BY
                    CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,
                    due_date ASC,
                    priority DESC,
                    created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

        return [
            Task(
                id=int(r["id"]),
                title=str(r["title"]),
                category=str(r["category"] or ""),
                priority=int(r["priority"] or 2),
                due_date=r["due_date"],
                done=bool(r["done"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def set_done(self, task_id: int, done: bool) -> None:
        with self._connect() as con:
            con.execute("UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, int(task_id)))

    def delete_task(self, task_id: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))


# -----------------------------
# Suppliers
# -----------------------------
@dataclass(frozen=True)
class Supplier:
    id: int
    name: str
    domain: str
    phone: str
    email: str
    contact: str
    notes: str
    logo_path: str
    created_at: str


@dataclass(frozen=True)
class SupplierDomain:
    name: str
    color_hex: str
    icon_key: str
    sort_order: int


class SupplierRepository:
    DEFAULT_DOMAINS: list[SupplierDomain] = [
        SupplierDomain("Réseau",         "#2D6CDF", "fa5s.network-wired", 10),
        SupplierDomain("Wi-Fi",          "#2D6CDF", "fa5s.wifi",          20),
        SupplierDomain("Fibre/Internet", "#7C3AED", "fa5s.globe-europe",  30),
        SupplierDomain("Téléphonie",     "#10B981", "fa5s.phone",         40),
        SupplierDomain("Impression",     "#F59E0B", "fa5s.print",         50),
        SupplierDomain("Sécurité",       "#EF4444", "fa5s.shield-alt",    60),
        SupplierDomain("Logiciels",      "#22C55E", "fa5s.puzzle-piece",  70),
        SupplierDomain("Matériel",       "#AAB3C5", "fa5s.toolbox",       80),
    ]

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _table_has_column(self, con: sqlite3.Connection, table: str, column: str) -> bool:
        cols = con.execute(f"PRAGMA table_info({table})").fetchall()
        return any(str(c[1]).lower() == column.lower() for c in cols)

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    domain TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    contact TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);")
            con.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_domain ON suppliers(domain);")

            if not self._table_has_column(con, "suppliers", "logo_path"):
                con.execute("ALTER TABLE suppliers ADD COLUMN logo_path TEXT NOT NULL DEFAULT '';")

            con.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color_hex TEXT NOT NULL DEFAULT '#AAB3C5',
                    icon_key  TEXT NOT NULL DEFAULT 'fa5s.address-book',
                    sort_order INTEGER NOT NULL DEFAULT 100
                );
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_supplier_domains_sort ON supplier_domains(sort_order, name);")

        self.ensure_default_domains()
        self._import_existing_domains_from_suppliers()

    def ensure_default_domains(self) -> None:
        with self._connect() as con:
            for d in self.DEFAULT_DOMAINS:
                con.execute(
                    """
                    INSERT OR IGNORE INTO supplier_domains(name, color_hex, icon_key, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (d.name, d.color_hex, d.icon_key, int(d.sort_order)),
                )

    def _import_existing_domains_from_suppliers(self) -> None:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT DISTINCT domain
                FROM suppliers
                WHERE domain IS NOT NULL AND TRIM(domain) != ''
                """
            ).fetchall()
            for r in rows:
                name = str(r["domain"]).strip()
                if name:
                    con.execute("INSERT OR IGNORE INTO supplier_domains(name) VALUES (?)", (name,))

    # ---- Domains CRUD ----
    def list_domain_records(self) -> list[SupplierDomain]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT name, color_hex, icon_key, sort_order
                FROM supplier_domains
                ORDER BY sort_order ASC, name COLLATE NOCASE ASC
                """
            ).fetchall()

        return [
            SupplierDomain(
                name=str(r["name"]),
                color_hex=str(r["color_hex"] or "#AAB3C5"),
                icon_key=str(r["icon_key"] or "fa5s.address-book"),
                sort_order=int(r["sort_order"] or 100),
            )
            for r in rows
        ]

    def list_domains(self) -> list[str]:
        return [d.name for d in self.list_domain_records()]

    def domain_in_use(self, domain_name: str) -> bool:
        dn = (domain_name or "").strip()
        if not dn:
            return False
        with self._connect() as con:
            n = con.execute(
                "SELECT COUNT(*) FROM suppliers WHERE domain = ?",
                (dn,),
            ).fetchone()[0]
        return int(n) > 0

    def add_domain(self, name: str, color_hex: str = "#AAB3C5", icon_key: str = "fa5s.address-book", sort_order: int = 100) -> None:
        n = (name or "").strip()
        if not n:
            raise ValueError("Nom de domaine vide.")
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO supplier_domains(name, color_hex, icon_key, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (n, (color_hex or "#AAB3C5").strip(), (icon_key or "fa5s.address-book").strip(), int(sort_order)),
            )

    def update_domain(
        self,
        old_name: str,
        new_name: str,
        color_hex: str,
        icon_key: str,
        sort_order: int,
    ) -> None:
        oldn = (old_name or "").strip()
        newn = (new_name or "").strip()
        if not oldn or not newn:
            raise ValueError("Nom de domaine invalide.")

        with self._connect() as con:
            con.execute(
                """
                UPDATE supplier_domains
                SET name=?, color_hex=?, icon_key=?, sort_order=?
                WHERE name=?
                """,
                (newn, (color_hex or "#AAB3C5").strip(), (icon_key or "fa5s.address-book").strip(), int(sort_order), oldn),
            )

            # Si renommage : on met à jour les suppliers qui utilisent l'ancien domaine
            if oldn != newn:
                con.execute(
                    "UPDATE suppliers SET domain=? WHERE domain=?",
                    (newn, oldn),
                )

    def delete_domain(self, name: str) -> None:
        n = (name or "").strip()
        if not n:
            return
        if self.domain_in_use(n):
            raise ValueError("Impossible : ce domaine est utilisé par au moins un prestataire.")
        with self._connect() as con:
            con.execute("DELETE FROM supplier_domains WHERE name=?", (n,))

    def upsert_domain_if_needed(self, name: str) -> None:
        n = (name or "").strip()
        if not n:
            return
        with self._connect() as con:
            con.execute("INSERT OR IGNORE INTO supplier_domains(name) VALUES (?)", (n,))

    # ---- Suppliers CRUD ----
    def add_supplier(
        self,
        name: str,
        domain: str = "",
        phone: str = "",
        email: str = "",
        contact: str = "",
        notes: str = "",
        logo_path: str = "",
    ) -> int:
        name = name.strip()
        if not name:
            raise ValueError("name is empty")

        domain = (domain or "").strip()
        self.upsert_domain_if_needed(domain)

        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as con:
            cur = con.execute(
                """
                INSERT INTO suppliers(name, domain, phone, email, contact, notes, logo_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    domain,
                    phone.strip(),
                    email.strip(),
                    contact.strip(),
                    notes.strip(),
                    (logo_path or "").strip(),
                    created_at,
                ),
            )
            return int(cur.lastrowid)

    def delete_supplier(self, supplier_id: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM suppliers WHERE id = ?", (int(supplier_id),))

    def list_suppliers(self, search: str = "", domain: str = "") -> list[Supplier]:
        where = []
        params: list = []

        s = search.strip()
        if s:
            where.append("(name LIKE ? OR domain LIKE ? OR phone LIKE ? OR email LIKE ? OR contact LIKE ? OR notes LIKE ?)")
            like = f"%{s}%"
            params += [like, like, like, like, like, like]

        d = (domain or "").strip()
        if d and d != "Tous":
            where.append("domain = ?")
            params.append(d)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
            SELECT id, name, domain, phone, email, contact, notes, logo_path, created_at
            FROM suppliers
            {where_sql}
            ORDER BY name COLLATE NOCASE ASC, created_at DESC
        """

        with self._connect() as con:
            rows = con.execute(sql, params).fetchall()

        return [
            Supplier(
                id=int(r["id"]),
                name=str(r["name"]),
                domain=str(r["domain"] or ""),
                phone=str(r["phone"] or ""),
                email=str(r["email"] or ""),
                contact=str(r["contact"] or ""),
                notes=str(r["notes"] or ""),
                logo_path=str(r["logo_path"] or ""),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def get_supplier(self, supplier_id: int) -> Supplier | None:
        with self._connect() as con:
            r = con.execute(
                """
                SELECT id, name, domain, phone, email, contact, notes, logo_path, created_at
                FROM suppliers
                WHERE id=?
                """,
                (int(supplier_id),),
            ).fetchone()
        if not r:
            return None
        return Supplier(
            id=int(r["id"]),
            name=str(r["name"]),
            domain=str(r["domain"] or ""),
            phone=str(r["phone"] or ""),
            email=str(r["email"] or ""),
            contact=str(r["contact"] or ""),
            notes=str(r["notes"] or ""),
            logo_path=str(r["logo_path"] or ""),
            created_at=str(r["created_at"]),
        )

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        domain: str = "",
        phone: str = "",
        email: str = "",
        contact: str = "",
        notes: str = "",
        logo_path: str = "",
    ) -> None:
        name = name.strip()
        if not name:
            raise ValueError("name is empty")

        domain = (domain or "").strip()
        self.upsert_domain_if_needed(domain)

        with self._connect() as con:
            con.execute(
                """
                UPDATE suppliers
                SET name=?, domain=?, phone=?, email=?, contact=?, notes=?, logo_path=?
                WHERE id=?
                """,
                (
                    name,
                    domain,
                    phone.strip(),
                    email.strip(),
                    contact.strip(),
                    notes.strip(),
                    (logo_path or "").strip(),
                    int(supplier_id),
                ),
            )
