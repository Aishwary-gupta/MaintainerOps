from maintainerops.client.fixtures import load_fixture_data
from maintainerops.models.findings import FindingType
from maintainerops.rules.completeness import CompletenessRule


def test_completeness_flags_vague_issue():
    _, issues, prs = load_fixture_data("tests/fixtures/sample_repo.json")
    rule = CompletenessRule()
    findings = rule.analyze(issues, prs)

    # Issue 101 should be flagged as incomplete
    flagged_numbers = [f.item_number for f in findings if f.finding_type == FindingType.INCOMPLETE_ISSUE]
    assert 101 in flagged_numbers
    assert 102 not in flagged_numbers

    issue_101_finding = next(f for f in findings if f.item_number == 101)
    assert issue_101_finding.draft_response is not None
    assert "reproduction steps" in issue_101_finding.summary
