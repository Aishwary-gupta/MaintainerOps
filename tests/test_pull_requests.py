from maintainerops.client.fixtures import load_fixture_data
from maintainerops.models.findings import FindingType
from maintainerops.rules.pull_requests import PullRequestHealthRule


def test_pr_health_detects_ci_failures_and_merge_conflicts():
    _, issues, prs = load_fixture_data("tests/fixtures/sample_repo.json")
    rule = PullRequestHealthRule()
    findings = rule.analyze(issues, prs)

    # PR 201 has failing check "Unit Tests (Linux)"
    ci_findings = [f for f in findings if f.finding_type == FindingType.CI_FAILURE]
    assert any(f.item_number == 201 for f in ci_findings)

    # PR 202 has merge conflicts (dirty state)
    conflict_findings = [f for f in findings if f.finding_type == FindingType.MERGE_CONFLICT]
    assert any(f.item_number == 202 for f in conflict_findings)
