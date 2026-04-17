# dashboard/app.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import math
import streamlit as st
import plotly.graph_objects as go
from pipeline.fetch import append_all, bootstrap_all, load_raw, SYMBOLS, MODEL_CONFIGS
from pipeline.train import run_training
from pipeline.predict import get_prediction


st.set_page_config(page_title="CryptoGuesser", layout="wide")
st.title("CryptoGuesser Dashboard")


# --- Sidebar controls ---
st.sidebar.header("Pipeline Controls")
symbol = st.sidebar.selectbox("Symbol", SYMBOLS)
model = st.sidebar.selectbox("Model", list(MODEL_CONFIGS.keys()))


if st.sidebar.button("Bootstrap Data (First Time)"):
    with st.spinner("Downloading full history — this takes 10–15 mins..."):
        bootstrap_all()
    st.success("Bootstrap complete — all symbols fetched for M1, M2, M3")


if st.sidebar.button("Fetch / Append Latest Data"):
    with st.spinner("Fetching from Binance..."):
        append_all()
    st.success("Data updated")


if st.sidebar.button("Train All Models"):
    all_results = {}
    with st.spinner("Training M1, M2, M3 — this may take 30+ minutes..."):
        for m in MODEL_CONFIGS.keys():
            all_results[m] = run_training(model=m)
    for m, metrics in all_results.items():
        st.success(f"[{m.upper()}] Val Accuracy: {metrics['val_accuracy']:.2%} | AUC: {metrics['val_auc']:.3f}")


# --- Prediction panel ---
st.header(f"Prediction — {symbol}")
if st.button("Run Prediction"):
    try:
        result = get_prediction(symbol=symbol, model=model)
        confidence = result["confidence"]
        direction = "⬆ UP" if result["signal"] == 1 else "⬇ DOWN"

        col1, col2, col3 = st.columns(3)
        col1.metric("Signal", direction)
        col2.metric("Confidence", f"{confidence:.1%}")
        col3.metric("Model", model.upper())

        if confidence < result["threshold"]:
            st.warning("Confidence below threshold — signal unreliable")

        st.caption(f"Model date: {result['model_date']} | Window end: {result['window_end']}")

    except FileNotFoundError:
        st.warning(f"No trained model found for {model.upper()}. Run 'Train All Models' first.")
    except Exception as e:
        st.error(f"Prediction failed: {e}")


# --- Price chart ---
st.header("Recent Price History")
try:
    df = load_raw(symbol, model)
    fig = go.Figure(data=[go.Candlestick(
        x=df["timestamp"], open=df["open"],
        high=df["high"], low=df["low"], close=df["close"]
    )])
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
except FileNotFoundError:
    st.warning(f"No data found for {symbol} / {model}. Run 'Bootstrap Data' first.")