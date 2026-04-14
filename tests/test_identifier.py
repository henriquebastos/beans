# Python imports
import subprocess

# Pip imports
# Internal imports
from beans.workspace import detect_identifier, detect_name, normalize_git_remote


class TestNormalizeGitRemote:
    def test_ssh(self):
        assert normalize_git_remote("git@github.com:org/repo.git") == "github.com/org/repo"

    def test_https_with_git_suffix(self):
        assert normalize_git_remote("https://github.com/org/repo.git") == "github.com/org/repo"

    def test_https_without_git_suffix(self):
        assert normalize_git_remote("https://github.com/org/repo") == "github.com/org/repo"

    def test_ssh_no_git_suffix(self):
        assert normalize_git_remote("git@github.com:org/repo") == "github.com/org/repo"

    def test_gitlab_ssh(self):
        assert normalize_git_remote("git@gitlab.com:team/project.git") == "gitlab.com/team/project"

    def test_https_with_trailing_slash(self):
        assert normalize_git_remote("https://github.com/org/repo/") == "github.com/org/repo"

    def test_nested_path(self):
        assert normalize_git_remote("git@github.com:org/sub/repo.git") == "github.com/org/sub/repo"


class TestDetectIdentifier:
    def test_returns_git_remote_when_available(self, tmp_path):
        # Create a git repo with a remote
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:me/myproject.git"],
            cwd=tmp_path, capture_output=True,
        )
        assert detect_identifier(tmp_path) == "github.com/me/myproject"

    def test_falls_back_to_path(self, tmp_path):
        assert detect_identifier(tmp_path) == str(tmp_path)

    def test_falls_back_to_path_when_no_remote(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        assert detect_identifier(tmp_path) == str(tmp_path)


class TestDetectName:
    def test_from_git_remote_identifier(self):
        assert detect_name(identifier="github.com/me/myblog") == "myblog"

    def test_from_path_identifier(self):
        assert detect_name(identifier="/home/user/projects/cool-thing") == "cool-thing"

    def test_from_nested_git_path(self):
        assert detect_name(identifier="gitlab.com/org/sub/repo") == "repo"
