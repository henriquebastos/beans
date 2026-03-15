# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean
from beans.store import BeanStore


@pytest.fixture()
def store():
    with BeanStore(sqlite3.connect(":memory:")) as s:
        yield s


@pytest.fixture()
def two_beans(store):
    a = store.create(Bean(title="Task A"))
    b = store.create(Bean(title="Task B"))
    return a, b


class TestBeanStoreAddDep:
    """BeanStore can store dependency edges between beans."""

    def test_add_dep_and_list_deps(self, store, two_beans):
        a, b = two_beans
        store.add_dep(a.id, b.id)

        assert store.list_deps(a.id) == [(a.id, b.id, "blocks")]

    def test_add_dep_default_type_is_blocks(self, store, two_beans):
        a, b = two_beans
        store.add_dep(a.id, b.id)

        deps = store.list_deps(a.id)
        assert deps[0][2] == "blocks"

    def test_add_dep_custom_type(self, store, two_beans):
        a, b = two_beans
        store.add_dep(a.id, b.id, dep_type="relates")

        assert store.list_deps(a.id) == [(a.id, b.id, "relates")]

    def test_list_deps_empty(self, store, two_beans):
        a, _ = two_beans
        assert store.list_deps(a.id) == []

    def test_add_multiple_deps(self, store):
        a = store.create(Bean(title="Task A"))
        b = store.create(Bean(title="Task B"))
        c = store.create(Bean(title="Task C"))

        store.add_dep(a.id, b.id)
        store.add_dep(a.id, c.id)

        assert set(store.list_deps(a.id)) == {
            (a.id, b.id, "blocks"),
            (a.id, c.id, "blocks"),
        }

    def test_list_deps_only_returns_from_bean(self, store):
        a = store.create(Bean(title="Task A"))
        b = store.create(Bean(title="Task B"))
        c = store.create(Bean(title="Task C"))

        store.add_dep(a.id, b.id)
        store.add_dep(c.id, b.id)

        assert store.list_deps(a.id) == [(a.id, b.id, "blocks")]


class TestBeanStoreRemoveDep:
    """BeanStore can remove dependency edges."""

    def test_remove_dep(self, store, two_beans):
        a, b = two_beans
        store.add_dep(a.id, b.id)

        assert store.remove_dep(a.id, b.id) == 1
        assert store.list_deps(a.id) == []

    def test_remove_nonexistent_dep(self, store, two_beans):
        a, b = two_beans
        assert store.remove_dep(a.id, b.id) == 0
