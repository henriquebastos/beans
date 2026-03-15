# Python imports
import datetime
import json
import sqlite3

# Internal imports
from beans.models import Bean

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
    labels TEXT NOT NULL DEFAULT '[]',
    parent_id TEXT,
    assignee TEXT,
    created_by TEXT,
    ref_id TEXT,
    created_at TEXT NOT NULL
);
"""


class BeanStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._init_db()

    def _init_db(self):
        self.conn.executescript(SCHEMA)

    @classmethod
    def from_path(cls, db_path: str) -> BeanStore:
        return cls(sqlite3.connect(db_path))

    def close(self):
        self.conn.close()

    def create_bean(self, bean: Bean) -> Bean:
        self.conn.execute(
            """INSERT INTO beans
            (id, title, type, status, priority, body, labels, parent_id, assignee, created_by, ref_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bean.id,
                bean.title,
                bean.type,
                bean.status,
                bean.priority,
                bean.body,
                json.dumps(bean.labels),
                bean.parent_id,
                bean.assignee,
                bean.created_by,
                bean.ref_id,
                bean.created_at.isoformat(),
            ),
        )
        self.conn.commit()
        return bean

    def list_beans(self) -> list[Bean]:
        cursor = self.conn.execute("SELECT * FROM beans")
        columns = [desc[0] for desc in cursor.description]
        return [self._row_to_bean(columns, row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_bean(columns: list[str], row: tuple) -> Bean:
        data = dict(zip(columns, row))
        data["labels"] = json.loads(data["labels"])
        data["created_at"] = datetime.datetime.fromisoformat(data["created_at"])
        return Bean(**data)
