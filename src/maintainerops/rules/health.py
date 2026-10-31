from typing import Any, Dict, List, Tuple
from maintainerops.models.findings import Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem


def calculate_repository_health(
    issues: List[IssueItem],
    pull_requests: List[PullRequestItem],
    findings: List[Finding],
) -> Tuple[int, str, Dict[str, Any]]:
    """Calculates a deterministic 0-100 Repository Health Index and letter grade."""
    open_issues = [i for i in issues if not i.is_pull_request and i.state == "open"]
    open_prs = [p for p in pull_requests if p.state == "open" and not p.draft]

    total_open_items = len(open_issues) + len(open_prs)
    if total_open_items == 0:
        return 100, "A+", {
            "status": "pristine",
            "message": "Zero open triage backlog. Pristine repository health.",
            "issue_quality_score": 100,
            "pr_pipeline_score": 100,
            "backlog_freshness_score": 100,
            "triage_burden": "Minimal",
            "primary_bottleneck": "None",
        }

    # 1. Issue Quality Score (0 - 100)
    incomplete_count = len([f for f in findings if f.finding_type == FindingType.INCOMPLETE_ISSUE])
    if open_issues:
        issue_quality_ratio = max(0.0, (len(open_issues) - incomplete_count) / len(open_issues))
        issue_quality_score = int(round(issue_quality_ratio * 100))
    else:
        issue_quality_score = 100

    # 2. PR Pipeline Health (0 - 100)
    blocked_pr_count = len(
        [f for f in findings if f.finding_type in [FindingType.CI_FAILURE, FindingType.MERGE_CONFLICT]]
    )
    if open_prs:
        pr_health_ratio = max(0.0, (len(open_prs) - blocked_pr_count) / len(open_prs))
        pr_pipeline_score = int(round(pr_health_ratio * 100))
    else:
        pr_pipeline_score = 100

    # 3. Backlog Freshness & Stale Ratio (0 - 100)
    stale_count = len(
        [f for f in findings if f.finding_type in [FindingType.STALE_PR, FindingType.STALE_ISSUE, FindingType.STALE_REVIEW]]
    )
    freshness_ratio = max(0.0, (total_open_items - stale_count) / total_open_items)
    backlog_freshness_score = int(round(freshness_ratio * 100))

    # 4. Critical Sentiment penalty
    critical_sentiment_count = len(
        [f for f in findings if f.finding_type == FindingType.COMMUNITY_SENTIMENT and f.severity == Severity.CRITICAL]
    )
    sentiment_penalty = min(20, critical_sentiment_count * 10)

    # Weighted Composite: 35% PR Pipeline, 35% Issue Quality, 30% Backlog Freshness
    composite_raw = (
        (pr_pipeline_score * 0.35)
        + (issue_quality_score * 0.35)
        + (backlog_freshness_score * 0.30)
        - sentiment_penalty
    )
    composite_score = max(5, min(100, int(round(composite_raw))))

    # Letter Grade
    if composite_score >= 95:
        grade = "A+"
    elif composite_score >= 85:
        grade = "A"
    elif composite_score >= 75:
        grade = "B"
    elif composite_score >= 65:
        grade = "C"
    elif composite_score >= 50:
        grade = "D"
    else:
        grade = "F"

    # Triage Burden categorization
    if composite_score >= 85:
        burden = "Low"
    elif composite_score >= 70:
        burden = "Moderate"
    elif composite_score >= 50:
        burden = "High"
    else:
        burden = "Critical"

    # Primary Bottleneck detection
    bottlenecks = []
    if blocked_pr_count > 0:
        bottlenecks.append(f"{blocked_pr_count} PR(s) blocked by failing CI or merge conflicts")
    if incomplete_count > 0:
        bottlenecks.append(f"{incomplete_count} incomplete bug report(s)")
    if stale_count > 0:
        bottlenecks.append(f"{stale_count} dormant or stale item(s)")
    if critical_sentiment_count > 0:
        bottlenecks.append(f"{critical_sentiment_count} urgent outage/sentiment alert(s)")

    primary_bottleneck = bottlenecks[0] if bottlenecks else "Healthy repository with no critical bottlenecks"

    summary = {
        "status": "computed",
        "composite_score": composite_score,
        "grade": grade,
        "triage_burden": burden,
        "primary_bottleneck": primary_bottleneck,
        "all_bottlenecks": bottlenecks,
        "issue_quality_score": issue_quality_score,
        "pr_pipeline_score": pr_pipeline_score,
        "backlog_freshness_score": backlog_freshness_score,
        "breakdown": {
            "incomplete_issues": incomplete_count,
            "blocked_prs": blocked_pr_count,
            "stale_items": stale_count,
            "critical_sentiments": critical_sentiment_count,
        },
    }

    return composite_score, grade, summary
