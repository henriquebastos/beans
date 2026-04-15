# Python imports
import json
from pathlib import Path

# Pip imports
import pytest

# Internal imports
from beans.config import CONFIG_FILE, BeanType, Config, config_path


@pytest.fixture()
def config_dir(tmp_path, monkeypatch):
    d = tmp_path / ".config" / "beans"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    return d


class TestConfigPath:
    """config_path() resolves XDG config directory."""

    def test_uses_xdg_config_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom"))
        path = config_path()
        assert path == tmp_path / "custom" / "beans" / "config.json"

    def test_falls_back_to_home_dot_config(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        path = config_path()
        assert path == Path.home() / ".config" / "beans" / "config.json"


class TestFromPath:
    """Config.from_path() loads existing file or creates empty config."""

    def test_returns_empty_config_when_no_file(self, config_dir):
        cfg = Config.from_path(config_dir / CONFIG_FILE)
        assert cfg.projects == []
        assert cfg.path == config_dir / CONFIG_FILE

    def test_reads_config_from_file(self, config_dir):
        config_dir.mkdir(parents=True)
        config_file = config_dir / CONFIG_FILE
        config_file.write_text(json.dumps({"projects": [{"name": "a", "identifier": "id-a", "store": "/a"}]}))

        cfg = Config.from_path(config_file)
        assert len(cfg.projects) == 1
        assert cfg.projects[0].name == "a"

    def test_raises_on_invalid_json(self, config_dir):
        config_dir.mkdir(parents=True)
        config_file = config_dir / CONFIG_FILE
        config_file.write_text("not json")

        with pytest.raises(json.JSONDecodeError):
            Config.from_path(config_file)


class TestBeanType:
    """BeanType is a frozen model with name and optional description."""

    def test_name_only(self):
        bt = BeanType(name="spike")
        assert bt.name == "spike"
        assert bt.description == ""

    def test_with_description(self):
        bt = BeanType(name="spike", description="Time-boxed investigation")
        assert bt.description == "Time-boxed investigation"

    def test_frozen(self):
        bt = BeanType(name="task")
        with pytest.raises(Exception):
            bt.name = "changed"


class TestConfigTypes:
    """Config.types defaults to [task, bug, epic] and supports customization."""

    def test_default_types(self):
        cfg = Config(path=Path("/tmp/config.json"))
        names = cfg.type_names()
        assert names == {"task", "bug", "epic"}

    def test_custom_types(self):
        cfg = Config(
            path=Path("/tmp/config.json"),
            types=[BeanType(name="story"), BeanType(name="spike")],
        )
        assert cfg.type_names() == {"story", "spike"}

    def test_types_roundtrip(self, config_dir):
        config_dir.mkdir(parents=True)
        config_file = config_dir / CONFIG_FILE
        cfg = Config(
            path=config_file,
            types=[BeanType(name="task"), BeanType(name="spike", description="Investigation")],
        )
        cfg.save()
        loaded = Config.from_path(config_file)
        assert loaded.type_names() == {"task", "spike"}
        assert loaded.types[1].description == "Investigation"

    def test_existing_config_without_types_gets_defaults(self, config_dir):
        """Backward compat: configs without 'types' key get default types."""
        config_dir.mkdir(parents=True)
        config_file = config_dir / CONFIG_FILE
        config_file.write_text(json.dumps({"projects": []}))
        cfg = Config.from_path(config_file)
        assert cfg.type_names() == {"task", "bug", "epic"}


class TestConfigAddRemoveType:
    """Config supports adding and removing types."""

    def test_add_type(self):
        cfg = Config(path=Path("/tmp/config.json"))
        cfg.add_type(BeanType(name="spike", description="Investigation"))
        assert "spike" in cfg.type_names()

    def test_add_duplicate_replaces(self):
        cfg = Config(path=Path("/tmp/config.json"))
        cfg.add_type(BeanType(name="task", description="Updated"))
        task_types = [t for t in cfg.types if t.name == "task"]
        assert len(task_types) == 1
        assert task_types[0].description == "Updated"

    def test_remove_type(self):
        cfg = Config(path=Path("/tmp/config.json"))
        assert cfg.remove_type("bug")
        assert "bug" not in cfg.type_names()

    def test_remove_nonexistent_returns_false(self):
        cfg = Config(path=Path("/tmp/config.json"))
        assert not cfg.remove_type("nonexistent")
