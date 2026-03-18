# Python imports
from datetime import UTC, datetime
import json
from typing import Annotated

# Pip imports
from pydantic import ValidationError
import typer

# Internal imports
from beans.models import Bean, BeanId, BeanNotFoundError, Dep, Error
from beans.project import DB_NAME, find_beans_dir, init_project
from beans.store import Store

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
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without writing")] = False,
):
    state["db"] = db
    state["json"] = json_output
    state["dry_run"] = dry_run


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
    err = Error(message=str(e))
    if state.get("json"):
        typer.echo(err.model_dump_json())
    else:
        typer.echo(err.message, err=True)
    raise typer.Exit(code=1) from e


def get_store(db_name=DB_NAME) -> Store:
    if state.get("db"):
        db_path = state["db"]
    else:
        try:
            db_path = str(find_beans_dir() / db_name)
        except FileNotFoundError:
            db_path = db_name
    return Store.from_path(db_path, dry_run=state.get("dry_run", False))


@app.command()
def init():
    """Initialize a beans project in the current directory."""
    beans_dir = init_project()
    typer.echo(f"Initialized beans project in {beans_dir}")


@app.command()
def create(
    title: str,
    body: Annotated[str, typer.Option(help="Bean description")] = "",
    parent: Annotated[str | None, typer.Option(help="Parent bean id", parser=BeanId)] = None,
):
    """Create a new bean."""
    bean = Bean(title=title, body=body, parent_id=parent)
    with get_store() as store:
        store.bean.create(bean)

    typer.echo(output(bean, state["json"]))


@app.command()
def show(bean_id: BeanIdArg):
    """Show a single bean by id."""
    try:
        with get_store() as store:
            bean = store.bean.get(bean_id)
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
    parent: Annotated[str | None, typer.Option(help="New parent bean id", parser=BeanId)] = None,
):
    """Update fields on a bean."""
    all_fields = {"title": title, "status": status, "priority": priority, "body": body, "parent_id": parent}
    fields = {k: v for k, v in all_fields.items() if v is not None}

    try:
        Bean.fields_validate(**fields)
    except ValidationError as e:
        error(e)

    try:
        with get_store() as store:
            if store.bean.update(bean_id, **fields) == 0:
                raise BeanNotFoundError(bean_id)
            bean = store.bean.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(output(bean, state["json"]))


@app.command()
def close(
    bean_id: BeanIdArg,
    reason: Annotated[str | None, typer.Option(help="Reason for closing")] = None,
):
    """Close a bean (set status=closed and closed_at)."""
    fields = {"status": "closed", "closed_at": datetime.now(UTC).isoformat()}
    if reason:
        fields["close_reason"] = reason
    try:
        with get_store() as store:
            store.bean.update(bean_id, **fields)
            bean = store.bean.get(bean_id)
    except BeanNotFoundError as e:
        error(e)

    typer.echo(output(bean, state["json"]))


@app.command()
def delete(bean_id: BeanIdArg):
    """Delete a bean."""
    with get_store() as store:
        if store.bean.delete(bean_id) == 0:
            error(BeanNotFoundError(bean_id))

    if not state["json"]:
        typer.echo(f"Deleted {bean_id}")


@app.command()
def claim(
    bean_id: BeanIdArg,
    actor: Annotated[str, typer.Option(help="Who is claiming the bean")],
):
    """Claim a bean (set assignee and status=in_progress)."""
    try:
        with get_store() as store:
            bean = store.bean.claim(bean_id, actor)
    except (BeanNotFoundError, ValueError) as e:
        error(e)

    typer.echo(output(bean, state["json"]))


@app.command()
def release(
    bean_id: Annotated[str | None, typer.Argument(parser=BeanId)] = None,
    actor: Annotated[str, typer.Option(help="Who is releasing the bean")] = "",
    mine: Annotated[bool, typer.Option("--mine", help="Release all beans claimed by actor")] = False,
):
    """Release a claimed bean (clear assignee, set status=open)."""
    if mine and bean_id:
        error(ValueError("Provide a bean id or --mine, not both"))
    elif mine:
        with get_store() as store:
            beans = store.bean.release_mine(actor)
        typer.echo(output(beans, state["json"]))
    elif bean_id:
        try:
            with get_store() as store:
                bean = store.bean.release(bean_id, actor)
        except (BeanNotFoundError, ValueError) as e:
            error(e)
        typer.echo(output(bean, state["json"]))
    else:
        error(ValueError("Provide a bean id or --mine"))


@app.command("list")
def list_beans():
    """List all beans."""
    with get_store() as store:
        beans = store.bean.list()

    typer.echo(output(beans, state["json"]))


@app.command()
def ready():
    """List only unblocked beans."""
    with get_store() as store:
        beans = store.bean.ready()

    typer.echo(output(beans, state["json"]))


@app.command()
def schema():
    """Output JSON schemas for all models."""
    schemas = {
        "Bean": Bean.model_json_schema(),
        "Dep": Dep.model_json_schema(),
        "Error": Error.model_json_schema(),
    }
    typer.echo(json.dumps(schemas))


@app.command("export-journal")
def export_journal():
    """Export journal entries as JSONL."""
    with get_store() as store:
        for line in store.journal.export():
            typer.echo(line)


@app.command()
def rebuild(journal_file: str):
    """Rebuild database from a JSONL journal file."""
    with open(journal_file) as f:
        lines = [line.strip() for line in f if line.strip()]

    with get_store() as store:
        store.journal.replay(lines)

    typer.echo(f"Replayed {len(lines)} entries")


@dep_app.command("add")
def dep_add(
    from_id: BeanIdArg,
    to_id: BeanIdArg,
    dep_type: Annotated[str, typer.Option("--type", help="Dependency type")] = "blocks",
):
    """Add a dependency between two beans."""
    dep = Dep(from_id=from_id, to_id=to_id, dep_type=dep_type)
    with get_store() as store:
        store.dep.add(dep)

    typer.echo(output(dep, state["json"]))


@dep_app.command("remove")
def dep_remove(from_id: BeanIdArg, to_id: BeanIdArg):
    """Remove a dependency between two beans."""
    with get_store() as store:
        if store.dep.remove(from_id, to_id) == 0:
            error(BeanNotFoundError(f"No dependency from {from_id} to {to_id}"))

    if not state["json"]:
        typer.echo(f"Removed {from_id} -> {to_id}")
