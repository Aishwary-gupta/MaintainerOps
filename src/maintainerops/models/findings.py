from enum import Enum
from typing import Any, Dict, List, Optional
from maintainerops.models.base import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingType(str, Enum):
    INCOMPLETE_ISSUE = "incomplete_issue"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    CI_FAILURE = "ci_failure"
    MERGE_CONFLICT = "merge_conflict"
    STALE_REVIEW = "stale_review"
    STALE_PR = "stale_pr"
    STALE_ISSUE = "stale_issue"
    GOOD_FIRST_ISSUE = "good_first_issue"
    COMMUNITY_SENTIMENT = "community_sentiment"
    HIGH_PRIORITY_ACTIONABLE = "high_priority_actionable"


class Evidence(BaseModel):
    metric_name: str
    observed_value: Any
    threshold_value: Optional[Any] = None
    details: str


class Finding(BaseModel):
    id: str = ""
    item_type: str = ""  # 'issue' or 'pull_request'
    item_number: int = 0
    item_title: str = ""
    item_url: str = ""
    finding_type: FindingType = FindingType.INCOMPLETE_ISSUE
    severity: Severity = Severity.MEDIUM
    confidence: float = 0.5
    summary: str = ""
    evidence: List[Evidence] = Field(default_factory=list)
    suggested_action: str = ""
    draft_response: Optional[str] = None
