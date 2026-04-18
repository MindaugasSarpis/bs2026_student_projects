from __future__ import annotations

import streamlit as st
import pandas as pd

from config import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_NEUTRAL, COLOR_BORDER, COLOR_SURFACE

def apply_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Space+Grotesk:wght@300;400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Mono', monospace;
        background-color: #0D1117;
        color: #C9D1D9;
    }

    /* Header */
    .main-header {
        display: flex;
        align-items: baseline;
        gap: 12px;
        border-bottom: 1px solid #30363D;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: #00D4AA;
        margin: 0;
        letter-spacing: -1px;
    }
    .main-subtitle {
        font-size: 0.75rem;
        color: #8B949E;
        letter-spacing: 3px;
        text-transform: uppercase;
    }

    /* Section header */
    .section-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #E6EDF3;
        border-left: 3px solid #00D4AA;
        padding-left: 10px;
        margin: 24px 0 16px;
        letter-spacing: 0.5px;
    }

    /* KPI card */
    .kpi-card {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 14px 16px;
        text-align: center;
    }
    .kpi-label {
        font-size: 0.65rem;
        color: #8B949E;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: #E6EDF3;
    }

    /* Health bar */
    .health-bar-wrap { margin: 6px 0; }
    .health-bar-bg {
        background: #21262D;
        border-radius: 4px;
        height: 10px;
        width: 100%;
        overflow: hidden;
    }
    .health-bar-fill {
        height: 10px;
        border-radius: 4px;
        transition: width 0.4s ease;
    }

    /* Comparison table */
    .compare-table { width: 100%; border-collapse: collapse; }
    .compare-table th, .compare-table td {
        padding: 8px 12px;
        font-size: 0.78rem;
        border-bottom: 1px solid #21262D;
        text-align: right;
    }
    .compare-table th { color: #8B949E; text-align: left; }
    .compare-table td:first-child { text-align: left; color: #8B949E; }
    .compare-table tr:hover { background: #1C2128; }

    /* Verdict card */
    .verdict-card {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 6px 0;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* Tag pill */
    .tag-pill {
        display: inline-block;
        background: #21262D;
        border: 1px solid #30363D;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.68rem;
        color: #8B949E;
        margin: 2px;
    }

    /* Streamlit overrides */
    .stSelectbox > div > div { background: #161B22 !important; border-color: #30363D !important; }
    .stTextInput > div > div > input { background: #161B22 !important; border-color: #30363D !important; color: #C9D1D9 !important; }
    div[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; }
    .stTabs [data-baseweb="tab"] { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #00D4AA; }
    section[data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="main-header">
        <span class="main-title">MarketLens</span>
        <span class="main-subtitle">Equity Intelligence Dashboard</span>
    </div>
    """, unsafe_allow_html=True)


def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def kpi_row(snapshot: dict, exclude: tuple = ("Company", "Sector", "Industry", "description")):
    """Render a horizontal row of KPI cards from a snapshot dict."""
    keys = [k for k in snapshot if k not in exclude]
    cols = st.columns(len(keys))
    for col, key in zip(cols, keys):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{key}</div>
                <div class="kpi-value">{snapshot[key]}</div>
            </div>
            """, unsafe_allow_html=True)


def company_banner(snapshot: dict, color: str = COLOR_PRIMARY):
    """Render company name, sector pill, and description."""
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:1.35rem;font-weight:700;color:{color};">
            {snapshot.get('Company','—')}
        </span>
        &nbsp;
        <span class="tag-pill">{snapshot.get('Sector','—')}</span>
        <span class="tag-pill">{snapshot.get('Industry','—')}</span>
    </div>
    """, unsafe_allow_html=True)

    desc = snapshot.get("description", "")
    if desc:
        with st.expander("About this company", expanded=False):
            st.markdown(f'<span style="font-size:0.8rem;color:#8B949E;">{desc[:800]}{"…" if len(desc)>800 else ""}</span>', unsafe_allow_html=True)


# ── Health score gauge ────────────────────────────────────────────────────

def health_gauge(score: float, notes: list[str], symbol: str):
    """Render a simple health bar with colour coding and notes."""
    if score >= 70:
        colour = "#00D4AA"
        label  = "Strong"
    elif score >= 45:
        colour = "#F0B429"
        label  = "Moderate"
    else:
        colour = "#FF6B6B"
        label  = "Weak"

    st.markdown(f"""
    <div style="margin:10px 0 4px;">
        <span style="font-size:0.7rem;color:#8B949E;letter-spacing:2px;text-transform:uppercase;">
            FUNDAMENTAL HEALTH — {symbol}
        </span>
        <span style="float:right;font-size:0.9rem;font-weight:600;color:{colour};">
            {score}/100 &nbsp; {label}
        </span>
    </div>
    <div class="health-bar-bg">
        <div class="health-bar-fill" style="width:{score}%;background:{colour};"></div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Health breakdown", expanded=False):
        for note in notes:
            st.markdown(f"- {note}")


# ── Stats table ───────────────────────────────────────────────────────────

def stats_table(data: dict, title: str = ""):
    """Render a compact key-value stats table."""
    if title:
        st.markdown(f'<div style="font-size:0.7rem;color:#8B949E;letter-spacing:2px;text-transform:uppercase;margin:8px 0 4px;">{title}</div>', unsafe_allow_html=True)

    rows_html = "".join(
        f"<tr><td>{k}</td><td style='color:#E6EDF3;text-align:right;'>{v}</td></tr>"
        for k, v in data.items()
    )
    st.markdown(f"""
    <table class="compare-table">
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)


def comparison_table(df: pd.DataFrame, sym1: str, sym2: str):
    """Render a styled comparison table with win-highlights."""
    if df.empty:
        st.info("No comparison data available.")
        return

    display_df = df[["Metric", sym1, sym2]].copy()

    def highlight_row(row):
        # For ratio/percent metrics, lower or higher might be better
        return ["", "", ""]

    # Plain table — Streamlit's st.dataframe for interactivity
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="medium"),
            sym1:     st.column_config.TextColumn(sym1, width="small"),
            sym2:     st.column_config.TextColumn(sym2, width="small"),
        },
    )

def verdict_cards(verdicts: list[str]):
    for v in verdicts:
        st.markdown(f'<div class="verdict-card">{v}</div>', unsafe_allow_html=True)


def ticker_input(label: str, default: str, key: str) -> str:
    raw = st.text_input(label, value=default, key=key, placeholder="e.g. AAPL")
    return raw.strip().upper()
