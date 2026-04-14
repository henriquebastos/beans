# Python imports
import json

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app
from beans.config import load_registry
from beans.workspace import find_beans_dir, init_project, init_project_local


@pytest.fixture()
def project_dir(tmp_path, monkeypatch):
    d = tmp_path / "myproject"
    d.mkdir()
    monkeypatch.chdir(d)
    return d


@pytest.fixture()
def cli():
    runner = CliRunner()

    def invoke(*args):
        return runner.invoke(app, [*args])

    return invoke


@pytest.fixture()
def jcli(cli):
    def invoke(*args):
        result = cli("--json", *args)
        data = json.loads(result.output) if result.output.strip() else None
        return result.exit_code, data

    return invoke


class TestInitCommand:
    """'beans init' creates .beans/ directory with db and AGENTS.md."""

    def test_init_creates_beans_dir(self, project_dir, cli):
        result = cli("init")

        assert result.exit_code == 0
        assert (project_dir / ".beans").is_dir()

    def test_init_creates_db(self, project_dir, cli):
        cli("init")

        assert (project_dir / ".beans" / "beans.db").exists()

    def test_init_creates_agents_md(self, project_dir, cli):
        cli("init")

        agents_file = project_dir / ".beans" / "AGENTS.md"
        assert agents_file.exists()
        assert "beans" in agents_file.read_text().lower()

    def test_init_creates_gitignore(self, project_dir, cli):
        cli("init")

        gitignore = project_dir / ".beans" / ".gitignore"
        assert gitignore.exists()
        assert gitignore.read_text() == "*\n!.gitignore\n!AGENTS.md\n!journal.jsonl\n"

    def test_init_idempotent(self, project_dir, cli):
        cli("init")
        result = cli("init")

        assert result.exit_code == 0

    def test_init_does_not_overwrite_existing_gitignore(self, project_dir, cli):
        beans_dir = project_dir / ".beans"
        beans_dir.mkdir()
        gitignore = beans_dir / ".gitignore"
        gitignore.write_text("custom rules")

        cli("init")

        assert gitignore.read_text() == "custom rules"

    def test_init_does_not_overwrite_existing_agents_md(self, project_dir, cli):
        beans_dir = project_dir / ".beans"
        beans_dir.mkdir()
        agents_file = beans_dir / "AGENTS.md"
        agents_file.write_text("custom content")

        cli("init")

        assert agents_file.read_text() == "custom content"

    def test_init_uses_env_override(self, tmp_path, monkeypatch):
        custom = tmp_path / "custom-beans"
        monkeypatch.setenv("MAGIC_BEANS_DIR", str(custom))
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert custom.is_dir()
        assert (custom / "beans.db").exists()
        assert (custom / "AGENTS.md").exists()
        assert not (tmp_path / ".beans").exists()


class TestInitProjectLocal:
    """init_project_local() creates .beans/ in cwd (backward compat)."""

    def test_init_local_creates_beans_dir(self, tmp_path):
        beans_dir = init_project_local(cwd=tmp_path)
        assert beans_dir == tmp_path / ".beans"
        assert (beans_dir / "beans.db").exists()
        assert (beans_dir / "AGENTS.md").exists()
        assert (beans_dir / ".gitignore").exists()

    def test_init_local_uses_env_override(self, tmp_path):
        custom = tmp_path / "custom-beans"
        beans_dir = init_project_local(cwd=tmp_path, env={"MAGIC_BEANS_DIR": str(custom)})
        assert beans_dir == custom
        assert (custom / "beans.db").exists()
        assert not (tmp_path / ".beans").exists()


class TestInitProjectRegistry:
    """init_project() creates a registry entry and store in XDG data dir."""

    def test_init_creates_store_in_data_dir(self, tmp_path):
        data = tmp_path / "data"
        config = tmp_path / "config" / "config.json"
        store_dir = init_project(cwd=tmp_path, data_base=data, config_file=config)
        assert store_dir.is_dir()
        assert (store_dir / "beans.db").exists()
        assert (store_dir / "AGENTS.md").exists()

    def test_init_registers_project(self, tmp_path):
        data = tmp_path / "data"
        config = tmp_path / "config" / "config.json"
        init_project(cwd=tmp_path, data_base=data, config_file=config)
        projects = load_registry(config)
        assert len(projects) == 1
        assert projects[0].name == tmp_path.name

    def test_init_with_explicit_name(self, tmp_path):
        data = tmp_path / "data"
        config = tmp_path / "config" / "config.json"
        init_project(cwd=tmp_path, name="myblog", data_base=data, config_file=config)
        projects = load_registry(config)
        assert projects[0].name == "myblog"

    def test_init_idempotent_same_identifier(self, tmp_path):
        data = tmp_path / "data"
        config = tmp_path / "config" / "config.json"
        init_project(cwd=tmp_path, data_base=data, config_file=config)
        init_project(cwd=tmp_path, data_base=data, config_file=config)
        projects = load_registry(config)
        assert len(projects) == 1

    def test_init_does_not_create_local_beans_dir(self, tmp_path):
        data = tmp_path / "data"
        config = tmp_path / "config" / "config.json"
        init_project(cwd=tmp_path, data_base=data, config_file=config)
        assert not (tmp_path / ".beans").exists()


class TestFindBeansDir:
    """find_beans_dir() walks up from cwd to find .beans/."""

    def test_finds_beans_dir_in_cwd(self, project_dir):
        (project_dir / ".beans").mkdir()
        assert find_beans_dir(project_dir) == project_dir / ".beans"

    def test_finds_beans_dir_in_parent(self, project_dir):
        (project_dir / ".beans").mkdir()
        subdir = project_dir / "src" / "app"
        subdir.mkdir(parents=True)
        assert find_beans_dir(subdir) == project_dir / ".beans"

    def test_raises_when_not_found(self, tmp_path, monkeypatch):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        with pytest.raises(FileNotFoundError, match=r"\.beans"):
            find_beans_dir(empty)

    def test_env_override_returns_specified_dir(self, tmp_path, monkeypatch):
        beans = tmp_path / "custom-beans"
        beans.mkdir()
        monkeypatch.setenv("MAGIC_BEANS_DIR", str(beans))
        assert find_beans_dir() == beans

    def test_env_override_raises_when_dir_missing(self, monkeypatch):
        monkeypatch.setenv("MAGIC_BEANS_DIR", "/no/such/path")
        with pytest.raises(FileNotFoundError, match="MAGIC_BEANS_DIR"):
            find_beans_dir()

    def test_env_override_takes_precedence(self, tmp_path, monkeypatch):
        # Create .beans/ in cwd
        project = tmp_path / "project"
        project.mkdir()
        (project / ".beans").mkdir()
        monkeypatch.chdir(project)

        # Point env var elsewhere
        other = tmp_path / "other-beans"
        other.mkdir()
        monkeypatch.setenv("MAGIC_BEANS_DIR", str(other))

        assert find_beans_dir() == other

    def test_registry_match_by_path_identifier(self, tmp_path, monkeypatch):
        """find_beans_dir resolves via registry when cwd matches a registered path identifier."""
        monkeypatch.delenv("MAGIC_BEANS_DIR", raising=False)
        config = tmp_path / "config" / "config.json"
        store = tmp_path / "store" / "myproject"
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        # Register project and set up store
        init_project(cwd=project_dir, data_base=tmp_path / "store", config_file=config)

        # find_beans_dir should resolve via registry
        result = find_beans_dir(start=project_dir, config_file=config)
        assert result == store
        assert (result / "beans.db").exists()

    def test_registry_takes_precedence_over_local_beans_dir(self, tmp_path, monkeypatch):
        """Registry match wins over .beans/ walk-up."""
        monkeypatch.delenv("MAGIC_BEANS_DIR", raising=False)
        config = tmp_path / "config" / "config.json"
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        # Create local .beans/
        (project_dir / ".beans").mkdir()

        # Register project
        init_project(cwd=project_dir, data_base=tmp_path / "store", config_file=config)

        # Registry should win
        result = find_beans_dir(start=project_dir, config_file=config)
        assert ".beans" not in str(result)

    def test_falls_back_to_local_when_not_in_registry(self, tmp_path, monkeypatch):
        """Walk-up still works when project is not registered."""
        monkeypatch.delenv("MAGIC_BEANS_DIR", raising=False)
        config = tmp_path / "config" / "config.json"
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        (project_dir / ".beans").mkdir()

        result = find_beans_dir(start=project_dir, config_file=config)
        assert result == project_dir / ".beans"


class TestProjectDiscovery:
    """CLI commands use project discovery to find .beans/beans.db."""

    def test_create_uses_discovered_db(self, project_dir, cli, jcli):
        cli("init")

        exit_code, _ = jcli("create", "Fix auth")
        assert exit_code == 0

        _, data = jcli("list")
        assert len(data) == 1
        assert data[0]["title"] == "Fix auth"

    def test_db_flag_overrides_discovery(self, project_dir, cli, jcli):
        cli("init")

        db_path = str(project_dir / "custom.db")
        cli("--db", db_path, "--json", "create", "Custom")

        _, data = jcli("list")
        assert len(data) == 0

    def test_create_without_init_fails_with_helpful_message(self, project_dir, jcli):
        exit_code, data = jcli("create", "Fix auth")

        assert exit_code == 1
        assert "beans init" in data["message"]
        assert not (project_dir / "beans.db").exists()
