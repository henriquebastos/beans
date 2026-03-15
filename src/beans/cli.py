# Python imports
from datetime import UTC, datetime
from typing import Annotated

# Pip imports
from pydantic import ValidationError
import typer

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError, Dep
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


def output(data, json=False) -> str:
    match data, json:
        case Bean(), True:
            return data.model_dump_json()
        case Bean(), False:
            return f"{data.id}  {local_timestamp(data.created_at)}  {data.title}"
        case Dep(), True:
            return data.model_dump_json()
        case Dep(), False:
            return f"{data.from_id} {data.dep_type} {data.to_id}"
        case list(), True:
            return "[" + ",".join(i.model_dump_json() for i in data) + "]"
        case list(), False:
            return "\n".join(output(item) for item in data)
    return ""


def error(e: Exception):
    typer.echo(str(e), err=True)
    raise typer.Exit(code=1) from e


def get_store() -> BeanStore:
    db_path = state.get("db") or "beans.db"  # TODO: project discovery (Phase 6.2)
    return BeanStore.from_path(db_path)


@app.command()
def create(
    title: str,
    parent: Annotated[str | None, typer.Option(help="Parent bean id", parser=BeanId)] = None,
):
    """Create a new bean."""
    bean = Bean(title=title, parent_id=parent)
    with get_store() as store:
        store.create(bean)

    typer.echo(output(bean, state["json"]))


@app.command()
def show(bean_id: BeanIdArg):
    """Show a single bean by id."""
    try:
        with get_store() as store:
            bean = store.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(output(bean, state["json"]))


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

    typer.echo(output(bean, state["json"]))


@app.command()
def close(bean_id: BeanIdArg):
    """Close a bean (set status=closed and closed_at)."""
    try:
        with get_store() as store:
            store.update(bean_id, status="closed", closed_at=datetime.now(UTC).isoformat())
            bean = store.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(output(bean, state["json"]))


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

    typer.echo(output(beans, state["json"]))


@app.command()
def ready():
    """List only unblocked beans."""
    with get_store() as store:
        beans = store.ready()

    typer.echo(output(beans, state["json"]))


@dep_app.command("add")
def dep_add(
    from_id: BeanIdArg,
    to_id: BeanIdArg,
    dep_type: Annotated[str, typer.Option("--type", help="Dependency type")] = "blocks",
):
    """Add a dependency between two beans."""
    with get_store() as store:
        dep = store.add_dep(from_id, to_id, dep_type=dep_type)

    typer.echo(output(dep, state["json"]))


@dep_app.command("remove")
def dep_remove(from_id: BeanIdArg, to_id: BeanIdArg):
    """Remove a dependency between two beans."""
    with get_store() as store:
        if store.remove_dep(from_id, to_id) == 0:
            error(BeanNotFoundError(f"No dependency from {from_id} to {to_id}"))

    typer.echo(f"Removed {from_id} -> {to_id}")
