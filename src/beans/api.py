# Internal imports
from beans.models import Bean
from beans.store import BeanStore


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
