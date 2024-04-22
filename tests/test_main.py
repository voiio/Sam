import os
from unittest import mock

from click.testing import CliRunner

from sam.__main__ import cli


class TestRun:
    def test_run(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code == 0
        assert "Usage: cli run [OPTIONS]" in result.output


class TestAssistants:
    def test_list(self, monkeypatch):
        monkeypatch.chdir("tests/fixtures")
        runner = CliRunner()
        result = runner.invoke(cli, ["assistants", "list"])
        assert result.exit_code == 0
        assert "Harry (default-project): asst_1234057341258907" in result.output

    def test_list__empty(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["assistants", "list"])
        assert result.exit_code == 0
        assert "No assistants configured." in result.output

    def test_upload(self, monkeypatch):
        monkeypatch.chdir("tests/fixtures")
        client = mock.MagicMock()
        monkeypatch.setattr("openai.OpenAI", lambda api_key: client)
        runner = CliRunner()
        result = runner.invoke(cli, ["assistants", "upload"])
        assert result.exit_code == 0
        assert "Uploading Harry... Done!" in result.output
        assert client.__enter__().beta.assistants.update.called

    def test_upload__empty(self, monkeypatch):
        client = mock.MagicMock()
        monkeypatch.setattr("openai.OpenAI", lambda api_key: client)
        runner = CliRunner()
        result = runner.invoke(cli, ["assistants", "upload"])
        assert result.exit_code == 0
        assert "No assistants configured." in result.output
