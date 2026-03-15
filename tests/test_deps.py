# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean, Dep
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


@pytest.fixture()
def two_beans(store):
    a = store.bean.create(Bean(title="Task A"))
    b = store.bean.create(Bean(title="Task B"))
    return a, b


class TestDepStoreAdd:
    """DepStore can store dependency edges between beans."""

    def test_add_and_list(self, store, two_beans):
        a, b = two_beans
        store.dep.add(a.id, b.id)

        assert store.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id)]

    def test_add_returns_dep(self, store, two_beans):
        a, b = two_beans
        dep = store.dep.add(a.id, b.id)

        assert dep == Dep(from_id=a.id, to_id=b.id)

    def test_add_default_type_is_blocks(self, store, two_beans):
        a, b = two_beans
        dep = store.dep.add(a.id, b.id)

        assert dep.dep_type == "blocks"

    def test_add_custom_type(self, store, two_beans):
        a, b = two_beans
        store.dep.add(a.id, b.id, dep_type="relates")

        assert store.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id, dep_type="relates")]

    def test_list_empty(self, store, two_beans):
        a, _ = two_beans
        assert store.dep.list(a.id) == []

    def test_add_multiple(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))

        store.dep.add(a.id, b.id)
        store.dep.add(a.id, c.id)

        assert set(store.dep.list(a.id)) == {
            Dep(from_id=a.id, to_id=b.id),
            Dep(from_id=a.id, to_id=c.id),
        }

    def test_list_only_returns_from_bean(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))

        store.dep.add(a.id, b.id)
        store.dep.add(c.id, b.id)

        assert store.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id)]


class TestDepStoreRemove:
    """DepStore can remove dependency edges."""

    def test_remove(self, store, two_beans):
        a, b = two_beans
        store.dep.add(a.id, b.id)

        assert store.dep.remove(a.id, b.id) == 1
        assert store.dep.list(a.id) == []

    def test_remove_nonexistent(self, store, two_beans):
        a, b = two_beans
        assert store.dep.remove(a.id, b.id) == 0
