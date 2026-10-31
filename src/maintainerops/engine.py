import os
from typing import List, Optional, Tuple
from maintainerops.ai import AIEnrichmentProvider
from maintainerops.client.fixtures import load_fixture_data
from maintainerops.client.github import GitHubClient
from maintainerops.config import Config, load_config
from maintainerops.models.findings import Finding, FindingType
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.models.report import ScanMetrics, ScanReport
from maintainerops.rules.completeness import CompletenessRule
from maintainerops.rules.duplicates import DuplicateRule
from maintainerops.rules.good_first_issue import GoodFirstIssueRule
from maintainerops.rules.health import calculate_repository_health
from maintainerops.rules.priority import PriorityRule
from maintainerops.rules.pull_requests import PullRequestHealthRule
from maintainerops.rules.sentiment import SentimentRule
from maintainerops.rules.stale import StaleRule
from maintainerops.templates import IssueTemplate, load_repository_templates


def analyze_repository(
    repo_name: str,
    issues: List[IssueItem],
    prs: List[PullRequestItem],
    cfg: Optional[Config] = None,
    templates: Optional[List[IssueTemplate]] = None,
    use_ai: bool = False,
) -> ScanReport:
    """Runs the explainable deterministic rule engine over issues and pull requests."""
    if cfg is None:
        cfg = Config()

    findings: List[Finding] = []

    # 1. Completeness Rule (Template-Aware)
    if cfg.check_completeness:
        completeness_rule = CompletenessRule(templates=templates)
        findings.extend(completeness_rule.analyze(issues, prs))

    # 2. Duplicate Detection
    if cfg.check_duplicates:
        dup_rule = DuplicateRule(similarity_threshold=cfg.similarity_threshold)
        findings.extend(dup_rule.analyze(issues, prs))

    # 3. Pull Request Health
    if cfg.check_pull_requests:
        pr_rule = PullRequestHealthRule()
        findings.extend(pr_rule.analyze(issues, prs))

    # 4. Actionable Priority
    if cfg.check_priority:
        priority_rule = PriorityRule()
        findings.extend(priority_rule.analyze(issues, prs))

    # 5. Stale Item & Lifecycle Rule
    if cfg.check_stale:
        stale_rule = StaleRule(stale_days_threshold=cfg.stale_days_threshold)
        findings.extend(stale_rule.analyze(issues, prs))

    # 6. Good First Issue Candidate Rule
    if cfg.check_good_first_issues:
        gfi_rule = GoodFirstIssueRule()
        findings.extend(gfi_rule.analyze(issues, prs))

    # 7. Community Urgency & Sentiment Rule
    if cfg.check_sentiment:
        sentiment_rule = SentimentRule()
        findings.extend(sentiment_rule.analyze(issues, prs))

    # Optional AI Enrichment (Tone refinement & thread summarization)
    if use_ai:
        ai_provider = AIEnrichmentProvider()
        if ai_provider.is_available():
            for f in findings:
                if f.draft_response:
                    refined = ai_provider.refine_draft(
                        original_draft=f.draft_response,
                        issue_title=f.item_title,
                        issue_body="",
                    )
                    f.draft_response = refined

    # Compute Repository Health Index and Letter Grade
    health_score, health_grade, health_summary = calculate_repository_health(
        issues=issues,
        pull_requests=prs,
        findings=findings,
    )

    metrics = ScanMetrics(
        total_issues_analyzed=len(issues),
        total_prs_analyzed=len(prs),
        incomplete_issues_count=len([f for f in findings if f.finding_type == FindingType.INCOMPLETE_ISSUE]),
        potential_duplicates_count=len([f for f in findings if f.finding_type == FindingType.POSSIBLE_DUPLICATE]),
        blocked_prs_count=len(
            [f for f in findings if f.finding_type in [FindingType.CI_FAILURE, FindingType.MERGE_CONFLICT]]
        ),
        stale_items_count=len(
            [f for f in findings if f.finding_type in [FindingType.STALE_PR, FindingType.STALE_ISSUE, FindingType.STALE_REVIEW]]
        ),
        good_first_issues_count=len([f for f in findings if f.finding_type == FindingType.GOOD_FIRST_ISSUE]),
        sentiment_alerts_count=len([f for f in findings if f.finding_type == FindingType.COMMUNITY_SENTIMENT]),
        actionable_high_priority_count=len([f for f in findings if f.finding_type == FindingType.HIGH_PRIORITY_ACTIONABLE]),
        health_score=health_score,
        health_grade=health_grade,
    )

    return ScanReport(
        repository=repo_name,
        metrics=metrics,
        findings=findings,
        health_summary=health_summary,
    )


def load_target_data(target: str) -> Tuple[str, List[IssueItem], List[PullRequestItem]]:
    """Loads repository data from either local JSON fixture or live GitHub API."""
    is_local_file = os.path.exists(target) or target.endswith(".json")
    if is_local_file:
        return load_fixture_data(target)

    if "/" not in target:
        raise ValueError("Invalid repository format. Use 'owner/repo' or provide a local JSON file path.")

    owner, repo = target.split("/", 1)
    client = GitHubClient()
    try:
        issues, prs = client.fetch_repo_items(owner, repo)
        return f"{owner}/{repo}", issues, prs
    finally:
        client.close()


def run_scan(
    target: str,
    config: Optional[Config] = None,
    templates: Optional[List[IssueTemplate]] = None,
    use_ai: bool = False,
) -> ScanReport:
    """End-to-end scanner execution from target identifier to ScanReport."""
    if config is None:
        config = load_config()

    if templates is None:
        # Check local templates or repository templates
        templates = load_repository_templates()

    repo_name, issues, prs = load_target_data(target)
    return analyze_repository(repo_name, issues, prs, config, templates=templates, use_ai=use_ai)
