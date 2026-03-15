# Python imports
import json

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app


@pytest.fixture()
def beans_dir(tmp_path):
    d = tmp_path / ".beans"
    d.mkdir()
    return d


@pytest.fixture()
def runner():
    return CliRunner()


class TestCreateCommand:
    """'beans create' creates a bean and prints it."""

    def test_create_outputs_bean_title(self, runner, beans_dir):
        result = runner.invoke(app, ["--db", str(beans_dir / "beans.db"), "create", "Fix auth"])
        assert result.exit_code == 0
        assert "Fix auth" in result.output

    def test_create_with_json_flag(self, runner, beans_dir):
        result = runner.invoke(app, ["--db", str(beans_dir / "beans.db"), "--json", "create", "Fix auth"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "Fix auth"
        assert data["status"] == "open"


class TestListCommand:
    """'beans list' lists all beans."""

    def test_list_empty(self, runner, beans_dir):
        result = runner.invoke(app, ["--db", str(beans_dir / "beans.db"), "list"])
        assert result.exit_code == 0

    def test_list_after_create(self, runner, beans_dir):
        db = str(beans_dir / "beans.db")
        runner.invoke(app, ["--db", db, "create", "First"])
        runner.invoke(app, ["--db", db, "create", "Second"])

        result = runner.invoke(app, ["--db", db, "list"])
        assert result.exit_code == 0
        assert "First" in result.output
        assert "Second" in result.output

    def test_list_json_flag(self, runner, beans_dir):
        db = str(beans_dir / "beans.db")
        runner.invoke(app, ["--db", db, "create", "Fix auth"])

        result = runner.invoke(app, ["--db", db, "--json", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Fix auth"
