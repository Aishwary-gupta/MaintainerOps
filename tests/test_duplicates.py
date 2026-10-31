from maintainerops.client.fixtures import load_fixture_data
from maintainerops.models.findings import FindingType
from maintainerops.rules.duplicates import DuplicateRule


def test_duplicate_detection_matches_similar_issues():
    _, issues, prs = load_fixture_data("tests/fixtures/sample_repo.json")
    rule = DuplicateRule(similarity_threshold=0.50)
    findings = rule.analyze(issues, prs)

    dup_findings = [f for f in findings if f.finding_type == FindingType.POSSIBLE_DUPLICATE]
    assert len(dup_findings) >= 1

    # Issue 102 and 103 discuss database connection pool timeout under concurrent load
    found = any(f.item_number in [102, 103] for f in dup_findings)
    assert found
