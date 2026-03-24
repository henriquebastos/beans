# Python imports
from datetime import UTC, datetime

# Internal imports
from beans.models import Bean, BeanNotFoundError, BeanUpdate, CyclicDepError, Dep, DepNotFoundError, OpenChildrenError
from beans.store import Store


def create_bean(store: Store, title, deps=None, **fields) -> Bean:
    bean = Bean(title=title, **fields)
    store.create(bean)
    if deps:
        for dep_id in deps:
            add_dep(store, dep_id, bean.id)
    return bean


def show_bean(store: Store, bean_id) -> Bean:
    return store.get(bean_id)


def update_bean(store: Store, bean_id, **fields) -> Bean:
    validated = BeanUpdate(**fields)
    clean = validated.model_dump(exclude_none=True)
    if store.update(bean_id, **clean) == 0:
        raise BeanNotFoundError(bean_id)
    return store.get(bean_id)


def close_bean(store: Store, bean_id, reason=None, force=False) -> Bean:
    if not force:
        # Check for open children
        all_beans = store.list()
        open_children = [b for b in all_beans if b.parent_id == bean_id and b.status != "closed"]
        if open_children:
            count = len(open_children)
            raise OpenChildrenError(
                f"Cannot close {bean_id}: {count} open {'child' if count == 1 else 'children'} remain"
            )
    fields = {"status": "closed", "closed_at": datetime.now(UTC).isoformat()}
    if reason:
        fields["close_reason"] = reason
    if store.update(bean_id, **fields) == 0:
        raise BeanNotFoundError(bean_id)
    return store.get(bean_id)


def reopen_bean(store: Store, bean_id, status="open") -> Bean:
    """Reopen a closed bean, clearing closed_at and close_reason."""
    store.update(bean_id, status=status, closed_at=None, close_reason=None)
    return store.get(bean_id)


def delete_bean(store: Store, bean_id) -> Bean:
    bean = store.get(bean_id)
    store.delete(bean_id)
    return bean


def claim_bean(store: Store, bean_id, actor) -> Bean:
    bean = store.get(bean_id)
    if bean.status == "closed":
        raise ValueError(f"Bean {bean_id} is closed")
    if bean.assignee == actor:
        return bean
    if bean.assignee:
        raise ValueError(f"Bean {bean_id} already claimed by {bean.assignee}")
    store.update(bean_id, assignee=actor, status="in_progress")
    return store.get(bean_id)


def release_bean(store: Store, bean_id, actor) -> Bean:
    bean = store.get(bean_id)
    if not bean.assignee:
        return bean
    if bean.assignee != actor:
        raise ValueError(f"Bean {bean_id} claimed by {bean.assignee}")
    store.update(bean_id, assignee=None, status="open")
    return store.get(bean_id)


def release_mine(store: Store, actor) -> list[Bean]:
    beans = store.list_by_assignee(actor)
    return [release_bean(store, bean.id, actor) for bean in beans]


def list_beans(store: Store, types=None, statuses=None, parent_id=None) -> list[Bean]:
    return store.list(types=types, statuses=statuses, parent_id=parent_id)


def ready_beans(store: Store, assignee=None, unassigned=False, parent_id=None) -> list[Bean]:
    return store.ready(assignee=assignee, unassigned=unassigned, parent_id=parent_id)


def search_beans(store: Store, query) -> list[Bean]:
    return store.search(query)


def stats(store: Store) -> dict:
    return store.stats()


def list_deps(store: Store, from_id) -> list[Dep]:
    return store.list_deps(from_id)


def add_dep(store: Store, from_id, to_id, dep_type="blocks") -> Dep:
    # Self-dep check
    if from_id == to_id:
        bean = store.get(from_id)
        raise CyclicDepError(
            f"Adding this dependency would create a cycle: {from_id} \"{bean.title}\" \u2192 {from_id} \"{bean.title}\""
        )

    # Cycle detection: check if from_id is reachable from to_id via existing deps
    all_deps = store.list_all_deps()

    # Build forward adjacency (from -> [to, ...])
    adjacency = {}
    for d in all_deps:
        adjacency.setdefault(d.from_id, []).append(d.to_id)

    # BFS/DFS from to_id to see if we can reach from_id
    visited = set()
    stack = [to_id]
    path_map = {to_id: [to_id]}

    while stack:
        current = stack.pop()
        if current == from_id:
            cycle_ids = [from_id] + path_map[from_id]
            # Fetch titles
            beans_by_id = {}
            for bid in set(cycle_ids):
                try:
                    beans_by_id[bid] = store.get(bid)
                except BeanNotFoundError:
                    beans_by_id[bid] = None

            parts = []
            for bid in cycle_ids:
                b = beans_by_id.get(bid)
                title = f' "{b.title}"' if b else ""
                parts.append(f"{bid}{title}")

            raise CyclicDepError(
                f"Adding this dependency would create a cycle: {' \u2192 '.join(parts)}"
            )

        if current in visited:
            continue
        visited.add(current)

        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                path_map[neighbor] = path_map[current] + [neighbor]
                stack.append(neighbor)

    dep = Dep(from_id=from_id, to_id=to_id, dep_type=dep_type)
    store.add_dep(dep)
    return dep


def remove_dep(store: Store, from_id, to_id) -> int:
    count = store.remove_dep(from_id, to_id)
    if count == 0:
        raise DepNotFoundError(f"No dependency from {from_id} to {to_id}")
    return count


def graph(store: Store) -> dict:
    beans = store.list()
    deps = store.list_all_deps()
    nodes = {b.id: {"id": b.id, "title": b.title, "status": b.status, "parent_id": b.parent_id} for b in beans}
    edges = [{"from_id": d.from_id, "to_id": d.to_id, "dep_type": d.dep_type} for d in deps]
    return {"nodes": list(nodes.values()), "edges": edges}
