import pytest
import streamlit as st
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_st_calls(monkeypatch):
    """
    Patch Streamlit UI calls globally so tests don't require a running
    Streamlit server. st.stop() in particular would raise StopException
    and abort test execution without this.
    """

    monkeypatch.setattr(st, 'info', MagicMock())
    monkeypatch.setattr(st, 'success', MagicMock())
    monkeypatch.setattr(st, 'warning', MagicMock())
    monkeypatch.setattr(st, 'error', MagicMock())
    monkeypatch.setattr(st, 'stop', MagicMock())

    spinner_ctx = MagicMock()
    spinner_ctx.__enter__ = MagicMock(return_value=None)
    spinner_ctx.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(st, 'spinner', MagicMock(return_value=spinner_ctx))

    def _make_columns(spec, **kwargs):
        n = len(spec) if hasattr(spec, '__len__') else int(spec)
        return [MagicMock() for _ in range(n)]

    monkeypatch.setattr(st, 'columns', MagicMock(side_effect=_make_columns))
    monkeypatch.setattr(st, 'progress', MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(st, 'empty', MagicMock(return_value=MagicMock()))
