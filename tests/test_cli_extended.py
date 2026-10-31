from pathlib import Path
from typer.testing import CliRunner
from maintainerops.cli import app

runner = CliRunner()


def test_cli_health_command():
    result = runner.invoke(app, ["health", "tests/fixtures/sample_repo.json"])
    assert result.exit_code == 0
    assert "Health Scorecard" in result.stdout
    assert "Health Index:" in result.stdout


def test_cli_draft_command():
    result = runner.invoke(app, ["draft", "tests/fixtures/sample_repo.json", "101"])
    assert result.exit_code == 0
    assert "Draft Reply for #101" in result.stdout
    assert "Hi @alice" in result.stdout


def test_cli_scan_html_format(tmp_path: Path):
    out_file = tmp_path / "test_report.html"
    result = runner.invoke(
        app,
        ["scan", "tests/fixtures/sample_repo.json", "--format", "html", "-o", str(out_file)],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "MaintainerOps Triage Dashboard" in content
    assert "maintainerops/sample-repo" in content


def test_cli_export_dashboard(tmp_path: Path):
    out_file = tmp_path / "exported.html"
    result = runner.invoke(
        app,
        ["export-dashboard", "tests/fixtures/enterprise_repo.json", "-o", str(out_file)],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "MaintainerOps Triage Dashboard" in content
    assert "maintainerops/enterprise-demo" in content
