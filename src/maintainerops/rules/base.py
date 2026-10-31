from abc import ABC, abstractmethod
from typing import List
from maintainerops.models.findings import Finding
from maintainerops.models.github import IssueItem, PullRequestItem


class BaseRule(ABC):
    """Abstract base class for all MaintainerOps triage and analysis rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the rule."""
        pass

    @abstractmethod
    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        """Runs the rule evaluation and returns generated findings."""
        pass
