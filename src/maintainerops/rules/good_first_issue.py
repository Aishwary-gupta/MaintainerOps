import hashlib
import re
from typing import List
from maintainerops.models.findings import Evidence, Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.rules.base import BaseRule


class GoodFirstIssueRule(BaseRule):
    """Identifies clear, low-barrier issues that make ideal starter tasks for new contributors."""

    @property
    def name(self) -> str:
        return "good_first_issue_candidate"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []

        gfi_keywords = ["good first issue", "good-first-issue", "beginner", "starter", "help wanted"]

        for issue in issues:
            if issue.is_pull_request or issue.state != "open":
                continue

            current_labels = [l.name.lower() for l in issue.labels]
            # Skip if already marked as good first issue
            if any(k in current_labels for k in gfi_keywords):
                continue

            body = (issue.body or "").strip()
            title = issue.title.lower()

            reasons = []
            evidences = []

            # 1. Documentation, typo, or beginner-friendly label
            is_doc_or_small = any(
                lbl in ["documentation", "docs", "typo", "cleanup", "refactor", "chore", "examples", "minor"]
                for lbl in current_labels
            ) or bool(re.search(r"\b(typo|docs|documentation|readme|example|guide|link broken)\b", title))

            if is_doc_or_small:
                reasons.append("Contains documentation, typo, or small maintenance scope")
                evidences.append(
                    Evidence(
                        metric_name="scope_category",
                        observed_value="small_maintenance_or_docs",
                        details="Issue targets documentation, typo fixes, or isolated small cleanup.",
                    )
                )

            # 2. Clear instructions / reproduction without deep complexity
            has_clear_instructions = len(body) >= 60 and len(body) <= 1500 and (
                "## steps" in body.lower()
                or "- [ ]" in body
                or "expected" in body.lower()
                or "should be" in body.lower()
            )

            if has_clear_instructions:
                reasons.append("Contains structured, clear expectations without excessive complexity")
                evidences.append(
                    Evidence(
                        metric_name="clarity_indicator",
                        observed_value=True,
                        details="Body contains structured checklist or clear expected behavior.",
                    )
                )

            # 3. Uncontested / low comment competition
            if is_doc_or_small and issue.comments_count <= 3:
                fid = hashlib.sha256(f"gfi_{issue.number}".encode()).hexdigest()[:12]
                findings.append(
                    Finding(
                        id=fid,
                        item_type="issue",
                        item_number=issue.number,
                        item_title=issue.title,
                        item_url=issue.html_url,
                        finding_type=FindingType.GOOD_FIRST_ISSUE,
                        severity=Severity.LOW,
                        confidence=0.85,
                        summary=f"Issue #{issue.number} is a strong candidate for newcomer contribution.",
                        evidence=evidences,
                        suggested_action="Apply 'good first issue' and 'help wanted' labels to invite new contributors.",
                        draft_response=(
                            "Hello contributors! This issue has been identified as beginner-friendly. "
                            "Feel free to submit a pull request if you'd like to tackle this! "
                            "Check out our CONTRIBUTING.md for local setup instructions."
                        ),
                    )
                )

        return findings
