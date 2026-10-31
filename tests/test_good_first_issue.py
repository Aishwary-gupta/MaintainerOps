from maintainerops.models.findings import FindingType
from maintainerops.models.github import IssueItem, Label, User
from maintainerops.rules.good_first_issue import GoodFirstIssueRule


def test_good_first_issue_detection():
    issue = IssueItem(
        number=104,
        title="Fix broken hyperlink in installation guide README",
        body="The link pointing to docs is broken.\n\nExpected behavior:\nLink should point to docs/config.md.",
        state="open",
        user=User(login="newbie"),
        labels=[Label(name="documentation")],
        comments_count=1,
    )

    rule = GoodFirstIssueRule()
    findings = rule.analyze(issues=[issue], pull_requests=[])

    assert len(findings) == 1
    f = findings[0]
    assert f.finding_type == FindingType.GOOD_FIRST_ISSUE
    assert f.item_number == 104
    assert "good first issue" in f.suggested_action.lower()


def test_good_first_issue_ignores_already_labeled():
    issue = IssueItem(
        number=105,
        title="Fix typo in README",
        body="Typo on line 10.",
        state="open",
        user=User(login="dev"),
        labels=[Label(name="good first issue")],
        comments_count=0,
    )

    rule = GoodFirstIssueRule()
    findings = rule.analyze(issues=[issue], pull_requests=[])
    assert len(findings) == 0
