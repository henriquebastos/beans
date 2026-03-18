# Python imports
import json
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean, CrossDep, Dep
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


class TestJournalReplay:
    """store.journal.replay() rebuilds database state from JSONL lines."""

    def test_replay_create(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            assert target.bean.list() == [bean]

    def test_replay_create_and_update(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.update(bean.id, title="Updated")
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            result = target.bean.get(bean.id)
            assert result.title == "Updated"

    def test_replay_create_and_delete(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.bean.delete(bean.id)
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            assert target.bean.list() == []

    def test_replay_full_cycle(self, store):
        b1 = store.bean.create(Bean(title="First"))
        b2 = store.bean.create(Bean(title="Second"))
        store.bean.update(b1.id, title="First Updated")
        store.bean.delete(b2.id)
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            beans = target.bean.list()
            assert len(beans) == 1
            assert beans[0].title == "First Updated"

    def test_replay_empty(self, store):
        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay([])
            assert target.bean.list() == []

    def test_replay_restores_deps(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        dep = Dep(from_id=a.id, to_id=b.id)
        store.dep.add(dep)
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            assert target.dep.list(a.id) == [dep]


class TestJournalDepTriggers:
    """Journal captures dep changes via triggers."""

    def test_dep_add_creates_journal_entry(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))

        entries = journal_entries(store)
        dep_entries = [e for e in entries if e["action"] == "dep_add"]
        assert len(dep_entries) == 1

    def test_dep_remove_creates_journal_entry(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))
        store.dep.remove(a.id, b.id)

        entries = journal_entries(store)
        dep_entries = [e for e in entries if e["action"] == "dep_remove"]
        assert len(dep_entries) == 1

    def test_cross_dep_add_creates_journal_entry(self, store):
        bean = store.bean.create(Bean(title="Task"))
        store.cross_dep.add(CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id))

        entries = journal_entries(store)
        cross_entries = [e for e in entries if e["action"] == "cross_dep_add"]
        assert len(cross_entries) == 1

    def test_cross_dep_remove_creates_journal_entry(self, store):
        bean = store.bean.create(Bean(title="Task"))
        store.cross_dep.add(CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id))
        store.cross_dep.remove("remote", "bean-aabbccdd", bean.id)

        entries = journal_entries(store)
        cross_entries = [e for e in entries if e["action"] == "cross_dep_remove"]
        assert len(cross_entries) == 1


class TestJournalCrossDepReplay:
    """Journal replay restores cross-project dependencies."""

    def test_replay_restores_cross_deps(self, store):
        bean = store.bean.create(Bean(title="Task"))
        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)
        store.cross_dep.add(dep)
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            assert target.cross_dep.list(bean.id) == [dep]

    def test_replay_cross_dep_add_and_remove(self, store):
        bean = store.bean.create(Bean(title="Task"))
        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)
        store.cross_dep.add(dep)
        store.cross_dep.remove("remote", "bean-aabbccdd", bean.id)
        lines = list(store.journal.export())

        with Store(sqlite3.connect(":memory:")) as target:
            target.journal.replay(lines)
            assert target.cross_dep.list(bean.id) == []
