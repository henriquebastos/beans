# Python imports
import sqlite3

# Pip imports
import pytest

# Internal imports
from beans.api import (
    add_dep,
    claim_bean,
    close_bean,
    create_bean,
    delete_bean,
    graph,
    list_beans,
    list_deps,
    ready_beans,
    release_bean,
    release_mine,
    remove_dep,
    reopen_bean,
    search_beans,
    show_bean,
    stats,
    update_bean,
)
from beans.models import BeanId, BeanNotFoundError, CyclicDepError, Dep, DepNotFoundError, OpenChildrenError
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


class TestCreateBean:
    """create_bean() persists a new bean and returns it."""

    def test_create_returns_bean(self, store):
        bean = create_bean(store, "Fix auth")
        assert bean.title == "Fix auth"
        assert bean.status == "open"
        assert bean.type == "task"

    def test_create_with_fields(self, store):
        bean = create_bean(store, "Design review", type="epic", priority=0, body="Details")
        assert bean.type == "epic"
        assert bean.priority == 0
        assert bean.body == "Details"

    def test_create_with_priority(self, store):
        bean = create_bean(store, "Urgent task", priority=0)
        assert bean.priority == 0

    def test_create_persists(self, store):
        bean = create_bean(store, "Fix auth")
        assert show_bean(store, bean.id) == bean

    def test_create_with_deps(self, store):
        blocker = create_bean(store, "Blocker")
        bean = create_bean(store, "Blocked", deps=[blocker.id])
        assert bean not in ready_beans(store)
        close_bean(store, blocker.id)
        assert bean in ready_beans(store)

    def test_create_with_multiple_deps(self, store):
        a = create_bean(store, "Dep A")
        b = create_bean(store, "Dep B")
        bean = create_bean(store, "Blocked by both", deps=[a.id, b.id])
        assert bean not in ready_beans(store)
        close_bean(store, a.id)
        assert bean not in ready_beans(store)
        close_bean(store, b.id)
        assert bean in ready_beans(store)


class TestShowBean:
    """show_bean() retrieves a single bean by id."""

    def test_show_existing(self, store):
        bean = create_bean(store, "Fix auth")
        assert show_bean(store, bean.id) == bean

    def test_show_nonexistent_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            show_bean(store, BeanId("bean-00000000"))


class TestUpdateBean:
    """update_bean() validates and applies field changes."""

    def test_update_title(self, store):
        bean = create_bean(store, "Old title")
        result = update_bean(store, bean.id, title="New title")
        assert result.title == "New title"

    def test_update_multiple_fields(self, store):
        bean = create_bean(store, "Fix auth")
        result = update_bean(store, bean.id, title="New", status="in_progress", priority=0)
        assert result.title == "New"
        assert result.status == "in_progress"
        assert result.priority == 0

    def test_update_nonexistent_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            update_bean(store, BeanId("bean-00000000"), title="Nope")

    def test_update_validates_fields(self, store):
        bean = create_bean(store, "Fix auth")
        with pytest.raises(Exception):
            update_bean(store, bean.id, status="invalid")


class TestCloseBean:
    """close_bean() sets status=closed and closed_at."""

    def test_close_sets_status_and_timestamp(self, store):
        bean = create_bean(store, "Fix auth")
        result = close_bean(store, bean.id)
        assert result.status == "closed"
        assert result.closed_at is not None

    def test_close_with_reason(self, store):
        bean = create_bean(store, "Fix auth")
        result = close_bean(store, bean.id, reason="Done in PR #42")
        assert result.close_reason == "Done in PR #42"

    def test_close_without_reason(self, store):
        bean = create_bean(store, "Fix auth")
        result = close_bean(store, bean.id)
        assert result.close_reason is None

    def test_close_nonexistent_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            close_bean(store, BeanId("bean-00000000"))


class TestReopenBean:
    """reopen_bean() clears closed_at and close_reason."""

    def test_reopen_clears_closed_fields(self, store):
        bean = create_bean(store, "Task")
        close_bean(store, bean.id, reason="Done")
        result = reopen_bean(store, bean.id)
        assert result.status == "open"
        assert result.closed_at is None
        assert result.close_reason is None

    def test_reopen_to_in_progress(self, store):
        bean = create_bean(store, "Task")
        close_bean(store, bean.id)
        result = reopen_bean(store, bean.id, status="in_progress")
        assert result.status == "in_progress"
        assert result.closed_at is None

    def test_reopen_preserves_other_fields(self, store):
        bean = create_bean(store, "Task", body="important", priority=1)
        close_bean(store, bean.id, reason="Done")
        result = reopen_bean(store, bean.id)
        assert result.body == "important"
        assert result.priority == 1


class TestCloseChildrenGuard:
    """close_bean() guards against closing beans with open children."""

    def test_close_with_open_children_raises(self, store):
        parent = create_bean(store, "Epic")
        create_bean(store, "Task", parent_id=parent.id)
        with pytest.raises(OpenChildrenError, match="1 open child remain"):
            close_bean(store, parent.id)

    def test_close_with_open_children_force(self, store):
        parent = create_bean(store, "Epic")
        create_bean(store, "Task", parent_id=parent.id)
        result = close_bean(store, parent.id, force=True)
        assert result.status == "closed"

    def test_close_with_all_children_closed(self, store):
        parent = create_bean(store, "Epic")
        child = create_bean(store, "Task", parent_id=parent.id)
        close_bean(store, child.id)
        result = close_bean(store, parent.id)
        assert result.status == "closed"

    def test_close_no_children_works(self, store):
        bean = create_bean(store, "Task")
        result = close_bean(store, bean.id)
        assert result.status == "closed"

    def test_close_multiple_open_children(self, store):
        parent = create_bean(store, "Epic")
        create_bean(store, "Task 1", parent_id=parent.id)
        create_bean(store, "Task 2", parent_id=parent.id)
        with pytest.raises(OpenChildrenError, match="2 open children remain"):
            close_bean(store, parent.id)


class TestDeleteBean:
    """delete_bean() removes a bean and returns it."""

    def test_delete_returns_bean(self, store):
        bean = create_bean(store, "Fix auth")
        result = delete_bean(store, bean.id)
        assert result == bean

    def test_delete_removes_from_store(self, store):
        bean = create_bean(store, "Fix auth")
        delete_bean(store, bean.id)
        with pytest.raises(BeanNotFoundError):
            show_bean(store, bean.id)

    def test_delete_nonexistent_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            delete_bean(store, BeanId("bean-00000000"))


class TestClaimBean:
    """claim_bean() atomically assigns a bean."""

    def test_claim_sets_assignee_and_status(self, store):
        bean = create_bean(store, "Fix auth")
        result = claim_bean(store, bean.id, "alice")
        assert result.assignee == "alice"
        assert result.status == "in_progress"

    def test_claim_same_actor_is_idempotent(self, store):
        bean = create_bean(store, "Fix auth")
        first = claim_bean(store, bean.id, "alice")
        second = claim_bean(store, bean.id, "alice")
        assert first == second

    def test_claim_different_actor_raises(self, store):
        bean = create_bean(store, "Fix auth")
        claim_bean(store, bean.id, "alice")
        with pytest.raises(ValueError, match="already claimed"):
            claim_bean(store, bean.id, "bob")

    def test_claim_nonexistent_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            claim_bean(store, BeanId("bean-00000000"), "alice")

    def test_claim_closed_bean_raises(self, store):
        bean = create_bean(store, "Fix auth")
        close_bean(store, bean.id)
        with pytest.raises(ValueError, match="closed"):
            claim_bean(store, bean.id, "alice")


class TestReleaseBean:
    """release_bean() clears assignee and sets status=open."""

    def test_release_clears_assignee(self, store):
        bean = create_bean(store, "Fix auth")
        claim_bean(store, bean.id, "alice")
        result = release_bean(store, bean.id, "alice")
        assert result.assignee is None
        assert result.status == "open"

    def test_release_unclaimed_is_idempotent(self, store):
        bean = create_bean(store, "Fix auth")
        result = release_bean(store, bean.id, "alice")
        assert result == bean

    def test_release_by_different_actor_raises(self, store):
        bean = create_bean(store, "Fix auth")
        claim_bean(store, bean.id, "alice")
        with pytest.raises(ValueError, match="claimed by alice"):
            release_bean(store, bean.id, "bob")

    def test_release_nonexistent_raises(self, store):
        with pytest.raises(BeanNotFoundError):
            release_bean(store, BeanId("bean-00000000"), "alice")


class TestReleaseMine:
    """release_mine() releases all beans claimed by an actor."""

    def test_release_mine(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        create_bean(store, "Task C")
        claim_bean(store, a.id, "alice")
        claim_bean(store, b.id, "alice")

        released = release_mine(store, "alice")
        assert len(released) == 2
        assert all(b.assignee is None for b in released)
        assert all(b.status == "open" for b in released)

    def test_release_mine_no_claims(self, store):
        create_bean(store, "Task A")
        assert release_mine(store, "alice") == []


class TestListBeans:
    """list_beans() returns all beans."""

    def test_list_empty(self, store):
        assert list_beans(store) == []

    def test_list_after_create(self, store):
        a = create_bean(store, "First")
        b = create_bean(store, "Second")
        assert list_beans(store) == [a, b]


class TestReadyBeans:
    """ready_beans() returns only unblocked beans."""

    def test_no_deps_all_ready(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        assert ready_beans(store) == [a, b]

    def test_blocked_bean_excluded(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        assert ready_beans(store) == [a]

    def test_closed_blocker_unblocks(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        close_bean(store, a.id)
        assert ready_beans(store) == [b]

    def test_ready_ordered_by_priority(self, store):
        low = create_bean(store, "Low", priority=3)
        high = create_bean(store, "High", priority=0)
        mid = create_bean(store, "Mid", priority=2)
        assert ready_beans(store) == [high, mid, low]

    def test_parent_with_open_children_not_ready(self, store):
        parent = create_bean(store, "Parent")
        create_bean(store, "Child", parent_id=parent.id)
        assert parent not in ready_beans(store)


class TestSearchBeans:
    """search_beans() finds beans by title and body."""

    def test_search_by_title(self, store):
        create_bean(store, "Fix auth bug")
        create_bean(store, "Add feature")
        results = search_beans(store, "auth")
        assert len(results) == 1
        assert results[0].title == "Fix auth bug"

    def test_search_by_body(self, store):
        create_bean(store, "Task", body="needs authentication fix")
        results = search_beans(store, "authentication")
        assert len(results) == 1

    def test_search_no_match(self, store):
        create_bean(store, "Fix auth")
        assert search_beans(store, "zzzzz") == []


class TestStats:
    """stats() returns aggregate counts."""

    def test_stats_counts_by_status(self, store):
        create_bean(store, "Open task")
        b = create_bean(store, "Closed task")
        close_bean(store, b.id)
        result = stats(store)
        assert result["by_status"]["open"] == 1
        assert result["by_status"]["closed"] == 1


class TestListDeps:
    """list_deps() returns dependencies from a bean."""

    def test_list_deps_returns_deps(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        assert list_deps(store, a.id) == [Dep(from_id=a.id, to_id=b.id)]

    def test_list_deps_empty(self, store):
        a = create_bean(store, "Task A")
        assert list_deps(store, a.id) == []


class TestAddDep:
    """add_dep() creates a dependency between beans."""

    def test_add_dep_returns_dep(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        dep = add_dep(store, a.id, b.id)
        assert dep == Dep(from_id=a.id, to_id=b.id, dep_type="blocks")

    def test_add_dep_custom_type(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        dep = add_dep(store, a.id, b.id, dep_type="relates")
        assert dep.dep_type == "relates"

    def test_add_dep_persists(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        assert len(store.dep.list(a.id)) == 1


class TestCyclicDepPrevention:
    """add_dep() prevents circular dependencies."""

    def test_self_dep_rejected(self, store):
        a = create_bean(store, "Task A")
        with pytest.raises(CyclicDepError, match="cycle"):
            add_dep(store, a.id, a.id)

    def test_direct_cycle_rejected(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        with pytest.raises(CyclicDepError, match="cycle"):
            add_dep(store, b.id, a.id)

    def test_transitive_cycle_rejected(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        c = create_bean(store, "Task C")
        add_dep(store, a.id, b.id)
        add_dep(store, b.id, c.id)
        with pytest.raises(CyclicDepError, match="cycle"):
            add_dep(store, c.id, a.id)

    def test_cycle_error_includes_titles(self, store):
        a = create_bean(store, "Alpha")
        b = create_bean(store, "Beta")
        add_dep(store, a.id, b.id)
        with pytest.raises(CyclicDepError, match="Alpha"):
            add_dep(store, b.id, a.id)

    def test_cycle_error_includes_path(self, store):
        a = create_bean(store, "Alpha")
        b = create_bean(store, "Beta")
        c = create_bean(store, "Gamma")
        add_dep(store, a.id, b.id)
        add_dep(store, b.id, c.id)
        with pytest.raises(CyclicDepError, match="\u2192"):
            add_dep(store, c.id, a.id)

    def test_non_cyclic_dep_allowed(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        c = create_bean(store, "Task C")
        add_dep(store, a.id, b.id)
        add_dep(store, a.id, c.id)
        dep = add_dep(store, b.id, c.id)
        assert dep.from_id == b.id
        assert dep.to_id == c.id


class TestRemoveDep:
    """remove_dep() removes a dependency."""

    def test_remove_existing_dep(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        assert remove_dep(store, a.id, b.id) == 1

    def test_remove_nonexistent_raises(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        with pytest.raises(DepNotFoundError):
            remove_dep(store, a.id, b.id)


class TestGraph:
    """graph() builds a node/edge structure from beans and deps."""

    def test_graph_with_deps(self, store):
        a = create_bean(store, "Task A")
        b = create_bean(store, "Task B")
        add_dep(store, a.id, b.id)
        result = graph(store)
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["edges"][0]["from_id"] == a.id

    def test_graph_empty(self, store):
        result = graph(store)
        assert result == {"nodes": [], "edges": []}

    def test_graph_preserves_parent_id(self, store):
        parent = create_bean(store, "Parent")
        child = create_bean(store, "Child", parent_id=parent.id)
        result = graph(store)
        child_node = next(n for n in result["nodes"] if n["id"] == child.id)
        assert child_node["parent_id"] == parent.id
