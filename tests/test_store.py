# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError
from beans.store import BeanStore


@pytest.fixture()
def store():
    with BeanStore(sqlite3.connect(":memory:")) as s:
        yield s


class TestBeanStoreCreateAndList:
    """BeanStore can persist and retrieve beans."""

    def test_list_empty_store(self, store):
        assert store.list() == []

    def test_create_and_list_one_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.list() == [bean]

    def test_create_multiple_beans(self, store):
        b1 = store.create(Bean(title="First"))
        b2 = store.create(Bean(title="Second"))

        assert store.list() == [b1, b2]

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
        store.create(bean)

        result, *_ = store.list()
        assert result == bean
        

class TestBeanStoreGetBean:
    """BeanStore can retrieve a single bean by id."""

    def test_get_existing_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.get(bean.id) == bean

    def test_get_nonexistent_bean_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            store.get(BeanId("bean-00000000"))


class TestBeanStoreUpdateBean:
    """BeanStore can update bean fields."""

    def test_update_title(self, store):
        bean = Bean(title="Old title")
        store.create(bean)

        assert store.update(bean.id, title="New title") == 1
        assert store.get(bean.id).title == "New title"

    def test_update_status(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, status="in_progress") == 1
        assert store.get(bean.id).status == "in_progress"

    def test_update_priority(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, priority=0) == 1
        assert store.get(bean.id).priority == 0

    def test_update_multiple_fields(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, title="New title", status="closed") == 1
        result = store.get(bean.id)
        assert result.title == "New title"
        assert result.status == "closed"

    def test_update_empty_fields(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id) == 0

    def test_update_nonexistent_returns_zero(self, store):
        assert store.update(BeanId("bean-00000000"), title="Nope") == 0


class TestBeanStoreDeleteBean:
    """BeanStore can delete a bean."""

    def test_delete_removes_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.delete(bean.id) == 1
        with pytest.raises(BeanNotFoundError):
            store.get(bean.id)

    def test_delete_nonexistent_returns_zero(self, store):
        assert store.delete(BeanId("bean-00000000")) == 0


class TestBeanStoreReady:
    """BeanStore.ready() returns only unblocked beans."""

    def test_no_deps_all_ready(self, store):
        a = store.create(Bean(title="Task A"))
        b = store.create(Bean(title="Task B"))

        assert store.ready() == [a, b]

    def test_blocked_bean_excluded(self, store):
        a = store.create(Bean(title="Task A"))
        b = store.create(Bean(title="Task B"))
        store.add_dep(a.id, b.id)

        assert store.ready() == [a]

    def test_transitive_blocking_excluded(self, store):
        a = store.create(Bean(title="Task A"))
        b = store.create(Bean(title="Task B"))
        c = store.create(Bean(title="Task C"))
        store.add_dep(a.id, b.id)
        store.add_dep(b.id, c.id)

        assert store.ready() == [a]

    def test_closed_blocker_does_not_block(self, store):
        a = store.create(Bean(title="Task A", status="closed"))
        b = store.create(Bean(title="Task B"))
        store.add_dep(a.id, b.id)

        assert store.ready() == [a, b]

    def test_ready_empty_store(self, store):
        assert store.ready() == []

    def test_chain_one_closed_unblocks_next(self, store):
        a = store.create(Bean(title="Task A", status="closed"))
        b = store.create(Bean(title="Task B"))
        c = store.create(Bean(title="Task C"))
        store.add_dep(a.id, b.id)
        store.add_dep(b.id, c.id)

        assert store.ready() == [a, b]

    def test_parent_with_open_children_not_ready(self, store):
        parent = store.create(Bean(title="Parent"))
        store.create(Bean(title="Child", parent_id=parent.id))

        assert parent not in store.ready()

    def test_parent_with_all_closed_children_is_ready(self, store):
        parent = store.create(Bean(title="Parent"))
        store.create(Bean(title="Child", parent_id=parent.id, status="closed"))

        assert parent in store.ready()

    def test_parent_with_no_children_is_ready(self, store):
        parent = store.create(Bean(title="Parent"))

        assert parent in store.ready()


class TestBeanStoreValidation:
    """BeanStore validates inputs."""

    def test_update_invalid_field_rejected(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        with pytest.raises(ValueError, match="Invalid fields"):
            store.update(bean.id, bogus="nope")

    def test_invalid_bean_id_rejected(self, store):
        with pytest.raises(ValueError, match="Invalid bean id"):
            BeanId("not-a-bean-id")
