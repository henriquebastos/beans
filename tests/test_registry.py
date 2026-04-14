# Python imports
from pathlib import Path

# Pip imports
import pytest

# Internal imports
from beans.config import Config, Project, data_dir


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


class TestConfig:
    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "config.json"
        cfg = Config(path=path, projects=[
            Project(name="a", identifier="github.com/x/a", store="/store/a"),
            Project(name="b", identifier="/home/user/b", store="/store/b"),
        ])
        cfg.save()
        loaded = Config.load(path)
        assert loaded.projects == cfg.projects

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "config.json"
        Config(path=path).save()
        assert path.exists()

    def test_path_excluded_from_json(self, tmp_path):
        path = tmp_path / "config.json"
        cfg = Config(path=path)
        cfg.save()
        assert "path" not in path.read_text()


class TestAddProject:
    def test_add_project(self):
        cfg = Config(path=Path("/tmp/c.json"))
        p = Project(name="myblog", identifier="github.com/me/blog", store="/store/myblog")
        cfg.add_project(p)
        assert cfg.projects == [p]

    def test_add_project_replaces_same_identifier(self):
        cfg = Config(path=Path("/tmp/c.json"))
        p1 = Project(name="old", identifier="github.com/me/blog", store="/store/old")
        p2 = Project(name="new", identifier="github.com/me/blog", store="/store/new")
        cfg.add_project(p1)
        cfg.add_project(p2)
        assert cfg.projects == [p2]

    def test_add_multiple_projects(self):
        cfg = Config(path=Path("/tmp/c.json"))
        p1 = Project(name="a", identifier="id-a", store="/store/a")
        p2 = Project(name="b", identifier="id-b", store="/store/b")
        cfg.add_project(p1)
        cfg.add_project(p2)
        assert cfg.projects == [p1, p2]


class TestRemoveProject:
    def test_remove_by_name(self):
        cfg = Config(path=Path("/tmp/c.json"))
        p = Project(name="myblog", identifier="id-a", store="/store/a")
        cfg.add_project(p)
        assert cfg.remove_project("myblog") is True
        assert cfg.projects == []

    def test_remove_nonexistent(self):
        cfg = Config(path=Path("/tmp/c.json"))
        assert cfg.remove_project("nope") is False


class TestFindProject:
    @pytest.fixture()
    def cfg(self):
        return Config(path=Path("/tmp/c.json"), projects=[
            Project(name="myblog", identifier="github.com/me/blog", store="/store/myblog"),
            Project(name="work-api", identifier="/home/user/work/api", store="/store/work-api"),
        ])

    def test_find_by_name(self, cfg):
        p = cfg.find_by_name("myblog")
        assert p is not None
        assert p.name == "myblog"

    def test_find_by_name_not_found(self, cfg):
        assert cfg.find_by_name("nope") is None

    def test_find_by_identifier(self, cfg):
        p = cfg.find_by_identifier("github.com/me/blog")
        assert p is not None
        assert p.name == "myblog"

    def test_find_by_identifier_not_found(self, cfg):
        assert cfg.find_by_identifier("nope") is None
