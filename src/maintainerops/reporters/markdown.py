from maintainerops.models.report import ScanReport
from maintainerops.models.findings import FindingType


def render_markdown(report: ScanReport) -> str:
    """Generates a clean, readable Markdown report suitable for CLI terminal output and GitHub Action Job Summaries."""
    lines = []
    lines.append(f"# 🛡️ MaintainerOps Triage Report: `{report.repository}`")
    lines.append(f"*Generated on {report.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} using MaintainerOps v{report.tool_version}*\n")

    # Summary table
    lines.append("## 📊 Scan Overview")
    lines.append(f"> **Repository Health Index:** `{report.metrics.health_score}/100` (Grade: **{report.metrics.health_grade}**)\n")
    lines.append("| Metric | Count |")
    lines.append("| :--- | :--- |")
    lines.append(f"| **Issues Analyzed** | {report.metrics.total_issues_analyzed} |")
    lines.append(f"| **Pull Requests Analyzed** | {report.metrics.total_prs_analyzed} |")
    lines.append(f"| ⚠️ **Incomplete Bug Reports** | {report.metrics.incomplete_issues_count} |")
    lines.append(f"| 🔍 **Likely Duplicates** | {report.metrics.potential_duplicates_count} |")
    lines.append(f"| 🚦 **Blocked Pull Requests** | {report.metrics.blocked_prs_count} |")
    lines.append(f"| ⏳ **Stale / Inactive Items** | {report.metrics.stale_items_count} |")
    lines.append(f"| 🌱 **Good First Issues** | {report.metrics.good_first_issues_count} |")
    lines.append(f"| 🚨 **Urgent / Sentiment Alerts** | {report.metrics.sentiment_alerts_count} |")
    lines.append(f"| 🔥 **High-Priority Actionable** | {report.metrics.actionable_high_priority_count} |\n")

    if not report.findings:
        lines.append("✅ **No blocking or incomplete issues found! Everything looks clean.**")
        return "\n".join(lines)

    lines.append("## 🔍 Triage Findings & Evidence\n")

    # Group by category
    categories = [
        ("🚨 Critical Outage & Community Urgency", FindingType.COMMUNITY_SENTIMENT),
        ("🔥 High-Priority Actionable Issues", FindingType.HIGH_PRIORITY_ACTIONABLE),
        ("🚦 Blocked Pull Requests (CI / Merge Conflicts)", [FindingType.CI_FAILURE, FindingType.MERGE_CONFLICT]),
        ("⚠️ Incomplete Bug Reports (Missing Reproduction/Environment)", FindingType.INCOMPLETE_ISSUE),
        ("🔍 Potential Duplicate Issues", FindingType.POSSIBLE_DUPLICATE),
        ("⏳ Stale & Inactive Backlog Items", [FindingType.STALE_PR, FindingType.STALE_ISSUE, FindingType.STALE_REVIEW]),
        ("🌱 Good First Issues for New Contributors", FindingType.GOOD_FIRST_ISSUE),
    ]

    for title, ftypes in categories:
        target_types = ftypes if isinstance(ftypes, list) else [ftypes]
        matched = [f for f in report.findings if f.finding_type in target_types]

        if not matched:
            continue

        lines.append(f"### {title} ({len(matched)})")
        for f in matched:
            item_badge = "PR" if f.item_type == "pull_request" else "Issue"
            lines.append(f"- **[{item_badge} #{f.item_number}]({f.item_url})**: {f.item_title}")
            lines.append(f"  - **Summary**: {f.summary}")
            lines.append(f"  - **Confidence**: `{int(f.confidence * 100)}%` | **Severity**: `{f.severity.value}`")
            lines.append(f"  - **Suggested Action**: {f.suggested_action}")

            if f.evidence:
                lines.append("  - **Evidence:**")
                for ev in f.evidence:
                    lines.append(f"    - *{ev.metric_name}*: {ev.details}")

            if f.draft_response:
                lines.append(f"  - **💬 Draft Reply:**\n    > _{f.draft_response}_")
            lines.append("")

    lines.append("---")
    lines.append("*MaintainerOps operates on explainable, deterministic heuristics. No automated actions or closures were performed.*")
    return "\n".join(lines)
