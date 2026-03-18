# Python imports
import json
import sqlite3
from typing import Self

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError, CrossDep, Dep


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
    closed_at TEXT,
    close_reason TEXT
);

CREATE TABLE IF NOT EXISTS deps (
    from_id TEXT NOT NULL REFERENCES beans(id),
    to_id TEXT NOT NULL REFERENCES beans(id),
    dep_type TEXT NOT NULL DEFAULT 'blocks',
    PRIMARY KEY (from_id, to_id)
);

CREATE TABLE IF NOT EXISTS cross_deps (
    project TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL REFERENCES beans(id),
    dep_type TEXT NOT NULL DEFAULT 'blocks',
    PRIMARY KEY (project, from_id, to_id)
);

CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    bean_id TEXT NOT NULL,
    snapshot TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

DROP TRIGGER IF EXISTS journal_after_insert;
DROP TRIGGER IF EXISTS journal_after_update;
DROP TRIGGER IF EXISTS journal_after_delete;
DROP TRIGGER IF EXISTS journal_after_dep_insert;
DROP TRIGGER IF EXISTS journal_after_dep_delete;
"""

INSERT_JOURNAL = "INSERT INTO journal (action, bean_id, snapshot) VALUES (?, ?, ?)"


def journal_log(conn, action, bean_id, snapshot) -> None:
    conn.execute(INSERT_JOURNAL, (action, bean_id, snapshot))


UPDATABLE_FIELDS = {"title", "type", "status", "priority", "body", "parent_id", "assignee", "closed_at", "close_reason"}

BEAN_COLUMNS = (
    "id, title, type, status, priority, body, parent_id, assignee,"
    " created_by, ref_id, created_at, closed_at, close_reason"
)

INSERT_BEAN = f"INSERT INTO beans ({BEAN_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

UPDATE_BEAN_ALL = """UPDATE beans SET title=?, type=?, status=?, priority=?, body=?,
    parent_id=?, assignee=?, created_by=?, ref_id=?, created_at=?, closed_at=?, close_reason=?
    WHERE id=?"""


def bean_values(bean: Bean) -> tuple:
    return (
        bean.id, bean.title, bean.type, bean.status, bean.priority,
        bean.body, bean.parent_id, bean.assignee, bean.created_by,
        bean.ref_id, bean.created_at.isoformat(),
        bean.closed_at.isoformat() if bean.closed_at else None,
        bean.close_reason,
    )


def bean_snapshot(bean: Bean) -> str:
    return bean.model_dump_json()


class BeanStore:
    def __init__(self, conn):
        self.conn = conn

    def create(self, bean: Bean) -> Bean:
        with self.conn:
            self.conn.execute(INSERT_BEAN, bean_values(bean))
            journal_log(self.conn, "create", bean.id, bean_snapshot(bean))
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
            if cursor.rowcount:
                bean = self.get(bean_id)
                journal_log(self.conn, "update", bean.id, bean_snapshot(bean))
        return cursor.rowcount

    def delete(self, bean_id) -> int:
        select = self.conn.execute("SELECT * FROM beans WHERE id = ?", (bean_id,))
        match = select.fetchone()
        cols = columns(select) if match else None
        with self.conn:
            self.conn.execute("DELETE FROM deps WHERE from_id = ? OR to_id = ?", (bean_id, bean_id))
            cursor = self.conn.execute("DELETE FROM beans WHERE id = ?", (bean_id,))
            if cursor.rowcount and match:
                bean = Bean(**row(cols, match))
                journal_log(self.conn, "delete", bean.id, bean_snapshot(bean))
        return cursor.rowcount

    def list(self) -> list[Bean]:
        cursor = self.conn.execute("SELECT * FROM beans")
        return [Bean(**r) for r in rows(cursor)]

    def search(self, query) -> list[Bean]:
        pattern = f"%{query}%"
        cursor = self.conn.execute(
            "SELECT * FROM beans WHERE title LIKE ? OR body LIKE ?",
            (pattern, pattern),
        )
        return [Bean(**r) for r in rows(cursor)]

    def list_by_assignee(self, actor) -> list[Bean]:
        cursor = self.conn.execute("SELECT * FROM beans WHERE assignee = ?", (actor,))
        return [Bean(**r) for r in rows(cursor)]

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
                JOIN beans b ON d.from_id = b.id
                WHERE d.dep_type = 'blocks' AND b.status != 'closed'
            ),
            blocked_by_children(id) AS (
                SELECT b.parent_id
                FROM beans b
                WHERE b.parent_id IS NOT NULL AND b.status != 'closed'
            ),
            blocked_by_cross_deps(id) AS (
                SELECT cd.to_id
                FROM cross_deps cd
                WHERE cd.dep_type = 'blocks'
            )
            SELECT * FROM beans
            WHERE status != 'closed'
              AND id NOT IN (SELECT id FROM blocked_by_deps)
              AND id NOT IN (SELECT id FROM blocked_by_children)
              AND id NOT IN (SELECT id FROM blocked_by_cross_deps)
            ORDER BY priority
        """)
        return [Bean(**r) for r in rows(cursor)]


class DepStore:
    def __init__(self, conn):
        self.conn = conn

    def add(self, dep: Dep) -> Dep:
        with self.conn:
            self.conn.execute(
                "INSERT INTO deps (from_id, to_id, dep_type) VALUES (?, ?, ?)",
                (dep.from_id, dep.to_id, dep.dep_type),
            )
            journal_log(self.conn, "dep_add", dep.to_id, dep.model_dump_json())
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
            if cursor.rowcount:
                dep = Dep(from_id=from_id, to_id=to_id)
                journal_log(self.conn, "dep_remove", to_id, dep.model_dump_json())
        return cursor.rowcount


class CrossDepStore:
    def __init__(self, conn):
        self.conn = conn

    def add(self, dep: CrossDep) -> CrossDep:
        with self.conn:
            self.conn.execute(
                "INSERT INTO cross_deps (project, from_id, to_id, dep_type) VALUES (?, ?, ?, ?)",
                (dep.project, dep.from_id, dep.to_id, dep.dep_type),
            )
            journal_log(self.conn, "cross_dep_add", dep.to_id, dep.model_dump_json())
        return dep

    def list(self, to_id) -> list[CrossDep]:
        cursor = self.conn.execute(
            "SELECT project, from_id, to_id, dep_type FROM cross_deps WHERE to_id = ?",
            (to_id,),
        )
        return [CrossDep(**r) for r in rows(cursor)]

    def remove(self, project, from_id, to_id) -> int:
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM cross_deps WHERE project = ? AND from_id = ? AND to_id = ?",
                (project, from_id, to_id),
            )
            if cursor.rowcount:
                dep = CrossDep(project=project, from_id=from_id, to_id=to_id)
                journal_log(self.conn, "cross_dep_remove", to_id, dep.model_dump_json())
        return cursor.rowcount


class JournalStore:
    def __init__(self, conn):
        self.conn = conn

    def export(self):
        cursor = self.conn.execute("SELECT action, bean_id, snapshot, created_at FROM journal ORDER BY id")
        for action, bean_id, snapshot, created_at in cursor:
            entry = {
                "action": action,
                "bean_id": bean_id,
                "snapshot": json.loads(snapshot) if snapshot else None,
                "created_at": created_at,
            }
            yield json.dumps(entry)

    def replay(self, lines):
        with self.conn:
            for line in lines:
                entry = json.loads(line)
                action = entry["action"]
                snapshot = entry["snapshot"]
                bean_id = entry["bean_id"]

                if action == "create":
                    bean = Bean(**snapshot)
                    self.conn.execute(INSERT_BEAN, bean_values(bean))
                elif action == "update":
                    bean = Bean(**snapshot)
                    vals = bean_values(bean)
                    self.conn.execute(UPDATE_BEAN_ALL, (*vals[1:], vals[0]))
                elif action == "delete":
                    self.conn.execute("DELETE FROM beans WHERE id=?", (bean_id,))
                elif action == "dep_add":
                    self.conn.execute(
                        "INSERT INTO deps (from_id, to_id, dep_type) VALUES (?, ?, ?)",
                        (snapshot["from_id"], snapshot["to_id"], snapshot["dep_type"]),
                    )
                elif action == "dep_remove":
                    self.conn.execute(
                        "DELETE FROM deps WHERE from_id = ? AND to_id = ?",
                        (snapshot["from_id"], snapshot["to_id"]),
                    )
                elif action == "cross_dep_add":
                    self.conn.execute(
                        "INSERT INTO cross_deps (project, from_id, to_id, dep_type) VALUES (?, ?, ?, ?)",
                        (snapshot["project"], snapshot["from_id"], snapshot["to_id"], snapshot["dep_type"]),
                    )
                elif action == "cross_dep_remove":
                    self.conn.execute(
                        "DELETE FROM cross_deps WHERE project = ? AND from_id = ? AND to_id = ?",
                        (snapshot["project"], snapshot["from_id"], snapshot["to_id"]),
                    )


class Store:
    def __init__(self, conn: sqlite3.Connection, dry_run=False):
        self.conn = conn
        conn.executescript(SCHEMA)
        if dry_run:
            conn.autocommit = True
            conn.execute("BEGIN")
        self.bean = BeanStore(conn)
        self.dep = DepStore(conn)
        self.cross_dep = CrossDepStore(conn)
        self.journal = JournalStore(conn)
        self.dry_run = dry_run

    @classmethod
    def from_path(cls, db_path: str, dry_run=False) -> Self:
        return cls(sqlite3.connect(db_path), dry_run=dry_run)

    def close(self):
        if self.dry_run:
            self.conn.execute("ROLLBACK")
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
