import json
from pathlib import Path
from typing import List, Tuple
from maintainerops.models.github import IssueItem, PullRequestItem


def load_fixture_data(file_path: str) -> Tuple[str, List[IssueItem], List[PullRequestItem]]:
    """Loads repository metadata, issues, and PRs from a local JSON fixture file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    repo_name = data.get("repository", "local/fixture-repo")
    issues = [IssueItem(**item) for item in data.get("issues", [])]
    prs = [PullRequestItem(**item) for item in data.get("pull_requests", [])]

    return repo_name, issues, prs
