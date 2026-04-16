"""O(n) multi-keyword matcher using Aho-Corasick automaton.

Matches are case-insensitive. The automaton is built once and cached per
keyword set fingerprint to avoid rebuilding on every call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import ahocorasick

from repops.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class KeywordMatch:
    pattern: str
    start: int
    end: int
    severity: int  # 1 low | 2 medium | 3 high


def build_automaton(patterns: list[tuple[str, int]]) -> ahocorasick.Automaton:
    """Build an Aho-Corasick automaton from (pattern, severity) pairs."""
    A = ahocorasick.Automaton()
    for idx, (pattern, severity) in enumerate(patterns):
        A.add_word(pattern.lower(), (idx, pattern, severity))
    A.make_automaton()
    logger.debug("aho_corasick_built", pattern_count=len(patterns))
    return A


def match_text(
    text: str,
    automaton: ahocorasick.Automaton,
) -> list[KeywordMatch]:
    """Return all keyword matches found in `text` (case-insensitive)."""
    if not text or not len(automaton):
        return []

    lower = text.lower()
    matches: list[KeywordMatch] = []

    for end_idx, (_, pattern, severity) in automaton.iter(lower):
        start_idx = end_idx - len(pattern) + 1
        matches.append(
            KeywordMatch(pattern=pattern, start=start_idx, end=end_idx, severity=severity)
        )

    return matches


def match_text_regex(text: str, patterns: list[tuple[str, int]]) -> list[KeywordMatch]:
    """Fallback regex matcher for patterns that need word-boundary matching."""
    matches: list[KeywordMatch] = []
    for pattern, severity in patterns:
        for m in re.finditer(rf"\b{re.escape(pattern)}\b", text, re.IGNORECASE):
            matches.append(
                KeywordMatch(
                    pattern=pattern,
                    start=m.start(),
                    end=m.end(),
                    severity=severity,
                )
            )
    return matches


def top_severity(matches: list[KeywordMatch]) -> int:
    """Return the highest severity across all matches (0 if no matches)."""
    if not matches:
        return 0
    return max(m.severity for m in matches)
