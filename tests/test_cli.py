from typer.testing import CliRunner
from maintainerops.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "MaintainerOps" in result.stdout


def test_cli_scan_fixture_markdown():
    result = runner.invoke(app, ["scan", "tests/fixtures/sample_repo.json", "--format", "markdown"])
    assert result.exit_code == 0
    assert "MaintainerOps Triage Report" in result.stdout
    assert "Incomplete Bug Reports" in result.stdout


def test_cli_scan_fixture_json():
    result = runner.invoke(app, ["scan", "tests/fixtures/sample_repo.json", "--format", "json"])
    assert result.exit_code == 0
    assert '"repository": "maintainerops/sample-repo"' in result.stdout
