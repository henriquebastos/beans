# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean
from beans.store import BeanStore


class TestBeanStoreCreateAndList:
    """BeanStore can persist and retrieve beans."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_list_empty_store(self, store):
        assert store.list_beans() == []

    def test_create_and_list_one_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create_bean(bean)

        beans = store.list_beans()
        assert len(beans) == 1
        assert beans[0].title == "Fix auth"
        assert beans[0].id == bean.id

    def test_create_multiple_beans(self, store):
        store.create_bean(Bean(title="First"))
        store.create_bean(Bean(title="Second"))

        beans = store.list_beans()
        assert len(beans) == 2
        titles = {b.title for b in beans}
        assert titles == {"First", "Second"}

    def test_roundtrip_preserves_all_fields(self, store):
        bean = Bean(
            title="Full bean",
            type="epic",
            status="in_progress",
            priority=0,
            body="Some details",
            parent_id="bean-00000000",
            assignee="alice",
            created_by="bob",
            ref_id="GH-42",
        )
        store.create_bean(bean)

        result = store.list_beans()[0]
        assert result.id == bean.id
        assert result.title == bean.title
        assert result.type == bean.type
        assert result.status == bean.status
        assert result.priority == bean.priority
        assert result.body == bean.body
        assert result.parent_id == bean.parent_id
        assert result.assignee == bean.assignee
        assert result.created_by == bean.created_by
        assert result.ref_id == bean.ref_id
        assert result.created_at == bean.created_at


class TestBeanStoreGetBean:
    """BeanStore can retrieve a single bean by id."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_get_existing_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create_bean(bean)

        result = store.get_bean(bean.id)
        assert result.id == bean.id
        assert result.title == "Fix auth"

    def test_get_nonexistent_bean_returns_none(self, store):
        result = store.get_bean("bean-00000000")
        assert result is None


class TestBeanStoreUpdateBean:
    """BeanStore can update bean fields."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_update_title(self, store):
        bean = Bean(title="Old title")
        store.create_bean(bean)

        result = store.update_bean(bean.id, {"title": "New title"})
        assert result.title == "New title"

    def test_update_status(self, store):
        bean = Bean(title="Fix auth")
        store.create_bean(bean)

        result = store.update_bean(bean.id, {"status": "in_progress"})
        assert result.status == "in_progress"

    def test_update_priority(self, store):
        bean = Bean(title="Fix auth")
        store.create_bean(bean)

        result = store.update_bean(bean.id, {"priority": 0})
        assert result.priority == 0

    def test_update_multiple_fields(self, store):
        bean = Bean(title="Fix auth")
        store.create_bean(bean)

        result = store.update_bean(bean.id, {"title": "New title", "status": "closed"})
        assert result.title == "New title"
        assert result.status == "closed"

    def test_update_persists(self, store):
        bean = Bean(title="Fix auth")
        store.create_bean(bean)

        store.update_bean(bean.id, {"title": "Updated"})
        result = store.get_bean(bean.id)
        assert result.title == "Updated"

    def test_update_nonexistent_bean_returns_none(self, store):
        result = store.update_bean("bean-00000000", {"title": "Nope"})
        assert result is None
