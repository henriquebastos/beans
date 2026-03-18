# Python imports
import json
import os
from pathlib import Path

CONFIG_DIR = "beans"
CONFIG_FILE = "config.json"
PROJECTS_FILE = "projects.json"
DEFAULT_XDG = ".config"


def config_dir(config_dir_name=CONFIG_DIR, default_xdg=DEFAULT_XDG) -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", Path.home() / default_xdg)
    return Path(xdg) / config_dir_name


def config_path(config_file=CONFIG_FILE, base=None) -> Path:
    return (base or config_dir()) / config_file


def projects_path(projects_file=PROJECTS_FILE, base=None) -> Path:
    return (base or config_dir()) / projects_file


def load_config(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_projects(path) -> dict:
    return load_config(path)


def save_projects(path, projects) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(projects, indent=2))
