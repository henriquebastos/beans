# Python imports
from datetime import datetime
import importlib.resources
import json
import os
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ValidationError

# Pip imports
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
from beans.config import BeanType, Config, config_path
from beans.models import (
    Bean,
    BeanId,
    BeanNotFoundError,
    CyclicDepError,
    Dep,
    DepNotFoundError,
    Error,
    OpenChildrenError,
)
from beans.store import Store
from beans.workspace import (
    ProjectNotFoundError,
    init_project,
    init_project_local,
    migrate_project,
    resolve_db,
    walk_beans_dir,
)

app = typer.Typer()
dep_app = typer.Typer()
app.add_typer(dep_app, name="dep")
types_app = typer.Typer()
app.add_typer(types_app, name="types")
BeanIdArg = Annotated[str, typer.Argument(parser=BeanId)]

ENV_BEANS_PARENT_ID = "MAGIC_BEANS_PARENT_ID"


def default_parent_id():
    """Get default parent_id from MAGIC_BEANS_PARENT_ID env var, or None."""
    val = os.environ.get(ENV_BEANS_PARENT_ID)
    if val:
        return BeanId(val)
    return None


class RunContext(BaseModel):
    config: Config
    db: Path | None = None
    project: str | None = None
    json_output: bool = False
    dry_run: bool = False
    fields: list[str] | None = None


@app.callback()
def main(
    ctx: typer.Context,
    db: Annotated[str | None, typer.Option(help="Path to SQLite database")] = None,
    project: Annotated[str | None, typer.Option("--project", help="Project name from registry")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without writing")] = False,
    fields: Annotated[
        str | None, typer.Option("--fields", help="Comma-separated list of fields to include (only with --json)")
    ] = None,
):
    config = Config.from_path(config_path())
    ctx.obj = RunContext(
        config=config, db=db, project=project, json_output=json_output, dry_run=dry_run,
        fields=fields.split(",") if fields else None,
    )


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


def error(rc: RunContext, e: Exception):
    err = Error(message=str(e))
    if rc.json_output:
        typer.echo(err.model_dump_json())
    else:
        typer.echo(err.message, err=True)
    raise typer.Exit(code=1) from e


def get_store(rc: RunContext) -> Store:
    try:
        db_path = resolve_db(db=rc.db, project=rc.project)
    except (FileNotFoundError, ProjectNotFoundError) as e:
        error(rc, e)
    return Store.from_path(db_path, dry_run=rc.dry_run)


@app.command()
def init(
    name: Annotated[str | None, typer.Option(help="Project name for registry")] = None,
    dir: Annotated[bool, typer.Option("--dir", help="Create local .beans/ directory instead of registry")] = False,
):
    """Initialize a beans project. Default: registry. Use --dir for local .beans/."""
    if dir:
        beans_dir = init_project_local()
        typer.echo(f"Initialized beans project in {beans_dir}")
        return

    store_dir = init_project(name=name)
    typer.echo(f"Initialized beans project in {store_dir}")


@app.command()
def migrate(
    name: Annotated[str | None, typer.Option(help="Project name for registry")] = None,
):
    """Migrate existing .beans/ to the project registry."""
    try:
        store_dir = migrate_project(name=name)
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e
    try:
        old_dir = walk_beans_dir()
    except FileNotFoundError:
        old_dir = None
    if old_dir:
        delete = typer.confirm(f"Delete old {old_dir}?", default=False)
        if delete:
            import shutil

            shutil.rmtree(old_dir)
            typer.echo(f"Deleted {old_dir}")
    typer.echo(f"Migrated to {store_dir}")


@app.command()
def create(
    ctx: typer.Context,
    title: str,
    type: Annotated[str | None, typer.Option(help="Bean type")] = None,
    body: Annotated[str, typer.Option(help="Bean description")] = "",
    parent: Annotated[str | None, typer.Option(help="Parent bean id", parser=BeanId)] = None,
    priority: Annotated[int | None, typer.Option(help="Priority (0=highest, 4=lowest)")] = None,
    dep: Annotated[
        list[str] | None,
        typer.Option("--dep", help="Bean ID that blocks this bean (repeatable)", parser=BeanId),
    ] = None,
):
    """Create a new bean."""
    rc = ctx.obj
    if parent is None:
        parent = default_parent_id()
    kwargs = {"body": body, "parent_id": parent}
    if type:
        kwargs["type"] = type
    if priority is not None:
        kwargs["priority"] = priority
    if dep:
        kwargs["deps"] = dep
    try:
        with get_store(rc) as store:
            bean = create_bean(store, title, valid_types=rc.config.type_names(), **kwargs)
    except (ValidationError, BeanNotFoundError, ValueError) as e:
        error(rc, e)

    typer.echo(output(bean, rc.json_output))


@app.command()
def show(ctx: typer.Context, bean_id: BeanIdArg):
    """Show a single bean by id."""
    rc = ctx.obj
    try:
        with get_store(rc) as store:
            bean = show_bean(store, bean_id)
            all_deps = store.list_all_deps()
    except BeanNotFoundError as e:
        error(rc, e)

    if rc.json_output:
        data = bean.model_dump()
        data["blocked_by"] = [str(d.from_id) for d in all_deps if d.to_id == bean_id and d.dep_type == "blocks"]
        data["blocks"] = [str(d.to_id) for d in all_deps if d.from_id == bean_id and d.dep_type == "blocks"]
        if rc.fields:
            data = {k: v for k, v in data.items() if k in rc.fields}
        typer.echo(json.dumps(data, default=str))
    else:
        typer.echo(output(bean, False, rc.fields))


@app.command()
def update(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    type: Annotated[str | None, typer.Option(help="New type")] = None,
    status: Annotated[str | None, typer.Option(help="New status")] = None,
    priority: Annotated[int | None, typer.Option(help="New priority")] = None,
    body: Annotated[str | None, typer.Option(help="New body")] = None,
    parent: Annotated[str | None, typer.Option(help="New parent bean id", parser=BeanId)] = None,
):
    """Update fields on a bean."""
    rc = ctx.obj
    fields = {"title": title, "type": type, "status": status, "priority": priority, "body": body, "parent_id": parent}
    clean_fields = {k: v for k, v in fields.items() if v is not None}
    try:
        with get_store(rc) as store:
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
        error(rc, e)

    typer.echo(output(bean, rc.json_output))


@app.command()
def close(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    reason: Annotated[str | None, typer.Option(help="Reason for closing")] = None,
    force: Annotated[bool, typer.Option("--force", help="Close even if children are open")] = False,
):
    """Close a bean (set status=closed and closed_at)."""
    rc = ctx.obj
    try:
        with get_store(rc) as store:
            bean = close_bean(store, bean_id, reason=reason, force=force)
    except (BeanNotFoundError, OpenChildrenError) as e:
        error(rc, e)

    typer.echo(output(bean, rc.json_output))


@app.command()
def delete(ctx: typer.Context, bean_id: BeanIdArg):
    """Delete a bean."""
    rc = ctx.obj
    try:
        with get_store(rc) as store:
            delete_bean(store, bean_id)
    except BeanNotFoundError as e:
        error(rc, e)

    if not rc.json_output:
        typer.echo(f"Deleted {bean_id}")


@app.command()
def claim(
    ctx: typer.Context,
    bean_id: BeanIdArg,
    actor: Annotated[str, typer.Option(help="Who is claiming the bean")],
):
    """Claim a bean (set assignee and status=in_progress)."""
    rc = ctx.obj
    try:
        with get_store(rc) as store:
            bean = claim_bean(store, bean_id, actor)
    except (BeanNotFoundError, ValueError) as e:
        error(rc, e)

    typer.echo(output(bean, rc.json_output))


@app.command()
def release(
    ctx: typer.Context,
    bean_id: Annotated[str | None, typer.Argument(parser=BeanId)] = None,
    actor: Annotated[str, typer.Option(help="Who is releasing the bean")] = "",
    mine: Annotated[bool, typer.Option("--mine", help="Release all beans claimed by actor")] = False,
):
    """Release a claimed bean (clear assignee, set status=open)."""
    rc = ctx.obj
    if mine and bean_id:
        error(rc, ValueError("Provide a bean id or --mine, not both"))
    elif mine:
        with get_store(rc) as store:
            beans = release_mine(store, actor)
        typer.echo(output(beans, rc.json_output))
    elif bean_id:
        try:
            with get_store(rc) as store:
                bean = release_bean(store, bean_id, actor)
        except (BeanNotFoundError, ValueError) as e:
            error(rc, e)
        typer.echo(output(bean, rc.json_output))
    else:
        error(rc, ValueError("Provide a bean id or --mine"))


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    type: Annotated[
        str | None,
        typer.Option("--type", help="Filter by type (comma-separated, e.g. epic,task)"),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option("--status", help="Filter by status (comma-separated, e.g. open,in_progress)"),
    ] = None,
    parent: Annotated[str | None, typer.Option(help="Filter by parent bean id", parser=BeanId)] = None,
):
    """List all beans."""
    rc = ctx.obj
    if parent is None:
        parent = default_parent_id()
    types = type.split(",") if type else None
    statuses = status.split(",") if status else None
    with get_store(rc) as store:
        beans = list_beans(store, types=types, statuses=statuses, parent_id=parent)

    typer.echo(output(beans, rc.json_output, rc.fields))


@app.command()
def ready(
    ctx: typer.Context,
    assignee: Annotated[str | None, typer.Option(help="Filter by assignee name")] = None,
    unassigned: Annotated[bool, typer.Option("--unassigned", help="Show only unclaimed beans")] = False,
    parent: Annotated[str | None, typer.Option(help="Filter by parent bean id", parser=BeanId)] = None,
):
    """List only unblocked beans."""
    rc = ctx.obj
    if parent is None:
        parent = default_parent_id()
    if assignee and unassigned:
        error(rc, ValueError("--assignee and --unassigned are mutually exclusive"))
    with get_store(rc) as store:
        beans = ready_beans(store, assignee=assignee, unassigned=unassigned, parent_id=parent)

    typer.echo(output(beans, rc.json_output, rc.fields))


@app.command()
def stats(ctx: typer.Context):
    """Show aggregate counts by status, type, and assignee."""
    rc = ctx.obj
    with get_store(rc) as store:
        data = get_stats(store)

    if rc.json_output:
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
    rc = ctx.obj
    with get_store(rc) as store:
        data = build_graph(store)

    if rc.json_output:
        typer.echo(json.dumps(data))
    else:
        text = format_graph(data)
        if text:
            typer.echo(text)


@app.command()
def search(ctx: typer.Context, query: str):
    """Search beans by title and body."""
    rc = ctx.obj
    with get_store(rc) as store:
        beans = search_beans(store, query)

    typer.echo(output(beans, rc.json_output, rc.fields))


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
def config(ctx: typer.Context):
    """Show config path and current configuration."""
    rc = ctx.obj
    typer.echo(f"Config: {rc.config.path}")
    typer.echo(rc.config.model_dump_json(indent=2))


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
    rc = ctx.obj
    with get_store(rc) as store:
        for line in store.journal.export():
            typer.echo(line)


@app.command()
def rebuild(ctx: typer.Context, journal_file: str):
    """Rebuild database from a JSONL journal file."""
    rc = ctx.obj
    with open(journal_file) as f:
        lines = [line.strip() for line in f if line.strip()]

    with get_store(rc) as store:
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
    rc = ctx.obj
    try:
        with get_store(rc) as store:
            dep = add_dep(store, from_id, to_id, dep_type)
    except CyclicDepError as e:
        error(rc, e)
    typer.echo(output(dep, rc.json_output))


@dep_app.command("remove")
def dep_remove(
    ctx: typer.Context,
    from_id: BeanIdArg,
    to_id: BeanIdArg,
):
    """Remove a dependency between two beans."""
    rc = ctx.obj
    try:
        with get_store(rc) as store:
            remove_dep(store, from_id, to_id)
    except DepNotFoundError as e:
        error(rc, e)

    if not rc.json_output:
        typer.echo(f"Removed {from_id} -> {to_id}")


@types_app.callback(invoke_without_command=True)
def types_list(ctx: typer.Context):
    """List configured bean types."""
    if ctx.invoked_subcommand is not None:
        return
    rc = ctx.obj
    for t in rc.config.types:
        line = t.name
        if t.description:
            line += f"  {t.description}"
        typer.echo(line)


@types_app.command("add")
def types_add(
    ctx: typer.Context,
    name: str,
    description: Annotated[str, typer.Option(help="Type description")] = "",
):
    """Add a bean type to config."""
    rc = ctx.obj
    rc.config.add_type(BeanType(name=name, description=description))
    rc.config.save()
    typer.echo(f"Added type: {name}")


@types_app.command("remove")
def types_remove(ctx: typer.Context, name: str):
    """Remove a bean type from config."""
    rc = ctx.obj
    if not rc.config.remove_type(name):
        typer.echo(f"Type not found: {name}", err=True)
        raise typer.Exit(code=1)
    rc.config.save()
    typer.echo(f"Removed type: {name}")
