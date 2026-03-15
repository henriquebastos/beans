# Python imports
from datetime import UTC, datetime

# Internal imports
from beans.models import Bean

FIXED_TIME = datetime(2025, 1, 1, tzinfo=UTC)


def make_bean(id_suffix, status="open") -> Bean:
    return Bean(id=f"bean-{id_suffix:0>8}", title=f"Task {id_suffix}", status=status, created_at=FIXED_TIME)


class TestReady:
    """ready() returns only beans that are not blocked by open dependencies."""

    def test_no_deps_all_ready(self):
        from beans.graph import ready

        a = make_bean("a")
        b = make_bean("b")

        assert ready([a, b], []) == [a, b]

    def test_blocked_bean_excluded(self):
        from beans.graph import ready

        a = make_bean("a")
        b = make_bean("b")
        deps = [(a.id, b.id, "blocks")]

        assert ready([a, b], deps) == [a]

    def test_transitive_blocking_excluded(self):
        from beans.graph import ready

        a = make_bean("a")
        b = make_bean("b")
        c = make_bean("c")
        deps = [
            (a.id, b.id, "blocks"),
            (b.id, c.id, "blocks"),
        ]

        assert ready([a, b, c], deps) == [a]

    def test_closed_blocker_does_not_block(self):
        from beans.graph import ready

        a = make_bean("a", status="closed")
        b = make_bean("b")
        deps = [(a.id, b.id, "blocks")]

        assert ready([a, b], deps) == [a, b]

    def test_empty_beans(self):
        from beans.graph import ready

        assert ready([], []) == []

    def test_closed_beans_still_returned(self):
        from beans.graph import ready

        a = make_bean("a", status="closed")
        assert ready([a], []) == [a]

    def test_chain_one_closed_unblocks_next(self):
        from beans.graph import ready

        a = make_bean("a", status="closed")
        b = make_bean("b")
        c = make_bean("c")
        deps = [
            (a.id, b.id, "blocks"),
            (b.id, c.id, "blocks"),
        ]

        assert ready([a, b, c], deps) == [a, b]

    def test_parent_with_open_children_not_ready(self):
        from beans.graph import ready

        parent = make_bean("p")
        child = make_bean("c")
        child.parent_id = parent.id

        assert ready([parent, child], []) == [child]

    def test_parent_with_closed_children_is_ready(self):
        from beans.graph import ready

        parent = make_bean("p")
        child = make_bean("c", status="closed")
        child.parent_id = parent.id

        assert ready([parent, child], []) == [parent, child]

    def test_parent_with_no_children_is_ready(self):
        from beans.graph import ready

        parent = make_bean("p")
        assert ready([parent], []) == [parent]
