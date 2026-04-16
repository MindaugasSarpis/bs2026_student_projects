"""Unit tests for the Aho-Corasick keyword matcher."""

import pytest

from repops.analyzer.keyword_matcher import (
    KeywordMatch,
    build_automaton,
    match_text,
    top_severity,
)


@pytest.fixture
def sample_automaton():
    patterns = [
        ("hate", 3),
        ("fake news", 2),
        ("violence", 3),
        ("test", 1),
    ]
    return build_automaton(patterns)


def test_single_match(sample_automaton):
    matches = match_text("This is a hate post", sample_automaton)
    assert len(matches) == 1
    assert matches[0].pattern == "hate"
    assert matches[0].severity == 3


def test_multiple_matches(sample_automaton):
    matches = match_text("hate and violence everywhere", sample_automaton)
    patterns = {m.pattern for m in matches}
    assert "hate" in patterns
    assert "violence" in patterns


def test_case_insensitive(sample_automaton):
    matches = match_text("HATE speech detected", sample_automaton)
    assert len(matches) == 1
    assert matches[0].pattern == "hate"


def test_multiword_match(sample_automaton):
    matches = match_text("This is fake news about something", sample_automaton)
    assert any(m.pattern == "fake news" for m in matches)


def test_no_match(sample_automaton):
    matches = match_text("This is a completely clean post.", sample_automaton)
    assert matches == []


def test_empty_text(sample_automaton):
    assert match_text("", sample_automaton) == []


def test_top_severity_empty():
    assert top_severity([]) == 0


def test_top_severity_returns_max():
    matches = [
        KeywordMatch(pattern="a", start=0, end=1, severity=1),
        KeywordMatch(pattern="b", start=2, end=3, severity=3),
        KeywordMatch(pattern="c", start=4, end=5, severity=2),
    ]
    assert top_severity(matches) == 3


def test_build_empty_automaton():
    A = build_automaton([])
    # Should not raise; just return no matches
    assert match_text("anything", A) == []
