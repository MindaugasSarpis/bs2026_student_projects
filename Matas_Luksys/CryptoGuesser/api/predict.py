import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))

import numpy as np
import torch
import joblib
from pathlib import Path

from fetch import load_raw, MODEL_CONFIGS
from clean import clean
from features import add_features, normalize_features, FEATURE_COLS

MODELS_DIR = Path("models")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model(model: str):
    latest_file = MODELS_DIR / model / "latest"
    if not latest_file.exists():
        raise FileNotFoundError(f"No trained model for [{model.upper()}]. Run: python cli.py train --model {model}")

    latest_date = latest_file.read_text().strip()
    model_dir = MODELS_DIR / model / latest_date

    checkpoint = torch.load(model_dir / "model.pt", map_location=DEVICE, weights_only=False)
    scaler = joblib.load(model_dir / "scaler.pkl")

    from train import CryptoLSTM
    net = CryptoLSTM(input_size=checkpoint["input_size"], cfg=checkpoint["cfg"])
    net.load_state_dict(checkpoint["model_state"])
    net.to(DEVICE)
    net.eval()

    return net, scaler, latest_date, checkpoint["window"]


def get_prediction(symbol: str, model: str = "m3", threshold: float = 0.65) -> dict:
    net, scaler, model_date, window = _load_model(model)

    df = load_raw(symbol, model)
    df = clean(df)
    df = add_features(df)

    # Use saved scaler — transform only, never refit
    df[FEATURE_COLS] = scaler.transform(df[FEATURE_COLS])

    if len(df) < window:
        raise ValueError(f"Not enough data for {symbol} — need at least {window} rows after cleaning")

    window_data = df[FEATURE_COLS].values[-window:]
    X = torch.tensor(window_data[np.newaxis, :, :], dtype=torch.float32).to(DEVICE)

    with torch.no_grad():
        with torch.amp.autocast(device_type="cuda"):
            logits = net(X)
        confidence = float(torch.sigmoid(logits).cpu().item())

    signal = 1 if confidence >= 0.5 else 0
    direction = "UP" if signal == 1 else "DOWN"
    reliable = confidence >= threshold or confidence <= (1 - threshold)

    return {
        "symbol": symbol,
        "signal": signal,
        "direction": direction,
        "confidence": confidence,
        "reliable": reliable,
        "threshold": threshold,
        "model_date": model_date,
        "window_end": str(df["timestamp"].iloc[-1].date()),
    }