"""
Streamlit UI: Order Arrival Calculator + Lane insights (map & TT comparison).

Run: streamlit run streamlit_app.py
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from holiday_checks import pod_public_holiday_on_date
from lane_insights import (
    POL_COUNTRY_TO_ISO3,
    make_tt_comparison_bars,
    make_world_tt_map,
    prepare_lane_frame,
)
from logistics_data import (
    distinct_pod_countries,
    load_products,
    load_tt_matrix,
    merge_product_transit,
)

_PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def _product_label(row: pd.Series) -> str:
    return (
        f"{row['Article_ID']} — {row['Product_Description']} — "
        f"{row['Supplier_Name']} (POL: {row['POL_Country']})"
    )


def _render_calculator(products: pd.DataFrame, tt: pd.DataFrame, pods: list[str]) -> None:
    st.subheader("Order calculator")
    st.caption(
        "Pick a planned contract sign date, product, and destination (POD). "
        "ETAs add calendar days to the sign date. "
        "If the delivery ETA is a weekend or a public holiday in the POD country, a notice is shown."
    )

    contract_sign = st.date_input(
        "Planned Contract Sign Date",
        value=date.today(),
        key="contract_sign",
    )

    default_pod = "Lithuania" if "Lithuania" in pods else pods[0]
    labels = [_product_label(products.iloc[i]) for i in range(len(products))]
    choice = st.selectbox(
        "Product",
        range(len(products)),
        format_func=lambda i: labels[i],
        key="product_choice",
    )
    row = products.iloc[choice]

    pod = st.selectbox(
        "Destination (POD)",
        pods,
        index=pods.index(default_pod) if default_pod in pods else 0,
        key="pod_calculator",
    )

    merged = merge_product_transit(row, pod, tt=tt)

    st.markdown("**Result**")
    if merged is None:
        st.warning(
            f"No transit row for **{row['POL_Country']}** → **{pod}**. "
            "Add or correct data in `data/TT_Offset.csv`."
        )
        return

    shipping_eta = contract_sign + timedelta(days=merged["tt_days"])
    delivery_eta = contract_sign + timedelta(days=merged["recommended_lead_days"])

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Transit time (days)", merged["tt_days"])
    with m2:
        st.metric("POD offset (days)", merged["pod_offset_days"])
    with m3:
        st.metric("Recommended lead time (days)", merged["recommended_lead_days"])

    st.markdown("**ETAs from contract sign**")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "Shipping ETA (contract + TT)",
            shipping_eta.isoformat(),
            help=f"{merged['tt_days']} calendar days after the planned contract sign date.",
        )
    with c2:
        st.metric(
            "Delivery ETA (contract + TT + offset)",
            delivery_eta.isoformat(),
            help=f"{merged['recommended_lead_days']} calendar days after the planned contract sign date.",
        )

    if _is_weekend(delivery_eta):
        st.warning(
            f"Delivery ETA **{delivery_eta.isoformat()}** ({delivery_eta.strftime('%A')}) is a **weekend**. "
            "Check whether the client's warehouse accepts weekend deliveries."
        )

    delivery_holiday = pod_public_holiday_on_date(merged["pod_country"], delivery_eta)
    if delivery_holiday:
        st.error(
            f"Delivery ETA **{delivery_eta.isoformat()}** falls on a public holiday in "
            f"**{merged['pod_country']}**: **{delivery_holiday}**. "
            "Avoid proposing this as the customer delivery date."
        )


def _render_lane_insights(tt: pd.DataFrame, pods: list[str]) -> None:
    st.subheader("Lane insights")
    st.caption(
        "Choose a **destination (POD)** to compare **transit times (TT)** from every origin "
        "in your matrix. The map colors each origin country; the chart ranks TT with end markers."
    )

    default_pod = "Lithuania" if "Lithuania" in pods else pods[0]
    pod_viz = st.selectbox(
        "Destination (POD) for comparison",
        pods,
        index=pods.index(default_pod) if default_pod in pods else 0,
        key="pod_lane_insights",
    )

    lane_df = prepare_lane_frame(tt, pod_viz)
    lane_pol = set(tt[tt["pod_country"] == pod_viz]["pol_country"].dropna().astype(str).str.strip().unique())
    missing_iso = sorted(lane_pol - set(POL_COUNTRY_TO_ISO3.keys()))
    if missing_iso:
        st.info(
            "Some POL labels have no ISO-3 mapping yet — they are omitted from the map. "
            f"Add them in `lane_insights.py` if needed: {', '.join(missing_iso)}."
        )

    fig_map = make_world_tt_map(lane_df, pod_viz)
    st.plotly_chart(fig_map, use_container_width=True, config=_PLOTLY_CONFIG)

    fig_bars = make_tt_comparison_bars(lane_df, pod_viz)
    st.plotly_chart(fig_bars, use_container_width=True, config=_PLOTLY_CONFIG)


def main() -> None:
    st.set_page_config(page_title="Order Arrival Calculator", layout="wide")
    st.title("Order Arrival Calculator")

    tt = load_tt_matrix()
    products = load_products()
    pods = distinct_pod_countries(tt)

    tab_calc, tab_insights = st.tabs(["Order calculator", "Lane insights"])

    with tab_calc:
        _render_calculator(products, tt, pods)

    with tab_insights:
        _render_lane_insights(tt, pods)


if __name__ == "__main__":
    main()
