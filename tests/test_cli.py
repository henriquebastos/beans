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
def invoke_agent(dbfile):
    runner = CliRunner()

    def invoke(*args):
        result = runner.invoke(app, ["--db", dbfile, "--json", *args])
        if result.exit_code != 0:
            return result.exit_code, None
        data = json.loads(result.output) if result.output.strip() else None
        return result.exit_code, data

    return invoke


@pytest.fixture()
def invoke_human(dbfile):
    runner = CliRunner()

    def invoke(*args):
        result = runner.invoke(app, ["--db", dbfile, *args])
        return result.exit_code

    return invoke


class TestCreateCommand:
    """'beans create' creates a bean and prints it."""

    def test_create_returns_bean(self, invoke_agent):
        exit_code, data = invoke_agent("create", "Fix auth")
        assert exit_code == 0
        assert data["title"] == "Fix auth"
        assert data["status"] == "open"


class TestListCommand:
    """'beans list' lists all beans."""

    def test_list_empty(self, invoke_agent):
        exit_code, data = invoke_agent("list")
        assert exit_code == 0
        assert data == []

    def test_list_after_create(self, invoke_agent):
        invoke_agent("create", "First")
        invoke_agent("create", "Second")

        exit_code, data = invoke_agent("list")
        assert exit_code == 0
        assert len(data) == 2
        assert data[0]["title"] == "First"
        assert data[1]["title"] == "Second"


class TestShowCommand:
    """'beans show' displays a single bean by id."""

    def test_show_existing_bean(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("show", created["id"])
        assert exit_code == 0
        assert data["title"] == "Fix auth"
        assert data["id"] == created["id"]

    def test_show_nonexistent_bean(self, invoke_human):
        assert invoke_human("show", "bean-00000000") != 0


class TestUpdateCommand:
    """'beans update' updates bean fields."""

    def test_update_title(self, invoke_agent):
        _, created = invoke_agent("create", "Old title")

        exit_code, data = invoke_agent("update", created["id"], "--title", "New title")
        assert exit_code == 0
        assert data["title"] == "New title"

    def test_update_status(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("update", created["id"], "--status", "in_progress")
        assert exit_code == 0
        assert data["status"] == "in_progress"

    def test_update_priority(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("update", created["id"], "--priority", "0")
        assert exit_code == 0
        assert data["priority"] == 0

    def test_update_nonexistent_bean(self, invoke_human):
        assert invoke_human("update", "bean-00000000", "--title", "Nope") != 0


class TestCloseCommand:
    """'beans close' closes a bean."""

    def test_close_sets_status_closed(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("close", created["id"])
        assert exit_code == 0
        assert data["status"] == "closed"
        assert data["closed_at"] is not None

    def test_close_nonexistent_bean(self, invoke_human):
        assert invoke_human("close", "bean-00000000") != 0


class TestDeleteCommand:
    """'beans delete' deletes a bean."""

    def test_delete_removes_bean(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, _ = invoke_agent("delete", created["id"])
        assert exit_code == 0

        exit_code, _ = invoke_agent("show", created["id"])
        assert exit_code != 0

    def test_delete_nonexistent_bean(self, invoke_human):
        assert invoke_human("delete", "bean-00000000") != 0


class TestCreateWithParent:
    """'beans create --parent' sets parent_id on the new bean."""

    def test_create_with_parent(self, invoke_agent):
        _, parent = invoke_agent("create", "Parent")

        exit_code, data = invoke_agent("create", "Child", "--parent", parent["id"])
        assert exit_code == 0
        assert data["parent_id"] == parent["id"]

    def test_create_without_parent(self, invoke_agent):
        _, data = invoke_agent("create", "No parent")
        assert data["parent_id"] is None


class TestReadyCommand:
    """'beans ready' lists only unblocked beans."""

    def test_ready_no_deps(self, invoke_agent):
        invoke_agent("create", "Task A")
        invoke_agent("create", "Task B")

        exit_code, data = invoke_agent("ready")
        assert exit_code == 0
        assert len(data) == 2

    def test_ready_excludes_blocked(self, invoke_agent):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")
        invoke_agent("dep", "add", a["id"], b["id"])

        exit_code, data = invoke_agent("ready")
        assert exit_code == 0
        assert len(data) == 1
        assert data[0]["title"] == "Task A"


class TestDepAddCommand:
    """'beans dep add' adds a dependency between two beans."""

    def test_dep_add(self, invoke_agent):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")

        exit_code, data = invoke_agent("dep", "add", a["id"], b["id"])
        assert exit_code == 0
        assert data["from_id"] == a["id"]
        assert data["to_id"] == b["id"]
        assert data["dep_type"] == "blocks"

    def test_dep_add_custom_type(self, invoke_agent):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")

        exit_code, data = invoke_agent("dep", "add", a["id"], b["id"], "--type", "relates")
        assert exit_code == 0
        assert data["dep_type"] == "relates"


class TestDepRemoveCommand:
    """'beans dep remove' removes a dependency between two beans."""

    def test_dep_remove(self, invoke_agent):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")
        invoke_agent("dep", "add", a["id"], b["id"])

        exit_code, _ = invoke_agent("dep", "remove", a["id"], b["id"])
        assert exit_code == 0

    def test_dep_remove_nonexistent(self, invoke_human):
        assert invoke_human("dep", "remove", "bean-aaaaaaaa", "bean-bbbbbbbb") != 0


class TestHumanOutput:
    """Text-mode output works for human consumption."""

    def test_list_outputs_beans(self, invoke_agent, invoke_human):
        invoke_agent("create", "Task A")
        assert invoke_human("list") == 0

    def test_show_outputs_bean(self, invoke_agent, invoke_human):
        _, data = invoke_agent("create", "Fix auth")
        assert invoke_human("show", data["id"]) == 0

    def test_delete_outputs_message(self, invoke_agent, invoke_human):
        _, data = invoke_agent("create", "Fix auth")
        assert invoke_human("delete", data["id"]) == 0

    def test_dep_add_outputs_edge(self, invoke_agent, invoke_human):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")
        assert invoke_human("dep", "add", a["id"], b["id"]) == 0

    def test_dep_remove_outputs_message(self, invoke_agent, invoke_human):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")
        invoke_agent("dep", "add", a["id"], b["id"])
        assert invoke_human("dep", "remove", a["id"], b["id"]) == 0


class TestInputValidation:
    """Invalid inputs are rejected with clear errors."""

    def test_update_invalid_status(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")
        exit_code, _ = invoke_agent("update", created["id"], "--status", "deleted")
        assert exit_code != 0

    def test_update_invalid_priority(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")
        exit_code, _ = invoke_agent("update", created["id"], "--priority", "5")
        assert exit_code != 0

    def test_show_invalid_id_format(self, invoke_human):
        assert invoke_human("show", "not-a-bean-id") != 0
