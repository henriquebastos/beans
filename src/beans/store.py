# Python imports
from datetime import UTC, datetime
import sqlite3

# Internal imports
from beans.models import Bean, BeanId


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

    def create_bean(self, bean: Bean) -> Bean:
        self.conn.execute(
            """INSERT INTO beans
            (id, title, type, status, priority, body, parent_id, assignee, created_by, ref_id, created_at, closed_at)
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
        self.conn.commit()
        return bean

    def get_bean(self, bean_id) -> Bean:
        bean_id = BeanId(bean_id)
        cursor = self.conn.execute("SELECT * FROM beans WHERE id LIKE ?", (bean_id + "%",))
        cols = columns(cursor)
        matches = cursor.fetchall()
        if len(matches) == 0:
            raise KeyError(f"Bean not found: {bean_id}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous prefix: {bean_id}")
        return Bean(**row(cols, matches[0]))

    def close_bean(self, bean_id) -> Bean:
        return self.update_bean(bean_id, {"status": "closed", "closed_at": datetime.now(UTC).isoformat()})

    def update_bean(self, bean_id, fields: dict) -> Bean:
        bean = self.get_bean(bean_id)
        if not fields:
            return bean
        for key in fields:
            if key not in UPDATABLE_FIELDS:
                raise ValueError(f"Invalid field: {key}")
        Bean.model_validate({"id": bean.id, "title": "validate", **fields})
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = [*fields.values(), bean.id]
        self.conn.execute(f"UPDATE beans SET {set_clause} WHERE id = ?", values)
        self.conn.commit()
        return self.get_bean(bean.id)

    def delete_bean(self, bean_id):
        bean = self.get_bean(bean_id)
        self.conn.execute("DELETE FROM beans WHERE id = ?", (bean.id,))
        self.conn.commit()

    def list_beans(self) -> list[Bean]:
        cursor = self.conn.execute("SELECT * FROM beans")
        cols = columns(cursor)
        return [Bean(**row(cols, values)) for values in cursor.fetchall()]
