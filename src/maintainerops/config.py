from pathlib import Path
from typing import Optional
from maintainerops.models.base import BaseModel
import yaml


class Config(BaseModel):
    similarity_threshold: float = 0.65
    min_body_length: int = 50
    check_completeness: bool = True
    check_duplicates: bool = True
    check_pull_requests: bool = True
    check_priority: bool = True
    check_stale: bool = True
    check_good_first_issues: bool = True
    check_sentiment: bool = True
    stale_days_threshold: int = 14


def load_config(config_path: Optional[str] = None) -> Config:
    """Loads configuration from YAML or returns defaults."""
    default_cfg = Config()
    target_path = Path(config_path) if config_path else Path(".maintainerops.yml")

    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return Config(**data)
        except Exception:
            return default_cfg

    return default_cfg
