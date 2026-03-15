# Python imports
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
