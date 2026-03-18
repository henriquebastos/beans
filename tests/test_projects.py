# Python imports
import json
import sqlite3

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app
from beans.config import load_projects, projects_path, save_projects
from beans.models import Bean, CrossDep
from beans.store import Store


@pytest.fixture()
def projects_dir(tmp_path, monkeypatch):
    d = tmp_path / ".config" / "beans"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    return d


class TestProjectsPath:
    """projects_path() resolves the projects registry file."""

    def test_uses_xdg_config_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom"))
        path = projects_path()
        assert path == tmp_path / "custom" / "beans" / "projects.json"


class TestLoadSaveProjects:
    """load_projects/save_projects manage the project registry."""

    def test_load_returns_empty_dict_when_no_file(self, projects_dir):
        assert load_projects(projects_dir / "projects.json") == {}

    def test_save_and_load(self, projects_dir):
        projects_dir.mkdir(parents=True)
        path = projects_dir / "projects.json"
        save_projects(path, {"myapp": "/path/to/myapp/.beans"})
        assert load_projects(path) == {"myapp": "/path/to/myapp/.beans"}

    def test_save_creates_parent_dirs(self, projects_dir):
        path = projects_dir / "projects.json"
        save_projects(path, {"myapp": "/path/to/myapp/.beans"})
        assert load_projects(path) == {"myapp": "/path/to/myapp/.beans"}


@pytest.fixture()
def dbfile(tmp_path):
    return str(tmp_path / "beans.db")


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


class TestProjectCommands:
    """'beans project' manages the cross-project registry."""

    def test_project_add_and_list(self, dbfile, projects_dir):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "project", "add", "myapp", "--path", "/tmp/myapp/.beans"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", dbfile, "project", "list"])
        assert result.exit_code == 0
        assert "myapp" in result.output

    def test_project_remove(self, dbfile, projects_dir):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "project", "add", "myapp", "--path", "/tmp/myapp/.beans"])
        result = runner.invoke(app, ["--db", dbfile, "project", "remove", "myapp"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", dbfile, "project", "list"])
        assert "myapp" not in result.output

    def test_project_list_empty(self, dbfile, projects_dir):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "project", "list"])
        assert result.exit_code == 0
        assert "No projects registered" in result.output

    def test_project_remove_nonexistent(self, dbfile, projects_dir):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "project", "remove", "nope"])
        assert result.exit_code != 0


class TestCrossDepStore:
    """CrossDepStore manages cross-project dependencies."""

    def test_add_and_list(self, store):
        bean = store.bean.create(Bean(title="Local task"))
        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)
        store.cross_dep.add(dep)

        assert store.cross_dep.list(bean.id) == [dep]

    def test_add_returns_dep(self, store):
        bean = store.bean.create(Bean(title="Local task"))
        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)

        assert store.cross_dep.add(dep) == dep

    def test_remove(self, store):
        bean = store.bean.create(Bean(title="Local task"))
        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)
        store.cross_dep.add(dep)

        assert store.cross_dep.remove("remote", "bean-aabbccdd", bean.id) == 1
        assert store.cross_dep.list(bean.id) == []

    def test_remove_nonexistent(self, store):
        bean = store.bean.create(Bean(title="Local task"))
        assert store.cross_dep.remove("remote", "bean-aabbccdd", bean.id) == 0


class TestCrossDepReady:
    """Ready query considers cross-project blockers."""

    def test_cross_dep_blocks_ready(self, store):
        bean = store.bean.create(Bean(title="Blocked task"))
        assert store.bean.ready() == [bean]

        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)
        store.cross_dep.add(dep)

        assert store.bean.ready() == []

    def test_removing_cross_dep_unblocks(self, store):
        bean = store.bean.create(Bean(title="Task"))
        dep = CrossDep(project="remote", from_id="bean-aabbccdd", to_id=bean.id)
        store.cross_dep.add(dep)
        store.cross_dep.remove("remote", "bean-aabbccdd", bean.id)

        assert store.bean.ready() == [bean]


class TestCrossDepCli:
    """CLI supports cross-project deps via --project flag."""

    def test_dep_add_with_project(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Local task"])
        bean = json.loads(result.output)

        result = runner.invoke(app, [
            "--db", dbfile, "--json", "dep", "add",
            "bean-aabbccdd", bean["id"], "--project", "remote",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["project"] == "remote"
        assert data["from_id"] == "bean-aabbccdd"
        assert data["to_id"] == bean["id"]

    def test_dep_add_with_project_blocks_ready(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Local task"])
        bean = json.loads(result.output)

        runner.invoke(app, [
            "--db", dbfile, "dep", "add",
            "bean-aabbccdd", bean["id"], "--project", "remote",
        ])

        result = runner.invoke(app, ["--db", dbfile, "--json", "ready"])
        data = json.loads(result.output)
        assert data == []

    def test_dep_remove_with_project(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Local task"])
        bean = json.loads(result.output)

        runner.invoke(app, [
            "--db", dbfile, "dep", "add",
            "bean-aabbccdd", bean["id"], "--project", "remote",
        ])
        result = runner.invoke(app, [
            "--db", dbfile, "dep", "remove",
            "bean-aabbccdd", bean["id"], "--project", "remote",
        ])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", dbfile, "--json", "ready"])
        data = json.loads(result.output)
        assert len(data) == 1
