# Python imports
import json

# Pip imports
import pytest
from typer.testing import CliRunner

# Internal imports
from beans.cli import app
from beans.project import find_beans_dir

runner = CliRunner()


@pytest.fixture()
def project_dir(tmp_path, monkeypatch):
    d = tmp_path / "myproject"
    d.mkdir()
    monkeypatch.chdir(d)
    return d


@pytest.fixture()
def invoke(project_dir):
    def invoke(*args):
        result = runner.invoke(app, ["--json", *args])
        data = json.loads(result.output) if result.output.strip() else None
        return result.exit_code, data

    return invoke


def init_project():
    return runner.invoke(app, ["init"])


class TestInitCommand:
    """'beans init' creates .beans/ directory with db and AGENTS.md."""

    def test_init_creates_beans_dir(self, project_dir):
        result = init_project()

        assert result.exit_code == 0
        assert (project_dir / ".beans").is_dir()

    def test_init_creates_db(self, project_dir):
        init_project()

        assert (project_dir / ".beans" / "beans.db").exists()

    def test_init_creates_agents_md(self, project_dir):
        init_project()

        agents_file = project_dir / ".beans" / "AGENTS.md"
        assert agents_file.exists()
        assert "beans" in agents_file.read_text().lower()

    def test_init_idempotent(self, project_dir):
        init_project()
        result = init_project()

        assert result.exit_code == 0

    def test_init_does_not_overwrite_existing_agents_md(self, project_dir):
        beans_dir = project_dir / ".beans"
        beans_dir.mkdir()
        agents_file = beans_dir / "AGENTS.md"
        agents_file.write_text("custom content")

        init_project()

        assert agents_file.read_text() == "custom content"


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


class TestProjectDiscovery:
    """CLI commands use project discovery to find .beans/beans.db."""

    def test_create_uses_discovered_db(self, project_dir, invoke):
        init_project()

        exit_code, _ = invoke("create", "Fix auth")
        assert exit_code == 0

        _, data = invoke("list")
        assert len(data) == 1
        assert data[0]["title"] == "Fix auth"

    def test_db_flag_overrides_discovery(self, project_dir, invoke):
        init_project()

        db_path = str(project_dir / "custom.db")
        runner.invoke(app, ["--db", db_path, "--json", "create", "Custom"])

        _, data = invoke("list")
        assert len(data) == 0
