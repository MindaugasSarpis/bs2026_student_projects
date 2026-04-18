import streamlit as st

st.set_page_config(
    page_title="MarketLens",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config import METRICS, POPULAR_TICKERS, COLOR_PRIMARY, COLOR_SECONDARY
import data as Data
import charts as Charts
import analysis as Analysis
import ui as UI

UI.apply_global_css()

UI.render_header()

UI.section_header("01 — Single Stock Analysis")

col_input, col_metric, col_period = st.columns([2, 3, 1])
with col_input:
    ticker1 = UI.ticker_input("Stock Symbol", "AAPL", key="s1_ticker")

with col_metric:
    metric_choice = st.selectbox(
        "Fundamental Metric",
        list(METRICS.keys()),
        index=list(METRICS.keys()).index("Revenue"),
        key="s1_metric",
        help=METRICS.get("Revenue", {}).get("description", ""),
    )

with col_period:
    price_period = st.selectbox(
        "Price History",
        ["1y", "2y", "3y", "5y", "10y"],
        index=3,
        key="s1_period",
    )

st.markdown('<div style="margin:8px 0 0;font-size:0.7rem;color:#8B949E;">💡 Popular: ' +
            " · ".join(f"<code>{t}</code>" for t in POPULAR_TICKERS[:12]) +
            "</div>", unsafe_allow_html=True)

if ticker1:
    with st.spinner(f"Fetching data for {ticker1}…"):
        valid1 = Data.validate_ticker(ticker1)

    if not valid1:
        st.error(f"❌ Could not find ticker **{ticker1}**. Please check the symbol and try again.")
    else:
        snapshot1    = Data.get_snapshot(ticker1)
        price_df1    = Data.fetch_price_history(ticker1, period=price_period)
        metric_series = Data.get_metric_series(ticker1, metric_choice)
        info1        = Data.fetch_ticker_info(ticker1)

        UI.company_banner(snapshot1, color=COLOR_PRIMARY)

        UI.kpi_row(snapshot1)

        st.markdown("<br>", unsafe_allow_html=True)

        chart_col, analysis_col = st.columns([3, 1])

        with chart_col:
            tab_price, tab_metric = st.tabs(["📈 Price Chart", f"📊 {metric_choice}"])

            with tab_price:
                fig_price = Charts.price_chart(price_df1, ticker1, color=COLOR_PRIMARY)
                st.plotly_chart(fig_price, width='stretch')

            with tab_metric:
                if metric_series is not None and not metric_series.empty:
                    metric_cfg = METRICS[metric_choice]
                    st.caption(f"_{metric_cfg['description']}_")
                    fig_metric = Charts.metric_bar_chart(
                        metric_series, ticker1, metric_choice, color=COLOR_PRIMARY
                    )
                    st.plotly_chart(fig_metric, width='stretch')

                    # Anomaly detection
                    anomalies = Analysis.detect_anomalies(metric_series)
                    if anomalies:
                        st.warning(
                            f"⚠️ Unusual value(s) detected for **{ticker1}** in: "
                            + ", ".join(str(y) for y in anomalies)
                        )
                else:
                    st.info(f"No annual data found for **{metric_choice}** on {ticker1}.")

        with analysis_col:
            score1, notes1 = Analysis.fundamental_health_score(info1)
            UI.health_gauge(score1, notes1, ticker1)

            st.markdown("<br>", unsafe_allow_html=True)

            trend1 = Analysis.price_trend_analysis(price_df1, ticker1)
            if "error" not in trend1:
                UI.stats_table(trend1, title="Price & Risk Stats")


st.markdown('<hr style="border-color:#30363D;margin:32px 0;">', unsafe_allow_html=True)


UI.section_header("02 — Stock Comparison & AI Insights")

col_a, col_b, col_m2 = st.columns([2, 2, 3])
with col_a:
    sym_a = UI.ticker_input("Stock A", "AAPL", key="s2_a")
with col_b:
    sym_b = UI.ticker_input("Stock B", "MSFT", key="s2_b")
with col_m2:
    metric2 = st.selectbox(
        "Metric to Compare",
        list(METRICS.keys()),
        index=list(METRICS.keys()).index("Revenue"),
        key="s2_metric",
    )

run_compare = st.button("⚡ Compare Stocks", type="primary", key="compare_btn")

if run_compare and sym_a and sym_b:
    if sym_a == sym_b:
        st.warning("Please select two **different** stock symbols.")
    else:
        with st.spinner(f"Loading data for {sym_a} vs {sym_b}…"):
            valid_a = Data.validate_ticker(sym_a)
            valid_b = Data.validate_ticker(sym_b)

        if not valid_a:
            st.error(f"❌ Invalid ticker: **{sym_a}**")
        elif not valid_b:
            st.error(f"❌ Invalid ticker: **{sym_b}**")
        else:
            # Fetch everything
            info_a    = Data.fetch_ticker_info(sym_a)
            info_b    = Data.fetch_ticker_info(sym_b)
            snap_a    = Data.get_snapshot(sym_a)
            snap_b    = Data.get_snapshot(sym_b)
            price_a   = Data.fetch_price_history(sym_a, "3y")
            price_b   = Data.fetch_price_history(sym_b, "3y")
            series_a  = Data.get_metric_series(sym_a, metric2)
            series_b  = Data.get_metric_series(sym_b, metric2)
            df_ratios = Data.get_comparable_metrics(sym_a, sym_b)

            banner_a, banner_b = st.columns(2)
            with banner_a:
                UI.company_banner(snap_a, color=COLOR_PRIMARY)
                UI.kpi_row(snap_a)
            with banner_b:
                UI.company_banner(snap_b, color=COLOR_SECONDARY)
                UI.kpi_row(snap_b)

            st.markdown("<br>", unsafe_allow_html=True)

            tab_perf, tab_metric2, tab_radar, tab_corr = st.tabs([
                "📈 Price Performance",
                f"📊 {metric2}",
                "🕸 Radar",
                "🔗 Correlation",
            ])

            with tab_perf:
                fig_overlay = Charts.price_overlay_chart(price_a, price_b, sym_a, sym_b)
                st.plotly_chart(fig_overlay, width='stretch')

            with tab_metric2:
                fig_cmp = Charts.metric_comparison_chart(series_a, series_b, sym_a, sym_b, metric2)
                st.plotly_chart(fig_cmp, width='stretch')

            with tab_radar:
                fig_radar = Charts.radar_chart(df_ratios, sym_a, sym_b)
                st.plotly_chart(fig_radar, width='stretch')

            with tab_corr:
                fig_corr = Charts.correlation_chart(price_a, price_b, sym_a, sym_b)
                st.plotly_chart(fig_corr, width='stretch')

            tbl_col, stats_col = st.columns([3, 2])

            with tbl_col:
                st.markdown('<div style="font-size:0.7rem;color:#8B949E;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">KEY RATIO COMPARISON</div>', unsafe_allow_html=True)
                UI.comparison_table(df_ratios, sym_a, sym_b)

            with stats_col:
                price_stats = Analysis.compare_price_stats(price_a, price_b, sym_a, sym_b)
                if not price_stats.empty:
                    st.markdown('<div style="font-size:0.7rem;color:#8B949E;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">RETURN & RISK STATS</div>', unsafe_allow_html=True)
                    st.dataframe(price_stats, width='stretch')

            st.markdown("<br>", unsafe_allow_html=True)
            UI.section_header(f"🤖 AI Verdict — {sym_a} vs {sym_b}")

            health_col_a, health_col_b, verdict_col = st.columns([1, 1, 3])

            with health_col_a:
                score_a, notes_a = Analysis.fundamental_health_score(info_a)
                UI.health_gauge(score_a, notes_a, sym_a)

            with health_col_b:
                score_b, notes_b = Analysis.fundamental_health_score(info_b)
                UI.health_gauge(score_b, notes_b, sym_b)

            with verdict_col:
                verdicts = Analysis.generate_ai_verdict(
                    info_a, info_b, sym_a, sym_b, price_a, price_b
                )
                UI.verdict_cards(verdicts)

                overall_winner = sym_a if score_a >= score_b else sym_b
                st.markdown(
                    f'<div style="margin-top:12px;padding:12px 16px;background:#161B22;border:1px solid #00D4AA;border-radius:6px;font-size:0.85rem;">'
                    f'<span style="color:#8B949E;">Overall Fundamental Score Edge → </span>'
                    f'<span style="color:#00D4AA;font-weight:600;">{overall_winner}</span>'
                    f' ({max(score_a, score_b):.0f}/100 vs {min(score_a, score_b):.0f}/100)'
                    f'<br><span style="color:#8B949E;font-size:0.72rem;">⚠️ This is not financial advice. Always do your own research.</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

elif run_compare:
    st.info("Please enter both stock symbols to compare.")
else:
    st.markdown(
        '<div style="color:#8B949E;font-size:0.8rem;padding:12px;background:#161B22;border:1px solid #30363D;border-radius:6px;">'
        '↑ Enter two tickers and click <strong style="color:#C9D1D9;">Compare Stocks</strong> to see a head-to-head breakdown.'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("""
<div style="margin-top:48px;padding-top:16px;border-top:1px solid #21262D;
            font-size:0.65rem;color:#8B949E;text-align:center;letter-spacing:1px;">
    MARKETLENS · DATA PROVIDED BY YAHOO FINANCE VIA YFINANCE · NOT FINANCIAL ADVICE
</div>
""", unsafe_allow_html=True)
