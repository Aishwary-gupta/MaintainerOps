from maintainerops.engine import run_scan
from maintainerops.reporters.html_report import render_html


def test_html_report_rendering():
    report = run_scan("tests/fixtures/sample_repo.json")
    html = render_html(report)

    assert "<!DOCTYPE html>" in html
    assert "MaintainerOps Triage Dashboard" in html
    assert "maintainerops/sample-repo" in html
    assert "report-data" in html
    assert "Repo Health Index" in html
