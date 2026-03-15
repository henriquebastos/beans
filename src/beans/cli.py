# Python imports
import json
from datetime import datetime
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


def get_store() -> BeanStore:
    db_path = state.get("db") or "beans.db"
    return BeanStore.from_path(db_path)


@app.command()
def create(title: str):
    """Create a new bean."""
    store = get_store()
    bean = Bean(title=title)
    store.create_bean(bean)
    store.close()

    if state.get("json"):
        typer.echo(bean.model_dump_json())
    else:
        typer.echo(f"{bean.id}  {local_timestamp(bean.created_at)}  {bean.title}")


@app.command("list")
def list_beans():
    """List all beans."""
    store = get_store()
    beans = store.list_beans()
    store.close()

    if state.get("json"):
        typer.echo(json.dumps([b.model_dump(mode="json") for b in beans]))
    else:
        for bean in beans:
            typer.echo(f"{bean.id}  {local_timestamp(bean.created_at)}  {bean.title}")
