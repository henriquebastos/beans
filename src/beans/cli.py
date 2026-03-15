# Python imports
from datetime import datetime
import json
from typing import Annotated

# Pip imports
import typer

# Internal imports
from beans.models import Bean
from beans.store import BeanStore

app = typer.Typer()

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
    return f"{bean.id}  {local_timestamp(bean.created_at)}  {bean.title}"


def get_store() -> BeanStore:
    db_path = state.get("db") or "beans.db"  # TODO: project discovery (Phase 6.2)
    return BeanStore.from_path(db_path)


@app.command()
def create(title: str):
    """Create a new bean."""
    bean = Bean(title=title)
    with get_store() as store:
        store.create_bean(bean)

    if state.get("json"):
        typer.echo(bean.model_dump_json())
    else:
        typer.echo(format_bean(bean))


@app.command()
def show(bean_id: str):
    """Show a single bean by id."""
    with get_store() as store:
        bean = store.get_bean(bean_id)

    if bean is None:
        typer.echo(f"Bean not found: {bean_id}", err=True)
        raise typer.Exit(code=1)

    if state.get("json"):
        typer.echo(bean.model_dump_json())
    else:
        typer.echo(format_bean(bean))


@app.command()
def update(
    bean_id: str,
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    status: Annotated[str | None, typer.Option(help="New status")] = None,
    priority: Annotated[int | None, typer.Option(help="New priority")] = None,
    body: Annotated[str | None, typer.Option(help="New body")] = None,
):
    """Update fields on a bean."""
    fields = {}
    if title is not None:
        fields["title"] = title
    if status is not None:
        fields["status"] = status
    if priority is not None:
        fields["priority"] = priority
    if body is not None:
        fields["body"] = body

    with get_store() as store:
        bean = store.update_bean(bean_id, fields)

    if bean is None:
        typer.echo(f"Bean not found: {bean_id}", err=True)
        raise typer.Exit(code=1)

    if state.get("json"):
        typer.echo(bean.model_dump_json())
    else:
        typer.echo(format_bean(bean))


@app.command()
def close(bean_id: str):
    """Close a bean (set status=closed and closed_at)."""
    with get_store() as store:
        bean = store.close_bean(bean_id)

    if bean is None:
        typer.echo(f"Bean not found: {bean_id}", err=True)
        raise typer.Exit(code=1)

    if state.get("json"):
        typer.echo(bean.model_dump_json())
    else:
        typer.echo(format_bean(bean))


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
