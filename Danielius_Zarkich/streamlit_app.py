"""
Streamlit UI for the Smart Holiday Delivery Scheduler.
Run: streamlit run streamlit_app.py
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from delivery_scheduler import ROUTES, evaluate_ship_date, suggest_safe_ship_date

def main() -> None:
    st.set_page_config(page_title="Smart Holiday Delivery Scheduler", layout="centered")
    st.title("Smart Holiday Delivery Scheduler")
    st.caption(
        "Checks public holidays along origin, transit hubs, and destination "
        "so shipments are less likely to stall over holiday closures."
    )

    route_keys = list(ROUTES.keys())
    labels = [f"{o} -> {d}: {ROUTES[(o, d)]['label']}" for o, d in route_keys]
    choice = st.selectbox("Corridor", range(len(route_keys)), format_func=lambda i: labels[i])
    origin, dest = route_keys[choice]

    cfg = ROUTES[(origin, dest)]
    st.info(f"**Transit in model:** {', '.join(cfg['transit']) or '— (none)'}")

    default = date.today()
    ship = st.date_input("Planned ship date", value=default)

    if st.button("Check schedule", type="primary"):
        report = evaluate_ship_date(origin, dest, ship)
        suggestion = suggest_safe_ship_date(origin, dest, ship)

        if report.is_safe:
            st.success("No public holidays along the modeled corridor window for this ship date.")
        else:
            st.error("Shipment may hit a holiday closure along the corridor.")
            for c in report.conflicts:
                st.write(
                    f"**{c.calendar_day.isoformat()}** (day +{c.day_offset}) — "
                    f"{c.country}: {c.holiday_name}"
                )

        if suggestion is not None and not report.is_safe:
            st.warning(f"**Suggested safe ship date:** {suggestion.isoformat()}")


if __name__ == "__main__":
    main()
