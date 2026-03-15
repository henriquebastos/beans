# Python imports
import sqlite3
from typing import Self

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError, Dep


def columns(cursor: sqlite3.Cursor) -> list[str]:
    return [desc[0] for desc in cursor.description]


def row(cols: list[str], values: tuple) -> dict:
    return dict(zip(cols, values))


def rows(cursor: sqlite3.Cursor):
    cols = columns(cursor)
    return (row(cols, values) for values in cursor.fetchall())


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS beans (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'task',
    status TEXT NOT NULL DEFAULT 'open',
    priority INTEGER NOT NULL DEFAULT 2,
    body TEXT NOT NULL DEFAULT '',
    parent_id TEXT,
    assignee TEXT,
    created_by TEXT,
    ref_id TEXT,
    created_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS deps (
    from_id TEXT NOT NULL REFERENCES beans(id),
    to_id TEXT NOT NULL REFERENCES beans(id),
    dep_type TEXT NOT NULL DEFAULT 'blocks',
    PRIMARY KEY (from_id, to_id)
);
"""


UPDATABLE_FIELDS = {"title", "type", "status", "priority", "body", "parent_id", "assignee", "closed_at"}


class BaseStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def init_db(conn: sqlite3.Connection, schema: str = SCHEMA):
        conn.executescript(schema)

    @classmethod
    def from_path(cls, db_path: str) -> Self:
        return cls(sqlite3.connect(db_path))

class BeanStore(BaseStore):
    def create(self, bean: Bean) -> Bean:
        with self.conn:
            self.conn.execute(
                """INSERT INTO beans
                (id, title, type, status, priority, body,
                parent_id, assignee, created_by, ref_id, created_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bean.id,
                    bean.title,
                    bean.type,
                    bean.status,
                    bean.priority,
                    bean.body,
                    bean.parent_id,
                    bean.assignee,
                    bean.created_by,
                    bean.ref_id,
                    bean.created_at.isoformat(),
                    bean.closed_at.isoformat() if bean.closed_at else None,
                ),
            )
        return bean

    def get(self, bean_id: BeanId) -> Bean:
        cursor = self.conn.execute("SELECT * FROM beans WHERE id = ?", (bean_id,))

        match = cursor.fetchone()
        if match is None:
            raise BeanNotFoundError(bean_id)

        return Bean(**row(columns(cursor), match))

    def update(self, bean_id, **fields) -> int:
        if not fields:
            return 0

        if (invalid := fields.keys() - UPDATABLE_FIELDS):
            raise ValueError(f"Invalid fields: {invalid}")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = [*fields.values(), bean_id]

        with self.conn:
            cursor = self.conn.execute(f"UPDATE beans SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount

    def delete(self, bean_id) -> int:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM beans WHERE id = ?", (bean_id,))
        return cursor.rowcount

    def list(self) -> list[Bean]:
        cursor = self.conn.execute("SELECT * FROM beans")
        return [Bean(**r) for r in rows(cursor)]

    def claim(self, bean_id, actor) -> Bean:
        bean = self.get(bean_id)
        if bean.assignee == actor:
            return bean
        if bean.assignee:
            raise ValueError(f"Bean {bean_id} already claimed by {bean.assignee}")
        self.update(bean_id, assignee=actor, status="in_progress")
        return self.get(bean_id)

    def release(self, bean_id, actor) -> Bean:
        bean = self.get(bean_id)
        if not bean.assignee:
            return bean
        if bean.assignee != actor:
            raise ValueError(f"Bean {bean_id} claimed by {bean.assignee}")
        self.update(bean_id, assignee=None, status="open")
        return self.get(bean_id)

    def release_mine(self, actor) -> list[Bean]:
        cursor = self.conn.execute("SELECT id FROM beans WHERE assignee = ?", (actor,))
        ids = [r[0] for r in cursor.fetchall()]
        return [self.release(bean_id, actor) for bean_id in ids]

    def ready(self) -> list[Bean]:
        cursor = self.conn.execute("""
            WITH RECURSIVE
            blocked_by_deps(id) AS (
                SELECT d.to_id
                FROM deps d
                JOIN beans b ON d.from_id = b.id
                WHERE d.dep_type = 'blocks' AND b.status != 'closed'
                UNION
                SELECT d.to_id
                FROM deps d
                JOIN blocked_by_deps bl ON d.from_id = bl.id
                WHERE d.dep_type = 'blocks'
            ),
            blocked_by_children(id) AS (
                SELECT b.parent_id
                FROM beans b
                WHERE b.parent_id IS NOT NULL AND b.status != 'closed'
            )
            SELECT * FROM beans
            WHERE id NOT IN (SELECT id FROM blocked_by_deps)
              AND id NOT IN (SELECT id FROM blocked_by_children)
        """)
        return [Bean(**r) for r in rows(cursor)]


class DepStore(BaseStore):
    def add(self, dep: Dep) -> Dep:
        with self.conn:
            self.conn.execute(
                "INSERT INTO deps (from_id, to_id, dep_type) VALUES (?, ?, ?)",
                (dep.from_id, dep.to_id, dep.dep_type),
            )
        return dep

    def list(self, from_id) -> list[Dep]:
        cursor = self.conn.execute(
            "SELECT from_id, to_id, dep_type FROM deps WHERE from_id = ?",
            (from_id,),
        )
        return [Dep(**r) for r in rows(cursor)]

    def remove(self, from_id, to_id) -> int:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM deps WHERE from_id = ? AND to_id = ?",
                (from_id, to_id),
            )
        return cursor.rowcount


class DryRunConnection:
    """Wraps a sqlite3.Connection to prevent commits for dry-run mode."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        conn.isolation_level = None
        conn.execute("BEGIN")

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def rollback(self):
        self.conn.rollback()


class Store(BaseStore):
    def __init__(self, conn: sqlite3.Connection, dry_run=False):
        super().__init__(conn)
        self.init_db(conn)
        wrapped = DryRunConnection(conn) if dry_run else conn
        self.bean = BeanStore(wrapped)
        self.dep = DepStore(wrapped)
        self.dry_run = dry_run

    @classmethod
    def from_path(cls, db_path: str, dry_run=False) -> Self:
        return cls(sqlite3.connect(db_path), dry_run=dry_run)

    def close(self):
        if self.dry_run:
            self.conn.rollback()
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
