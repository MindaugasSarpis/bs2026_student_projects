# pipeline/clean.py
import pandas as pd
import numpy as np

FREQ_MAP = {
    "1h":  "1h",
    "4h":  "4h",
    "1d":  "1D",
}

def clean(df: pd.DataFrame, timeframe: str = "1d") -> pd.DataFrame:
    """
    Validates and cleans a raw OHLCV dataframe.
    - Removes duplicate timestamps
    - Validates OHLCV logic (high >= low, prices > 0)
    - Fills single-candle gaps via forward-fill (timeframe-aware)
    - Drops rows with nulls after filling
    """
    df = df.copy()
    df.sort_values("timestamp", inplace=True)
    df.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)

    # Validate OHLCV sanity
    invalid_mask = (
        (df["high"] < df["low"]) |
        (df["close"] <= 0) |
        (df["open"] <= 0) |
        (df["volume"] < 0)
    )
    if invalid_mask.any():
        print(f"  [clean] Dropping {invalid_mask.sum()} invalid rows")
        df = df[~invalid_mask]

    # Fill single-candle gaps with forward fill (timeframe-aware)
    freq = FREQ_MAP.get(timeframe, "1D")
    df = df.set_index("timestamp")
    full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq, tz="UTC")
    df = df.reindex(full_range)
    df["symbol"] = df["symbol"].ffill()
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].ffill(limit=1)
    df = df.dropna(subset=numeric_cols)
    df.index.name = "timestamp"
    df = df.reset_index()

    return df