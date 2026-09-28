# CryptoGuesser

AI-powered cryptocurrency price direction predictor using a 3-model LSTM ensemble
trained on Binance market data. Predicts whether a token's next candle will go UP or DOWN.

***

## Architecture

Three models are trained in parallel, each seeing a different time resolution:

| Model | Candle Size | History | Lookback | Captures |
|-------|-------------|---------|----------|----------|
| M1    | 1h          | 6 months | 96 candles | Short momentum, hourly patterns |
| M2    | 4h          | 1 year   | 84 candles | Weekly cycles, trend continuation |
| M3    | 1d          | 3 years  | 60 candles | Macro trend, bull/bear phases |

Predictions from all three models are combined into an ensemble signal.
Only models above the confidence threshold (default 65%) vote.
If no model is confident enough, the system abstains.

***

## Project Structure

```
CryptoGuesser/
├── pipeline/
│   ├── fetch.py       — data ingestion from Binance (bootstrap + daily append)
│   ├── clean.py       — data cleaning and preprocessing
│   ├── features.py    — feature engineering
│   ├── train.py       — LSTM model training
│   └── predict.py     — inference / ensemble prediction
├── dashboard/
│   └── app.py         — Streamlit visual dashboard
├── data/raw/
│   └── m1, m2, m3     — parquet files per symbol per model (git-ignored)
├── models/
│   └── m1, m2, m3     — model checkpoints, scalers, config.json (git-ignored)
├── cli.py             — command-line entry point
└── requirements.txt
```

***

## Supported Symbols

BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, ADA/USDT,
AVAX/USDT, DOT/USDT, LINK/USDT, XRP/USDT, MATIC/USDT

***

## Requirements

- Python 3.12
- NVIDIA GPU with CUDA 12.x (recommended — CPU works but is slow)
- ~2GB disk space for data + models

***

## First-Time Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/CryptoGuesser.git
cd CryptoGuesser
```

### 2. Create and activate virtual environment

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 4. Create required local directories

```powershell
New-Item -Path "data\raw" -ItemType Directory -Force
New-Item -Path "models" -ItemType Directory -Force
```

### 5. Verify GPU is available (optional but recommended)

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

***

## Daily Usage

### Every session — activate the environment first

```powershell
cd C:\Github\CryptoGuesser
.venv\Scripts\activate
```

### Check current state

```powershell
python cli.py status
```

Shows how many candles are stored per model and which model checkpoints exist.

***

## Pipeline Commands

### Fetch — first-time data bootstrap

Downloads full history for all 10 symbols across M1, M2, M3.
Only needed once or after a full data reset.

```powershell
python cli.py fetch
```

Expected time: 10–15 minutes

### Append — daily data update

Fetches only the latest candles and merges them into existing data.
Run this every day before predicting.

```powershell
python cli.py append                  # update all models
python cli.py append --models m1      # update specific model only
```

### Train — build prediction models

Trains LSTM models on stored data. Run after initial fetch and after daily appends.

```powershell
python cli.py train                          # train all three models
python cli.py train --model m3               # train specific model
python cli.py train --model m3 --epochs 5   # quick smoke test
```

Expected time on RTX 4080 Super: 15–30 minutes for all three models.

| Metric | Meaning |
|--------|---------|
| Val AUC > 0.55 | Model is learning above random chance |
| Val AUC > 0.60 | Decent signal, usable |
| Val AUC > 0.65 | Strong signal for crypto prediction |

### Predict — get price direction signal

```powershell
python cli.py predict --symbol BTC/USDT            # ensemble (all 3 models)
python cli.py predict --symbol ETH/USDT --model m3 # single model
python cli.py predict --symbol SOL/USDT --threshold 0.70  # stricter confidence
```

***

## Dashboard

Launch the Streamlit dashboard for a visual interface to fetch data, train models, and view predictions:

```powershell
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`. Provides candlestick charts, pipeline controls, and prediction signals with confidence scores.

***

## Model Artifacts

Each training run saves the following to `models/{m1|m2|m3}/{YYYY-MM-DD}/`:

| File | Contents |
|------|----------|
| `model.pt` | PyTorch model weights + architecture config |
| `scaler.pkl` | Fitted StandardScaler — must match the model it was trained with |
| `config.json` | Training metadata: val accuracy, AUC, epochs, feature list |

`models/{m}/latest` is a text pointer to the most recent run date, used by `predict.py` to load the correct checkpoint.