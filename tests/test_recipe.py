# Pip imports
from typer.testing import CliRunner

# Internal imports
from beans.cli import app

runner = CliRunner()


def invoke(*args):
    return runner.invoke(app, [*args])


class TestRecipeCommand:
    """'beans recipe <client>' outputs agent-specific instructions."""

    def test_recipe_claude(self):
        result = invoke("recipe", "claude")
        assert result.exit_code == 0
        assert "# Beans — Claude Integration" in result.output

    def test_recipe_gpt(self):
        result = invoke("recipe", "gpt")
        assert result.exit_code == 0
        assert "# Beans — GPT Integration" in result.output

    def test_recipe_generic(self):
        result = invoke("recipe", "generic")
        assert result.exit_code == 0
        assert "# Beans — Agent Integration" in result.output

    def test_recipe_unknown_client(self):
        result = invoke("recipe", "unknown")
        assert result.exit_code != 0
        assert "Unknown recipe: unknown" in result.output

    def test_recipe_no_argument(self):
        result = invoke("recipe")
        assert result.exit_code != 0
        assert "Provide a client name or use --list" in result.output

    def test_recipe_list(self):
        result = invoke("recipe", "--list")
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert "claude" in lines
        assert "gpt" in lines
        assert "generic" in lines
