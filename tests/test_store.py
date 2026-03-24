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

    def test_delete_bean_with_deps_cascades(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))

        assert store.bean.delete(a.id) == 1
        assert store.dep.list(a.id) == []

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

        assert store.bean.ready() == [b]

    def test_ready_empty_store(self, store):
        assert store.bean.ready() == []

    def test_chain_one_closed_unblocks_next(self, store):
        a = store.bean.create(Bean(title="Task A", status="closed"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))
        store.dep.add(Dep(from_id=b.id, to_id=c.id))

        assert store.bean.ready() == [b]

    def test_closed_intermediate_does_not_propagate_blocking(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B", status="closed"))
        c = store.bean.create(Bean(title="Task C"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))
        store.dep.add(Dep(from_id=b.id, to_id=c.id))

        assert c in store.bean.ready()

    def test_ready_ordered_by_priority(self, store):
        low = store.bean.create(Bean(title="Low", priority=3))
        high = store.bean.create(Bean(title="High", priority=0))
        mid = store.bean.create(Bean(title="Mid", priority=2))

        result = store.bean.ready()
        assert result == [high, mid, low]

    def test_fan_in_partial_close_still_blocked(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))
        store.dep.add(Dep(from_id=a.id, to_id=c.id))
        store.dep.add(Dep(from_id=b.id, to_id=c.id))

        store.bean.update(a.id, status="closed")
        assert c not in store.bean.ready()

        store.bean.update(b.id, status="closed")
        assert c in store.bean.ready()

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


class TestBeanStoreListFilters:
    """BeanStore.list() supports type and status filtering."""

    def test_filter_by_type(self, store):
        store.bean.create(Bean(title="Task", type="task"))
        epic = store.bean.create(Bean(title="Epic", type="epic"))
        result = store.bean.list(types=["epic"])
        assert result == [epic]

    def test_filter_by_multiple_types(self, store):
        task = store.bean.create(Bean(title="Task", type="task"))
        epic = store.bean.create(Bean(title="Epic", type="epic"))
        store.bean.create(Bean(title="Bug", type="bug"))
        result = store.bean.list(types=["task", "epic"])
        assert set(b.id for b in result) == {task.id, epic.id}

    def test_filter_by_status(self, store):
        open_bean = store.bean.create(Bean(title="Open"))
        store.bean.create(Bean(title="Closed", status="closed"))
        result = store.bean.list(statuses=["open"])
        assert result == [open_bean]

    def test_filter_by_type_and_status(self, store):
        task_open = store.bean.create(Bean(title="Task Open", type="task"))
        store.bean.create(Bean(title="Epic Open", type="epic"))
        store.bean.create(Bean(title="Task Closed", type="task", status="closed"))
        result = store.bean.list(types=["task"], statuses=["open"])
        assert result == [task_open]

    def test_no_filters_returns_all(self, store):
        a = store.bean.create(Bean(title="A"))
        b = store.bean.create(Bean(title="B"))
        assert store.bean.list() == [a, b]


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


class TestDepStoreCRUD:
    """DepStore can store and remove dependency edges."""

    def test_add_and_list(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        dep = Dep(from_id=a.id, to_id=b.id)
        store.dep.add(dep)

        assert store.dep.list(a.id) == [dep]

    def test_add_multiple(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))

        ab = Dep(from_id=a.id, to_id=b.id)
        ac = Dep(from_id=a.id, to_id=c.id)
        store.dep.add(ab)
        store.dep.add(ac)

        assert set(store.dep.list(a.id)) == {ab, ac}

    def test_list_only_returns_from_bean(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        c = store.bean.create(Bean(title="Task C"))

        store.dep.add(Dep(from_id=a.id, to_id=b.id))
        store.dep.add(Dep(from_id=c.id, to_id=b.id))

        assert store.dep.list(a.id) == [Dep(from_id=a.id, to_id=b.id)]

    def test_list_empty(self, store):
        a = store.bean.create(Bean(title="Task A"))
        assert store.dep.list(a.id) == []

    def test_remove(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        store.dep.add(Dep(from_id=a.id, to_id=b.id))

        assert store.dep.remove(a.id, b.id) == 1
        assert store.dep.list(a.id) == []

    def test_remove_nonexistent(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        assert store.dep.remove(a.id, b.id) == 0


class TestBeanStoreStats:
    """BeanStore.stats() returns aggregate counts."""

    def test_stats_empty_store(self, store):
        result = store.bean.stats()
        assert result == {"by_status": {}, "by_type": {}, "by_assignee": {}}

    def test_stats_by_type(self, store):
        store.bean.create(Bean(title="A"))
        store.bean.create(Bean(title="B", type="bug"))
        store.bean.create(Bean(title="C", type="epic"))
        store.bean.create(Bean(title="D"))

        result = store.bean.stats()
        assert result["by_type"] == {"task": 2, "bug": 1, "epic": 1}

    def test_stats_by_assignee(self, store):
        store.bean.create(Bean(title="A", assignee="alice"))
        store.bean.create(Bean(title="B", assignee="bob"))
        store.bean.create(Bean(title="C", assignee="alice"))
        store.bean.create(Bean(title="D"))

        result = store.bean.stats()
        assert result["by_assignee"] == {"alice": 2, "bob": 1, "unassigned": 1}


class TestBeanStoreSearch:
    """BeanStore.search() finds beans by title and body."""

    def test_search_case_insensitive(self, store):
        store.bean.create(Bean(title="Fix Auth"))

        assert len(store.bean.search("fix auth")) == 1
        assert len(store.bean.search("FIX AUTH")) == 1

    def test_search_empty_query_returns_all(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))

        assert store.bean.search("") == [bean]

    def test_search_multiple_matches(self, store):
        store.bean.create(Bean(title="Fix auth login"))
        store.bean.create(Bean(title="Fix auth signup"))
        store.bean.create(Bean(title="Add tests"))

        results = store.bean.search("auth")
        assert len(results) == 2


class TestDepStoreListAll:
    """DepStore.list_all() returns all dependencies."""

    def test_list_all_empty(self, store):
        assert store.dep.list_all() == []

    def test_list_all_returns_all_deps(self, store):
        a = store.bean.create(Bean(title="A"))
        b = store.bean.create(Bean(title="B"))
        c = store.bean.create(Bean(title="C"))
        d1 = store.dep.add(Dep(from_id=a.id, to_id=b.id))
        d2 = store.dep.add(Dep(from_id=b.id, to_id=c.id))

        assert store.dep.list_all() == [d1, d2]


class TestSchemaMigration:
    """Store applies schema migrations via PRAGMA user_version."""

    def test_new_database_gets_latest_version(self):
        from beans.store import SCHEMA_VERSION

        with Store(sqlite3.connect(":memory:")) as s:
            version = s.conn.execute("PRAGMA user_version").fetchone()[0]
            assert version == SCHEMA_VERSION

    def test_migration_drops_stale_tables(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE beans (id TEXT PRIMARY KEY, title TEXT NOT NULL,
                type TEXT DEFAULT 'task', status TEXT DEFAULT 'open',
                priority INTEGER DEFAULT 2, body TEXT DEFAULT '',
                parent_id TEXT, assignee TEXT, created_by TEXT, ref_id TEXT,
                created_at TEXT NOT NULL, closed_at TEXT, close_reason TEXT);
            CREATE TABLE deps (from_id TEXT, to_id TEXT, dep_type TEXT DEFAULT 'blocks',
                PRIMARY KEY (from_id, to_id));
            CREATE TABLE journal (id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL, bean_id TEXT NOT NULL, snapshot TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')));
            CREATE TABLE labels (bean_id TEXT, label TEXT, PRIMARY KEY (bean_id, label));
            CREATE TABLE cross_deps (from_id TEXT, to_id TEXT, project TEXT,
                dep_type TEXT DEFAULT 'blocks', PRIMARY KEY (from_id, to_id, project));
        """)
        tables_before = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "labels" in tables_before
        assert "cross_deps" in tables_before

        with Store(conn) as s:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables_after = {r[0] for r in s.conn.execute(query).fetchall()}
            assert "labels" not in tables_after
            assert "cross_deps" not in tables_after

    def test_reopening_migrated_database_is_idempotent(self, tmp_path):
        from beans.store import SCHEMA_VERSION

        db_path = str(tmp_path / "test.db")
        with Store.from_path(db_path) as s:
            s.bean.create(Bean(title="Survives migration"))

        with Store.from_path(db_path) as s:
            version = s.conn.execute("PRAGMA user_version").fetchone()[0]
            assert version == SCHEMA_VERSION
            assert s.bean.list()[0].title == "Survives migration"
