# Python imports
import importlib.resources
import os
from pathlib import Path
import re
import shutil
import subprocess

# Internal imports
from beans.config import Project, config_path, data_dir, load_config, save_config
from beans.store import Store

DEFAULT_BEANS_DIR = ".beans"
ENV_BEANS_DIR = "MAGIC_BEANS_DIR"
ENV_BEANS_PARENT_ID = "MAGIC_BEANS_PARENT_ID"
DB_NAME = "beans.db"
AGENTS_MD = "AGENTS.md"
GITIGNORE = ".gitignore"
GITIGNORE_CONTENT = "*\n!.gitignore\n!AGENTS.md\n!journal.jsonl\n"


def env_beans_dir(env=os.environ, var=ENV_BEANS_DIR) -> Path | None:
    if not (value := env.get(var)):
        return None
    return Path(value)


def walk_beans_dir(start=None, dirname=DEFAULT_BEANS_DIR) -> Path:
    current = Path(start) if start else Path.cwd()
    while True:
        candidate = current / dirname
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(f"No {dirname} directory found (walked up from {start or Path.cwd()})")
        current = parent


def find_in_registry(start=None, config_file=None) -> Path | None:
    """Check project registry for a matching project. Returns store path or None."""
    cfg = load_config(config_file or config_path())
    cwd = Path(start) if start else Path.cwd()
    identifier = detect_identifier(cwd)
    project = cfg.find_by_identifier(identifier)
    if project:
        store = Path(project.store)
        if store.is_dir():
            return store
    # Also try matching cwd as path identifier
    for p in cfg.projects:
        if cwd == Path(p.identifier) or str(cwd).startswith(p.identifier + "/"):
            store = Path(p.store)
            if store.is_dir():
                return store
    return None


def find_beans_dir(start=None, dirname=DEFAULT_BEANS_DIR, env=os.environ, var=ENV_BEANS_DIR, config_file=None) -> Path:
    """Find beans store directory. Checks: env var → registry → local .beans/ walk-up."""
    if beans_dir := env_beans_dir(env=env, var=var):
        if not beans_dir.is_dir():
            raise FileNotFoundError(f"{var}={beans_dir} is not a directory")
        return beans_dir
    if beans_dir := find_in_registry(start=start, config_file=config_file):
        return beans_dir
    return walk_beans_dir(start=start, dirname=dirname)


class ProjectNotFoundError(KeyError):
    pass


def resolve_db(
    db=None,
    project=None,
    config_file=None,
    db_name=DB_NAME,
) -> Path:
    """Resolve the database path. Three branches:
    1. db: explicit path — use it, fail if missing
    2. project: registry lookup by name — find it or fail
    3. auto-discover: env → registry → .beans/ walk-up — find it or fail
    """
    if db:
        return Path(db)
    if project:
        cfg = load_config(config_file or config_path())
        p = cfg.find_by_name(project)
        if p is None:
            raise ProjectNotFoundError(f"Project '{project}' not found in registry")
        return Path(p.store) / db_name
    try:
        return find_beans_dir(config_file=config_file) / db_name
    except FileNotFoundError:
        raise FileNotFoundError("No beans project found. Did you run 'beans init'?")


def setup_store_dir(beans_dir, db_name=DB_NAME, agents_md=AGENTS_MD) -> Path:
    """Create store directory with db, AGENTS.md, and .gitignore. Returns the dir."""
    beans_dir = Path(beans_dir)
    beans_dir.mkdir(parents=True, exist_ok=True)

    db_path = beans_dir / db_name
    Store.from_path(str(db_path)).close()

    agents_file = beans_dir / agents_md
    if not agents_file.exists():
        template = importlib.resources.files("beans.templates").joinpath(agents_md).read_text()
        agents_file.write_text(template)

    gitignore_file = beans_dir / GITIGNORE
    if not gitignore_file.exists():
        gitignore_file.write_text(GITIGNORE_CONTENT)

    return beans_dir


def init_project(
    cwd=None,
    name=None,
    data_base=None,
    config_file=None,
) -> Path:
    """Initialize a beans project in the registry. Returns the store dir path."""
    base = Path(cwd) if cwd else Path.cwd()
    identifier = detect_identifier(base)
    project_name = name or detect_name(identifier)
    store_path = (data_base or data_dir()) / project_name
    cfg_path = config_file or config_path()

    store_dir = setup_store_dir(store_path)
    cfg = load_config(cfg_path)
    cfg.add_project(Project(name=project_name, identifier=identifier, store=str(store_dir)))
    save_config(cfg, cfg_path)

    return store_dir


def init_project_local(
    dirname=DEFAULT_BEANS_DIR,
    cwd=None,
    env=os.environ,
    var=ENV_BEANS_DIR,
) -> Path:
    """Initialize a beans project locally in .beans/. Returns the .beans/ path."""
    base = Path(cwd) if cwd else Path.cwd()
    beans_dir = env_beans_dir(env=env, var=var) or base / dirname
    return setup_store_dir(beans_dir)


SSH_PATTERN = re.compile(r"^[\w.-]+@([\w.-]+):(.*?)(?:\.git)?/?$")
HTTPS_PATTERN = re.compile(r"^https?://([\w.-]+)/(.*?)(?:\.git)?/?$")


def normalize_git_remote(url, ssh_pattern=SSH_PATTERN, https_pattern=HTTPS_PATTERN) -> str:
    if m := ssh_pattern.match(url):
        return f"{m.group(1)}/{m.group(2)}"
    if m := https_pattern.match(url):
        return f"{m.group(1)}/{m.group(2)}"
    return url


def git_remote_url(cwd) -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def detect_identifier(cwd) -> str:
    cwd = Path(cwd)
    if url := git_remote_url(cwd):
        return normalize_git_remote(url)
    return str(cwd)


def detect_name(identifier) -> str:
    return identifier.rstrip("/").rsplit("/", 1)[-1]


def migrate_project(
    cwd=None,
    name=None,
    data_base=None,
    config_file=None,
    db_name=DB_NAME,
) -> Path:
    """Migrate existing .beans/ to registry. Returns the new store dir path."""
    base = Path(cwd) if cwd else Path.cwd()
    try:
        old_dir = walk_beans_dir(start=base)
    except FileNotFoundError:
        raise FileNotFoundError("No .beans/ directory found. Nothing to migrate.")

    identifier = detect_identifier(base)
    project_name = name or detect_name(identifier)
    store_path = (data_base or data_dir()) / project_name
    cfg_path = config_file or config_path()

    # Copy files from old to new
    store_path.mkdir(parents=True, exist_ok=True)
    for item in old_dir.iterdir():
        dest = store_path / item.name
        if item.is_file():
            shutil.copy2(str(item), str(dest))

    # Register
    cfg = load_config(cfg_path)
    cfg.add_project(Project(name=project_name, identifier=identifier, store=str(store_path)))
    save_config(cfg, cfg_path)

    return store_path
