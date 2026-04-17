"""
Streamlit UI: Order Arrival Calculator — contract sign date, product, POD, TT, offsets, ETAs.

Run: streamlit run streamlit_app.py
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from holiday_checks import pod_public_holiday_on_date
from logistics_data import (
    distinct_pod_countries,
    load_products,
    load_tt_matrix,
    merge_product_transit,
)


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def _product_label(row: pd.Series) -> str:
    return (
        f"{row['Article_ID']} — {row['Product_Description']} — "
        f"{row['Supplier_Name']} (POL: {row['POL_Country']})"
    )


def main() -> None:
    st.set_page_config(page_title="Order Arrival Calculator", layout="centered")
    st.title("Order Arrival Calculator")
    st.caption(
        "Pick a planned contract sign date, product, and destination (POD). "
        "ETAs add calendar days to the sign date. "
        "If the delivery ETA is a weekend or a public holiday in the POD country, a notice is shown."
    )

    contract_sign = st.date_input(
        "Planned Contract Sign Date",
        value=date.today(),
    )

    products = load_products()
    tt = load_tt_matrix()
    pods = distinct_pod_countries(tt)
    default_pod = "Lithuania" if "Lithuania" in pods else pods[0]

    labels = [_product_label(products.iloc[i]) for i in range(len(products))]
    choice = st.selectbox("Product", range(len(products)), format_func=lambda i: labels[i])
    row = products.iloc[choice]

    pod = st.selectbox(
        "Destination (POD)",
        pods,
        index=pods.index(default_pod) if default_pod in pods else 0,
    )

    merged = merge_product_transit(row, pod, tt=tt)

    st.subheader("Result")
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


if __name__ == "__main__":
    main()
