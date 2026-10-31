from datetime import datetime
from typing import Any, Dict, List, Optional
from maintainerops.models.base import BaseModel, Field


class Label(BaseModel):
    name: str
    color: Optional[str] = None
    description: Optional[str] = None


class User(BaseModel):
    login: str
    id: Optional[int] = None
    html_url: Optional[str] = None


class CheckRun(BaseModel):
    id: int
    name: str
    status: str  # queued, in_progress, completed
    conclusion: Optional[str] = None  # success, failure, neutral, cancelled, timed_out, action_required
    html_url: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IssueItem(BaseModel):
    number: int
    title: str
    body: Optional[str] = ""
    state: str = "open"  # open, closed
    user: Optional[User] = None
    labels: List[Label] = Field(default_factory=list)
    created_at: Any = None
    updated_at: Any = None
    closed_at: Optional[Any] = None
    html_url: str = ""
    comments_count: int = 0
    reactions_count: int = 0
    is_pull_request: bool = False


class PullRequestItem(BaseModel):
    number: int
    title: str
    body: Optional[str] = ""
    state: str = "open"
    user: Optional[User] = None
    labels: List[Label] = Field(default_factory=list)
    created_at: Any = None
    updated_at: Any = None
    html_url: str = ""
    draft: bool = False
    mergeable: Optional[bool] = None
    mergeable_state: Optional[str] = "clean"  # clean, dirty, blocked, unknown
    requested_reviewers: List[User] = Field(default_factory=list)
    check_runs: List[CheckRun] = Field(default_factory=list)
