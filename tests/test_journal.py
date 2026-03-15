# Python imports
import json
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


def journal_entries(store) -> list[dict]:
    cursor = store.conn.execute("SELECT action, bean_id, snapshot, created_at FROM journal ORDER BY id")
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


class TestJournalCreate:
    """Creating a bean also creates a journal entry via trigger."""

    def test_create_bean_creates_journal_entry(self, store):
        store.bean.create(Bean(title="Fix auth"))

        cursor = store.conn.execute("SELECT * FROM journal")
        entries = cursor.fetchall()
        assert len(entries) == 1

    def test_journal_entry_has_correct_action(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))

        cursor = store.conn.execute("SELECT action, bean_id FROM journal")
        action, bean_id = cursor.fetchone()
        assert action == "create"
        assert bean_id == bean.id

    def test_journal_entry_stores_snapshot(self, store):
        store.bean.create(Bean(title="Fix auth"))

        cursor = store.conn.execute("SELECT snapshot FROM journal")
        snapshot = cursor.fetchone()[0]
        assert snapshot is not None
        assert "Fix auth" in snapshot

    def test_journal_entry_has_timestamp(self, store):
        store.bean.create(Bean(title="Fix auth"))

        cursor = store.conn.execute("SELECT created_at FROM journal")
        created_at = cursor.fetchone()[0]
        assert created_at is not None


class TestJournalUpdate:
    """Updating a bean creates a journal entry with action='update'."""

    def test_update_creates_journal_entry(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.update(bean.id, title="New title")

        entries = journal_entries(store)
        assert len(entries) == 2
        assert entries[1]["action"] == "update"
        assert entries[1]["bean_id"] == bean.id

    def test_update_snapshot_reflects_new_values(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.update(bean.id, title="New title")

        entries = journal_entries(store)
        assert "New title" in entries[1]["snapshot"]

    def test_multiple_updates_create_multiple_entries(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.update(bean.id, title="First")
        store.bean.update(bean.id, title="Second")

        entries = journal_entries(store)
        assert len(entries) == 3
        assert all(e["action"] == "update" for e in entries[1:])


class TestJournalDelete:
    """Deleting a bean creates a journal entry with action='delete'."""

    def test_delete_creates_journal_entry(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.delete(bean.id)

        entries = journal_entries(store)
        assert len(entries) == 2
        assert entries[1]["action"] == "delete"
        assert entries[1]["bean_id"] == bean.id

    def test_delete_snapshot_has_final_state(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.delete(bean.id)

        entries = journal_entries(store)
        assert "Fix auth" in entries[1]["snapshot"]


class TestJournalExport:
    """store.journal.export() produces JSONL lines."""

    def test_export_empty(self, store):
        lines = list(store.journal.export())
        assert lines == []

    def test_export_after_create(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))

        lines = list(store.journal.export())
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["action"] == "create"
        assert entry["bean_id"] == bean.id
        assert "snapshot" in entry
        assert "created_at" in entry

    def test_export_produces_valid_jsonl(self, store):
        store.bean.create(Bean(title="First"))
        store.bean.create(Bean(title="Second"))

        lines = list(store.journal.export())
        assert len(lines) == 2
        for line in lines:
            parsed = json.loads(line)
            assert "action" in parsed

    def test_export_after_crud_cycle(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.update(bean.id, title="Updated")
        store.bean.delete(bean.id)

        lines = list(store.journal.export())
        assert len(lines) == 3
        actions = [json.loads(line)["action"] for line in lines]
        assert actions == ["create", "update", "delete"]
