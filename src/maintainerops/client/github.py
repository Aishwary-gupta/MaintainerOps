import os
from typing import List, Optional, Tuple
import httpx
from maintainerops.models.github import CheckRun, IssueItem, PullRequestItem


class GitHubClient:
    """GitHub REST API v3 client with pagination, auth, and rate limit handling."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MaintainerOps-Triage-Engine/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.client = httpx.Client(base_url=self.BASE_URL, headers=headers, timeout=20.0)

    def fetch_repo_items(
        self, owner: str, repo: str, max_items: int = 50
    ) -> Tuple[List[IssueItem], List[PullRequestItem]]:
        """Fetches recent open issues and pull requests."""
        url = f"/repos/{owner}/{repo}/issues"
        params = {"state": "open", "per_page": min(max_items, 100)}

        response = self.client.get(url, params=params)
        if response.status_code == 403:
            msg = response.json().get("message", "Rate limit exceeded")
            raise PermissionError(f"GitHub API Error (403): {msg}. Set GITHUB_TOKEN environment variable.")
        elif response.status_code == 404:
            raise FileNotFoundError(f"Repository {owner}/{repo} not found or is private.")
        response.raise_for_status()

        raw_items = response.json()
        issues: List[IssueItem] = []
        prs: List[PullRequestItem] = []

        for item in raw_items:
            is_pr = "pull_request" in item
            if is_pr:
                # Fetch detailed PR status if possible
                pr_num = item["number"]
                pr_item = self._fetch_pr_detail(owner, repo, pr_num, item)
                prs.append(pr_item)
            else:
                issues.append(
                    IssueItem(
                        number=item["number"],
                        title=item["title"],
                        body=item.get("body") or "",
                        state=item.get("state", "open"),
                        user={"login": item["user"]["login"]} if item.get("user") else None,
                        labels=[{"name": l["name"]} for l in item.get("labels", [])],
                        created_at=item["created_at"],
                        updated_at=item["updated_at"],
                        html_url=item["html_url"],
                        comments_count=item.get("comments", 0),
                        reactions_count=item.get("reactions", {}).get("total_count", 0),
                        is_pull_request=False,
                    )
                )

        return issues, prs

    def _fetch_pr_detail(self, owner: str, repo: str, pr_number: int, summary_item: dict) -> PullRequestItem:
        """Fetches PR detail including mergeable status and check runs."""
        mergeable = None
        mergeable_state = "unknown"
        draft = summary_item.get("draft", False)
        check_runs: List[CheckRun] = []

        try:
            detail_res = self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
            if detail_res.status_code == 200:
                data = detail_res.json()
                mergeable = data.get("mergeable")
                mergeable_state = data.get("mergeable_state", "unknown")
                draft = data.get("draft", False)
        except Exception:
            pass

        # Attempt to fetch check-runs for the PR head commit
        try:
            checks_res = self.client.get(f"/repos/{owner}/{repo}/commits/pull/{pr_number}/head/check-runs")
            if checks_res.status_code == 200:
                for c in checks_res.json().get("check_runs", []):
                    check_runs.append(
                        CheckRun(
                            id=c["id"],
                            name=c["name"],
                            status=c["status"],
                            conclusion=c.get("conclusion"),
                            html_url=c.get("html_url"),
                        )
                    )
        except Exception:
            pass

        return PullRequestItem(
            number=pr_number,
            title=summary_item["title"],
            body=summary_item.get("body") or "",
            state=summary_item.get("state", "open"),
            user={"login": summary_item["user"]["login"]} if summary_item.get("user") else None,
            labels=[{"name": l["name"]} for l in summary_item.get("labels", [])],
            created_at=summary_item["created_at"],
            updated_at=summary_item["updated_at"],
            html_url=summary_item["html_url"],
            draft=draft,
            mergeable=mergeable,
            mergeable_state=mergeable_state,
            check_runs=check_runs,
        )

    def close(self):
        self.client.close()
