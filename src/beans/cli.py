# Python imports
from datetime import datetime
import json
from typing import Annotated

# Pip imports
from pydantic import ValidationError
import typer

# Internal imports
from beans.models import Bean, BeanId
from beans.store import BeanStore

app = typer.Typer()
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


def format_bean(bean: Bean) -> str:
    if state.get("json"):
        return bean.model_dump_json()
    return f"{bean.id}  {local_timestamp(bean.created_at)}  {bean.title}"


def bean_error(e: Exception):
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
        store.create_bean(bean)

    typer.echo(format_bean(bean))


@app.command()
def show(bean_id: BeanIdArg):
    """Show a single bean by id."""
    try:
        with get_store() as store:
            bean = store.get_bean(bean_id)
    except (KeyError, ValueError) as e:
        bean_error(e)

    typer.echo(format_bean(bean))


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
        with get_store() as store:
            bean = store.update_bean(bean_id, fields)
    except (KeyError, ValueError, ValidationError) as e:
        bean_error(e)

    typer.echo(format_bean(bean))


@app.command()
def close(bean_id: BeanIdArg):
    """Close a bean (set status=closed and closed_at)."""
    try:
        with get_store() as store:
            bean = store.close_bean(bean_id)
    except (KeyError, ValueError) as e:
        bean_error(e)

    typer.echo(format_bean(bean))


@app.command()
def delete(bean_id: BeanIdArg):
    """Delete a bean."""
    try:
        with get_store() as store:
            store.delete_bean(bean_id)
    except (KeyError, ValueError) as e:
        bean_error(e)

    typer.echo(f"Deleted {bean_id}")


@app.command("list")
def list_beans():
    """List all beans."""
    with get_store() as store:
        beans = store.list_beans()

    if state.get("json"):
        typer.echo(json.dumps([b.model_dump(mode="json") for b in beans]))
    else:
        for bean in beans:
            typer.echo(format_bean(bean))
