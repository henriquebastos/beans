# Python imports
import json
import sqlite3

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app
from beans.models import Bean
from beans.store import Store


@pytest.fixture()
def store():
    with Store(sqlite3.connect(":memory:")) as s:
        yield s


@pytest.fixture()
def dbfile(tmp_path):
    return str(tmp_path / "beans.db")


class TestBeanStoreStats:
    """BeanStore.stats() returns aggregate counts."""

    def test_stats_empty_store(self, store):
        result = store.bean.stats()
        assert result == {"by_status": {}, "by_type": {}, "by_assignee": {}}

    def test_stats_by_status(self, store):
        store.bean.create(Bean(title="A"))
        store.bean.create(Bean(title="B", status="in_progress"))
        store.bean.create(Bean(title="C", status="closed"))
        store.bean.create(Bean(title="D"))

        result = store.bean.stats()
        assert result["by_status"] == {"open": 2, "in_progress": 1, "closed": 1}

    def test_stats_by_type(self, store):
        store.bean.create(Bean(title="A"))
        store.bean.create(Bean(title="B", type="bug"))
        store.bean.create(Bean(title="C", type="epic"))
        store.bean.create(Bean(title="D"))

        result = store.bean.stats()
        assert result["by_type"] == {"task": 2, "bug": 1, "epic": 1}

    def test_stats_by_assignee(self, store):
        store.bean.create(Bean(title="A", assignee="alice"))
        store.bean.create(Bean(title="B", assignee="bob"))
        store.bean.create(Bean(title="C", assignee="alice"))
        store.bean.create(Bean(title="D"))

        result = store.bean.stats()
        assert result["by_assignee"] == {"alice": 2, "bob": 1, "unassigned": 1}


class TestStatsCommand:
    """'beans stats' outputs aggregate counts."""

    def test_stats_json_output(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Task A"])
        runner.invoke(app, ["--db", dbfile, "create", "Task B", "--type", "bug"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "stats"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["by_status"] == {"open": 2}
        assert data["by_type"] == {"task": 1, "bug": 1}

    def test_stats_human_output(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Task A"])
        runner.invoke(app, ["--db", dbfile, "create", "Task B", "--type", "bug"])

        result = runner.invoke(app, ["--db", dbfile, "stats"])
        assert result.exit_code == 0
        assert "Status" in result.output
        assert "Type" in result.output
        assert "open" in result.output

    def test_stats_empty(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "stats"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == {"by_status": {}, "by_type": {}, "by_assignee": {}}
