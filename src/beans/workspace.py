# Python imports
import importlib.resources
from pathlib import Path

# Internal imports
from beans.store import Store

BEANS_DIR = ".beans"
DB_NAME = "beans.db"
AGENTS_MD = "AGENTS.md"
GITIGNORE = ".gitignore"
GITIGNORE_CONTENT = "*\n!.gitignore\n!AGENTS.md\n!journal.jsonl\n"


def find_beans_dir(start=None, dirname=BEANS_DIR) -> Path:
    """Walk up from start (default cwd) to find a .beans/ directory."""
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
    beans_dir = Path.cwd() / dirname
    beans_dir.mkdir(exist_ok=True)

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
