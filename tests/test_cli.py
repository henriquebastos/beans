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

    def test_create_with_body(self, invoke_agent):
        exit_code, data = invoke_agent("create", "Fix auth", "--body", "Detailed description")
        assert exit_code == 0
        assert data["body"] == "Detailed description"

    def test_create_without_body_defaults_empty(self, invoke_agent):
        exit_code, data = invoke_agent("create", "Fix auth")
        assert exit_code == 0
        assert data["body"] == ""

    def test_create_with_type(self, invoke_agent):
        exit_code, data = invoke_agent("create", "Design review", "--type", "epic")
        assert exit_code == 0
        assert data["type"] == "epic"

    def test_create_without_type_defaults_task(self, invoke_agent):
        exit_code, data = invoke_agent("create", "Fix auth")
        assert exit_code == 0
        assert data["type"] == "task"


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

    def test_update_parent(self, invoke_agent):
        _, parent = invoke_agent("create", "Parent")
        _, child = invoke_agent("create", "Child")

        exit_code, data = invoke_agent("update", child["id"], "--parent", parent["id"])
        assert exit_code == 0
        assert data["parent_id"] == parent["id"]

    def test_update_body(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("update", created["id"], "--body", "Detailed description")
        assert exit_code == 0
        assert data["body"] == "Detailed description"

    def test_update_type(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("update", created["id"], "--type", "bug")
        assert exit_code == 0
        assert data["type"] == "bug"

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

    def test_close_with_reason(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("close", created["id"], "--reason", "Completed in PR #42")
        assert exit_code == 0
        assert data["status"] == "closed"
        assert data["close_reason"] == "Completed in PR #42"

    def test_close_without_reason_defaults_none(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("close", created["id"])
        assert exit_code == 0
        assert data["close_reason"] is None

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


class TestClaimCommand:
    """'beans claim' atomically claims a bean."""

    def test_claim_sets_assignee(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("claim", created["id"], "--actor", "alice")
        assert exit_code == 0
        assert data["assignee"] == "alice"
        assert data["status"] == "in_progress"

    def test_claim_already_claimed(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")
        invoke_agent("claim", created["id"], "--actor", "alice")

        exit_code, _ = invoke_agent("claim", created["id"], "--actor", "bob")
        assert exit_code != 0


class TestReleaseCommand:
    """'beans release' releases a claimed bean."""

    def test_release_clears_assignee(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")
        invoke_agent("claim", created["id"], "--actor", "alice")

        exit_code, data = invoke_agent("release", created["id"], "--actor", "alice")
        assert exit_code == 0
        assert data["assignee"] is None
        assert data["status"] == "open"

    def test_release_unclaimed_is_idempotent(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("release", created["id"], "--actor", "alice")
        assert exit_code == 0
        assert data["assignee"] is None

    def test_release_by_different_actor(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")
        invoke_agent("claim", created["id"], "--actor", "alice")

        exit_code, _ = invoke_agent("release", created["id"], "--actor", "bob")
        assert exit_code != 0

    def test_release_mine(self, invoke_agent):
        _, a = invoke_agent("create", "Task A")
        _, b = invoke_agent("create", "Task B")
        invoke_agent("claim", a["id"], "--actor", "alice")
        invoke_agent("claim", b["id"], "--actor", "alice")

        exit_code, data = invoke_agent("release", "--mine", "--actor", "alice")
        assert exit_code == 0
        assert len(data) == 2

    def test_release_mine_empty(self, invoke_agent):
        exit_code, data = invoke_agent("release", "--mine", "--actor", "alice")
        assert exit_code == 0
        assert data == []

    def test_release_both_id_and_mine_is_error(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")
        exit_code, _ = invoke_agent("release", created["id"], "--mine", "--actor", "alice")
        assert exit_code != 0


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


class TestDryRunMode:
    """'--dry-run' shows what would happen without writing."""

    def test_dry_run_create_shows_bean_but_does_not_persist(self, invoke_agent):
        exit_code, data = invoke_agent("--dry-run", "create", "Fix auth")
        assert exit_code == 0
        assert data["title"] == "Fix auth"

        _, beans = invoke_agent("list")
        assert beans == []

    def test_dry_run_update_shows_change_but_does_not_persist(self, invoke_agent):
        _, created = invoke_agent("create", "Old title")

        exit_code, data = invoke_agent("--dry-run", "update", created["id"], "--title", "New title")
        assert exit_code == 0
        assert data["title"] == "New title"

        _, bean = invoke_agent("show", created["id"])
        assert bean["title"] == "Old title"

    def test_dry_run_delete_does_not_persist(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, _ = invoke_agent("--dry-run", "delete", created["id"])
        assert exit_code == 0

        _, bean = invoke_agent("show", created["id"])
        assert bean["title"] == "Fix auth"

    def test_dry_run_close_does_not_persist(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("--dry-run", "close", created["id"])
        assert exit_code == 0
        assert data["status"] == "closed"

        _, bean = invoke_agent("show", created["id"])
        assert bean["status"] == "open"

    def test_dry_run_claim_does_not_persist(self, invoke_agent):
        _, created = invoke_agent("create", "Fix auth")

        exit_code, data = invoke_agent("--dry-run", "claim", created["id"], "--actor", "alice")
        assert exit_code == 0
        assert data["assignee"] == "alice"

        _, bean = invoke_agent("show", created["id"])
        assert bean["assignee"] is None

    def test_dry_run_rebuild_does_not_persist(self, dbfile, tmp_path):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])

        result = runner.invoke(app, ["--db", dbfile, "export-journal"])
        journal_file = str(tmp_path / "journal.jsonl")
        with open(journal_file, "w") as f:
            f.write(result.output)

        target_db = str(tmp_path / "target.db")
        result = runner.invoke(app, ["--db", target_db, "--dry-run", "rebuild", journal_file])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", target_db, "--json", "list"])
        data = json.loads(result.output)
        assert data == []


class TestSchemaCommand:
    """'beans schema' outputs JSON schemas for all models."""

    def test_schema_includes_all_models(self, invoke_agent):
        exit_code, data = invoke_agent("schema")
        assert exit_code == 0
        assert "Bean" in data
        assert "Dep" in data
        assert "Error" in data

    def test_schema_bean_has_properties(self, invoke_agent):
        exit_code, data = invoke_agent("schema")
        assert exit_code == 0
        assert "properties" in data["Bean"]
        assert "id" in data["Bean"]["properties"]
        assert "title" in data["Bean"]["properties"]


class TestJsonErrorOutput:
    """Errors in --json mode return structured JSON."""

    def test_show_nonexistent_returns_json_error(self, invoke_agent):
        exit_code, data = invoke_agent("show", "bean-00000000")
        assert exit_code != 0
        assert "message" in data

    def test_update_nonexistent_returns_json_error(self, invoke_agent):
        exit_code, data = invoke_agent("update", "bean-00000000", "--title", "Nope")
        assert exit_code != 0
        assert "message" in data


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


class TestExportJournalCommand:
    """'beans export-journal' exports journal entries as JSONL."""

    def test_export_empty(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "export-journal"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_export_after_create(self, dbfile):
        runner = CliRunner()
        runner.invoke(app, ["--db", dbfile, "create", "Fix auth"])

        result = runner.invoke(app, ["--db", dbfile, "export-journal"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["action"] == "create"

    def test_export_crud_cycle(self, dbfile):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean = json.loads(result.output)

        runner.invoke(app, ["--db", dbfile, "update", bean["id"], "--title", "Updated"])
        runner.invoke(app, ["--db", dbfile, "delete", bean["id"]])

        result = runner.invoke(app, ["--db", dbfile, "export-journal"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 3
        actions = [json.loads(line)["action"] for line in lines]
        assert actions == ["create", "update", "delete"]


class TestRebuildCommand:
    """'beans rebuild' rebuilds a database from a JSONL file."""

    def test_rebuild_from_journal(self, dbfile, tmp_path):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean = json.loads(result.output)

        journal_file = str(tmp_path / "journal.jsonl")
        result = runner.invoke(app, ["--db", dbfile, "export-journal"])
        with open(journal_file, "w") as f:
            f.write(result.output)

        target_db = str(tmp_path / "rebuilt.db")
        result = runner.invoke(app, ["--db", target_db, "rebuild", journal_file])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", target_db, "--json", "list"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["id"] == bean["id"]
        assert data[0]["title"] == "Fix auth"

    def test_rebuild_with_updates(self, dbfile, tmp_path):
        runner = CliRunner()
        result = runner.invoke(app, ["--db", dbfile, "--json", "create", "Fix auth"])
        bean = json.loads(result.output)
        runner.invoke(app, ["--db", dbfile, "update", bean["id"], "--title", "Updated"])

        journal_file = str(tmp_path / "journal.jsonl")
        result = runner.invoke(app, ["--db", dbfile, "export-journal"])
        with open(journal_file, "w") as f:
            f.write(result.output)

        target_db = str(tmp_path / "rebuilt.db")
        result = runner.invoke(app, ["--db", target_db, "rebuild", journal_file])
        assert result.exit_code == 0

        result = runner.invoke(app, ["--db", target_db, "--json", "show", bean["id"]])
        data = json.loads(result.output)
        assert data["title"] == "Updated"
