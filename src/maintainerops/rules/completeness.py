import re
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


class CompletenessRule(BaseRule):
    """Detects incomplete bug reports lacking reproduction steps, environment, or logs."""

    @property
    def name(self) -> str:
        return "bug_report_completeness"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []

        for issue in issues:
            if issue.is_pull_request or issue.state != "open":
                continue

            body = (issue.body or "").strip()
            missing_elements = []
            evidences = []

            # Check 1: Very short description
            if len(body) < 50:
                missing_elements.append("sufficient description (under 50 chars)")
                evidences.append(
                    Evidence(
                        metric_name="body_length",
                        observed_value=len(body),
                        threshold_value=50,
                        details="The issue body contains fewer than 50 characters.",
                    )
                )

            # Check 2: Reproduction steps indicator
            has_repro = bool(
                re.search(
                    r"(steps to reproduce|reproduction steps|how to reproduce|reproduce|to reproduce|repro:)",
                    body,
                    re.IGNORECASE,
                )
                or re.search(r"(\n\s*1\.\s+.*\n\s*2\.\s+)", body)
            )
            if not has_repro:
                missing_elements.append("reproduction steps")
                evidences.append(
                    Evidence(
                        metric_name="reproduction_steps",
                        observed_value="absent",
                        threshold_value="present",
                        details="No reproduction steps section or numbered execution steps found.",
                    )
                )

            # Check 3: Environment info (OS, version, Python/Node)
            has_env = bool(
                re.search(
                    r"(environment|os|version|platform|browser|python|node|runtime)",
                    body,
                    re.IGNORECASE,
                )
            )
            if not has_env:
                missing_elements.append("environment details")
                evidences.append(
                    Evidence(
                        metric_name="environment_details",
                        observed_value="absent",
                        threshold_value="present",
                        details="No mention of OS, version, or runtime environment.",
                    )
                )

            # If 2 or more key elements are missing, generate an explainable finding
            if len(missing_elements) >= 2:
                finding_id = hashlib.sha256(
                    f"completeness_{issue.number}".encode()
                ).hexdigest()[:12]

                missing_str = ", ".join(missing_elements)
                login = _get_user_login(issue.user)
                draft = (
                    f"Hi @{login}, thanks for opening this issue! "
                    f"To help us triage and resolve this efficiently, could you please provide: "
                    f"{missing_str}? Thank you!"
                )

                findings.append(
                    Finding(
                        id=finding_id,
                        item_type="issue",
                        item_number=issue.number,
                        item_title=issue.title,
                        item_url=issue.html_url,
                        finding_type=FindingType.INCOMPLETE_ISSUE,
                        severity=Severity.MEDIUM,
                        confidence=0.85,
                        summary=f"Bug report appears incomplete (missing {missing_str}).",
                        evidence=evidences,
                        suggested_action="Request missing reproduction details from author.",
                        draft_response=draft,
                    )
                )

        return findings
