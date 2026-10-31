import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from maintainerops.models.base import BaseModel, Field

DEFAULT_STATE_FILE = ".maintainerops_state.json"


class TriageDecision(BaseModel):
    action: str  # accept, edit, skip
    finding_id: str
    item_number: int
    item_type: str
    item_title: str
    draft_response: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: Optional[str] = None


class MaintainerState(BaseModel):
    dismissed_ids: List[str] = Field(default_factory=list)
    decisions: List[TriageDecision] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def get_state_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    env_path = os.getenv("MAINTAINEROPS_STATE_PATH")
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_STATE_FILE)


def load_state(custom_path: Optional[str] = None) -> MaintainerState:
    path = get_state_path(custom_path)
    if not path.exists():
        return MaintainerState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MaintainerState(**data)
    except Exception:
        return MaintainerState()


def save_state(state: MaintainerState, custom_path: Optional[str] = None) -> None:
    path = get_state_path(custom_path)
    state.updated_at = datetime.now(timezone.utc).isoformat()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.model_dump(), indent=2), encoding="utf-8")
    except Exception as e:
        # Gracefully handle write errors without crashing
        pass


def is_dismissed(finding_id: str, custom_path: Optional[str] = None) -> bool:
    state = load_state(custom_path)
    return finding_id in state.dismissed_ids


def dismiss_finding(finding_id: str, custom_path: Optional[str] = None) -> None:
    state = load_state(custom_path)
    if finding_id not in state.dismissed_ids:
        state.dismissed_ids.append(finding_id)
        save_state(state, custom_path)


def record_decision(
    action: str,
    finding: Any,
    draft_response: Optional[str] = None,
    notes: Optional[str] = None,
    custom_path: Optional[str] = None,
) -> None:
    state = load_state(custom_path)
    decision = TriageDecision(
        action=action,
        finding_id=getattr(finding, "id", str(finding)),
        item_number=getattr(finding, "item_number", 0),
        item_type=getattr(finding, "item_type", "unknown"),
        item_title=getattr(finding, "item_title", ""),
        draft_response=draft_response or getattr(finding, "draft_response", None),
        notes=notes,
    )
    state.decisions.append(decision)
    if action == "skip" and decision.finding_id not in state.dismissed_ids:
        state.dismissed_ids.append(decision.finding_id)
    save_state(state, custom_path)
