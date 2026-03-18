# Python imports
from datetime import UTC, datetime

# Internal imports
from beans.models import Bean, BeanNotFoundError, BeanUpdate
from beans.store import BeanStore


def create_bean(store: BeanStore, title, **fields) -> Bean:
    bean = Bean(title=title, **fields)
    store.create(bean)
    return bean


def update_bean(store: BeanStore, bean_id, **fields) -> Bean:
    validated = BeanUpdate(**fields)
    clean = validated.model_dump(exclude_none=True)
    if store.update(bean_id, **clean) == 0:
        raise BeanNotFoundError(bean_id)
    return store.get(bean_id)


def close_bean(store: BeanStore, bean_id, reason=None) -> Bean:
    fields = {"status": "closed", "closed_at": datetime.now(UTC).isoformat()}
    if reason:
        fields["close_reason"] = reason
    if store.update(bean_id, **fields) == 0:
        raise BeanNotFoundError(bean_id)
    return store.get(bean_id)


def claim_bean(store: BeanStore, bean_id, actor) -> Bean:
    bean = store.get(bean_id)
    if bean.status == "closed":
        raise ValueError(f"Bean {bean_id} is closed")
    if bean.assignee == actor:
        return bean
    if bean.assignee:
        raise ValueError(f"Bean {bean_id} already claimed by {bean.assignee}")
    store.update(bean_id, assignee=actor, status="in_progress")
    return store.get(bean_id)


def release_bean(store: BeanStore, bean_id, actor) -> Bean:
    bean = store.get(bean_id)
    if not bean.assignee:
        return bean
    if bean.assignee != actor:
        raise ValueError(f"Bean {bean_id} claimed by {bean.assignee}")
    store.update(bean_id, assignee=None, status="open")
    return store.get(bean_id)


def release_mine(store: BeanStore, actor) -> list[Bean]:
    beans = store.list_by_assignee(actor)
    return [release_bean(store, bean.id, actor) for bean in beans]


def stats(store: BeanStore) -> dict:
    return store.stats()
