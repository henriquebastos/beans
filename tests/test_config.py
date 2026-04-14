# Python imports
import json
from pathlib import Path

# Pip imports
import pytest

# Internal imports
from beans.config import CONFIG_FILE, Config, config_path


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


class TestLoadConfig:
    """Config.load() reads config from an existing file."""

    def test_raises_when_file_missing(self, config_dir):
        with pytest.raises(FileNotFoundError):
            Config.load(config_dir / CONFIG_FILE)

    def test_reads_config_from_file(self, config_dir):
        config_dir.mkdir(parents=True)
        config_file = config_dir / CONFIG_FILE
        config_file.write_text(json.dumps({"projects": [{"name": "a", "identifier": "id-a", "store": "/a"}]}))

        cfg = Config.load(config_file)
        assert len(cfg.projects) == 1
        assert cfg.projects[0].name == "a"

    def test_raises_on_invalid_json(self, config_dir):
        config_dir.mkdir(parents=True)
        config_file = config_dir / CONFIG_FILE
        config_file.write_text("not json")

        with pytest.raises(json.JSONDecodeError):
            Config.load(config_file)
