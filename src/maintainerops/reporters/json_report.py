import json
from maintainerops.models.report import ScanReport


def render_json(report: ScanReport, indent: int = 2) -> str:
    """Serializes the ScanReport into clean JSON format."""
    return json.dumps(report.model_dump(mode="json"), indent=indent)
