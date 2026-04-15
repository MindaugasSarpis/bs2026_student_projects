import pandas as pd
import numpy as np


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates and cleans a raw OHLCV dataframe.
    - Removes duplicate timestamps
    - Validates OHLCV logic (high >= low, prices > 0)
    - Fills gaps in daily candles (forward-fill up to 1 day)
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

    # Fill single-day gaps with forward fill
    df = df.set_index("timestamp")
    full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="1D", tz="UTC")
    df = df.reindex(full_range)
    df["symbol"] = df["symbol"].ffill()
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].ffill(limit=1)
    df = df.dropna(subset=numeric_cols)
    df.index.name = "timestamp"
    df = df.reset_index()

    return df
