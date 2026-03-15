# Internal imports
from beans.models import Bean


def blocked_ids(beans: list[Bean], deps: list[tuple]) -> set[str]:
    open_ids = {b.id for b in beans if b.status != "closed"}
    blocked = set()

    for from_id, to_id, dep_type in deps:
        if dep_type == "blocks" and from_id in open_ids:
            blocked.add(to_id)

    changed = True
    while changed:
        changed = False
        for from_id, to_id, dep_type in deps:
            if dep_type == "blocks" and from_id in blocked and to_id not in blocked:
                blocked.add(to_id)
                changed = True

    return blocked


def blocked_by_children(beans: list[Bean]) -> set[str]:
    blocked = set()
    for b in beans:
        if b.parent_id and b.status != "closed":
            blocked.add(b.parent_id)
    return blocked


def ready(beans: list[Bean], deps: list[tuple]) -> list[Bean]:
    excluded = blocked_ids(beans, deps) | blocked_by_children(beans)
    return [b for b in beans if b.id not in excluded]
