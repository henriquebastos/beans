# Python imports
import importlib.resources
import os
from pathlib import Path
import re
import subprocess

# Internal imports
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


def find_beans_dir(start=None, dirname=DEFAULT_BEANS_DIR, env=os.environ, var=ENV_BEANS_DIR) -> Path:
    """Walk up from start (default cwd) to find a .beans/ directory."""
    if beans_dir := env_beans_dir(env=env, var=var):
        if not beans_dir.is_dir():
            raise FileNotFoundError(f"{var}={beans_dir} is not a directory")
        return beans_dir
    return walk_beans_dir(start=start, dirname=dirname)


def init_project(
    dirname=DEFAULT_BEANS_DIR,
    db_name=DB_NAME,
    agents_md=AGENTS_MD,
    cwd=None,
    env=os.environ,
    var=ENV_BEANS_DIR,
) -> Path:
    """Initialize a beans project in the current directory. Returns the .beans/ path."""
    base = Path(cwd) if cwd else Path.cwd()
    beans_dir = env_beans_dir(env=env, var=var) or base / dirname
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
