from datetime import datetime, timedelta, timezone
from maintainerops.models.findings import FindingType
from maintainerops.models.github import IssueItem, PullRequestItem, User
from maintainerops.rules.stale import StaleRule


def test_stale_pr_waiting_on_author():
    old_time = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    pr = PullRequestItem(
        number=301,
        title="fix: old pr",
        body="Some description",
        state="open",
        user=User(login="contributor_1"),
        updated_at=old_time,
        mergeable_state="dirty",
    )

    rule = StaleRule(stale_days_threshold=14)
    findings = rule.analyze(issues=[], pull_requests=[pr])

    assert len(findings) == 1
    f = findings[0]
    assert f.finding_type == FindingType.STALE_PR
    assert f.item_number == 301
    assert "waiting on contributor" in f.summary.lower()
    assert "Hi @contributor_1" in f.draft_response


def test_stale_pr_waiting_on_maintainer_review():
    old_time = (datetime.now(timezone.utc) - timedelta(days=16)).isoformat()
    pr = PullRequestItem(
        number=302,
        title="feat: ready for review",
        body="Full description",
        state="open",
        user=User(login="contributor_2"),
        updated_at=old_time,
        mergeable_state="clean",
        requested_reviewers=[User(login="lead_maintainer")],
    )

    rule = StaleRule(stale_days_threshold=14)
    findings = rule.analyze(issues=[], pull_requests=[pr])

    assert len(findings) == 1
    f = findings[0]
    assert f.finding_type == FindingType.STALE_PR
    assert "waiting on maintainer review" in f.summary.lower()


def test_dormant_issue():
    old_time = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    issue = IssueItem(
        number=105,
        title="Old unresolved question",
        body="Is this still valid?",
        state="open",
        user=User(login="inactive_author"),
        updated_at=old_time,
        comments_count=1,
    )

    rule = StaleRule(stale_days_threshold=14)
    findings = rule.analyze(issues=[issue], pull_requests=[])

    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.STALE_ISSUE
    assert findings[0].item_number == 105
