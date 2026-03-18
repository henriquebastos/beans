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


class TestBeanStoreSearch:
    """BeanStore.search() finds beans by title and body."""

    def test_search_by_title(self, store):
        store.bean.create(Bean(title="Fix authentication bug"))
        store.bean.create(Bean(title="Add logging"))

        results = store.bean.search("auth")
        assert len(results) == 1
        assert results[0].title == "Fix authentication bug"

    def test_search_by_body(self, store):
        store.bean.create(Bean(title="Task A", body="Check the database connection"))
        store.bean.create(Bean(title="Task B", body="Update the README"))

        results = store.bean.search("database")
        assert len(results) == 1
        assert results[0].title == "Task A"

    def test_search_case_insensitive(self, store):
        store.bean.create(Bean(title="Fix Auth"))

        assert len(store.bean.search("fix auth")) == 1
        assert len(store.bean.search("FIX AUTH")) == 1

    def test_search_no_results(self, store):
        store.bean.create(Bean(title="Fix auth"))

        assert store.bean.search("deploy") == []

    def test_search_empty_query_returns_all(self, store):
        bean = store.bean.create(Bean(title="Fix auth"))

        assert store.bean.search("") == [bean]

    def test_search_multiple_matches(self, store):
        store.bean.create(Bean(title="Fix auth login"))
        store.bean.create(Bean(title="Fix auth signup"))
        store.bean.create(Bean(title="Add tests"))

        results = store.bean.search("auth")
        assert len(results) == 2


class TestSearchCommand:
    """'beans search <query>' finds matching beans."""

    def test_search_returns_matches(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Fix auth"])
        runner.invoke(app, ["--db", dbfile, "create", "Add logging"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "search", "auth"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["title"] == "Fix auth"

    def test_search_no_matches(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Fix auth"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "search", "deploy"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []
