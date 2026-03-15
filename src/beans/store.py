# Python imports
import json
import sqlite3
from datetime import datetime, timezone

# Internal imports
from beans.models import Bean

SCHEMA = """
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
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    def create_bean(self, bean: Bean) -> Bean:
        self.conn.execute(
            """INSERT INTO beans (id, title, type, status, priority, body, labels, parent_id, assignee, created_by, ref_id, created_at)
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
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        beans = []
        for row in rows:
            data = dict(zip(columns, row))
            data["labels"] = json.loads(data["labels"])
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            beans.append(Bean(**data))
        return beans
