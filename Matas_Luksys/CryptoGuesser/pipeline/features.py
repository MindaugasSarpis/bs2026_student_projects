import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False
    print("[features] pandas_ta not installed — using manual indicator calculations")


FEATURE_COLS = [
    # Price-derived
    "log_return", "volume_change", "high_low_range", "close_position",
    # Trend
    "rsi", "macd", "macd_signal", "macd_hist",
    "ema_9", "ema_21", "ema_cross",
    # Volatility
    "bb_upper", "bb_lower", "bb_width", "atr",
    # Momentum
    "roc", "willr", "stoch_k", "stoch_d",
    # Volume
    "obv_norm",
]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("timestamp").reset_index(drop=True)

    # ── Price-derived ─────────────────────────────────────────────────────────
    df["log_return"]     = np.log(df["close"] / df["close"].shift(1))
    df["volume_change"]  = np.log(df["volume"] / df["volume"].shift(1).replace(0, np.nan))
    df["high_low_range"] = (df["high"] - df["low"]) / df["close"]
    df["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"] + 1e-9)

    if HAS_TA:

        # ── RSI ───────────────────────────────────────────────────────────────
        df.ta.rsi(length=14, append=True)
        rsi_col = [c for c in df.columns if c.startswith("RSI_")]
        if rsi_col:
            df.rename(columns={rsi_col[0]: "rsi"}, inplace=True)

        # ── MACD ──────────────────────────────────────────────────────────────
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        macd_col  = [c for c in df.columns if c.startswith("MACD_") and not c.startswith("MACDs_") and not c.startswith("MACDh_")]
        macds_col = [c for c in df.columns if c.startswith("MACDs_")]
        macdh_col = [c for c in df.columns if c.startswith("MACDh_")]
        if macd_col:  df.rename(columns={macd_col[0]: "macd"}, inplace=True)
        if macds_col: df.rename(columns={macds_col[0]: "macd_signal"}, inplace=True)
        if macdh_col: df.rename(columns={macdh_col[0]: "macd_hist"}, inplace=True)
        else: df["macd_hist"] = df.get("macd", 0) - df.get("macd_signal", 0)

        # ── Bollinger Bands ───────────────────────────────────────────────────
        df.ta.bbands(length=20, append=True)
        bbu_col = [c for c in df.columns if c.startswith("BBU_")]
        bbl_col = [c for c in df.columns if c.startswith("BBL_")]
        bbb_col = [c for c in df.columns if c.startswith("BBB_")]
        bbm_col = [c for c in df.columns if c.startswith("BBM_")]
        bbp_col = [c for c in df.columns if c.startswith("BBP_")]
        if bbu_col: df.rename(columns={bbu_col[0]: "bb_upper"}, inplace=True)
        if bbl_col: df.rename(columns={bbl_col[0]: "bb_lower"}, inplace=True)
        if bbb_col: df.rename(columns={bbb_col[0]: "bb_width"}, inplace=True)
        for col in bbm_col + bbp_col:
            if col in df.columns:
                df.drop(columns=[col], inplace=True)

        # ── EMAs ──────────────────────────────────────────────────────────────
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        ema9_col  = [c for c in df.columns if c.startswith("EMA_9")]
        ema21_col = [c for c in df.columns if c.startswith("EMA_21")]
        if ema9_col:  df.rename(columns={ema9_col[0]: "ema_9"}, inplace=True)
        if ema21_col: df.rename(columns={ema21_col[0]: "ema_21"}, inplace=True)

        # ── ATR ───────────────────────────────────────────────────────────────
        df.ta.atr(length=14, append=True)
        atr_col = [c for c in df.columns if c.startswith("ATRr_") or c.startswith("ATR_")]
        if atr_col: df.rename(columns={atr_col[0]: "atr"}, inplace=True)

        # ── Rate of Change ────────────────────────────────────────────────────
        df.ta.roc(length=10, append=True)
        roc_col = [c for c in df.columns if c.startswith("ROC_")]
        if roc_col: df.rename(columns={roc_col[0]: "roc"}, inplace=True)

        # ── Williams %R ───────────────────────────────────────────────────────
        df.ta.willr(length=14, append=True)
        willr_col = [c for c in df.columns if c.startswith("WILLR_")]
        if willr_col: df.rename(columns={willr_col[0]: "willr"}, inplace=True)

        # ── Stochastic ────────────────────────────────────────────────────────
        df.ta.stoch(append=True)
        stochk_col = [c for c in df.columns if c.startswith("STOCHk_")]
        stochd_col = [c for c in df.columns if c.startswith("STOCHd_")]
        if stochk_col: df.rename(columns={stochk_col[0]: "stoch_k"}, inplace=True)
        if stochd_col: df.rename(columns={stochd_col[0]: "stoch_d"}, inplace=True)

        # ── OBV normalized ────────────────────────────────────────────────────
        df.ta.obv(append=True)
        obv_col = [c for c in df.columns if c.startswith("OBV")]
        if obv_col:
            df.rename(columns={obv_col[0]: "obv_raw"}, inplace=True)
            df["obv_norm"] = df["obv_raw"].pct_change().fillna(0)
            df.drop(columns=["obv_raw"], inplace=True)

    else:
        # ── Manual fallbacks ──────────────────────────────────────────────────
        df["rsi"]        = _manual_rsi(df["close"], 14)
        df["macd"], df["macd_signal"] = _manual_macd(df["close"])
        df["macd_hist"]  = df["macd"] - df["macd_signal"]
        df["ema_9"]      = df["close"].ewm(span=9).mean()
        df["ema_21"]     = df["close"].ewm(span=21).mean()
        df["bb_upper"], df["bb_lower"], df["bb_width"] = _manual_bbands(df["close"])
        df["atr"]        = _manual_atr(df)
        df["roc"]        = df["close"].pct_change(10)
        df["willr"]      = _manual_willr(df, 14)
        df["stoch_k"], df["stoch_d"] = _manual_stoch(df, 14)
        df["obv_norm"]   = _manual_obv(df)

    # ── Derived from indicators ───────────────────────────────────────────────
    df["ema_cross"] = df["ema_9"] - df["ema_21"]

    # ── Target label ─────────────────────────────────────────────────────────
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)

    # ── Validate all required columns exist ──────────────────────────────────
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(missing)

    df.dropna(subset=FEATURE_COLS + ["target"], inplace=True)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(subset=FEATURE_COLS, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


def normalize_features(df: pd.DataFrame, scaler=None):
    from sklearn.preprocessing import StandardScaler
    df = df.copy()
    if scaler is None:
        scaler = StandardScaler()
        df[FEATURE_COLS] = scaler.fit_transform(df[FEATURE_COLS])
    else:
        df[FEATURE_COLS] = scaler.transform(df[FEATURE_COLS])
    return df, scaler


def build_windows(df: pd.DataFrame, window: int = 30):
    X, y = [], []
    values = df[FEATURE_COLS].values
    targets = df["target"].values
    for i in range(window, len(df)):
        X.append(values[i - window:i])
        y.append(targets[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ── Manual Indicator Fallbacks ────────────────────────────────────────────────

def _manual_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _manual_macd(series: pd.Series):
    ema_fast = series.ewm(span=12).mean()
    ema_slow = series.ewm(span=26).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9).mean()
    return macd, signal


def _manual_bbands(series: pd.Series, period: int = 20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    width = (upper - lower) / sma
    return upper, lower, width


def _manual_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close).abs(),
        (low - close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _manual_willr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    lowest_low   = df["low"].rolling(period).min()
    return -100 * (highest_high - df["close"]) / (highest_high - lowest_low + 1e-9)


def _manual_stoch(df: pd.DataFrame, period: int = 14):
    lowest_low   = df["low"].rolling(period).min()
    highest_high = df["high"].rolling(period).max()
    k = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low + 1e-9)
    d = k.rolling(3).mean()
    return k, d


def _manual_obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff()).fillna(0)
    obv = (direction * df["volume"]).cumsum()
    return obv.pct_change().fillna(0)