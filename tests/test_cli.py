# Python imports
import json
import shlex

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app


@pytest.fixture()
def dbfile(tmp_path):
    return str(tmp_path / "beans.db")


@pytest.fixture()
def cli(dbfile):
    runner = CliRunner()

    def invoke(cmd):
        result = runner.invoke(app, ["--db", dbfile, *shlex.split(cmd)])
        return result.exit_code, result.output

    return invoke


@pytest.fixture()
def jcli(cli):
    def invoke(cmd):
        exit_code, output = cli(cmd)
        data = json.loads(output) if output.strip() else None
        return exit_code, data

    return invoke


class TestCommandWiring:
    """Each command routes through api.py and returns exit code 0."""

    def test_create(self, jcli):
        exit_code, data = jcli('--json create "Fix auth"')
        assert exit_code == 0
        assert data["title"] == "Fix auth"

    def test_show(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, data = jcli(f"--json show {created['id']}")
        assert exit_code == 0
        assert data["id"] == created["id"]

    def test_update(self, jcli):
        _, created = jcli('--json create "Old title"')
        exit_code, data = jcli(f'--json update {created["id"]} --title "New title"')
        assert exit_code == 0
        assert data["title"] == "New title"

    def test_close(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, data = jcli(f"--json close {created['id']}")
        assert exit_code == 0
        assert data["status"] == "closed"

    def test_delete(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = jcli(f"--json delete {created['id']}")
        assert exit_code == 0

    def test_list(self, jcli):
        jcli('--json create "Task A"')
        exit_code, data = jcli("--json list")
        assert exit_code == 0
        assert len(data) == 1

    def test_ready(self, jcli):
        jcli('--json create "Task A"')
        exit_code, data = jcli("--json ready")
        assert exit_code == 0
        assert len(data) == 1

    def test_claim(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, data = jcli(f"--json claim {created['id']} --actor alice")
        assert exit_code == 0
        assert data["assignee"] == "alice"

    def test_release(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        jcli(f"--json claim {created['id']} --actor alice")
        exit_code, data = jcli(f"--json release {created['id']} --actor alice")
        assert exit_code == 0
        assert data["assignee"] is None

    def test_search(self, jcli):
        jcli('--json create "Fix auth bug"')
        exit_code, data = jcli("--json search auth")
        assert exit_code == 0
        assert len(data) == 1

    def test_create_with_priority(self, jcli):
        exit_code, data = jcli('--json create "Urgent" --priority 0')
        assert exit_code == 0
        assert data["priority"] == 0

    def test_create_default_priority(self, jcli):
        exit_code, data = jcli('--json create "Normal"')
        assert exit_code == 0
        assert data["priority"] == 2

    def test_create_invalid_priority(self, cli):
        exit_code, _ = cli('create "Bad" --priority 5')
        assert exit_code != 0

    def test_search_no_matches(self, jcli):
        jcli('--json create "Fix auth"')
        exit_code, data = jcli("--json search deploy")
        assert exit_code == 0
        assert data == []

    def test_dep_add(self, jcli):
        _, a = jcli('--json create "Task A"')
        _, b = jcli('--json create "Task B"')
        exit_code, data = jcli(f"--json dep add {a['id']} {b['id']}")
        assert exit_code == 0
        assert data["from_id"] == a["id"]

    def test_dep_remove(self, jcli):
        _, a = jcli('--json create "Task A"')
        _, b = jcli('--json create "Task B"')
        jcli(f"--json dep add {a['id']} {b['id']}")
        exit_code, _ = jcli(f"--json dep remove {a['id']} {b['id']}")
        assert exit_code == 0


class TestReleaseArgParsing:
    """'beans release' handles --mine vs bean_id argument parsing."""

    def test_release_mine(self, jcli):
        _, a = jcli('--json create "Task A"')
        jcli(f"--json claim {a['id']} --actor alice")
        exit_code, data = jcli("--json release --mine --actor alice")
        assert exit_code == 0
        assert len(data) == 1

    def test_release_mine_empty(self, jcli):
        exit_code, data = jcli("--json release --mine --actor alice")
        assert exit_code == 0
        assert data == []

    def test_release_both_id_and_mine_is_error(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = jcli(f"--json release {created['id']} --mine --actor alice")
        assert exit_code != 0


class TestHumanOutput:
    """Text-mode output works for human consumption."""

    def test_list_outputs_beans(self, cli, jcli):
        jcli('--json create "Task A"')
        exit_code, _ = cli("list")
        assert exit_code == 0

    def test_show_outputs_bean(self, cli, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = cli(f"show {created['id']}")
        assert exit_code == 0

    def test_delete_outputs_message(self, cli, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = cli(f"delete {created['id']}")
        assert exit_code == 0

    def test_dep_add_outputs_edge(self, cli, jcli):
        _, a = jcli('--json create "Task A"')
        _, b = jcli('--json create "Task B"')
        exit_code, _ = cli(f"dep add {a['id']} {b['id']}")
        assert exit_code == 0

    def test_dep_remove_outputs_message(self, cli, jcli):
        _, a = jcli('--json create "Task A"')
        _, b = jcli('--json create "Task B"')
        jcli(f"--json dep add {a['id']} {b['id']}")
        exit_code, _ = cli(f"dep remove {a['id']} {b['id']}")
        assert exit_code == 0


class TestDryRunMode:
    """'--dry-run' shows what would happen without writing."""

    def test_dry_run_create_shows_bean_but_does_not_persist(self, jcli):
        exit_code, data = jcli('--json --dry-run create "Fix auth"')
        assert exit_code == 0
        assert data["title"] == "Fix auth"

        _, beans = jcli("--json list")
        assert beans == []

    def test_dry_run_update_shows_change_but_does_not_persist(self, jcli):
        _, created = jcli('--json create "Old title"')

        exit_code, data = jcli(f'--json --dry-run update {created["id"]} --title "New title"')
        assert exit_code == 0
        assert data["title"] == "New title"

        _, bean = jcli(f"--json show {created['id']}")
        assert bean["title"] == "Old title"

    def test_dry_run_delete_does_not_persist(self, jcli):
        _, created = jcli('--json create "Fix auth"')

        exit_code, _ = jcli(f"--json --dry-run delete {created['id']}")
        assert exit_code == 0

        _, bean = jcli(f"--json show {created['id']}")
        assert bean["title"] == "Fix auth"

    def test_dry_run_close_does_not_persist(self, jcli):
        _, created = jcli('--json create "Fix auth"')

        exit_code, data = jcli(f"--json --dry-run close {created['id']}")
        assert exit_code == 0
        assert data["status"] == "closed"

        _, bean = jcli(f"--json show {created['id']}")
        assert bean["status"] == "open"

    def test_dry_run_claim_does_not_persist(self, jcli):
        _, created = jcli('--json create "Fix auth"')

        exit_code, data = jcli(f"--json --dry-run claim {created['id']} --actor alice")
        assert exit_code == 0
        assert data["assignee"] == "alice"

        _, bean = jcli(f"--json show {created['id']}")
        assert bean["assignee"] is None

    def test_dry_run_rebuild_does_not_persist(self, cli, jcli, tmp_path):
        jcli('--json create "Fix auth"')

        _, journal = cli("export-journal")
        journal_file = str(tmp_path / "journal.jsonl")
        with open(journal_file, "w") as f:
            f.write(journal)

        target_db = str(tmp_path / "target.db")
        exit_code, _ = cli(f"--db {target_db} --dry-run rebuild {journal_file}")
        assert exit_code == 0

        _, beans = jcli(f"--db {target_db} --json list")
        assert beans == []


class TestSchemaCommand:
    """'beans schema' outputs JSON schemas for all models."""

    def test_schema_includes_all_models(self, jcli):
        exit_code, data = jcli("--json schema")
        assert exit_code == 0
        assert "Bean" in data
        assert "Dep" in data
        assert "Error" in data

    def test_schema_bean_has_properties(self, jcli):
        exit_code, data = jcli("--json schema")
        assert exit_code == 0
        assert "properties" in data["Bean"]
        assert "id" in data["Bean"]["properties"]
        assert "title" in data["Bean"]["properties"]


class TestJsonErrorOutput:
    """Errors in --json mode return structured JSON."""

    def test_show_nonexistent_returns_json_error(self, jcli):
        exit_code, data = jcli("--json show bean-00000000")
        assert exit_code != 0
        assert "message" in data

    def test_update_nonexistent_returns_json_error(self, jcli):
        exit_code, data = jcli('--json update bean-00000000 --title "Nope"')
        assert exit_code != 0
        assert "message" in data

    def test_delete_nonexistent_returns_json_error(self, jcli):
        exit_code, data = jcli("--json delete bean-00000000")
        assert exit_code != 0
        assert "message" in data

    def test_close_nonexistent_returns_json_error(self, jcli):
        exit_code, data = jcli("--json close bean-00000000")
        assert exit_code != 0
        assert "message" in data

    def test_claim_already_claimed_returns_json_error(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        jcli(f"--json claim {created['id']} --actor alice")
        exit_code, data = jcli(f"--json claim {created['id']} --actor bob")
        assert exit_code != 0
        assert "message" in data

    def test_release_by_wrong_actor_returns_json_error(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        jcli(f"--json claim {created['id']} --actor alice")
        exit_code, data = jcli(f"--json release {created['id']} --actor bob")
        assert exit_code != 0
        assert "message" in data

    def test_release_no_args_returns_error(self, cli):
        exit_code, _ = cli("release --actor alice")
        assert exit_code != 0

    def test_dep_remove_nonexistent_returns_json_error(self, jcli):
        exit_code, data = jcli("--json dep remove bean-aaaaaaaa bean-bbbbbbbb")
        assert exit_code != 0
        assert "message" in data


class TestInputValidation:
    """Invalid inputs are rejected with clear errors."""

    def test_update_invalid_status(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = jcli(f"--json update {created['id']} --status deleted")
        assert exit_code != 0

    def test_update_invalid_priority(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = jcli(f"--json update {created['id']} --priority 5")
        assert exit_code != 0

    def test_create_invalid_type(self, cli):
        exit_code, _ = cli('create "Bad" --type invalid')
        assert exit_code != 0

    def test_update_invalid_type(self, jcli):
        _, created = jcli('--json create "Fix auth"')
        exit_code, _ = jcli(f"--json update {created['id']} --type invalid")
        assert exit_code != 0

    def test_show_invalid_id_format(self, cli):
        exit_code, _ = cli("show not-a-bean-id")
        assert exit_code != 0


class TestExportJournalCommand:
    """'beans export-journal' exports journal entries as JSONL."""

    def test_export_empty(self, cli):
        exit_code, output = cli("export-journal")
        assert exit_code == 0
        assert output.strip() == ""

    def test_export_after_create(self, cli):
        cli('create "Fix auth"')

        exit_code, output = cli("export-journal")
        assert exit_code == 0
        lines = output.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["action"] == "create"

    def test_export_crud_cycle(self, cli, jcli):
        _, bean = jcli('--json create "Fix auth"')

        cli(f'update {bean["id"]} --title "Updated"')
        cli(f"delete {bean['id']}")

        exit_code, output = cli("export-journal")
        assert exit_code == 0
        lines = output.strip().split("\n")
        assert len(lines) == 3
        actions = [json.loads(line)["action"] for line in lines]
        assert actions == ["create", "update", "delete"]


class TestRebuildCommand:
    """'beans rebuild' rebuilds a database from a JSONL file."""

    def test_rebuild_from_journal(self, cli, jcli, tmp_path):
        _, bean = jcli('--json create "Fix auth"')

        journal_file = str(tmp_path / "journal.jsonl")
        _, journal = cli("export-journal")
        with open(journal_file, "w") as f:
            f.write(journal)

        target_db = str(tmp_path / "rebuilt.db")
        exit_code, _ = cli(f"--db {target_db} rebuild {journal_file}")
        assert exit_code == 0

        _, data = jcli(f"--db {target_db} --json list")
        assert len(data) == 1
        assert data[0]["id"] == bean["id"]
        assert data[0]["title"] == "Fix auth"

    def test_rebuild_with_updates(self, cli, jcli, tmp_path):
        _, bean = jcli('--json create "Fix auth"')
        cli(f'update {bean["id"]} --title "Updated"')

        journal_file = str(tmp_path / "journal.jsonl")
        _, journal = cli("export-journal")
        with open(journal_file, "w") as f:
            f.write(journal)

        target_db = str(tmp_path / "rebuilt.db")
        exit_code, _ = cli(f"--db {target_db} rebuild {journal_file}")
        assert exit_code == 0

        _, data = jcli(f"--db {target_db} --json show {bean['id']}")
        assert data["title"] == "Updated"


class TestStatsCommand:
    """'beans stats' outputs aggregate counts."""

    def test_stats_json_output(self, jcli):
        jcli('--json create "Task A"')
        jcli('--json create "Task B" --type bug')

        exit_code, data = jcli("--json stats")
        assert exit_code == 0
        assert data["by_status"] == {"open": 2}
        assert data["by_type"] == {"task": 1, "bug": 1}

    def test_stats_human_output(self, cli, jcli):
        jcli('--json create "Task A"')
        jcli('--json create "Task B" --type bug')

        exit_code, output = cli("stats")
        assert exit_code == 0
        assert "Status" in output
        assert "Type" in output
        assert "open" in output

    def test_stats_empty(self, jcli):
        exit_code, data = jcli("--json stats")
        assert exit_code == 0
        assert data == {"by_status": {}, "by_type": {}, "by_assignee": {}}


class TestGraphCommand:
    """'beans graph' renders the dependency tree."""

    def test_graph_no_deps(self, cli, jcli):
        jcli('--json create "Task A"')
        jcli('--json create "Task B"')

        exit_code, output = cli("graph")
        assert exit_code == 0
        assert "Task A" in output
        assert "Task B" in output

    def test_graph_with_deps(self, cli, jcli):
        _, a = jcli('--json create "Task A"')
        _, b = jcli('--json create "Task B"')
        cli(f"dep add {a['id']} {b['id']}")

        exit_code, output = cli("graph")
        assert exit_code == 0
        assert "Task A" in output
        assert "Task B" in output

    def test_graph_with_parent_child(self, cli, jcli):
        _, parent = jcli('--json create "Parent"')
        jcli(f'--json create "Child" --parent {parent["id"]}')

        exit_code, output = cli("graph")
        assert exit_code == 0
        assert "Parent" in output
        assert "Child" in output

    def test_graph_json_output(self, jcli):
        _, a = jcli('--json create "Task A"')
        _, b = jcli('--json create "Task B"')
        jcli(f"--json dep add {a['id']} {b['id']}")

        exit_code, data = jcli("--json graph")
        assert exit_code == 0
        assert "nodes" in data
        assert "edges" in data

    def test_graph_empty(self, cli):
        exit_code, _ = cli("graph")
        assert exit_code == 0

    def test_graph_shows_status(self, cli, jcli):
        _, bean = jcli('--json create "Done"')
        cli(f"close {bean['id']}")

        exit_code, output = cli("graph")
        assert exit_code == 0
        assert "closed" in output


class TestConfigCommand:
    """'beans config' shows config path and values."""

    def test_config_shows_xdg_path(self, cli, tmp_path, monkeypatch):
        config_dir = tmp_path / ".config" / "beans"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        exit_code, output = cli("config")
        assert exit_code == 0
        assert str(config_dir / "config.json") in output

    def test_config_shows_no_configuration(self, cli, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        exit_code, output = cli("config")
        assert exit_code == 0
        assert "No configuration set." in output

    def test_config_shows_values(self, cli, tmp_path, monkeypatch):
        config_dir = tmp_path / ".config" / "beans"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text(json.dumps({"actor": "alice"}))

        exit_code, output = cli("config")
        assert exit_code == 0
        assert "alice" in output


class TestRecipeCommand:
    """'beans recipe <client>' outputs agent-specific instructions."""

    def test_recipe_claude(self, cli):
        exit_code, output = cli("recipe claude")
        assert exit_code == 0
        assert "# Beans — Claude Integration" in output

    def test_recipe_gpt(self, cli):
        exit_code, output = cli("recipe gpt")
        assert exit_code == 0
        assert "# Beans — GPT Integration" in output

    def test_recipe_generic(self, cli):
        exit_code, output = cli("recipe generic")
        assert exit_code == 0
        assert "# Beans — Agent Integration" in output

    def test_recipe_unknown_client(self, cli):
        exit_code, output = cli("recipe unknown")
        assert exit_code != 0
        assert "Unknown recipe: unknown" in output

    def test_recipe_no_argument(self, cli):
        exit_code, output = cli("recipe")
        assert exit_code != 0
        assert "Provide a client name or use --list" in output

    def test_recipe_list(self, cli):
        exit_code, output = cli("recipe --list")
        assert exit_code == 0
        lines = output.strip().split("\n")
        assert "claude" in lines
        assert "gpt" in lines
        assert "generic" in lines
