# Python imports
import json
import sqlite3
from typing import Self

# Internal imports
from beans.models import Bean, BeanNotFoundError, Dep


def columns(cursor: sqlite3.Cursor) -> list[str]:
    return [desc[0] for desc in cursor.description]


def row(cols: list[str], values: tuple) -> dict:
    return dict(zip(cols, values))


def rows(cursor: sqlite3.Cursor):
    cols = columns(cursor)
    return (row(cols, values) for values in cursor.fetchall())


# Result mappers

def one_bean(cursor) -> Bean | None:
    match = cursor.fetchone()
    if match is None:
        return None
    return Bean(**row(columns(cursor), match))


def beans(cursor) -> list[Bean]:
    return [Bean(**r) for r in rows(cursor)]


def deps(cursor) -> list[Dep]:
    return [Dep(**r) for r in rows(cursor)]


# Query builders

UPDATABLE_FIELDS = {"title", "type", "status", "priority", "body", "parent_id", "assignee", "closed_at", "close_reason"}


def bean_values(bean: Bean) -> tuple:
    return (
        bean.id, bean.title, bean.type, bean.status, bean.priority,
        bean.body, bean.parent_id, bean.assignee, bean.created_by,
        bean.ref_id, bean.created_at.isoformat(),
        bean.closed_at.isoformat() if bean.closed_at else None,
        bean.close_reason,
    )


def insert_query(bean: Bean) -> tuple[str, tuple]:
    sql = (
        "INSERT INTO beans (id, title, type, status, priority, body, parent_id,"
        " assignee, created_by, ref_id, created_at, closed_at, close_reason)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    return sql, bean_values(bean)


def update_query(bean_id, **fields) -> tuple[str, list]:
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    sql = f"UPDATE beans SET {set_clause} WHERE id = ?"
    return sql, [*fields.values(), bean_id]


def update_all_query(bean: Bean) -> tuple[str, tuple]:
    sql = (
        "UPDATE beans SET title=?, type=?, status=?, priority=?, body=?,"
        " parent_id=?, assignee=?, created_by=?, ref_id=?, created_at=?, closed_at=?, close_reason=?"
        " WHERE id=?"
    )
    vals = bean_values(bean)
    return sql, (*vals[1:], vals[0])


def validate_fields(fields, updatable=UPDATABLE_FIELDS) -> None:
    if (invalid := fields.keys() - updatable):
        raise ValueError(f"Invalid fields: {invalid}")


def bean_snapshot(bean: Bean) -> str:
    return bean.model_dump_json()


# Schema and migrations

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


SCHEMA_VERSION = 2

MIGRATIONS = {
    2: "DROP TABLE IF EXISTS labels; DROP TABLE IF EXISTS cross_deps;",
}


def migrate(conn, migrations=MIGRATIONS, target=SCHEMA_VERSION) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version in range(current + 1, target + 1):
        if version in migrations:
            conn.executescript(migrations[version])
    conn.executescript(f"PRAGMA user_version = {target};")


# Sub-stores

class BeanStore:
    def __init__(self, conn):
        self.conn = conn

    def create(self, bean: Bean) -> Bean:
        sql, params = insert_query(bean)
        with self.conn:
            self.conn.execute(sql, params)
            journal_log(self.conn, "create", bean.id, bean_snapshot(bean))
        return bean

    def get(self, bean_id) -> Bean:
        cursor = self.conn.execute("SELECT * FROM beans WHERE id = ?", (bean_id,))
        bean = one_bean(cursor)
        if bean is None:
            raise BeanNotFoundError(bean_id)
        return bean

    def update(self, bean_id, **fields) -> int:
        if not fields:
            return 0
        validate_fields(fields)
        sql, params = update_query(bean_id, **fields)
        with self.conn:
            cursor = self.conn.execute(sql, params)
            if cursor.rowcount:
                bean = self.get(bean_id)
                journal_log(self.conn, "update", bean.id, bean_snapshot(bean))
        return cursor.rowcount

    def delete(self, bean_id) -> int:
        cursor = self.conn.execute("SELECT * FROM beans WHERE id = ?", (bean_id,))
        bean = one_bean(cursor)
        with self.conn:
            self.conn.execute("DELETE FROM deps WHERE from_id = ? OR to_id = ?", (bean_id, bean_id))
            cursor = self.conn.execute("DELETE FROM beans WHERE id = ?", (bean_id,))
            if cursor.rowcount and bean:
                journal_log(self.conn, "delete", bean.id, bean_snapshot(bean))
        return cursor.rowcount

    def list(self, types=None, statuses=None, parent_id=None) -> list[Bean]:
        sql = "SELECT * FROM beans"
        params = []
        clauses = []
        if types:
            placeholders = ",".join("?" for _ in types)
            clauses.append(f"type IN ({placeholders})")
            params.extend(types)
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            params.extend(statuses)
        if parent_id:
            clauses.append("parent_id = ?")
            params.append(parent_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        return beans(self.conn.execute(sql, params))

    def search(self, query) -> list[Bean]:
        pattern = f"%{query}%"
        return beans(self.conn.execute(
            "SELECT * FROM beans WHERE title LIKE ? OR body LIKE ?",
            (pattern, pattern),
        ))

    def list_by_assignee(self, actor) -> list[Bean]:
        return beans(self.conn.execute("SELECT * FROM beans WHERE assignee = ?", (actor,)))

    def stats(self) -> dict:
        result = {"by_status": {}, "by_type": {}, "by_assignee": {}}
        for label, col in [("by_status", "status"), ("by_type", "type")]:
            cursor = self.conn.execute(f"SELECT {col}, COUNT(*) FROM beans GROUP BY {col}")
            result[label] = dict(cursor.fetchall())
        cursor = self.conn.execute(
            "SELECT COALESCE(assignee, 'unassigned'), COUNT(*) FROM beans GROUP BY COALESCE(assignee, 'unassigned')"
        )
        result["by_assignee"] = dict(cursor.fetchall())
        return result

    def ready(self, assignee=None, unassigned=False, parent_id=None) -> list[Bean]:
        sql = """
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
            )
            SELECT * FROM beans
            WHERE status != 'closed'
              AND id NOT IN (SELECT id FROM blocked_by_deps)
              AND id NOT IN (SELECT id FROM blocked_by_children)
        """
        params: list = []
        if assignee is not None:
            sql += "  AND assignee = ?\n"
            params.append(assignee)
        elif unassigned:
            sql += "  AND assignee IS NULL\n"
        if parent_id:
            sql += "  AND parent_id = ?\n"
            params.append(parent_id)
        sql += "  ORDER BY priority"
        return beans(self.conn.execute(sql, params))


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
        return deps(self.conn.execute(
            "SELECT from_id, to_id, dep_type FROM deps WHERE from_id = ?",
            (from_id,),
        ))

    def list_all(self) -> list[Dep]:
        return deps(self.conn.execute("SELECT from_id, to_id, dep_type FROM deps"))

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
                    sql, params = insert_query(Bean(**snapshot))
                    self.conn.execute(sql, params)
                elif action == "update":
                    sql, params = update_all_query(Bean(**snapshot))
                    self.conn.execute(sql, params)
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


# Composite store

class Store:
    def __init__(self, conn: sqlite3.Connection, dry_run=False):
        self.conn = conn
        conn.executescript(SCHEMA)
        migrate(conn)
        if dry_run:
            conn.autocommit = True
            conn.execute("BEGIN")
        self.bean = BeanStore(conn)
        self.dep = DepStore(conn)
        self.journal = JournalStore(conn)
        self.dry_run = dry_run

    # Bean delegation
    def create(self, bean: Bean) -> Bean:
        return self.bean.create(bean)

    def get(self, bean_id) -> Bean:
        return self.bean.get(bean_id)

    def update(self, bean_id, **fields) -> int:
        return self.bean.update(bean_id, **fields)

    def delete(self, bean_id) -> int:
        return self.bean.delete(bean_id)

    def list(self, types=None, statuses=None, parent_id=None) -> list[Bean]:
        return self.bean.list(types=types, statuses=statuses, parent_id=parent_id)

    def list_by_assignee(self, actor) -> list[Bean]:
        return self.bean.list_by_assignee(actor)

    def ready(self, assignee=None, unassigned=False, parent_id=None) -> list[Bean]:
        return self.bean.ready(assignee=assignee, unassigned=unassigned, parent_id=parent_id)

    def search(self, query) -> list[Bean]:
        return self.bean.search(query)

    def stats(self) -> dict:
        return self.bean.stats()

    # Dep delegation
    def add_dep(self, dep: Dep) -> Dep:
        return self.dep.add(dep)

    def list_deps(self, from_id) -> list[Dep]:
        return self.dep.list(from_id)

    def list_all_deps(self) -> list[Dep]:
        return self.dep.list_all()

    def remove_dep(self, from_id, to_id) -> int:
        return self.dep.remove(from_id, to_id)

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
