"""
Route health map, schedule Gantt, and logistics friction heatmap — built on
delivery_scheduler routes and python-holidays.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import holidays
import numpy as np
import pandas as pd

from delivery_scheduler import (
    ROUTES,
    evaluate_ship_date,
    suggest_safe_ship_date,
)

# ---------------------------------------------------------------------------
# Geographic waypoints (city name, lat, lon) — simplified corridors for maps
# ---------------------------------------------------------------------------

ROUTE_WAYPOINTS: dict[tuple[str, str], list[tuple[str, float, float]]] = {
    ("LT", "DE"): [
        ("Vilnius", 54.6872, 25.2797),
        ("Warsaw", 52.2297, 21.0122),
        # Split Poland / Germany leg so each model leg has its own map segment
        ("Łódź", 51.7592, 19.4560),
        ("Berlin", 52.5200, 13.4050),
    ],
    ("LT", "PL"): [
        ("Vilnius", 54.6872, 25.2797),
        ("Kaunas", 54.8985, 23.9036),
        ("Warsaw", 52.2297, 21.0122),
    ],
    ("DE", "FR"): [
        ("Berlin", 52.5200, 13.4050),
        ("Cologne", 50.9375, 6.9603),
        ("Brussels", 50.8503, 4.3517),
        ("Paris", 48.8566, 2.3522),
    ],
}


def _leg_segment_risk(
    legs: list[tuple[str, int, int]],
    leg_index: int,
    conflicts: list[Any],
) -> tuple[bool, str]:
    """True if this leg hits a public holiday in its corridor country."""
    if leg_index >= len(legs):
        return False, ""
    cc, a, b = legs[leg_index]
    msgs: list[str] = []
    for c in conflicts:
        if c.country == cc and a <= c.day_offset < b:
            msgs.append(f"{c.calendar_day}: {c.holiday_name}")
    if msgs:
        return True, "; ".join(msgs[:3]) + ("…" if len(msgs) > 3 else "")
    return False, ""


def build_route_health_map(
    origin: str,
    destination: str,
    ship_date: date,
) -> Any:
    """
    Folium map: polyline segments green (clear) or red (holiday risk on that leg).
    Markers show city + delay hint from holiday conflicts.
    """
    import folium

    key = (origin.upper(), destination.upper())
    if key not in ROUTES or key not in ROUTE_WAYPOINTS:
        raise KeyError(f"No map waypoints for {origin} -> {destination}")

    cfg = ROUTES[key]
    legs = cfg["legs"]
    pts = ROUTE_WAYPOINTS[key]
    report = evaluate_ship_date(origin, destination, ship_date)

    if len(pts) != len(legs) + 1:
        raise ValueError("Waypoints must be legs + 1 for this route.")

    lats = [p[1] for p in pts]
    lons = [p[2] for p in pts]
    center = (float(np.mean(lats)), float(np.mean(lons)))

    m = folium.Map(location=center, zoom_start=5, tiles="cartodbpositron")

    # Per-segment polylines
    for i in range(len(legs)):
        bad, detail = _leg_segment_risk(legs, i, report.conflicts)
        color = "#e41a1c" if bad else "#4daf4a"
        weight = 5
        folium.PolyLine(
            locations=[(pts[i][1], pts[i][2]), (pts[i + 1][1], pts[i + 1][2])],
            color=color,
            weight=weight,
            opacity=0.9,
            tooltip=f"Leg {i + 1} ({legs[i][0]}): {'RISK' if bad else 'clear'}",
        ).add_to(m)

    # City markers with popups (countries for legs meeting at this hub)
    cc_at_city: dict[str, set[str]] = {}
    for i, (name, _, _) in enumerate(pts):
        if i == 0:
            cc_at_city[name] = {legs[0][0]}
        elif i == len(pts) - 1:
            cc_at_city[name] = {legs[-1][0]}
        else:
            cc_at_city[name] = {legs[i - 1][0], legs[i][0]}

    for i, (name, lat, lon) in enumerate(pts):
        lines: list[str] = [f"<b>{name}</b>"]
        for c in report.conflicts:
            if c.country in cc_at_city.get(name, set()):
                lines.append(
                    f"Delay: ~24h risk — {c.holiday_name} ({c.calendar_day}); "
                    f"corridor day +{c.day_offset}"
                )
        if len(lines) == 1:
            lines.append("No holiday conflict flagged here for this ship date.")
        popup_html = "<br>".join(lines)
        folium.Marker(
            (lat, lon),
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color="blue" if i in (0, len(pts) - 1) else "green"),
        ).add_to(m)

    return m


def build_schedule_gantt_figure(
    origin: str,
    destination: str,
    naive_ship: date,
    *,
    horizon_days: int = 14,
) -> Any:
    """
    Plotly figure: naive vs smart truck windows with vertical gray holiday zones
    across corridor countries on the timeline.
    """
    import plotly.express as px

    key = (origin.upper(), destination.upper())
    if key not in ROUTES:
        raise KeyError(f"No route {origin} -> {destination}")

    legs = ROUTES[key]["legs"]
    countries = sorted({c for c, _, _ in legs})
    smart_ship = suggest_safe_ship_date(origin, destination, naive_ship)
    if smart_ship is None:
        smart_ship = naive_ship + timedelta(days=7)

    start = naive_ship
    end = naive_ship + timedelta(days=horizon_days)
    years = list({d.year for d in [start, end]})

    cal_by_cc: dict[str, Any] = {
        cc: holidays.country_holidays(cc, years=years) for cc in countries
    }

    holiday_days: list[date] = []
    d = start
    while d <= end:
        if any(d in cal for cal in cal_by_cc.values()):
            holiday_days.append(d)
        d += timedelta(days=1)

    span = max(end for _, _, end in legs)
    naive_a0, naive_a1 = naive_ship, naive_ship + timedelta(days=min(4, span))
    naive_b0 = naive_ship + timedelta(days=1)
    naive_b1 = naive_b0 + timedelta(days=4)

    offset_fix = (smart_ship - naive_ship).days
    smart_a0 = naive_a0 + timedelta(days=offset_fix)
    smart_a1 = naive_a1 + timedelta(days=offset_fix)
    smart_b0 = naive_b0 + timedelta(days=offset_fix)
    smart_b1 = naive_b1 + timedelta(days=offset_fix)

    rows: list[dict] = [
        {
            "task": "Truck A (naive)",
            "start": pd.Timestamp(naive_a0),
            "end": pd.Timestamp(naive_a1),
            "schedule": "Naive",
        },
        {
            "task": "Truck B (naive)",
            "start": pd.Timestamp(naive_b0),
            "end": pd.Timestamp(naive_b1),
            "schedule": "Naive",
        },
        {
            "task": "Truck A (smart)",
            "start": pd.Timestamp(smart_a0),
            "end": pd.Timestamp(smart_a1),
            "schedule": "Smart",
        },
        {
            "task": "Truck B (smart)",
            "start": pd.Timestamp(smart_b0),
            "end": pd.Timestamp(smart_b1),
            "schedule": "Smart",
        },
    ]
    df = pd.DataFrame(rows)

    fig = px.timeline(
        df,
        x_start="start",
        x_end="end",
        y="task",
        color="schedule",
        color_discrete_map={"Naive": "#fb6a4a", "Smart": "#31a354"},
        title=f"Holiday Gantt — {ROUTES[key]['label']} (naive ship {naive_ship})",
    )
    fig.update_yaxes(autorange="reversed")

    for hd in holiday_days:
        fig.add_vrect(
            x0=hd,
            x1=hd + timedelta(days=1),
            fillcolor="rgba(90,90,90,0.28)",
            layer="below",
            line_width=0,
        )

    fig.update_layout(
        height=440,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis_title="Calendar",
        legend_title="Schedule",
    )
    fig.update_xaxes(range=[pd.Timestamp(start), pd.Timestamp(end)])
    return fig


def friction_series_for_corridor(
    year: int,
    countries: list[str],
    *,
    december_boost: float = 0.35,
) -> pd.Series:
    """
    Daily 'logistics friction' score: count of corridor countries with a public
    holiday that day + small December uplift (peak retail / weather narrative).
    """
    cals = {cc: holidays.country_holidays(cc, years=year) for cc in countries}
    idx = pd.date_range(date(year, 1, 1), date(year, 12, 31), freq="D")
    scores = []
    for d in idx:
        base = sum(1 for cal in cals.values() if d.date() in cal)
        if d.month == 12:
            base += december_boost
        scores.append(base)
    return pd.Series(scores, index=idx, name="friction")


def build_friction_calendar_heatmap(
    year: int,
    countries: list[str],
) -> Any:
    """
    Seaborn heatmap: weeks × weekdays, color = friction score.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    s = friction_series_for_corridor(year, countries)
    df = s.reset_index()
    df.columns = ["date", "friction"]
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["dow"] = df["date"].dt.weekday

    pivot = df.pivot_table(index="week", columns="dow", values="friction", aggfunc="max")
    dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig, ax = plt.subplots(figsize=(12, max(8, len(pivot) * 0.12)))
    sns.heatmap(
        pivot,
        cmap="YlOrRd",
        ax=ax,
        cbar_kws={"label": "Logistics friction (holidays + Dec boost)"},
        linewidths=0.2,
        linecolor="white",
    )
    ax.set_title(
        f"Cost of celebration — daily friction ({year}) — "
        f"{', '.join(countries)}",
        fontsize=13,
    )
    ax.set_xlabel("Weekday")
    ax.set_ylabel("ISO week of year")
    ax.set_xticklabels(dow_labels, rotation=0)
    plt.tight_layout()
    return fig
