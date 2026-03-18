# Python imports
import json

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app


@pytest.fixture()
def dbfile(tmp_path):
    return str(tmp_path / "beans.db")


@pytest.fixture()
def invoke(dbfile):
    runner = CliRunner()

    def run(*args):
        result = runner.invoke(app, ["--db", dbfile, "--json", *args])
        data = json.loads(result.output) if result.output.strip() else None
        return result.exit_code, data

    return run


class TestFieldFiltering:
    """'--fields' limits output columns for bean commands."""

    def test_show_with_fields(self, invoke):
        _, created = invoke("create", "Fix auth")

        exit_code, data = invoke("--fields", "id,title", "show", created["id"])
        assert exit_code == 0
        assert set(data.keys()) == {"id", "title"}
        assert data["title"] == "Fix auth"

    def test_list_with_fields(self, invoke):
        invoke("create", "Task A")
        invoke("create", "Task B")

        exit_code, data = invoke("--fields", "id,title,status", "list")
        assert exit_code == 0
        assert len(data) == 2
        assert set(data[0].keys()) == {"id", "title", "status"}

    def test_ready_with_fields(self, invoke):
        invoke("create", "Task A")

        exit_code, data = invoke("--fields", "id,title", "ready")
        assert exit_code == 0
        assert len(data) == 1
        assert set(data[0].keys()) == {"id", "title"}

    def test_search_with_fields(self, invoke):
        invoke("create", "Fix auth")

        exit_code, data = invoke("--fields", "id,title", "search", "auth")
        assert exit_code == 0
        assert len(data) == 1
        assert set(data[0].keys()) == {"id", "title"}

    def test_fields_without_flag_returns_all(self, invoke):
        _, created = invoke("create", "Fix auth")

        exit_code, data = invoke("show", created["id"])
        assert exit_code == 0
        assert "id" in data
        assert "title" in data
        assert "status" in data
        assert "created_at" in data

    def test_fields_ignored_without_json(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Fix auth"])

        result = runner.invoke(app, ["--db", dbfile, "--fields", "id,title", "list"])
        assert result.exit_code == 0
        assert "Fix auth" in result.output
        assert "{" not in result.output
