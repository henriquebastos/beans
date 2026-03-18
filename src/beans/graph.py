# Internal imports
from beans.models import Bean, Dep


def blocked_ids(beans: list[Bean], deps: list[Dep]) -> set[str]:
    open_ids = {b.id for b in beans if b.status != "closed"}
    blocked = set()

    for dep in deps:
        if dep.dep_type == "blocks" and dep.from_id in open_ids:
            blocked.add(dep.to_id)

    changed = True
    while changed:
        changed = False
        for dep in deps:
            if (
                dep.dep_type == "blocks"
                and dep.from_id in open_ids
                and dep.from_id in blocked
                and dep.to_id not in blocked
            ):
                blocked.add(dep.to_id)
                changed = True

    return blocked


def blocked_by_children(beans: list[Bean]) -> set[str]:
    blocked = set()
    for b in beans:
        if b.parent_id and b.status != "closed":
            blocked.add(b.parent_id)
    return blocked


def ready(beans: list[Bean], deps: list[Dep]) -> list[Bean]:
    excluded = blocked_ids(beans, deps) | blocked_by_children(beans)
    return [b for b in beans if b.id not in excluded]
