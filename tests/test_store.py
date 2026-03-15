# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError, Dep
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


class TestBeanStoreCreateAndList:
    """BeanStore can persist and retrieve beans."""

    def test_list_empty_store(self, store):
        assert store.bean.list() == []

    def test_create_and_list_one_bean(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.list() == [bean]

    def test_create_multiple_beans(self, store):
        b1 = store.bean.create(Bean(title="First"))
        b2 = store.bean.create(Bean(title="Second"))

        assert store.bean.list() == [b1, b2]

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
        store.bean.create(bean)

        result, *_ = store.bean.list()
        assert result == bean


class TestBeanStoreGetBean:
    """BeanStore can retrieve a single bean by id."""

    def test_get_existing_bean(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.get(bean.id) == bean

    def test_get_nonexistent_bean_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            store.bean.get(BeanId("bean-00000000"))


class TestBeanStoreUpdateBean:
    """BeanStore can update bean fields."""

    def test_update_title(self, store):
        bean = Bean(title="Old title")
        store.bean.create(bean)

        assert store.bean.update(bean.id, title="New title") == 1
        assert store.bean.get(bean.id).title == "New title"

    def test_update_status(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.update(bean.id, status="in_progress") == 1
        assert store.bean.get(bean.id).status == "in_progress"

    def test_update_priority(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.update(bean.id, priority=0) == 1
        assert store.bean.get(bean.id).priority == 0

    def test_update_multiple_fields(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.update(bean.id, title="New title", status="closed") == 1
        result = store.bean.get(bean.id)
        assert result.title == "New title"
        assert result.status == "closed"

    def test_update_empty_fields(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.update(bean.id) == 0

    def test_update_nonexistent_returns_zero(self, store):
        assert store.bean.update(BeanId("bean-00000000"), title="Nope") == 0


class TestBeanStoreDeleteBean:
    """BeanStore can delete a bean."""

    def test_delete_removes_bean(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        assert store.bean.delete(bean.id) == 1
        with pytest.raises(BeanNotFoundError):
            store.bean.get(bean.id)

    def test_delete_nonexistent_returns_zero(self, store):
        assert store.bean.delete(BeanId("bean-00000000")) == 0


class TestBeanStoreReady:
    """BeanStore.ready() returns only unblocked beans."""

    def test_no_deps_all_ready(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))

        assert store.bean.ready() == [a, b]

    def test_blocked_bean_excluded(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))

        assert store.bean.ready() == [a]

    def test_transitive_blocking_excluded(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))
        store.dep.add(Dep(from_id=b.id, to_id=c.id))

        assert store.bean.ready() == [a]

    def test_closed_blocker_does_not_block(self, store):
        a = store.bean.create(Bean(title="Task A", status="closed"))
        b = store.bean.create(Bean(title="Task B"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))

        assert store.bean.ready() == [a, b]

    def test_ready_empty_store(self, store):
        assert store.bean.ready() == []

    def test_chain_one_closed_unblocks_next(self, store):
        a = store.bean.create(Bean(title="Task A", status="closed"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))
        store.dep.add(Dep(from_id=b.id, to_id=c.id))

        assert store.bean.ready() == [a, b]

    def test_parent_with_open_children_not_ready(self, store):
        parent = store.bean.create(Bean(title="Parent"))
        store.bean.create(Bean(title="Child", parent_id=parent.id))

        assert parent not in store.bean.ready()

    def test_parent_with_all_closed_children_is_ready(self, store):
        parent = store.bean.create(Bean(title="Parent"))
        store.bean.create(Bean(title="Child", parent_id=parent.id, status="closed"))

        assert parent in store.bean.ready()

    def test_parent_with_no_children_is_ready(self, store):
        parent = store.bean.create(Bean(title="Parent"))

        assert parent in store.bean.ready()


class TestBeanStoreValidation:
    """BeanStore validates inputs."""

    def test_update_invalid_field_rejected(self, store):
        bean = Bean(title="Fix auth")
        store.bean.create(bean)

        with pytest.raises(ValueError, match="Invalid fields"):
            store.bean.update(bean.id, bogus="nope")

    def test_invalid_bean_id_rejected(self, store):
        with pytest.raises(ValueError, match="Invalid bean id"):
            BeanId("not-a-bean-id")
