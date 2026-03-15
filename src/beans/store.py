# Python imports
import sqlite3

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError


def columns(cursor: sqlite3.Cursor) -> list[str]:
    return [desc[0] for desc in cursor.description]


def row(cols: list[str], values: tuple) -> dict:
    return dict(zip(cols, values))


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
"""


UPDATABLE_FIELDS = {"title", "type", "status", "priority", "body", "parent_id", "assignee", "closed_at"}


class BeanStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.init_db(conn)

    @staticmethod
    def init_db(conn: sqlite3.Connection, schema: str = SCHEMA):
        conn.executescript(schema)

    @classmethod
    def from_path(cls, db_path: str) -> BeanStore:
        return cls(sqlite3.connect(db_path))

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

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

        cols = columns(cursor)
        return Bean(**row(cols, match))

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
        cols = columns(cursor)
        return [Bean(**row(cols, values)) for values in cursor.fetchall()]
