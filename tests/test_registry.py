# Python imports
import json
from pathlib import Path

# Pip imports
import pytest

# Internal imports
from beans.config import (
    Project,
    add_project,
    data_dir,
    find_project_by_identifier,
    find_project_by_name,
    load_registry,
    remove_project,
    save_registry,
)


class TestProject:
    def test_project_fields(self):
        p = Project(name="myblog", identifier="github.com/me/blog", store="/some/path")
        assert p.name == "myblog"
        assert p.identifier == "github.com/me/blog"
        assert p.store == "/some/path"

    def test_project_equality(self):
        p1 = Project(name="myblog", identifier="github.com/me/blog", store="/a")
        p2 = Project(name="myblog", identifier="github.com/me/blog", store="/a")
        assert p1 == p2

    def test_project_serialization(self):
        p = Project(name="myblog", identifier="github.com/me/blog", store="/some/path")
        d = p.model_dump()
        assert d == {"name": "myblog", "identifier": "github.com/me/blog", "store": "/some/path"}
        assert Project(**d) == p


class TestDataDir:
    def test_data_dir_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        result = data_dir()
        assert result == Path.home() / ".local" / "share" / "beans"

    def test_data_dir_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "custom"))
        result = data_dir()
        assert result == tmp_path / "custom" / "beans"


class TestRegistry:
    def test_load_empty_when_no_file(self, tmp_path):
        path = tmp_path / "config.json"
        assert load_registry(path) == []

    def test_load_empty_when_no_projects_key(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"other": "stuff"}))
        assert load_registry(path) == []

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "config.json"
        projects = [
            Project(name="a", identifier="github.com/x/a", store="/store/a"),
            Project(name="b", identifier="/home/user/b", store="/store/b"),
        ]
        save_registry(projects, path)
        assert load_registry(path) == projects

    def test_save_preserves_other_config(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"editor": "vim"}))
        projects = [Project(name="a", identifier="id-a", store="/store/a")]
        save_registry(projects, path)
        data = json.loads(path.read_text())
        assert data["editor"] == "vim"
        assert "projects" in data

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "config.json"
        save_registry([], path)
        assert path.exists()


class TestAddProject:
    def test_add_project(self, tmp_path):
        path = tmp_path / "config.json"
        p = Project(name="myblog", identifier="github.com/me/blog", store="/store/myblog")
        add_project(p, path)
        assert load_registry(path) == [p]

    def test_add_project_replaces_same_identifier(self, tmp_path):
        path = tmp_path / "config.json"
        p1 = Project(name="old", identifier="github.com/me/blog", store="/store/old")
        p2 = Project(name="new", identifier="github.com/me/blog", store="/store/new")
        add_project(p1, path)
        add_project(p2, path)
        result = load_registry(path)
        assert result == [p2]

    def test_add_multiple_projects(self, tmp_path):
        path = tmp_path / "config.json"
        p1 = Project(name="a", identifier="id-a", store="/store/a")
        p2 = Project(name="b", identifier="id-b", store="/store/b")
        add_project(p1, path)
        add_project(p2, path)
        assert load_registry(path) == [p1, p2]


class TestRemoveProject:
    def test_remove_by_name(self, tmp_path):
        path = tmp_path / "config.json"
        p = Project(name="myblog", identifier="id-a", store="/store/a")
        add_project(p, path)
        assert remove_project("myblog", path) is True
        assert load_registry(path) == []

    def test_remove_nonexistent(self, tmp_path):
        path = tmp_path / "config.json"
        assert remove_project("nope", path) is False


class TestFindProject:
    @pytest.fixture()
    def registry(self, tmp_path):
        path = tmp_path / "config.json"
        projects = [
            Project(name="myblog", identifier="github.com/me/blog", store="/store/myblog"),
            Project(name="work-api", identifier="/home/user/work/api", store="/store/work-api"),
        ]
        save_registry(projects, path)
        return path

    def test_find_by_name(self, registry):
        p = find_project_by_name("myblog", registry)
        assert p is not None
        assert p.name == "myblog"

    def test_find_by_name_not_found(self, registry):
        assert find_project_by_name("nope", registry) is None

    def test_find_by_identifier(self, registry):
        p = find_project_by_identifier("github.com/me/blog", registry)
        assert p is not None
        assert p.name == "myblog"

    def test_find_by_identifier_not_found(self, registry):
        assert find_project_by_identifier("nope", registry) is None
