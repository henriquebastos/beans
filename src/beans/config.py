# Python imports
import json
import os
from pathlib import Path

# Pip imports
from pydantic import BaseModel

CONFIG_DIR = "beans"
CONFIG_FILE = "config.json"
DATA_DIR = "beans"
DEFAULT_XDG_CONFIG = ".config"
DEFAULT_XDG_DATA = ".local/share"


class Project(BaseModel, frozen=True):
    name: str
    identifier: str
    store: str


def config_dir(config_dir_name=CONFIG_DIR, default_xdg=DEFAULT_XDG_CONFIG) -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", Path.home() / default_xdg)
    return Path(xdg) / config_dir_name


def config_path(config_file=CONFIG_FILE, base=None) -> Path:
    return (base or config_dir()) / config_file


def data_dir(data_dir_name=DATA_DIR, default_xdg=DEFAULT_XDG_DATA) -> Path:
    xdg = os.environ.get("XDG_DATA_HOME", Path.home() / default_xdg)
    return Path(xdg) / data_dir_name


def load_config(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_registry(path) -> list[Project]:
    config = load_config(path)
    return [Project(**p) for p in config.get("projects", [])]


def save_registry(projects: list[Project], path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    config = load_config(path)
    config["projects"] = [p.model_dump() for p in projects]
    path.write_text(json.dumps(config, indent=2) + "\n")


def add_project(project: Project, path) -> None:
    projects = [p for p in load_registry(path) if p.identifier != project.identifier]
    projects.append(project)
    save_registry(projects, path)


def remove_project(name, path) -> bool:
    projects = load_registry(path)
    filtered = [p for p in projects if p.name != name]
    if len(filtered) == len(projects):
        return False
    save_registry(filtered, path)
    return True


def find_project_by_name(name, path) -> Project | None:
    for p in load_registry(path):
        if p.name == name:
            return p
    return None


def find_project_by_identifier(identifier, path) -> Project | None:
    for p in load_registry(path):
        if p.identifier == identifier:
            return p
    return None
