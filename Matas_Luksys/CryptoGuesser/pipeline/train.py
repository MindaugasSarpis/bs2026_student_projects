import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import roc_auc_score
import joblib
import sqlite3
import json
from pathlib import Path
from datetime import datetime

from fetch import load_raw, SYMBOLS, MODEL_CONFIGS
from clean import clean
from features import add_features, normalize_features, build_windows, FEATURE_COLS

MODELS_DIR = Path("models")
DB_PATH = Path("db/metadata.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[train] Using device: {DEVICE}")


# ── Model Complexity Config ───────────────────────────────────────────────────

MODEL_COMPLEXITY = {
    "m1": {"units_1": 512, "units_2": 256, "units_3": 128, "attention_heads": 8},
    "m2": {"units_1": 256, "units_2": 128, "units_3": 64,  "attention_heads": 4},
    "m3": {"units_1": 256, "units_2": 128, "units_3": 64,  "attention_heads": 4},
}


# ── Model Architecture ────────────────────────────────────────────────────────

class CryptoLSTM(nn.Module):
    def __init__(self, input_size: int, cfg: dict):
        super().__init__()

        self.lstm1 = nn.LSTM(input_size, cfg["units_1"], batch_first=True)
        self.drop1 = nn.Dropout(0.2)

        self.lstm2 = nn.LSTM(cfg["units_1"], cfg["units_2"], batch_first=True)
        self.drop2 = nn.Dropout(0.2)

        self.attention = nn.MultiheadAttention(
            embed_dim=cfg["units_2"],
            num_heads=cfg["attention_heads"],
            dropout=0.1,
            batch_first=True
        )
        self.layer_norm = nn.LayerNorm(cfg["units_2"])

        self.lstm3 = nn.LSTM(cfg["units_2"], cfg["units_3"], batch_first=True)
        self.drop3 = nn.Dropout(0.2)

        self.fc1 = nn.Linear(cfg["units_3"], 64)
        self.fc2 = nn.Linear(64, 32)
        self.out = nn.Linear(32, 1)
        self.relu = nn.ReLU()

    def forward(self, x):
        x, _ = self.lstm1(x)
        x = self.drop1(x)

        x, _ = self.lstm2(x)
        x = self.drop2(x)

        attn_out, _ = self.attention(x, x, x)
        x = self.layer_norm(x + attn_out)

        x, (h_n, _) = self.lstm3(x)
        x = self.drop3(h_n[-1])

        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.out(x).squeeze(1)  # raw logits — sigmoid applied at loss/inference


# ── Database ──────────────────────────────────────────────────────────────────

def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS training_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            model_name TEXT,
            model_path TEXT,
            val_accuracy REAL,
            val_auc REAL,
            epochs_trained INTEGER,
            symbols TEXT
        )
    """)
    con.commit()
    con.close()


def _log_run(run_date, model_name, model_path, val_acc, val_auc, epochs, symbols):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO training_runs
        (run_date, model_name, model_path, val_accuracy, val_auc, epochs_trained, symbols)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (run_date, model_name, model_path, val_acc, val_auc, epochs, json.dumps(symbols)))
    con.commit()
    con.close()


# ── Training ──────────────────────────────────────────────────────────────────

def run_training(model: str = "m3", symbols: list = None, window: int = None, epochs: int = 150) -> dict:
    _init_db()

    if model not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model '{model}'. Valid: {list(MODEL_CONFIGS.keys())}")

    if symbols is None:
        symbols = SYMBOLS
    if window is None:
        window = MODEL_CONFIGS[model]["lookback"]

    print(f"Loading and preparing data for [{model.upper()}]...")
    all_X, all_y = [], []

    for symbol in symbols:
        try:
            df = load_raw(symbol, model)
            df = clean(df)
            df = add_features(df)
            df, _ = normalize_features(df)
            X, y = build_windows(df, window=window)
            all_X.append(X)
            all_y.append(y)
            print(f"  {symbol}: {len(y)} samples")
        except Exception as e:
            print(f"  Skipping {symbol}: {e}")

    if not all_X:
        raise RuntimeError("No data loaded — run fetch first.")

    X = np.concatenate(all_X, axis=0)
    y = np.concatenate(all_y, axis=0)
    print(f"Total samples: {len(y)} | Class balance: {y.mean():.2%} up")
    print(f"Device: {DEVICE}")

    # Chronological split — NO shuffling
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    # Class weights for imbalance
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weights = torch.tensor(weights, dtype=torch.float32).to(DEVICE)

    # DataLoaders
    train_ds = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32)
    )
    val_ds = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32)
    )
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=False, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=256, shuffle=False, pin_memory=True)

    # Model, optimizer, scheduler
    cfg = MODEL_COMPLEXITY[model]
    net = CryptoLSTM(input_size=X.shape[2], cfg=cfg).to(DEVICE)
    optimizer = torch.optim.Adam(net.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # Mixed precision — uses tensor cores on 4080 Super
    amp_scaler = torch.amp.GradScaler()

    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0
    patience = 10
    history = []

    print(f"\nTraining [{model.upper()}] — {len(train_ds)} train | {len(val_ds)} val samples\n")

    for epoch in range(1, epochs + 1):

        # ── Train ──
        net.train()
        train_losses = []
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
            optimizer.zero_grad()

            with torch.amp.autocast(device_type="cuda"):
                logits = net(X_batch)
                sample_weights = torch.where(y_batch == 1, class_weights[1], class_weights[0])
                loss = nn.functional.binary_cross_entropy_with_logits(
                    logits, y_batch, weight=sample_weights
                )

            amp_scaler.scale(loss).backward()
            amp_scaler.step(optimizer)
            amp_scaler.update()
            train_losses.append(loss.item())

        # ── Validate ──
        net.eval()
        val_losses, val_preds, val_true = [], [], []
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
                with torch.amp.autocast(device_type="cuda"):
                    logits = net(X_batch)
                    loss = nn.functional.binary_cross_entropy_with_logits(logits, y_batch)
                val_losses.append(loss.item())
                # Apply sigmoid to convert logits → probabilities
                probs = torch.sigmoid(logits).cpu().numpy()
                val_preds.extend(probs)
                val_true.extend(y_batch.cpu().numpy())

        train_loss = np.mean(train_losses)
        val_loss   = np.mean(val_losses)
        val_acc    = np.mean((np.array(val_preds) >= 0.5) == np.array(val_true))
        try:
            val_auc = roc_auc_score(val_true, val_preds)
        except Exception:
            val_auc = 0.0

        scheduler.step(val_loss)
        history.append({
            "epoch": epoch, "train_loss": train_loss,
            "val_loss": val_loss, "val_accuracy": val_acc, "val_auc": val_auc
        })

        print(f"Epoch {epoch:>3}/{epochs} | "
              f"train_loss={train_loss:.4f} | "
              f"val_loss={val_loss:.4f} | "
              f"val_acc={val_acc:.2%} | "
              f"val_auc={val_auc:.3f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in net.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"\nEarly stopping at epoch {epoch}")
                break

    # Restore best weights
    net.load_state_dict(best_state)

    # Save checkpoint
    run_date = datetime.utcnow().strftime("%Y-%m-%d")
    model_dir = MODELS_DIR / model / run_date
    model_dir.mkdir(parents=True, exist_ok=True)

    torch.save({
        "model_state": net.state_dict(),
        "input_size": X.shape[2],
        "window": window,
        "cfg": cfg,
        "model_name": model,
    }, model_dir / "model.pt")

    # Save scaler fitted on training data
    from sklearn.preprocessing import StandardScaler
    flat_features = X_train.reshape(-1, X_train.shape[2])
    inf_scaler = StandardScaler().fit(flat_features)
    joblib.dump(inf_scaler, model_dir / "scaler.pkl")

    # Update latest pointer
    (MODELS_DIR / model).mkdir(parents=True, exist_ok=True)
    (MODELS_DIR / model / "latest").write_text(run_date)

    best_acc = max(h["val_accuracy"] for h in history)
    best_auc = max(h["val_auc"] for h in history)

    _log_run(run_date, model, str(model_dir), best_acc, best_auc, len(history), symbols)
    print(f"\nTraining complete — Val Accuracy: {best_acc:.2%} | Val AUC: {best_auc:.3f}")
    print(f"Saved to: {model_dir}")

    return {"val_accuracy": best_acc, "val_auc": best_auc, "model_dir": str(model_dir)}