from __future__ import annotations

import yfinance as yf
import pandas as pd
import streamlit as st
from typing import Optional

from config import METRICS, STATEMENT_METRICS


# ── Cached fetchers ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_info(symbol: str) -> dict:
    """Return the yfinance .info dict for a ticker (cached 1 h)."""
    try:
        return yf.Ticker(symbol).info
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_financials(symbol: str) -> pd.DataFrame:
    """Annual income statement (transposed so dates are rows)."""
    try:
        df = yf.Ticker(symbol).financials
        return df.T.sort_index()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cashflow(symbol: str) -> pd.DataFrame:
    """Annual cash-flow statement (transposed so dates are rows)."""
    try:
        df = yf.Ticker(symbol).cashflow
        return df.T.sort_index()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    """OHLCV price history for a given period."""
    try:
        df = yf.Ticker(symbol).history(period=period)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def validate_ticker(symbol: str) -> bool:
    """Return True if the symbol appears to be a valid ticker."""
    info = fetch_ticker_info(symbol)
    return bool(info and info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"))


# ── Metric extraction helpers ─────────────────────────────────────────────

def get_metric_series(symbol: str, metric_name: str) -> Optional[pd.Series]:
    """
    Return a pd.Series (index = year, values = metric) for a given metric name.
    Returns None if data is unavailable.
    """
    cfg = METRICS.get(metric_name)
    if cfg is None:
        return None

    source = cfg["source"]
    key    = cfg["key"]

    if source == "info":
        # Single point from info dict — wrap in a Series for consistency
        info  = fetch_ticker_info(symbol)
        value = info.get(key)
        if value is None:
            return None
        return pd.Series({pd.Timestamp.now().year: value}, name=metric_name)

    if source == "financials":
        df = fetch_financials(symbol)
    elif source == "cashflow":
        df = fetch_cashflow(symbol)
    else:
        return None

    if df.empty or key not in df.columns:
        return None

    series = df[key].dropna()
    series.index = pd.DatetimeIndex(series.index).year
    series.name  = metric_name
    return series.sort_index()


def get_snapshot(symbol: str) -> dict:
    info = fetch_ticker_info(symbol)

    def _pct(v):
        return f"{v*100:.1f}%" if v is not None else "—"

    def _b(v):
        if v is None:
            return "—"
        if abs(v) >= 1e12:
            return f"${v/1e12:.2f}T"
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"

    def _ratio(v):
        return f"{v:.2f}x" if v is not None else "—"

    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

    return {
        "Company":        info.get("longName", symbol),
        "Sector":         info.get("sector", "—"),
        "Industry":       info.get("industry", "—"),
        "Price":          f"${price:.2f}" if price else "—",
        "Market Cap":     _b(info.get("marketCap")),
        "P/E (TTM)":      _ratio(info.get("trailingPE")),
        "EPS (TTM)": f"${info.get('trailingEps', 0):.2f}" if info.get("trailingEps") else "—",
        "Div Yield":      _pct(info.get("dividendYield")),
        "52W High":       f"${info.get('fiftyTwoWeekHigh', 0):.2f}" if info.get("fiftyTwoWeekHigh") else "—",
        "52W Low":        f"${info.get('fiftyTwoWeekLow', 0):.2f}" if info.get("fiftyTwoWeekLow") else "—",
        "Profit Margin":  _pct(info.get("profitMargins")),
        "ROE":            _pct(info.get("returnOnEquity")),
        "description":    info.get("longBusinessSummary", ""),
    }


def get_comparable_metrics(sym1: str, sym2: str) -> pd.DataFrame:
    """
    Build a side-by-side DataFrame of key ratio/single-value metrics
    for the comparison section.
    """
    ratio_metrics = [
        ("P/E Ratio",        "trailingPE",        "x"),
        ("P/B Ratio",        "priceToBook",       "x"),
        ("Profit Margin",    "profitMargins",     "%"),
        ("ROE",              "returnOnEquity",    "%"),
        ("ROA",              "returnOnAssets",    "%"),
        ("EPS (TTM)",        "trailingEps",       "$"),
        ("Debt/Equity",      "debtToEquity",      "x"),
        ("Revenue Growth",   "revenueGrowth",     "%"),
        ("Div Yield",        "dividendYield",     "%"),
    ]

    info1 = fetch_ticker_info(sym1)
    info2 = fetch_ticker_info(sym2)

    rows = []
    for label, key, unit in ratio_metrics:
        v1 = info1.get(key)
        v2 = info2.get(key)

        def fmt(v, u):
            if v is None:
                return "—"
            if u == "%":
                return f"{v*100:.2f}%"
            if u == "$":
                return f"${v:.2f}"
            if u == "x":
                return f"{v:.2f}x"
            return f"{v:.2f}"

        rows.append({
            "Metric": label,
            sym1:     fmt(v1, unit),
            sym2:     fmt(v2, unit),
            "_v1":    v1,
            "_v2":    v2,
            "_unit":  unit,
        })

    return pd.DataFrame(rows)
