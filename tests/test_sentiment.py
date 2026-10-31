from maintainerops.models.findings import FindingType, Severity
from maintainerops.models.github import IssueItem, User
from maintainerops.rules.sentiment import SentimentRule


def test_sentiment_critical_outage():
    issue = IssueItem(
        number=102,
        title="Production down: database timeout after upgrade",
        body="Our entire production down due to sudden connection timeout under heavy concurrency.",
        state="open",
        user=User(login="ops_lead"),
        comments_count=10,
        reactions_count=8,
    )

    rule = SentimentRule()
    findings = rule.analyze(issues=[issue], pull_requests=[])

    assert len(findings) == 1
    f = findings[0]
    assert f.finding_type == FindingType.COMMUNITY_SENTIMENT
    assert f.severity == Severity.CRITICAL
    assert "production outage" in f.summary.lower()
    assert "apologize for the friction" in f.draft_response


def test_sentiment_user_frustration():
    issue = IssueItem(
        number=103,
        title="Why are maintainers ignoring pull requests?",
        body="This is a terrible experience, completely unusable and nobody answers for months.",
        state="open",
        user=User(login="angry_user"),
        comments_count=5,
    )

    rule = SentimentRule()
    findings = rule.analyze(issues=[issue], pull_requests=[])

    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.COMMUNITY_SENTIMENT
    assert findings[0].severity == Severity.HIGH
