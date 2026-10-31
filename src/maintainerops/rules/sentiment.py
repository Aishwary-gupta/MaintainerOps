import hashlib
import re
from typing import List
from maintainerops.models.findings import Evidence, Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.rules.base import BaseRule


def _get_user_login(user) -> str:
    if hasattr(user, "login"):
        return user.login
    if isinstance(user, dict):
        return user.get("login", "contributor")
    return "contributor"


class SentimentRule(BaseRule):
    """Detects elevated community frustration or critical production urgency requiring empathetic maintainer triage."""

    @property
    def name(self) -> str:
        return "community_sentiment"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []

        urgency_patterns = [
            (r"\b(production\s+down|down\s+in\s+prod|breaking\s+prod)\b", "Production outage reported", Severity.CRITICAL),
            (r"\b(data\s+loss|corrupted\s+database|security\s+vulnerability|cve-)\b", "Critical data integrity / security risk", Severity.CRITICAL),
            (r"\b(unusable|completely\s+broken|major\s+regression|release\s+blocker)\b", "Severe functionality regression", Severity.HIGH),
            (r"\b(ignoring\s+(us|users|prs)|waste\s+of\s+time|terrible\s+experience|no\s+one\s+answers)\b", "High user frustration / abandonment sentiment", Severity.HIGH),
        ]

        for issue in issues:
            if issue.is_pull_request or issue.state != "open":
                continue

            text = f"{issue.title}\n{issue.body or ''}".lower()
            detected_matches = []
            max_severity = Severity.HIGH

            for pattern, desc, sev in urgency_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    detected_matches.append(desc)
                    if sev == Severity.CRITICAL:
                        max_severity = Severity.CRITICAL

            if detected_matches:
                login = _get_user_login(issue.user)
                fid = hashlib.sha256(f"sentiment_{issue.number}".encode()).hexdigest()[:12]

                findings.append(
                    Finding(
                        id=fid,
                        item_type="issue",
                        item_number=issue.number,
                        item_title=issue.title,
                        item_url=issue.html_url,
                        finding_type=FindingType.COMMUNITY_SENTIMENT,
                        severity=max_severity,
                        confidence=0.9,
                        summary=f"Elevated urgency / community sensitivity detected: {', '.join(detected_matches)}.",
                        evidence=[
                            Evidence(
                                metric_name="sentiment_signals",
                                observed_value=detected_matches,
                                details=f"Detected high-urgency keywords: {'; '.join(detected_matches)}.",
                            ),
                            Evidence(
                                metric_name="community_engagement",
                                observed_value={
                                    "reactions": issue.reactions_count,
                                    "comments": issue.comments_count,
                                },
                                details=f"Has {issue.reactions_count} reactions and {issue.comments_count} comments.",
                            ),
                        ],
                        suggested_action="Maintainer should reply with prompt empathetic acknowledgment and priority assessment.",
                        draft_response=(
                            f"Hi @{login}, thank you for flagging this urgent issue. We understand the high impact "
                            f"this causes and apologize for the friction. The maintainer team is prioritizing investigating "
                            f"this report. If you have any temporary workarounds or logs, please share them below."
                        ),
                    )
                )

        return findings
