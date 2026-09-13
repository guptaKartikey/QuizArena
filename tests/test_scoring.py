import pytest
from backend.scoring import calculate_score

def test_correct_answer_scoring():
    pts, bonus = calculate_score(
        is_correct=True,
        response_time=2.0,
        total_time=30.0,
        correct_points=10.0,
        enable_speed_bonus=True
    )
    assert pts > 10.0
    assert bonus > 0.0

def test_negative_marking():
    # Enabled
    pts_neg, _ = calculate_score(
        is_correct=False,
        response_time=5.0,
        total_time=30.0,
        wrong_points=-5.0,
        enable_negative_marking=True
    )
    assert pts_neg == -5.0

    # Disabled
    pts_no_neg, _ = calculate_score(
        is_correct=False,
        response_time=5.0,
        total_time=30.0,
        wrong_points=-5.0,
        enable_negative_marking=False
    )
    assert pts_no_neg == 0.0
