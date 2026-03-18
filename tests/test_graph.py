# Python imports
from datetime import UTC, datetime

# Internal imports
from beans.graph import ready
from beans.models import Bean, Dep

FIXED_TIME = datetime(2025, 1, 1, tzinfo=UTC)


def make_bean(id_suffix, status="open") -> Bean:
    return Bean(id=f"bean-{id_suffix:0>8}", title=f"Task {id_suffix}", status=status, created_at=FIXED_TIME)


class TestReady:
    """ready() returns only beans that are not blocked by open dependencies."""

    def test_no_deps_all_ready(self):
        a = make_bean("a")
        b = make_bean("b")

        assert ready([a, b], []) == [a, b]

    def test_blocked_bean_excluded(self):
        a = make_bean("a")
        b = make_bean("b")
        deps = [Dep(from_id=a.id, to_id=b.id)]

        assert ready([a, b], deps) == [a]

    def test_transitive_blocking_excluded(self):
        a = make_bean("a")
        b = make_bean("b")
        c = make_bean("c")
        deps = [
            Dep(from_id=a.id, to_id=b.id),
            Dep(from_id=b.id, to_id=c.id),
        ]

        assert ready([a, b, c], deps) == [a]

    def test_closed_blocker_does_not_block(self):
        a = make_bean("a", status="closed")
        b = make_bean("b")
        deps = [Dep(from_id=a.id, to_id=b.id)]

        assert ready([a, b], deps) == [a, b]

    def test_empty_beans(self):
        assert ready([], []) == []

    def test_closed_beans_still_returned(self):
        a = make_bean("a", status="closed")
        assert ready([a], []) == [a]

    def test_chain_one_closed_unblocks_next(self):
        a = make_bean("a", status="closed")
        b = make_bean("b")
        c = make_bean("c")
        deps = [
            Dep(from_id=a.id, to_id=b.id),
            Dep(from_id=b.id, to_id=c.id),
        ]

        assert ready([a, b, c], deps) == [a, b]

    def test_closed_intermediate_does_not_propagate_blocking(self):
        a = make_bean("a")
        b = make_bean("b", status="closed")
        c = make_bean("c")
        deps = [
            Dep(from_id=a.id, to_id=b.id),
            Dep(from_id=b.id, to_id=c.id),
        ]

        assert c in ready([a, b, c], deps)

    def test_parent_with_open_children_not_ready(self):
        parent = make_bean("p")
        child = make_bean("c")
        child.parent_id = parent.id

        assert ready([parent, child], []) == [child]

    def test_parent_with_closed_children_is_ready(self):
        parent = make_bean("p")
        child = make_bean("c", status="closed")
        child.parent_id = parent.id

        assert ready([parent, child], []) == [parent, child]

    def test_parent_with_no_children_is_ready(self):
        parent = make_bean("p")
        assert ready([parent], []) == [parent]
