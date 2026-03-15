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
def runner():
    return CliRunner()


class TestCreateCommand:
    """'beans create' creates a bean and prints it."""

    def test_create_outputs_bean_title(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "create", "Fix auth"])
        assert result.exit_code == 0
        assert "Fix auth" in result.output

    def test_create_with_json_flag(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "Fix auth"
        assert data["status"] == "open"


class TestListCommand:
    """'beans list' lists all beans."""

    def test_list_empty(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "list"])
        assert result.exit_code == 0

    def test_list_after_create(self, runner, dbfile):
        runner.invoke(app, ["--db", dbfile, "create", "First"])
        runner.invoke(app, ["--db", dbfile, "create", "Second"])

        result = runner.invoke(app, ["--db", dbfile, "list"])
        assert result.exit_code == 0
        assert "First" in result.output
        assert "Second" in result.output

    def test_list_json_flag(self, runner, dbfile):
        runner.invoke(app, ["--db", dbfile, "create", "Fix auth"])

        result = runner.invoke(app, ["--db", dbfile, "--json", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Fix auth"


class TestShowCommand:
    """'beans show' displays a single bean by id."""

    def test_show_existing_bean(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "show", bean_id])
        assert result.exit_code == 0
        assert "Fix auth" in result.output

    def test_show_json_flag(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "--json", "show", bean_id])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "Fix auth"
        assert data["id"] == bean_id

    def test_show_nonexistent_bean(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "show", "bean-00000000"])
        assert result.exit_code != 0


class TestUpdateCommand:
    """'beans update' updates bean fields."""

    def test_update_title(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Old title"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "--json", "update", bean_id, "--title", "New title"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "New title"

    def test_update_status(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "--json", "update", bean_id, "--status", "in_progress"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "in_progress"

    def test_update_priority(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "--json", "update", bean_id, "--priority", "0"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["priority"] == 0

    def test_update_nonexistent_bean(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "update", "bean-00000000", "--title", "Nope"])
        assert result.exit_code != 0


class TestCloseCommand:
    """'beans close' closes a bean."""

    def test_close_sets_status_closed(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "--json", "close", bean_id])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "closed"
        assert data["closed_at"] is not None

    def test_close_nonexistent_bean(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "close", "bean-00000000"])
        assert result.exit_code != 0


class TestDeleteCommand:
    """'beans delete' deletes a bean."""

    def test_delete_removes_bean(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "delete", bean_id])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", dbfile, "show", bean_id])
        assert result.exit_code != 0

    def test_delete_nonexistent_bean(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "delete", "bean-00000000"])
        assert result.exit_code != 0


class TestDepAddCommand:
    """'beans dep add' adds a dependency between two beans."""

    def test_dep_add(self, runner, dbfile):
        a = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"]).output)
        b = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"]).output)

        result = runner.invoke(app, ["--db", dbfile, "dep", "add", a["id"], b["id"]])
        assert result.exit_code == 0

    def test_dep_add_custom_type(self, runner, dbfile):
        a = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"]).output)
        b = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"]).output)

        result = runner.invoke(app, ["--db", dbfile, "dep", "add", a["id"], b["id"], "--type", "relates"])
        assert result.exit_code == 0

    def test_dep_add_json_output(self, runner, dbfile):
        a = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"]).output)
        b = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"]).output)

        result = runner.invoke(app, ["--db", dbfile, "--json", "dep", "add", a["id"], b["id"]])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["from_id"] == a["id"]
        assert data["to_id"] == b["id"]
        assert data["dep_type"] == "blocks"


class TestDepRemoveCommand:
    """'beans dep remove' removes a dependency between two beans."""

    def test_dep_remove(self, runner, dbfile):
        a = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"]).output)
        b = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"]).output)
        runner.invoke(app, ["--db", dbfile, "dep", "add", a["id"], b["id"]])

        result = runner.invoke(app, ["--db", dbfile, "dep", "remove", a["id"], b["id"]])
        assert result.exit_code == 0

    def test_dep_remove_nonexistent(self, runner, dbfile):
        a = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task A"]).output)
        b = json.loads(runner.invoke(app, ["--db", dbfile, "--json", "create", "Task B"]).output)

        result = runner.invoke(app, ["--db", dbfile, "dep", "remove", a["id"], b["id"]])
        assert result.exit_code != 0


class TestInputValidation:
    """Invalid inputs are rejected with clear errors."""

    def test_update_invalid_status(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "update", bean_id, "--status", "deleted"])
        assert result.exit_code != 0

    def test_update_invalid_priority(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean_id = json.loads(result.output)["id"]

        result = runner.invoke(app, ["--db", dbfile, "update", bean_id, "--priority", "5"])
        assert result.exit_code != 0

    def test_show_invalid_id_format(self, runner, dbfile):
        result = runner.invoke(app, ["--db", dbfile, "show", "not-a-bean-id"])
        assert result.exit_code != 0
