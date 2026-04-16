"""Unit tests for the profile risk score calculation."""

import pytest

from repops.analyzer.profile_scorer import compute_risk_score


def test_zero_posts_returns_zero():
    assert compute_risk_score(0, 0, 0.0, 0) == 0.0


def test_clean_profile():
    score = compute_risk_score(total_posts=100, flagged_posts=0, avg_hate_score=0.0, top_keyword_severity=0)
    assert score == 0.0


def test_fully_flagged_high_severity():
    score = compute_risk_score(
        total_posts=10,
        flagged_posts=10,
        avg_hate_score=0.95,
        top_keyword_severity=3,
    )
    assert score > 0.9


def test_low_flag_rate():
    score = compute_risk_score(
        total_posts=100,
        flagged_posts=2,
        avg_hate_score=0.65,
        top_keyword_severity=1,
    )
    assert score < 0.4


def test_score_capped_at_one():
    score = compute_risk_score(
        total_posts=1,
        flagged_posts=1,
        avg_hate_score=1.0,
        top_keyword_severity=3,
    )
    assert score <= 1.0


def test_score_is_float():
    score = compute_risk_score(50, 25, 0.7, 2)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
