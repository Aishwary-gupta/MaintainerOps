from maintainerops.models.findings import Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.rules.health import calculate_repository_health


def test_health_pristine_repository():
    score, grade, summary = calculate_repository_health([], [], [])
    assert score == 100
    assert grade == "A+"
    assert summary["status"] == "pristine"


def test_health_burdened_repository():
    issues = [
        IssueItem(number=1, title="Crash", state="open"),
        IssueItem(number=2, title="Bug", state="open"),
    ]
    prs = [
        PullRequestItem(number=10, title="PR 1", state="open"),
    ]
    findings = [
        Finding(id="1", finding_type=FindingType.INCOMPLETE_ISSUE, severity=Severity.MEDIUM),
        Finding(id="2", finding_type=FindingType.CI_FAILURE, severity=Severity.HIGH),
        Finding(id="3", finding_type=FindingType.COMMUNITY_SENTIMENT, severity=Severity.CRITICAL),
    ]

    score, grade, summary = calculate_repository_health(issues, prs, findings)
    assert score < 85
    assert grade in ["B", "C", "D", "F"]
    assert "PR(s) blocked" in summary["primary_bottleneck"]
