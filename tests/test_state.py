from pathlib import Path
from maintainerops.models.findings import Finding, FindingType
from maintainerops.state import dismiss_finding, is_dismissed, load_state, record_decision


def test_state_dismiss_and_check(tmp_path: Path):
    state_file = str(tmp_path / "state.json")

    assert not is_dismissed("find_123", custom_path=state_file)

    dismiss_finding("find_123", custom_path=state_file)
    assert is_dismissed("find_123", custom_path=state_file)

    state = load_state(custom_path=state_file)
    assert "find_123" in state.dismissed_ids


def test_state_record_decision(tmp_path: Path):
    state_file = str(tmp_path / "state.json")
    f = Finding(id="find_456", item_number=101, item_title="Test Issue", draft_response="Hello")

    record_decision("accept", f, draft_response="Hello edited", custom_path=state_file)
    state = load_state(custom_path=state_file)

    assert len(state.decisions) == 1
    assert state.decisions[0].action == "accept"
    assert state.decisions[0].item_number == 101
    assert state.decisions[0].draft_response == "Hello edited"
