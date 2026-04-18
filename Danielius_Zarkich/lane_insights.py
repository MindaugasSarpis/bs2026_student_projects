"""
Generalized lane visualizations: world map of TT by POL for a chosen POD, plus TT comparison chart.

Uses ISO-3166 alpha-3 codes for Plotly choropleths (see POL_COUNTRY_TO_ISO3).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Labels in data/TT_Offset.csv (POL Country column) -> ISO-3166 alpha-3
POL_COUNTRY_TO_ISO3: dict[str, str] = {
    "China": "CHN",
    "South Korea": "KOR",
    "Vietnam": "VNM",
    "Taiwan": "TWN",
    "India": "IND",
    "Pakistan": "PAK",
    "USA": "USA",
    "Turkey": "TUR",
    "Egypt": "EGY",
    "Italy": "ITA",
    "UK": "GBR",
    "France": "FRA",
}

# Approximate centroid for POD marker on the map (lat, lon)
POD_LATLON: dict[str, tuple[float, float]] = {
    "Lithuania": (55.3, 23.9),
    "Romania": (45.9, 25.0),
    "Spain": (40.4, -3.7),
    "Germany": (51.2, 10.5),
}


def prepare_lane_frame(tt: pd.DataFrame, pod: str) -> pd.DataFrame:
    """Rows for one POD with ISO3 for mapping; empty if none."""
    sub = tt[tt["pod_country"] == str(pod).strip()].copy()
    if sub.empty:
        return sub
    sub["iso3"] = sub["pol_country"].map(POL_COUNTRY_TO_ISO3)
    sub = sub.dropna(subset=["iso3", "tt_days"])
    return sub


def make_world_tt_map(lane_df: pd.DataFrame, pod: str) -> go.Figure:
    """
    Choropleth: POL countries colored by transit time (days) to the selected POD.
    Adds a marker at the POD destination.
    """
    if lane_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No mapped countries for this POD",
            annotations=[
                dict(
                    text="Check POL_COUNTRY_TO_ISO3 in lane_insights.py",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                )
            ],
        )
        return fig

    fig = px.choropleth(
        lane_df,
        locations="iso3",
        locationmode="ISO-3",
        color="tt_days",
        hover_name="pol_country",
        hover_data={
            "tt_days": True,
            "pod_offset_days": True,
            "iso3": False,
            "pol_country": False,
        },
        labels={"tt_days": "TT (days)", "pod_offset_days": "POD offset (d)"},
        color_continuous_scale="YlGnBu",
        range_color=(int(lane_df["tt_days"].min()), int(lane_df["tt_days"].max())),
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color="white", selector=dict(type="choropleth"))

    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        showland=True,
        landcolor="rgb(243,243,243)",
        coastlinecolor="rgb(180,180,180)",
        oceancolor="rgb(230,245,255)",
        showocean=True,
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        title=dict(
            text=f"<b>Transit time (days) to POD: {pod}</b><br>"
            "<sup>Origin countries (POL) colored by sea/land TT from your matrix</sup>",
            font=dict(size=15),
        ),
        margin=dict(l=0, r=0, t=64, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="TT days"),
        height=480,
        geo=dict(domain=dict(x=[0, 1], y=[0, 1])),
    )

    pos = POD_LATLON.get(pod.strip())
    if pos is not None:
        lat, lon = pos
        fig.add_trace(
            go.Scattergeo(
                lat=[lat],
                lon=[lon],
                mode="markers+text",
                text=[f"POD · {pod}"],
                textposition="top center",
                textfont=dict(size=12, color="crimson"),
                marker=dict(
                    size=14,
                    color="crimson",
                    symbol="circle",
                    line=dict(width=2, color="white"),
                ),
                name="Destination (POD)",
                showlegend=True,
            )
        )
    return fig


def make_tt_comparison_bars(lane_df: pd.DataFrame, pod: str) -> go.Figure:
    """
    Horizontal lollipop-style chart: each POL origin with its TT (bullet markers at end of bars).
    """
    if lane_df.empty:
        return go.Figure()

    # Shortest TT at bottom of chart, longest at top (easier to scan)
    df = lane_df.sort_values("tt_days", ascending=True).copy()
    countries = df["pol_country"].tolist()
    tts = df["tt_days"].astype(int).tolist()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=tts,
            y=countries,
            orientation="h",
            name="TT (days)",
            marker=dict(
                color=tts,
                colorscale="YlGnBu",
                cmin=min(tts),
                cmax=max(tts),
                line=dict(color="white", width=1),
                showscale=False,
            ),
            text=[f"{t} d" for t in tts],
            textposition="outside",
            hovertemplate="%{y}<br>TT: %{x} days<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=tts,
            y=countries,
            mode="markers",
            marker=dict(size=11, color="white", line=dict(color="#0c4a6e", width=2), symbol="circle"),
            name="",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"<b>TT comparison</b> — all origins → <b>{pod}</b>",
            font=dict(size=15),
        ),
        xaxis_title="Transit time (days)",
        yaxis_title="",
        height=max(360, 28 * len(countries)),
        margin=dict(l=8, r=48, t=56, b=48),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,0.95)",
        showlegend=False,
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)", zeroline=False),
    )
    return fig
