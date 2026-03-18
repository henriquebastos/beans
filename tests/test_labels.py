# Python imports
import json
import sqlite3

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app
from beans.models import Bean, Label
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


@pytest.fixture()
def dbfile(tmp_path):
    return str(tmp_path / "beans.db")


class TestLabelStore:
    """LabelStore manages labels on beans."""

    def test_add_label(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        label = store.label.add(bean.id, "urgent")
        assert label == Label(bean_id=bean.id, label="urgent")

    def test_list_labels(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.label.add(bean.id, "urgent")
        store.label.add(bean.id, "backend")

        labels = store.label.list(bean.id)
        assert labels == [Label(bean_id=bean.id, label="backend"), Label(bean_id=bean.id, label="urgent")]

    def test_remove_label(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        store.label.add(bean.id, "urgent")
        assert store.label.remove(bean.id, "urgent") == 1
        assert store.label.list(bean.id) == []

    def test_remove_nonexistent_label(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        assert store.label.remove(bean.id, "nope") == 0

    def test_list_empty(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))
        assert store.label.list(bean.id) == []

    def test_beans_by_label(self, store):
        a = store.bean.create(Bean(title="Task A"))
        b = store.bean.create(Bean(title="Task B"))
        store.bean.create(Bean(title="Task C"))
        store.label.add(a.id, "urgent")
        store.label.add(b.id, "urgent")

        beans = store.label.beans_by_label("urgent")
        assert len(beans) == 2
        assert {b.id for b in beans} == {a.id, b.id}


class TestLabelCommands:
    """'beans label' subcommands manage labels."""

    def test_label_add(self, dbfile):
        runner = CliRunner()
        r = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean = json.loads(r.output)

        result = runner.invoke(app, ["--db", dbfile, "--json", "label", "add", bean["id"], "urgent"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["label"] == "urgent"

    def test_label_remove(self, dbfile):
        runner = CliRunner()
        r = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean = json.loads(r.output)
        runner.invoke(app, ["--db", dbfile, "label", "add", bean["id"], "urgent"])

        result = runner.invoke(app, ["--db", dbfile, "label", "remove", bean["id"], "urgent"])
        assert result.exit_code == 0

    def test_label_list(self, dbfile):
        runner = CliRunner()
        r = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean = json.loads(r.output)
        runner.invoke(app, ["--db", dbfile, "label", "add", bean["id"], "urgent"])
        runner.invoke(app, ["--db", dbfile, "label", "add", bean["id"], "backend"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "label", "list", bean["id"]])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_list_filter_by_label(self, dbfile):
        runner = CliRunner()
        r1 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"])
        r2 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"])
        a = json.loads(r1.output)
        json.loads(r2.output)
        runner.invoke(app, ["--db", dbfile, "label", "add", a["id"], "urgent"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "--label", "urgent", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["title"] == "Task A"

    def test_ready_filter_by_label(self, dbfile):
        runner = CliRunner()
        r1 = runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"])
        runner.invoke(app, ["--db", dbfile, "create", "Task B"])
        a = json.loads(r1.output)
        runner.invoke(app, ["--db", dbfile, "label", "add", a["id"], "urgent"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "--label", "urgent", "ready"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["title"] == "Task A"
