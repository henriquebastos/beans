# Python imports
import importlib.resources
import os
from pathlib import Path

# Internal imports
from beans.store import Store

BEANS_DIR = ".beans"
ENV_BEANS_DIR = "MAGIC_BEANS_DIR"
DB_NAME = "beans.db"
AGENTS_MD = "AGENTS.md"


def find_beans_dir(start=None, dirname=BEANS_DIR) -> Path:
    """Walk up from start (default cwd) to find a .beans/ directory."""
    env_override = os.environ.get(ENV_BEANS_DIR)
    if env_override:
        p = Path(env_override)
        if not p.is_dir():
            raise FileNotFoundError(f"{ENV_BEANS_DIR}={env_override} is not a directory")
        return p
    current = Path(start) if start else Path.cwd()
    while True:
        candidate = current / dirname
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(f"No {dirname} directory found (walked up from {start or Path.cwd()})")
        current = parent


def init_project(dirname=BEANS_DIR, db_name=DB_NAME, agents_md=AGENTS_MD) -> Path:
    """Initialize a beans project in the current directory. Returns the .beans/ path."""
    env_override = os.environ.get(ENV_BEANS_DIR)
    beans_dir = Path(env_override) if env_override else Path.cwd() / dirname
    beans_dir.mkdir(exist_ok=True)

    db_path = beans_dir / db_name
    Store.from_path(str(db_path)).close()

    agents_file = beans_dir / agents_md
    if not agents_file.exists():
        template = importlib.resources.files("beans.templates").joinpath(agents_md).read_text()
        agents_file.write_text(template)

    return beans_dir
