from click.testing import CliRunner
from sam.__main__ import cli


class TestRun:
    def test_run(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert "Usage: cli run [OPTIONS]" in result.output
