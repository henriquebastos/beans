# Python imports
import json
import os
from pathlib import Path
from typing import Self

# Pip imports
from pydantic import BaseModel, Field

CONFIG_DIR = "beans"
CONFIG_FILE = "config.json"
DATA_DIR = "beans"
DEFAULT_XDG_CONFIG = ".config"
DEFAULT_XDG_DATA = ".local/share"


class Project(BaseModel, frozen=True):
    name: str
    identifier: str
    store: str


class Config(BaseModel):
    path: Path = Field(exclude=True)
    projects: list[Project] = []

    @classmethod
    def load(cls, path) -> Self:
        path = Path(path)
        data = json.loads(path.read_text())
        return cls(path=path, **data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.model_dump_json(indent=2) + "\n")

    def add_project(self, project: Project) -> None:
        self.projects = [p for p in self.projects if p.identifier != project.identifier]
        self.projects.append(project)

    def remove_project(self, name) -> bool:
        before = len(self.projects)
        self.projects = [p for p in self.projects if p.name != name]
        return len(self.projects) < before

    def find_by_name(self, name) -> Project | None:
        for p in self.projects:
            if p.name == name:
                return p
        return None

    def find_by_identifier(self, identifier) -> Project | None:
        for p in self.projects:
            if p.identifier == identifier:
                return p
        return None


def config_dir(config_dir_name=CONFIG_DIR, default_xdg=DEFAULT_XDG_CONFIG) -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", Path.home() / default_xdg)
    return Path(xdg) / config_dir_name


def config_path(config_file=CONFIG_FILE, base=None) -> Path:
    return (base or config_dir()) / config_file


def data_dir(data_dir_name=DATA_DIR, default_xdg=DEFAULT_XDG_DATA) -> Path:
    xdg = os.environ.get("XDG_DATA_HOME", Path.home() / default_xdg)
    return Path(xdg) / data_dir_name
