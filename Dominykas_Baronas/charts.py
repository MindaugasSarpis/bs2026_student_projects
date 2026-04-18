from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_BG, COLOR_SURFACE,
    COLOR_BORDER, COLOR_NEUTRAL, PLOTLY_TEMPLATE,
)


def _base_layout(**kwargs) -> dict:
    base = dict(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'IBM Plex Mono', monospace", color="#C9D1D9"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=COLOR_BORDER,
            showgrid=True,
            zeroline=False,
        ),
    )
    base.update(kwargs)
    return base

def price_chart(
    price_df: pd.DataFrame,
    symbol: str,
    color: str = COLOR_PRIMARY,
) -> go.Figure:
    if price_df.empty:
        return _empty_fig("No price data available")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.02,
    )

    fig.add_trace(
        go.Candlestick(
            x=price_df.index,
            open=price_df["Open"],
            high=price_df["High"],
            low=price_df["Low"],
            close=price_df["Close"],
            name=symbol,
            increasing_line_color=color,
            decreasing_line_color=COLOR_SECONDARY,
            increasing_fillcolor=color,
            decreasing_fillcolor=COLOR_SECONDARY,
        ),
        row=1, col=1,
    )

    vol_colors = [
        color if c >= o else COLOR_SECONDARY
        for o, c in zip(price_df["Open"], price_df["Close"])
    ]
    fig.add_trace(
        go.Bar(
            x=price_df.index,
            y=price_df["Volume"],
            name="Volume",
            marker_color=vol_colors,
            opacity=0.6,
        ),
        row=2, col=1,
    )

    layout = _base_layout(
        title=dict(text=f"{symbol} — Price & Volume", x=0.02),
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )
    layout["yaxis2"] = dict(gridcolor=COLOR_BORDER, showgrid=True, zeroline=False)
    fig.update_layout(**layout)
    return fig


def price_overlay_chart(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    sym1: str,
    sym2: str,
) -> go.Figure:
    if df1.empty or df2.empty:
        return _empty_fig("Price data unavailable for one or both tickers")

    c1 = df1["Close"].rename(sym1)
    c2 = df2["Close"].rename(sym2)
    combined = pd.concat([c1, c2], axis=1).dropna()

    rebased = combined / combined.iloc[0] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rebased.index, y=rebased[sym1],
        name=sym1, line=dict(color=COLOR_PRIMARY, width=2),
        fill="tozeroy", fillcolor=f"rgba(0,212,170,0.06)",
    ))
    fig.add_trace(go.Scatter(
        x=rebased.index, y=rebased[sym2],
        name=sym2, line=dict(color=COLOR_SECONDARY, width=2),
        fill="tozeroy", fillcolor=f"rgba(255,107,107,0.06)",
    ))

    fig.update_layout(**_base_layout(
        title=dict(text="Relative Price Performance (rebased to 100)", x=0.02),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    ))
    return fig

def metric_bar_chart(
    series: pd.Series,
    symbol: str,
    metric_name: str,
    color: str = COLOR_PRIMARY,
) -> go.Figure:
    if series is None or series.empty:
        return _empty_fig(f"No data for {metric_name}")

    y = series.values
    x = series.index.astype(str)

    bar_colors = [
        color if (i == 0 or y[i] >= y[i - 1]) else COLOR_SECONDARY
        for i in range(len(y))
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=y,
        marker_color=bar_colors,
        text=[_fmt_val(v, metric_name) for v in y],
        textposition="outside",
        textfont=dict(size=10),
        name=symbol,
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="lines+markers",
        line=dict(color=color, width=1.5, dash="dot"),
        marker=dict(size=5),
        showlegend=False,
    ))

    fig.update_layout(**_base_layout(
        title=dict(text=f"{symbol} — {metric_name} (Annual)", x=0.02),
        showlegend=False,
        yaxis_tickformat=_tick_format(metric_name),
    ))
    return fig


def metric_comparison_chart(
    s1: pd.Series,
    s2: pd.Series,
    sym1: str,
    sym2: str,
    metric_name: str,
) -> go.Figure:
    if (s1 is None or s1.empty) and (s2 is None or s2.empty):
        return _empty_fig(f"No data for {metric_name}")

    fig = go.Figure()

    if s1 is not None and not s1.empty:
        fig.add_trace(go.Bar(
            x=s1.index.astype(str), y=s1.values,
            name=sym1, marker_color=COLOR_PRIMARY,
            text=[_fmt_val(v, metric_name) for v in s1.values],
            textposition="outside", textfont=dict(size=9),
        ))

    if s2 is not None and not s2.empty:
        fig.add_trace(go.Bar(
            x=s2.index.astype(str), y=s2.values,
            name=sym2, marker_color=COLOR_SECONDARY,
            text=[_fmt_val(v, metric_name) for v in s2.values],
            textposition="outside", textfont=dict(size=9),
        ))

    fig.update_layout(**_base_layout(
        title=dict(text=f"{metric_name} Comparison (Annual)", x=0.02),
        barmode="group",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_tickformat=_tick_format(metric_name),
    ))
    return fig


def radar_chart(df_compare: pd.DataFrame, sym1: str, sym2: str) -> go.Figure:
    numeric_rows = df_compare[df_compare["_v1"].notna() & df_compare["_v2"].notna()].copy()

    if numeric_rows.empty:
        return _empty_fig("Not enough comparable data for radar chart")

    def safe_norm(a, b):
        mx = max(abs(a), abs(b), 1e-9)
        return a / mx, b / mx

    cats   = []
    vals1  = []
    vals2  = []
    for _, row in numeric_rows.iterrows():
        v1, v2 = row["_v1"], row["_v2"]
        if v1 is None or v2 is None:
            continue
        n1, n2 = safe_norm(v1, v2)
        cats.append(row["Metric"])
        vals1.append(n1)
        vals2.append(n2)

    if not cats:
        return _empty_fig("Not enough comparable data for radar chart")

    cats  += [cats[0]]
    vals1 += [vals1[0]]
    vals2 += [vals2[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals1, theta=cats, fill="toself",
        name=sym1,
        line_color=COLOR_PRIMARY,
        fillcolor=f"rgba(0,212,170,0.15)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=vals2, theta=cats, fill="toself",
        name=sym2,
        line_color=COLOR_SECONDARY,
        fillcolor=f"rgba(255,107,107,0.15)",
    ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[-1, 1], gridcolor=COLOR_BORDER),
            angularaxis=dict(gridcolor=COLOR_BORDER),
        ),
        font=dict(family="'IBM Plex Mono', monospace", color="#C9D1D9"),
        margin=dict(l=30, r=30, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        title=dict(text="Ratio Snapshot — Radar", x=0.02),
    )
    return fig


def correlation_chart(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    sym1: str,
    sym2: str,
) -> go.Figure:
    if df1.empty or df2.empty:
        return _empty_fig("Not enough data for correlation")

    r1 = df1["Close"].pct_change().rename(sym1)
    r2 = df2["Close"].pct_change().rename(sym2)
    combined = pd.concat([r1, r2], axis=1).dropna()
    rolling_corr = combined[sym1].rolling(30).corr(combined[sym2]).dropna()

    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color=COLOR_NEUTRAL, opacity=0.5)
    fig.add_trace(go.Scatter(
        x=rolling_corr.index, y=rolling_corr.values,
        mode="lines",
        line=dict(color=COLOR_PRIMARY, width=2),
        fill="tozeroy",
        fillcolor="rgba(0,212,170,0.08)",
        name="30-day Rolling Corr",
    ))

    fig.update_layout(**_base_layout(
        title=dict(text=f"30-Day Rolling Return Correlation ({sym1} vs {sym2})", x=0.02),
        showlegend=False,
        yaxis=dict(range=[-1, 1], gridcolor=COLOR_BORDER, showgrid=True, zeroline=False),
    ))
    return fig


def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=COLOR_NEUTRAL),
    )
    fig.update_layout(**_base_layout(showlegend=False))
    return fig


def _fmt_val(v, metric_name: str) -> str:
    if v is None:
        return "—"
    if "%" in metric_name or metric_name in ("Profit Margin", "Return on Equity", "Return on Assets", "Revenue Growth (YoY)", "Dividend Yield"):
        return f"{v*100:.1f}%"
    if abs(v) >= 1e12:
        return f"${v/1e12:.1f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"{v:.2f}"


def _tick_format(metric_name: str) -> str:
    if "Ratio" in metric_name or "Debt" in metric_name:
        return ".2f"
    if "Margin" in metric_name or "Return" in metric_name or "Growth" in metric_name or "Yield" in metric_name:
        return ".1%"
    return "$.2s"
