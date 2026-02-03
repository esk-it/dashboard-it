import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Task:
    id: int
    title: str
    category: str
    priority: int          # 1 (low) → 3 (high)
    due_date: Optional[str]  # "YYYY-MM-DD" or None
    done: bool
    created_at: str        # ISO string


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
        # status: "all" | "open" | "done"
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
        """Retourne (open_count, done_count)."""
        with self._connect() as con:
            open_count = con.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0]
            done_count = con.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        return int(open_count), int(done_count)

    def top_open_tasks(self, limit: int = 5) -> list[Task]:
        """Top tâches ouvertes (triées par due_date puis création)."""
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
                (int(limit),)
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

def count_tasks(self) -> tuple[int, int]:
    """Retourne (open_count, done_count)."""
    with self._connect() as con:
        open_count = con.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0]
        done_count = con.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    return int(open_count), int(done_count)

def top_open_tasks(self, limit: int = 5) -> list[Task]:
    """Top tâches ouvertes (triées par due_date puis création)."""
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
            (int(limit),)
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
@dataclass(frozen=True)
class Supplier:
    id: int
    name: str
    domain: str
    phone: str
    email: str
    contact: str
    notes: str
    created_at: str


class SupplierRepository:
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

    def add_supplier(
        self,
        name: str,
        domain: str = "",
        phone: str = "",
        email: str = "",
        contact: str = "",
        notes: str = "",
    ) -> int:
        name = name.strip()
        if not name:
            raise ValueError("name is empty")

        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as con:
            cur = con.execute(
                """
                INSERT INTO suppliers(name, domain, phone, email, contact, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, domain.strip(), phone.strip(), email.strip(), contact.strip(), notes.strip(), created_at),
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

        d = domain.strip()
        if d and d != "Tous":
            where.append("domain = ?")
            params.append(d)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
            SELECT id, name, domain, phone, email, contact, notes, created_at
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
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def list_domains(self) -> list[str]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT DISTINCT domain FROM suppliers WHERE domain IS NOT NULL AND domain != '' ORDER BY domain COLLATE NOCASE"
            ).fetchall()
        return [str(r["domain"]) for r in rows]
