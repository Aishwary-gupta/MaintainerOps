import hashlib
from datetime import datetime, timezone
from typing import Any, List, Optional
from maintainerops.models.findings import Evidence, Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.rules.base import BaseRule


def _parse_datetime(val: Any) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            cleaned = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _get_user_login(user) -> str:
    if hasattr(user, "login"):
        return user.login
    if isinstance(user, dict):
        return user.get("login", "contributor")
    return "contributor"


class StaleRule(BaseRule):
    """Detects inactive pull requests and dormant issues requiring follow-up or triage."""

    def __init__(self, stale_days_threshold: int = 14):
        self.stale_days_threshold = stale_days_threshold

    @property
    def name(self) -> str:
        return "stale_lifecycle"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []
        now = datetime.now(timezone.utc)

        # 1. Evaluate Pull Requests
        for pr in pull_requests:
            if pr.state != "open" or pr.draft:
                continue

            last_activity = _parse_datetime(pr.updated_at) or _parse_datetime(pr.created_at)
            if not last_activity:
                continue

            inactive_days = max(0, (now - last_activity).days)
            if inactive_days >= self.stale_days_threshold:
                login = _get_user_login(pr.user)
                fid = hashlib.sha256(f"stale_pr_{pr.number}".encode()).hexdigest()[:12]

                waiting_state = "contributor"
                if pr.requested_reviewers and pr.mergeable_state == "clean":
                    waiting_state = "maintainer_review"

                summary = (
                    f"PR #{pr.number} has been inactive for {inactive_days} days "
                    f"(waiting on {waiting_state.replace('_', ' ')})."
                )

                if waiting_state == "maintainer_review":
                    draft = (
                        f"Friendly maintainer reminder: PR #{pr.number} from @{login} has been "
                        f"awaiting review for {inactive_days} days with passing checks."
                    )
                    action = "Schedule maintainer code review."
                else:
                    draft = (
                        f"Hi @{login}, checking in on this PR! It has been inactive for {inactive_days} days. "
                        f"Are you still working on this, or is there any blocker we can help resolve? Thanks!"
                    )
                    action = "Ping contributor for status update or close if abandoned."

                findings.append(
                    Finding(
                        id=fid,
                        item_type="pull_request",
                        item_number=pr.number,
                        item_title=pr.title,
                        item_url=pr.html_url,
                        finding_type=FindingType.STALE_PR,
                        severity=Severity.LOW if inactive_days < 30 else Severity.MEDIUM,
                        confidence=0.85,
                        summary=summary,
                        evidence=[
                            Evidence(
                                metric_name="inactive_days",
                                observed_value=inactive_days,
                                threshold_value=self.stale_days_threshold,
                                details=f"Last recorded activity was {inactive_days} days ago.",
                            ),
                            Evidence(
                                metric_name="waiting_on",
                                observed_value=waiting_state,
                                details=f"Currently identified as waiting on {waiting_state.replace('_', ' ')}.",
                            ),
                        ],
                        suggested_action=action,
                        draft_response=draft,
                    )
                )

        # 2. Evaluate Dormant Issues
        for issue in issues:
            if issue.is_pull_request or issue.state != "open":
                continue

            last_activity = _parse_datetime(issue.updated_at) or _parse_datetime(issue.created_at)
            if not last_activity:
                continue

            inactive_days = max(0, (now - last_activity).days)
            # Issues have a slightly longer dormancy threshold (2x)
            issue_threshold = max(21, self.stale_days_threshold * 2)

            if inactive_days >= issue_threshold and issue.comments_count <= 2:
                login = _get_user_login(issue.user)
                fid = hashlib.sha256(f"stale_issue_{issue.number}".encode()).hexdigest()[:12]

                findings.append(
                    Finding(
                        id=fid,
                        item_type="issue",
                        item_number=issue.number,
                        item_title=issue.title,
                        item_url=issue.html_url,
                        finding_type=FindingType.STALE_ISSUE,
                        severity=Severity.LOW,
                        confidence=0.8,
                        summary=f"Issue #{issue.number} has had no activity for {inactive_days} days.",
                        evidence=[
                            Evidence(
                                metric_name="inactive_days",
                                observed_value=inactive_days,
                                threshold_value=issue_threshold,
                                details=f"No new comments or updates in {inactive_days} days.",
                            )
                        ],
                        suggested_action="Verify if issue still persists in modern releases, or mark stale.",
                        draft_response=(
                            f"Hi @{login}, this issue has been inactive for {inactive_days} days. "
                            f"Could you please confirm if this is still reproducible in the latest version of the project? "
                            f"Thank you!"
                        ),
                    )
                )

        return findings
