# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import Bean, Dep
from beans.store import MainStore


@pytest.fixture()
def main():
    with MainStore(sqlite3.connect(":memory:")) as s:
        yield s


@pytest.fixture()
def two_beans(main):
    a = main.bean.create(Bean(title="Task A"))
    b = main.bean.create(Bean(title="Task B"))
    return a, b


class TestDepStoreAdd:
    """DepStore can store dependency edges between beans."""

    def test_add_and_list(self, main, two_beans):
        a, b = two_beans
        main.dep.add(a.id, b.id)

        assert main.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id)]

    def test_add_returns_dep(self, main, two_beans):
        a, b = two_beans
        dep = main.dep.add(a.id, b.id)

        assert dep == Dep(from_id=a.id, to_id=b.id)

    def test_add_default_type_is_blocks(self, main, two_beans):
        a, b = two_beans
        dep = main.dep.add(a.id, b.id)

        assert dep.dep_type == "blocks"

    def test_add_custom_type(self, main, two_beans):
        a, b = two_beans
        main.dep.add(a.id, b.id, dep_type="relates")

        assert main.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id, dep_type="relates")]

    def test_list_empty(self, main, two_beans):
        a, _ = two_beans
        assert main.dep.list(a.id) == []

    def test_add_multiple(self, main):
        a = main.bean.create(Bean(title="Task A"))
        b = main.bean.create(Bean(title="Task B"))
        c = main.bean.create(Bean(title="Task C"))

        main.dep.add(a.id, b.id)
        main.dep.add(a.id, c.id)

        assert set(main.dep.list(a.id)) == {
            Dep(from_id=a.id, to_id=b.id),
            Dep(from_id=a.id, to_id=c.id),
        }

    def test_list_only_returns_from_bean(self, main):
        a = main.bean.create(Bean(title="Task A"))
        b = main.bean.create(Bean(title="Task B"))
        c = main.bean.create(Bean(title="Task C"))

        main.dep.add(a.id, b.id)
        main.dep.add(c.id, b.id)

        assert main.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id)]


class TestDepStoreRemove:
    """DepStore can remove dependency edges."""

    def test_remove(self, main, two_beans):
        a, b = two_beans
        main.dep.add(a.id, b.id)

        assert main.dep.remove(a.id, b.id) == 1
        assert main.dep.list(a.id) == []

    def test_remove_nonexistent(self, main, two_beans):
        a, b = two_beans
        assert main.dep.remove(a.id, b.id) == 0
