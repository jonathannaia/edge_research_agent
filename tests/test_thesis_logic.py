from src.services.thesis_service import evaluate_thesis_signal


def test_strengthening_to_weakening_is_invalidating():
    assert evaluate_thesis_signal("Strengthening", "Weakening", score_delta=-0.5) == "invalidating"


def test_unchanged_to_weakening_with_negative_delta_is_invalidating():
    assert evaluate_thesis_signal("Unchanged", "Weakening", score_delta=-1.0) == "invalidating"


def test_weakening_to_strengthening_is_confirming():
    assert evaluate_thesis_signal("Weakening", "Strengthening", score_delta=0.5) == "confirming"


def test_unchanged_to_strengthening_with_positive_delta_is_confirming():
    assert evaluate_thesis_signal("Unchanged", "Strengthening", score_delta=0.3) == "confirming"


def test_unchanged_to_unchanged_is_neutral():
    assert evaluate_thesis_signal("Unchanged", "Unchanged", score_delta=0.0) == "neutral"


def test_strengthening_to_strengthening_with_no_move_is_neutral():
    # already strengthening and stays strengthening with no further score improvement
    assert evaluate_thesis_signal("Strengthening", "Strengthening", score_delta=0.0) == "neutral"


def test_weakening_to_weakening_is_neutral_transition_but_still_weak():
    # no NEW transition occurred (already weakening), and score_delta is flat, so this is
    # treated as neutral (no fresh confirming/invalidating signal this cycle)
    assert evaluate_thesis_signal("Weakening", "Weakening", score_delta=0.0) == "neutral"
