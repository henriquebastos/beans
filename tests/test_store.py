# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.models import AmbiguousIdError, Bean, BeanId, BeanNotFoundError
from beans.store import BeanStore


class TestBeanStoreCreateAndList:
    """BeanStore can persist and retrieve beans."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_list_empty_store(self, store):
        assert store.list() == []

    def test_create_and_list_one_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        beans = store.list()
        assert len(beans) == 1
        assert beans[0].title == "Fix auth"
        assert beans[0].id == bean.id

    def test_create_multiple_beans(self, store):
        store.create(Bean(title="First"))
        store.create(Bean(title="Second"))

        beans = store.list()
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
        store.create(bean)

        result, *_ = store.list()
        assert result == bean
        

class TestBeanStoreGetBean:
    """BeanStore can retrieve a single bean by id."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_get_existing_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        result = store.get(bean.id)
        assert result.id == bean.id
        assert result.title == "Fix auth"

    def test_get_nonexistent_bean_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            store.get(BeanId("bean-00000000"))


class TestBeanStoreUpdateBean:
    """BeanStore can update bean fields."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_update_title(self, store):
        bean = Bean(title="Old title")
        store.create(bean)

        assert store.update(bean.id, {"title": "New title"}) == 1
        assert store.get(bean.id).title == "New title"

    def test_update_status(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, {"status": "in_progress"}) == 1
        assert store.get(bean.id).status == "in_progress"

    def test_update_priority(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, {"priority": 0}) == 1
        assert store.get(bean.id).priority == 0

    def test_update_multiple_fields(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, {"title": "New title", "status": "closed"}) == 1
        result = store.get(bean.id)
        assert result.title == "New title"
        assert result.status == "closed"

    def test_update_empty_fields(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        assert store.update(bean.id, {}) == 0

    def test_update_nonexistent_bean_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            store.update(BeanId("bean-00000000"), {"title": "Nope"})


class TestBeanStoreDeleteBean:
    """BeanStore can delete a bean."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_delete_removes_bean(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        store.delete(bean.id)
        with pytest.raises(BeanNotFoundError):
            store.get(bean.id)

    def test_delete_nonexistent_returns_zero(self, store):
        assert store.delete(BeanId("bean-00000000")) == 0


class TestBeanStorePrefixMatch:
    """BeanStore resolves id prefixes to full beans."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_full_id_match(self, store):
        bean = Bean(id="bean-aabbccdd", title="Fix auth")
        store.create(bean)

        result = store.get("bean-aabbccdd")
        assert result.id == "bean-aabbccdd"

    def test_prefix_match(self, store):
        bean = Bean(id="bean-aabbccdd", title="Fix auth")
        store.create(bean)

        result = store.get("bean-aabb")
        assert result.id == "bean-aabbccdd"

    def test_short_prefix_match(self, store):
        bean = Bean(id="bean-aabbccdd", title="Fix auth")
        store.create(bean)

        result = store.get("bean-aa")
        assert result.id == "bean-aabbccdd"

    def test_ambiguous_prefix_raises(self, store):
        store.create(Bean(id="bean-aabb0001", title="First"))
        store.create(Bean(id="bean-aabb0002", title="Second"))

        with pytest.raises(AmbiguousIdError):
            store.get("bean-aabb")

    def test_no_match_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            store.get("bean-zzzzzzzz")


class TestBeanStoreValidation:
    """BeanStore validates inputs."""

    @pytest.fixture()
    def store(self):
        with BeanStore(sqlite3.connect(":memory:")) as s:
            yield s

    def test_update_invalid_status_rejected(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        with pytest.raises(ValueError, match="status"):
            store.update(bean.id, {"status": "deleted"})

    def test_update_invalid_priority_rejected(self, store):
        bean = Bean(title="Fix auth")
        store.create(bean)

        with pytest.raises(ValueError, match="priority"):
            store.update(bean.id, {"priority": 5})

    def test_invalid_bean_id_rejected(self, store):
        with pytest.raises(ValueError, match="Invalid bean id"):
            BeanId("not-a-bean-id")
