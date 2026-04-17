import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pipeline.fetch import append_all, load_raw, SYMBOLS, MODEL_CONFIGS
from pipeline.train import run_training
from pipeline.predict import get_prediction


st.set_page_config(page_title="CryptoGuesser", layout="wide")
st.title("CryptoGuesser Dashboard")


# --- Sidebar controls ---
st.sidebar.header("Pipeline Controls")
symbol = st.sidebar.selectbox("Symbol", SYMBOLS)
model = st.sidebar.selectbox("Model", list(MODEL_CONFIGS.keys()))

if st.sidebar.button("Fetch / Append Latest Data"):
    with st.spinner("Fetching from Binance..."):
        append_all()
    st.success("Data updated")

if st.sidebar.button("Train New Model"):
    with st.spinner("Training... this may take a few minutes"):
        metrics = run_training()
    st.success(f"Done — Val Accuracy: {metrics['val_accuracy']:.2%}")


# --- Prediction panel ---
st.header(f"Prediction — {symbol}")
if st.button("Run Prediction"):
    result = get_prediction(symbol)
    confidence = result["confidence"]
    direction = "⬆ UP" if result["signal"] == 1 else "⬇ DOWN"

    col1, col2 = st.columns(2)
    col1.metric("Signal", direction)
    col2.metric("Confidence", f"{confidence:.1%}")

    if confidence < 0.65:
        st.warning("Confidence below threshold — signal unreliable")


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
    st.warning(f"No data found for {symbol} / {model}. Run 'Fetch / Append Latest Data' first.")