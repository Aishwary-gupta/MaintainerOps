import hashlib
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


def _get_check_conclusion(check) -> str:
    if hasattr(check, "conclusion"):
        return check.conclusion or ""
    if isinstance(check, dict):
        return check.get("conclusion") or ""
    return ""


def _get_check_name(check) -> str:
    if hasattr(check, "name"):
        return check.name
    if isinstance(check, dict):
        return check.get("name", "check")
    return "check"


class PullRequestHealthRule(BaseRule):
    """Identifies blocked PRs due to failing CI checks or merge conflicts."""

    @property
    def name(self) -> str:
        return "pr_health_blockers"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []

        for pr in pull_requests:
            if pr.state != "open" or pr.draft:
                continue

            login = _get_user_login(pr.user)

            # Check 1: Merge Conflicts
            if pr.mergeable is False or pr.mergeable_state in ["dirty", "conflicting"]:
                fid = hashlib.sha256(f"pr_conflict_{pr.number}".encode()).hexdigest()[:12]
                findings.append(
                    Finding(
                        id=fid,
                        item_type="pull_request",
                        item_number=pr.number,
                        item_title=pr.title,
                        item_url=pr.html_url,
                        finding_type=FindingType.MERGE_CONFLICT,
                        severity=Severity.HIGH,
                        confidence=1.0,
                        summary=f"PR #{pr.number} has merge conflicts blocking integration.",
                        evidence=[
                            Evidence(
                                metric_name="mergeable_state",
                                observed_value=pr.mergeable_state,
                                details="Git reports conflicting changes with base branch.",
                            )
                        ],
                        suggested_action="Request contributor rebase against main branch.",
                        draft_response=f"Hi @{login}, this PR currently has merge conflicts with the base branch. Could you please rebase your branch? Thanks!",
                    )
                )

            # Check 2: CI check run failures
            failing_checks = [
                _get_check_name(c)
                for c in pr.check_runs
                if _get_check_conclusion(c) in ["failure", "timed_out", "action_required"]
            ]
            if failing_checks:
                fid = hashlib.sha256(f"pr_ci_{pr.number}".encode()).hexdigest()[:12]
                checks_list = ", ".join(failing_checks[:3])
                findings.append(
                    Finding(
                        id=fid,
                        item_type="pull_request",
                        item_number=pr.number,
                        item_title=pr.title,
                        item_url=pr.html_url,
                        finding_type=FindingType.CI_FAILURE,
                        severity=Severity.HIGH,
                        confidence=1.0,
                        summary=f"PR #{pr.number} has {len(failing_checks)} failing CI check(s): {checks_list}.",
                        evidence=[
                            Evidence(
                                metric_name="failing_checks",
                                observed_value=failing_checks,
                                details=f"Failed check runs: {', '.join(failing_checks)}",
                            )
                        ],
                        suggested_action="Review CI logs or prompt contributor to fix broken tests/lint.",
                        draft_response=f"Hi @{login}, one or more CI checks ({checks_list}) failed on this PR. Please inspect the test logs and push an update.",
                    )
                )

        return findings
