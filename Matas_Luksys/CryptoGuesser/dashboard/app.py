# dashboard/app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pipeline.fetch import fetch_ohlcv
from pipeline.train import run_training
from api.predict import get_prediction

st.set_page_config(page_title="CryptoGuesser", layout="wide")
st.title("CryptoGuesser Dashboard")

# --- Sidebar controls ---
st.sidebar.header("Pipeline Controls")
symbol = st.sidebar.selectbox("Symbol", ["BTC/USDT","ETH/USDT","SOL/USDT", "..."])

if st.sidebar.button("Fetch / Append Latest Data"):
    with st.spinner("Fetching from Binance..."):
        fetch_ohlcv(symbol, days=2)  # append mode
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
df = pd.read_parquet(f"data/raw/{symbol.replace('/','_')}.parquet")
fig = go.Figure(data=[go.Candlestick(
    x=df["timestamp"], open=df["open"],
    high=df["high"], low=df["low"], close=df["close"]
)])
st.plotly_chart(fig, use_container_width=True)
