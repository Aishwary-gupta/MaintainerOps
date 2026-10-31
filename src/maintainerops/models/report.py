from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from maintainerops.models.base import BaseModel, Field
from maintainerops.models.findings import Finding


class ScanMetrics(BaseModel):
    total_issues_analyzed: int = 0
    total_prs_analyzed: int = 0
    incomplete_issues_count: int = 0
    potential_duplicates_count: int = 0
    blocked_prs_count: int = 0
    stale_items_count: int = 0
    good_first_issues_count: int = 0
    sentiment_alerts_count: int = 0
    actionable_high_priority_count: int = 0
    health_score: int = 100
    health_grade: str = "A"


class ScanReport(BaseModel):
    repository: str = ""
    scan_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_version: str = "0.2.0"
    metrics: ScanMetrics = Field(default_factory=ScanMetrics)
    findings: List[Finding] = Field(default_factory=list)
    health_summary: Optional[Dict[str, Any]] = None
