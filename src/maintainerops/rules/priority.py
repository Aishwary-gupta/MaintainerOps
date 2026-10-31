import hashlib
from typing import List
from maintainerops.models.findings import Evidence, Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.rules.base import BaseRule


class PriorityRule(BaseRule):
    """Identifies actionable, high-priority issues based on reactions, comments, and severity labels."""

    @property
    def name(self) -> str:
        return "priority_actionable"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []

        for issue in issues:
            if issue.is_pull_request or issue.state != "open":
                continue

            # Signal 1: High reactions (community interest)
            # Signal 2: Urgent labels (e.g. bug, critical, security)
            # Signal 3: Has complete body
            has_urgent_label = any(
                l.name.lower() in ["bug", "critical", "urgent", "security", "p0", "p1"]
                for l in issue.labels
            )
            is_high_engagement = issue.reactions_count >= 5 or issue.comments_count >= 10
            is_well_formed = len(issue.body or "") >= 100

            if (has_urgent_label or is_high_engagement) and is_well_formed:
                fid = hashlib.sha256(f"priority_{issue.number}".encode()).hexdigest()[:12]
                score = 50 + (issue.reactions_count * 5) + (issue.comments_count * 2)
                score = min(score, 100)

                findings.append(
                    Finding(
                        id=fid,
                        item_type="issue",
                        item_number=issue.number,
                        item_title=issue.title,
                        item_url=issue.html_url,
                        finding_type=FindingType.HIGH_PRIORITY_ACTIONABLE,
                        severity=Severity.HIGH,
                        confidence=0.9,
                        summary=f"High-priority issue: {issue.reactions_count} reactions, {issue.comments_count} comments.",
                        evidence=[
                            Evidence(
                                metric_name="priority_score",
                                observed_value=score,
                                threshold_value=70,
                                details=f"Composite priority score calculated as {score}/100.",
                            ),
                            Evidence(
                                metric_name="engagement_metrics",
                                observed_value={
                                    "reactions": issue.reactions_count,
                                    "comments": issue.comments_count,
                                },
                                details=f"{issue.reactions_count} reactions, {issue.comments_count} comments.",
                            ),
                        ],
                        suggested_action="Prioritize maintainer triage and investigation.",
                    )
                )

        return findings
