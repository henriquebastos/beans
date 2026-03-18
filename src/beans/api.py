# Python imports
from datetime import UTC, datetime

# Internal imports
from beans.models import Bean, BeanNotFoundError, BeanUpdate, Dep, DepNotFoundError
from beans.store import Store


def create_bean(store: Store, title, **fields) -> Bean:
    bean = Bean(title=title, **fields)
    store.bean.create(bean)
    return bean


def show_bean(store: Store, bean_id) -> Bean:
    return store.bean.get(bean_id)


def update_bean(store: Store, bean_id, **fields) -> Bean:
    validated = BeanUpdate(**fields)
    clean = validated.model_dump(exclude_none=True)
    if store.bean.update(bean_id, **clean) == 0:
        raise BeanNotFoundError(bean_id)
    return store.bean.get(bean_id)


def close_bean(store: Store, bean_id, reason=None) -> Bean:
    fields = {"status": "closed", "closed_at": datetime.now(UTC).isoformat()}
    if reason:
        fields["close_reason"] = reason
    if store.bean.update(bean_id, **fields) == 0:
        raise BeanNotFoundError(bean_id)
    return store.bean.get(bean_id)


def delete_bean(store: Store, bean_id) -> Bean:
    bean = store.bean.get(bean_id)
    store.bean.delete(bean_id)
    return bean


def claim_bean(store: Store, bean_id, actor) -> Bean:
    bean = store.bean.get(bean_id)
    if bean.status == "closed":
        raise ValueError(f"Bean {bean_id} is closed")
    if bean.assignee == actor:
        return bean
    if bean.assignee:
        raise ValueError(f"Bean {bean_id} already claimed by {bean.assignee}")
    store.bean.update(bean_id, assignee=actor, status="in_progress")
    return store.bean.get(bean_id)


def release_bean(store: Store, bean_id, actor) -> Bean:
    bean = store.bean.get(bean_id)
    if not bean.assignee:
        return bean
    if bean.assignee != actor:
        raise ValueError(f"Bean {bean_id} claimed by {bean.assignee}")
    store.bean.update(bean_id, assignee=None, status="open")
    return store.bean.get(bean_id)


def release_mine(store: Store, actor) -> list[Bean]:
    beans = store.bean.list_by_assignee(actor)
    return [release_bean(store, bean.id, actor) for bean in beans]


def list_beans(store: Store) -> list[Bean]:
    return store.bean.list()


def ready_beans(store: Store) -> list[Bean]:
    return store.bean.ready()


def search_beans(store: Store, query) -> list[Bean]:
    return store.bean.search(query)


def stats(store: Store) -> dict:
    return store.bean.stats()


def add_dep(store: Store, from_id, to_id, dep_type="blocks") -> Dep:
    dep = Dep(from_id=from_id, to_id=to_id, dep_type=dep_type)
    store.dep.add(dep)
    return dep


def remove_dep(store: Store, from_id, to_id) -> int:
    count = store.dep.remove(from_id, to_id)
    if count == 0:
        raise DepNotFoundError(f"No dependency from {from_id} to {to_id}")
    return count


def graph(store: Store) -> dict:
    beans = store.bean.list()
    deps = store.dep.list_all()
    nodes = {b.id: {"id": b.id, "title": b.title, "status": b.status, "parent_id": b.parent_id} for b in beans}
    edges = [{"from_id": d.from_id, "to_id": d.to_id, "dep_type": d.dep_type} for d in deps]
    return {"nodes": list(nodes.values()), "edges": edges}
