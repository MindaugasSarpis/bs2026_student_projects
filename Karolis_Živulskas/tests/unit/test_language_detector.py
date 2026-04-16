"""Unit tests for language detection and the is_supported() gate."""

from unittest.mock import patch

import pytest

from repops.analyzer.language_detector import detect_language, is_supported


def test_english_detected():
    assert detect_language("This is a clearly English sentence for testing purposes.") == "en"


def test_short_text_returns_und():
    # Below _MIN_TEXT_LENGTH → always undetermined
    assert detect_language("hi") == "und"


def test_empty_string_returns_und():
    assert detect_language("") == "und"


def test_whitespace_only_returns_und():
    assert detect_language("     ") == "und"


def test_returns_string():
    result = detect_language("Some text here for testing detection purposes.")
    assert isinstance(result, str)
    assert len(result) >= 2


# -----------------------------------------------------------------------
# is_supported() — checks against settings.supported_languages
# -----------------------------------------------------------------------
def test_english_is_supported():
    assert is_supported("en") is True


def test_lithuanian_is_supported():
    assert is_supported("lt") is True


def test_russian_not_supported():
    assert is_supported("ru") is False


def test_undetermined_not_supported():
    assert is_supported("und") is False


def test_unknown_code_not_supported():
    assert is_supported("zh") is False
