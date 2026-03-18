# Python imports
import json
import sqlite3

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app
from beans.models import Bean, Dep
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


@pytest.fixture()
def dbfile(tmp_path):
    return str(tmp_path / "beans.db")


class TestDepStoreListAll:
    """DepStore.list_all() returns all dependencies."""

    def test_list_all_empty(self, store):
        assert store.dep.list_all() == []

    def test_list_all_returns_all_deps(self, store):
        a = store.bean.create(Bean(title="A"))
        b = store.bean.create(Bean(title="B"))
        c = store.bean.create(Bean(title="C"))
        d1 = store.dep.add(Dep(from_id=a.id, to_id=b.id))
        d2 = store.dep.add(Dep(from_id=b.id, to_id=c.id))

        assert store.dep.list_all() == [d1, d2]


class TestGraphCommand:
    """'beans graph' renders the dependency tree."""

    def test_graph_no_deps(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Task A"])
        runner.invoke(app, ["--db", dbfile, "create", "Task B"])

        result = runner.invoke(app, ["--db", dbfile, "graph"])
        assert result.exit_code == 0
        assert "Task A" in result.output
        assert "Task B" in result.output

    def test_graph_with_deps(self, dbfile):
        runner = CliRunner()
        r1 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"])
        r2 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"])
        a = json.loads(r1.output)
        b = json.loads(r2.output)
        runner.invoke(app, ["--db", dbfile, "dep", "add", a["id"], b["id"]])

        result = runner.invoke(app, ["--db", dbfile, "graph"])
        assert result.exit_code == 0
        assert "Task A" in result.output
        assert "Task B" in result.output

    def test_graph_with_parent_child(self, dbfile):
        runner = CliRunner()
        r1 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Parent"])
        parent = json.loads(r1.output)
        runner.invoke(app, ["--db", dbfile, "create", "Child", "--parent", parent["id"]])

        result = runner.invoke(app, ["--db", dbfile, "graph"])
        assert result.exit_code == 0
        assert "Parent" in result.output
        assert "Child" in result.output

    def test_graph_json_output(self, dbfile):
        runner = CliRunner()
        r1 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"])
        r2 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"])
        a = json.loads(r1.output)
        b = json.loads(r2.output)
        runner.invoke(app, ["--db", dbfile, "dep", "add", a["id"], b["id"]])

        result = runner.invoke(app, ["--db", dbfile, "--json", "graph"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "nodes" in data
        assert "edges" in data

    def test_graph_empty(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "graph"])
        assert result.exit_code == 0

    def test_graph_shows_status(self, dbfile):
        runner = CliRunner()
        r1 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Done"])
        bean = json.loads(r1.output)
        runner.invoke(app, ["--db", dbfile, "close", bean["id"]])

        result = runner.invoke(app, ["--db", dbfile, "graph"])
        assert result.exit_code == 0
        assert "closed" in result.output
