import os
from pathlib import Path
from maintainerops.review import run_interactive_review
from maintainerops.state import load_state


def test_review_loop_accept_edit_skip_quit(tmp_path: Path, monkeypatch):
    state_file = str(tmp_path / "review_state.json")
    monkeypatch.setenv("MAINTAINEROPS_STATE_PATH", state_file)

    # Mock inputs:
    # 1st finding: 'a' (Accept)
    # 2nd finding: 'e' (Edit), then revised draft text 'Customized polite reply'
    # 3rd finding: 's' (Skip/Dismiss)
    # 4th finding: 'q' (Quit)
    inputs = iter(["a", "e", "Customized polite reply", "s", "q"])

    run_interactive_review(
        target="tests/fixtures/sample_repo.json",
        show_all=True,
        input_func=lambda prompt="": next(inputs),
    )

    state = load_state(state_file)
    assert len(state.decisions) == 3
    actions = [d.action for d in state.decisions]
    assert "accept" in actions
    assert "edit" in actions
    assert "skip" in actions

    # Check that skipped finding is in dismissed_ids
    assert len(state.dismissed_ids) >= 1
