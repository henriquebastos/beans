# Python imports
from datetime import UTC, datetime
import json
from typing import Annotated

# Pip imports
from pydantic import ValidationError
import typer

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError
from beans.store import BeanStore

app = typer.Typer()
dep_app = typer.Typer()
app.add_typer(dep_app, name="dep")
BeanIdArg = Annotated[str, typer.Argument(parser=BeanId)]

# Global state shared across commands
state: dict = {}


@app.callback()
def main(
    db: Annotated[str | None, typer.Option(help="Path to SQLite database")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
):
    state["db"] = db
    state["json"] = json_output


def local_timestamp(dt: datetime, fmt="%Y-%m-%d %H:%M") -> str:
    return dt.astimezone().strftime(fmt)


def line(bean: Bean) -> str:
    if state.get("json"):
        return bean.model_dump_json()
    return f"{bean.id}  {local_timestamp(bean.created_at)}  {bean.title}"


def error(e: Exception):
    typer.echo(str(e), err=True)
    raise typer.Exit(code=1) from e


def get_store() -> BeanStore:
    db_path = state.get("db") or "beans.db"  # TODO: project discovery (Phase 6.2)
    return BeanStore.from_path(db_path)


@app.command()
def create(title: str):
    """Create a new bean."""
    bean = Bean(title=title)
    with get_store() as store:
        store.create(bean)

    typer.echo(line(bean))


@app.command()
def show(bean_id: BeanIdArg):
    """Show a single bean by id."""
    try:
        with get_store() as store:
            bean = store.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(line(bean))


@app.command()
def update(
    bean_id: BeanIdArg,
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    status: Annotated[str | None, typer.Option(help="New status")] = None,
    priority: Annotated[int | None, typer.Option(help="New priority")] = None,
    body: Annotated[str | None, typer.Option(help="New body")] = None,
):
    """Update fields on a bean."""
    all_fields = {"title": title, "status": status, "priority": priority, "body": body}
    fields = {k: v for k, v in all_fields.items() if v is not None}

    try:
        Bean.model_validate({"id": "bean-00000000", "title": "validate", **fields})
    except ValidationError as e:
        error(e)

    try:
        with get_store() as store:
            if store.update(bean_id, **fields) == 0:
                raise BeanNotFoundError(bean_id)
            bean = store.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(line(bean))


@app.command()
def close(bean_id: BeanIdArg):
    """Close a bean (set status=closed and closed_at)."""
    try:
        with get_store() as store:
            store.update(bean_id, status="closed", closed_at=datetime.now(UTC).isoformat())
            bean = store.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(line(bean))


@app.command()
def delete(bean_id: BeanIdArg):
    """Delete a bean."""
    with get_store() as store:
        if store.delete(bean_id) == 0:
            error(BeanNotFoundError(bean_id))

    typer.echo(f"Deleted {bean_id}")


@app.command("list")
def list_beans():
    """List all beans."""
    with get_store() as store:
        beans = store.list()

    if state.get("json"):
        typer.echo(json.dumps([b.model_dump(mode="json") for b in beans]))
    else:
        for bean in beans:
            typer.echo(line(bean))


@dep_app.command("add")
def dep_add(
    from_id: BeanIdArg,
    to_id: BeanIdArg,
    dep_type: Annotated[str, typer.Option("--type", help="Dependency type")] = "blocks",
):
    """Add a dependency between two beans."""
    with get_store() as store:
        store.add_dep(from_id, to_id, dep_type=dep_type)

    if state.get("json"):
        typer.echo(json.dumps({"from_id": str(from_id), "to_id": str(to_id), "dep_type": dep_type}))
    else:
        typer.echo(f"{from_id} {dep_type} {to_id}")


@dep_app.command("remove")
def dep_remove(from_id: BeanIdArg, to_id: BeanIdArg):
    """Remove a dependency between two beans."""
    with get_store() as store:
        if store.remove_dep(from_id, to_id) == 0:
            error(BeanNotFoundError(f"No dependency from {from_id} to {to_id}"))

    typer.echo(f"Removed {from_id} -> {to_id}")
