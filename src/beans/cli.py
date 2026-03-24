# Python imports
from datetime import datetime
import importlib.resources
import json
from typing import Annotated, NamedTuple

# Pip imports
from pydantic import ValidationError
import typer

# Internal imports
from beans.api import (
    add_dep,
    claim_bean,
    close_bean,
    create_bean,
    delete_bean,
    list_beans,
    ready_beans,
    release_bean,
    release_mine,
    remove_dep,
    reopen_bean,
    search_beans,
    show_bean,
    update_bean,
)
from beans.api import graph as build_graph
from beans.api import stats as get_stats
from beans.config import config_path, load_config
from beans.models import Bean, BeanId, BeanNotFoundError, CyclicDepError, Dep, DepNotFoundError, Error, OpenChildrenError
from beans.store import Store
from beans.workspace import DB_NAME, find_beans_dir, init_project

app = typer.Typer()
dep_app = typer.Typer()
app.add_typer(dep_app, name="dep")
BeanIdArg = Annotated[str, typer.Argument(parser=BeanId)]


class Config(NamedTuple):
    db: str | None = None
    json: bool = False
    dry_run: bool = False
    fields: list[str] | None = None


@app.callback()
def main(
    ctx: typer.Context,
    db: Annotated[str | None, typer.Option(help="Path to SQLite database")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without writing")] = False,
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated list of fields to include")] = None,
):
    ctx.obj = Config(db=db, json=json_output, dry_run=dry_run, fields=fields.split(",") if fields else None)


def local_timestamp(dt: datetime, fmt="%Y-%m-%d %H:%M") -> str:
    return dt.astimezone().strftime(fmt)


def filter_fields(data, fields, dumps=json.dumps) -> str:
    if isinstance(data, list):
        return dumps([{k: v for k, v in i.model_dump().items() if k in fields} for i in data], default=str)
    return dumps({k: v for k, v in data.model_dump().items() if k in fields}, default=str)


def output(data, json=False, fields=None) -> str:
    if json and fields:
        return filter_fields(data, fields)
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
    type: Annotated[str | None, typer.Option(help="Bean type (task, bug, epic, project)")] = None,
    body: Annotated[str, typer.Option(help="Bean description")] = "",
    parent: Annotated[str | None, typer.Option(help="Parent bean id", parser=BeanId)] = None,
    priority: Annotated[int | None, typer.Option(help="Priority (0=highest, 4=lowest)")] = None,
    dep: Annotated[list[str] | None, typer.Option("--dep", help="Bean ID that blocks this bean (repeatable)", parser=BeanId)] = None,
):
    """Create a new bean."""
    cfg = ctx.obj
    kwargs = {"body": body, "parent_id": parent}
    if type:
        kwargs["type"] = type
    if priority is not None:
        kwargs["priority"] = priority
    if dep:
        kwargs["deps"] = dep
    try:
        with get_store(cfg) as store:
            bean = create_bean(store, title, **kwargs)
    except ValidationError as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def show(ctx: typer.Context, bean_id: BeanIdArg):
    """Show a single bean by id."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            bean = show_bean(store, bean_id)
    except BeanNotFoundError as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json, cfg.fields))


@app.command()
def update(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    type: Annotated[str | None, typer.Option(help="New type (task, bug, epic, project)")] = None,
    status: Annotated[str | None, typer.Option(help="New status")] = None,
    priority: Annotated[int | None, typer.Option(help="New priority")] = None,
    body: Annotated[str | None, typer.Option(help="New body")] = None,
    parent: Annotated[str | None, typer.Option(help="New parent bean id", parser=BeanId)] = None,
):
    """Update fields on a bean."""
    cfg = ctx.obj
    fields = {"title": title, "type": type, "status": status, "priority": priority, "body": body, "parent_id": parent}
    clean_fields = {k: v for k, v in fields.items() if v is not None}
    try:
        with get_store(cfg) as store:
            # If status is changing away from closed, use reopen_bean
            if status and status != "closed":
                current = show_bean(store, bean_id)
                if current.status == "closed":
                    other_fields = {k: v for k, v in clean_fields.items() if k != "status"}
                    bean = reopen_bean(store, bean_id, status=status)
                    if other_fields:
                        bean = update_bean(store, bean_id, **other_fields)
                else:
                    bean = update_bean(store, bean_id, **clean_fields)
            else:
                bean = update_bean(store, bean_id, **clean_fields)
    except (BeanNotFoundError, ValidationError) as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def close(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    reason: Annotated[str | None, typer.Option(help="Reason for closing")] = None,
    force: Annotated[bool, typer.Option("--force", help="Close even if children are open")] = False,
):
    """Close a bean (set status=closed and closed_at)."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            bean = close_bean(store, bean_id, reason=reason, force=force)
    except (BeanNotFoundError, OpenChildrenError) as e:
        error(cfg, e)

    typer.echo(output(bean, cfg.json))


@app.command()
def delete(ctx: typer.Context, bean_id: BeanIdArg):
    """Delete a bean."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            delete_bean(store, bean_id)
    except BeanNotFoundError as e:
        error(cfg, e)

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
            bean = claim_bean(store, bean_id, actor)
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
            beans = release_mine(store, actor)
        typer.echo(output(beans, cfg.json))
    elif bean_id:
        try:
            with get_store(cfg) as store:
                bean = release_bean(store, bean_id, actor)
        except (BeanNotFoundError, ValueError) as e:
            error(cfg, e)
        typer.echo(output(bean, cfg.json))
    else:
        error(cfg, ValueError("Provide a bean id or --mine"))


@app.command("list")
def list_cmd(ctx: typer.Context):
    """List all beans."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        beans = list_beans(store)

    typer.echo(output(beans, cfg.json, cfg.fields))


@app.command()
def ready(ctx: typer.Context):
    """List only unblocked beans."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        beans = ready_beans(store)

    typer.echo(output(beans, cfg.json, cfg.fields))


@app.command()
def stats(ctx: typer.Context):
    """Show aggregate counts by status, type, and assignee."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        data = get_stats(store)

    if cfg.json:
        typer.echo(json.dumps(data))
    else:
        for section, counts in data.items():
            label = section.replace("by_", "").title()
            typer.echo(f"\n{label}:")
            for key, count in sorted(counts.items()):
                typer.echo(f"  {key}: {count}")


def format_graph(data) -> str:
    nodes = {n["id"]: n for n in data["nodes"]}
    children = {}
    roots = []
    for n in data["nodes"]:
        pid = n.get("parent_id")
        if pid and pid in nodes:
            children.setdefault(pid, []).append(n["id"])
        else:
            roots.append(n["id"])

    blocked_by = {}
    for e in data["edges"]:
        if e["dep_type"] == "blocks":
            blocked_by.setdefault(e["to_id"], []).append(e["from_id"])

    lines = []

    def render(node_id, indent=0):
        n = nodes[node_id]
        prefix = "  " * indent
        status_mark = f" [{n['status']}]"
        lines.append(f"{prefix}{n['id']}  {n['title']}{status_mark}")
        blockers = blocked_by.get(node_id, [])
        for b_id in blockers:
            if b_id in nodes:
                lines.append(f"{prefix}  ← blocked by {b_id}")
        for child_id in children.get(node_id, []):
            render(child_id, indent + 1)

    for root_id in roots:
        render(root_id)

    return "\n".join(lines)


@app.command("graph")
def graph_cmd(ctx: typer.Context):
    """Show dependency tree visualization."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        data = build_graph(store)

    if cfg.json:
        typer.echo(json.dumps(data))
    else:
        text = format_graph(data)
        if text:
            typer.echo(text)


@app.command()
def search(ctx: typer.Context, query: str):
    """Search beans by title and body."""
    cfg = ctx.obj
    with get_store(cfg) as store:
        beans = search_beans(store, query)

    typer.echo(output(beans, cfg.json, cfg.fields))


@app.command()
def schema():
    """Output JSON schemas for all models."""
    schemas = {
        "Bean": Bean.model_json_schema(),
        "Dep": Dep.model_json_schema(),
        "Error": Error.model_json_schema(),
    }
    typer.echo(json.dumps(schemas))


@app.command()
def config():
    """Show config path and current configuration."""
    path = config_path()
    cfg = load_config(path)
    typer.echo(f"Config: {path}")
    if cfg:
        typer.echo(json.dumps(cfg, indent=2))
    else:
        typer.echo("No configuration set.")


RECIPES_DIR = importlib.resources.files("beans.templates.recipes")


def list_recipes(recipes_dir=RECIPES_DIR) -> list[str]:
    return sorted(r.stem for r in recipes_dir.iterdir() if r.suffix == ".md")


def load_recipe(client, recipes_dir=RECIPES_DIR) -> str:
    recipe_file = recipes_dir / f"{client}.md"
    if not recipe_file.is_file():
        available = ", ".join(list_recipes(recipes_dir))
        raise FileNotFoundError(f"Unknown recipe: {client}. Available: {available}")
    return recipe_file.read_text()


@app.command()
def recipe(
    client: Annotated[str | None, typer.Argument(help="Client name (claude, gpt, generic)")] = None,
    list_all: Annotated[bool, typer.Option("--list", help="List available recipes")] = False,
):
    """Output agent integration recipe for a client."""
    if list_all:
        for name in list_recipes():
            typer.echo(name)
        return
    if not client:
        typer.echo("Provide a client name or use --list", err=True)
        raise typer.Exit(code=1)
    try:
        typer.echo(load_recipe(client))
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e


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
    try:
        with get_store(cfg) as store:
            dep = add_dep(store, from_id, to_id, dep_type)
    except CyclicDepError as e:
        error(cfg, e)
    typer.echo(output(dep, cfg.json))


@dep_app.command("remove")
def dep_remove(
    ctx: typer.Context,
    from_id: BeanIdArg,
    to_id: BeanIdArg,
):
    """Remove a dependency between two beans."""
    cfg = ctx.obj
    try:
        with get_store(cfg) as store:
            remove_dep(store, from_id, to_id)
    except DepNotFoundError as e:
        error(cfg, e)

    if not cfg.json:
        typer.echo(f"Removed {from_id} -> {to_id}")
