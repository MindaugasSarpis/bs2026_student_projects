import ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT",
    "AVAX/USDT", "DOT/USDT", "LINK/USDT", "XRP/USDT", "MATIC/USDT"
]

# Model dataset configurations
MODEL_CONFIGS = {
    "m1": {"timeframe": "1h",  "days": 180,  "lookback": 96},
    "m2": {"timeframe": "4h",  "days": 365,  "lookback": 84},
    "m3": {"timeframe": "1d",  "days": 1095, "lookback": 60},
}

RAW_DIR = Path("data/raw")
exchange = ccxt.binance({"enableRateLimit": True})


def _symbol_to_filename(symbol: str) -> str:
    return symbol.replace("/", "_")


def _model_dir(model: str) -> Path:
    path = RAW_DIR / model
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_dataframe(raw: list, symbol: str) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["symbol"] = symbol
    return df


def fetch_full(symbol: str, model: str) -> pd.DataFrame:
    """Fetch full history for a symbol/model config. Used for bootstrap."""
    cfg = MODEL_CONFIGS[model]
    since_dt = datetime.now(timezone.utc) - timedelta(days=cfg["days"])
    since_ms = exchange.parse8601(since_dt.strftime("%Y-%m-%dT00:00:00Z"))

    all_candles = []
    while True:
        candles = exchange.fetch_ohlcv(
            symbol,
            timeframe=cfg["timeframe"],
            since=since_ms,
            limit=1000
        )
        if not candles:
            break
        all_candles.extend(candles)
        since_ms = candles[-1][0] + 1
        if len(candles) < 1000:
            break

    return _to_dataframe(all_candles, symbol)


def fetch_latest(symbol: str, model: str) -> pd.DataFrame:
    """Fetch only the last 2 candles for daily append."""
    cfg = MODEL_CONFIGS[model]
    raw = exchange.fetch_ohlcv(symbol, timeframe=cfg["timeframe"], limit=2)
    return _to_dataframe(raw, symbol)


def save_raw(df: pd.DataFrame, symbol: str, model: str):
    """Append-safe save — deduplicates by timestamp before writing."""
    path = _model_dir(model) / f"{_symbol_to_filename(symbol)}.parquet"
    if path.exists():
        existing = pd.read_parquet(path)
        combined = pd.concat([existing, df], ignore_index=True)
        combined.drop_duplicates(subset=["timestamp", "symbol"], keep="last", inplace=True)
        combined.sort_values("timestamp", inplace=True)
        combined.to_parquet(path, index=False)
    else:
        df.sort_values("timestamp", inplace=True)
        df.to_parquet(path, index=False)
    return path


def load_raw(symbol: str, model: str) -> pd.DataFrame:
    path = _model_dir(model) / f"{_symbol_to_filename(symbol)}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No data for {symbol} / {model}. Run fetch first.")
    return pd.read_parquet(path)


def bootstrap_all(models: list = None):
    """First-time full fetch for all symbols across specified models."""
    if models is None:
        models = list(MODEL_CONFIGS.keys())

    for model in models:
        cfg = MODEL_CONFIGS[model]
        print(f"\n[{model.upper()}] timeframe={cfg['timeframe']} | days={cfg['days']}")
        for symbol in SYMBOLS:
            print(f"  Fetching {symbol}...", end=" ")
            df = fetch_full(symbol, model)
            path = save_raw(df, symbol, model)
            print(f"{len(df)} candles → {path}")


def append_all(models: list = None):
    """Daily append — fetches last 2 candles per symbol/model, deduplicates."""
    if models is None:
        models = list(MODEL_CONFIGS.keys())

    for model in models:
        print(f"\n[{model.upper()}] Appending latest candles...")
        for symbol in SYMBOLS:
            df = fetch_latest(symbol, model)
            save_raw(df, symbol, model)
            print(f"  {symbol} updated")
