# Python imports
from datetime import datetime
import json
from typing import Annotated, NamedTuple

# Pip imports
from pydantic import ValidationError
import typer

# Internal imports
from beans.api import claim_bean, close_bean, create_bean, release_bean, release_mine, update_bean
from beans.models import Bean, BeanId, BeanNotFoundError, Dep, Error
from beans.project import DB_NAME, find_beans_dir, init_project
from beans.store import Store

app = typer.Typer()
dep_app = typer.Typer()
app.add_typer(dep_app, name="dep")
BeanIdArg = Annotated[str, typer.Argument(parser=BeanId)]


class Config(NamedTuple):
    db: str | None = None
    json: bool = False
    dry_run: bool = False


@app.callback()
def main(
    ctx: typer.Context,
    db: Annotated[str | None, typer.Option(help="Path to SQLite database")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without writing")] = False,
):
    ctx.obj = Config(db=db, json=json_output, dry_run=dry_run)


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


def error(cfg: Config, e: Exception):
    err = Error(message=str(e))
    if cfg.json:
        typer.echo(err.model_dump_json())
    else:
        typer.echo(err.message, err=True)
    raise typer.Exit(code=1) from e


def get_store(cfg: Config, db_name=DB_NAME) -> Store:
    if cfg.db:
        db_path = cfg.db
    else:
        try:
            db_path = str(find_beans_dir() / db_name)
        except FileNotFoundError:
            db_path = db_name
    return Store.from_path(db_path, dry_run=cfg.dry_run)


@app.command()
def init():
    """Initialize a beans project in the current directory."""
    beans_dir = init_project()
    typer.echo(f"Initialized beans project in {beans_dir}")


@app.command()
def create(
    ctx: typer.Context,
    title: str,
    type: Annotated[str | None, typer.Option(help="Bean type (task, bug, epic)")] = None,
    body: Annotated[str, typer.Option(help="Bean description")] = "",
    parent: Annotated[str | None, typer.Option(help="Parent bean id", parser=BeanId)] = None,
):
    """Create a new bean."""
    cfg = ctx.obj
    kwargs = {"body": body, "parent_id": parent}
    if type:
        kwargs["type"] = type
    with get_store(cfg) as store:
        bean = create_bean(store.bean, title, **kwargs)

    typer.echo(output(bean, cfg.json))


@app.command()
def show(ctx: typer.Context, bean_id: BeanIdArg):
    """Show a single bean by id."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            bean = store.bean.get(bean_id)
    except BeanNotFoundError as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def update(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    type: Annotated[str | None, typer.Option(help="New type (task, bug, epic)")] = None,
    status: Annotated[str | None, typer.Option(help="New status")] = None,
    priority: Annotated[int | None, typer.Option(help="New priority")] = None,
    body: Annotated[str | None, typer.Option(help="New body")] = None,
    parent: Annotated[str | None, typer.Option(help="New parent bean id", parser=BeanId)] = None,
):
    """Update fields on a bean."""
    cfg = ctx.obj
    fields = {"title": title, "type": type, "status": status, "priority": priority, "body": body, "parent_id": parent}
    try:
        with get_store(cfg) as store:
            bean = update_bean(store.bean, bean_id, **{k: v for k, v in fields.items() if v is not None})
    except (BeanNotFoundError, ValidationError) as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def close(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    reason: Annotated[str | None, typer.Option(help="Reason for closing")] = None,
):
    """Close a bean (set status=closed and closed_at)."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            bean = close_bean(store.bean, bean_id, reason=reason)
    except BeanNotFoundError as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def delete(ctx: typer.Context, bean_id: BeanIdArg):
    """Delete a bean."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        if store.bean.delete(bean_id) == 0:
            error(cfg, BeanNotFoundError(bean_id))

    if not cfg.json:
        typer.echo(f"Deleted {bean_id}")


@app.command()
def claim(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    actor: Annotated[str, typer.Option(help="Who is claiming the bean")],
):
    """Claim a bean (set assignee and status=in_progress)."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            bean = claim_bean(store.bean, bean_id, actor)
    except (BeanNotFoundError, ValueError) as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def release(
    ctx: typer.Context,
    bean_id: Annotated[str | None, typer.Argument(parser=BeanId)] = None,
    actor: Annotated[str, typer.Option(help="Who is releasing the bean")] = "",
    mine: Annotated[bool, typer.Option("--mine", help="Release all beans claimed by actor")] = False,
):
    """Release a claimed bean (clear assignee, set status=open)."""
    cfg = ctx.obj
    if mine and bean_id:
        error(cfg, ValueError("Provide a bean id or --mine, not both"))
    elif mine:
        with get_store(cfg) as store:
            beans = release_mine(store.bean, actor)
        typer.echo(output(beans, cfg.json))
    elif bean_id:
        try:
            with get_store(cfg) as store:
                bean = release_bean(store.bean, bean_id, actor)
        except (BeanNotFoundError, ValueError) as e:
            error(cfg, e)
        typer.echo(output(bean, cfg.json))
    else:
        error(cfg, ValueError("Provide a bean id or --mine"))


@app.command("list")
def list_beans(ctx: typer.Context):
    """List all beans."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        beans = store.bean.list()

    typer.echo(output(beans, cfg.json))


@app.command()
def ready(ctx: typer.Context):
    """List only unblocked beans."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        beans = store.bean.ready()

    typer.echo(output(beans, cfg.json))


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
def export_journal(ctx: typer.Context):
    """Export journal entries as JSONL."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        for line in store.journal.export():
            typer.echo(line)


@app.command()
def rebuild(ctx: typer.Context, journal_file: str):
    """Rebuild database from a JSONL journal file."""
    cfg = ctx.obj
    with open(journal_file) as f:
        lines = [line.strip() for line in f if line.strip()]

    with get_store(cfg) as store:
        store.journal.replay(lines)

    typer.echo(f"Replayed {len(lines)} entries")


@dep_app.command("add")
def dep_add(
    ctx: typer.Context,
    from_id: BeanIdArg,
    to_id: BeanIdArg,
    dep_type: Annotated[str, typer.Option("--type", help="Dependency type")] = "blocks",
):
    """Add a dependency between two beans."""
    cfg = ctx.obj
    dep = Dep(from_id=from_id, to_id=to_id, dep_type=dep_type)
    with get_store(cfg) as store:
        store.dep.add(dep)

    typer.echo(output(dep, cfg.json))


@dep_app.command("remove")
def dep_remove(ctx: typer.Context, from_id: BeanIdArg, to_id: BeanIdArg):
    """Remove a dependency between two beans."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        if store.dep.remove(from_id, to_id) == 0:
            error(cfg, BeanNotFoundError(f"No dependency from {from_id} to {to_id}"))

    if not cfg.json:
        typer.echo(f"Removed {from_id} -> {to_id}")
