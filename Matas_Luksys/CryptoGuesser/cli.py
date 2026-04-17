import click
from datetime import datetime, UTC
from pipeline.fetch import bootstrap_all, append_all, SYMBOLS, MODEL_CONFIGS
from pipeline.train import run_training
from pipeline.predict import get_prediction


@click.group()
def cli():
    """CryptoGuesser — data pipeline & model management"""
    pass


@cli.command()
@click.option(
    "--models", default="all", show_default=True,
    help="Comma-separated models to fetch: m1,m2,m3 or 'all'"
)
def fetch(models):
    """Bootstrap full historical data for all symbols."""
    target = list(MODEL_CONFIGS.keys()) if models == "all" else models.split(",")
    invalid = [m for m in target if m not in MODEL_CONFIGS]
    if invalid:
        raise click.BadParameter(f"Unknown models: {invalid}. Valid: {list(MODEL_CONFIGS.keys())}")
    click.echo(f"Bootstrapping models: {target}")
    for m in target:
        cfg = MODEL_CONFIGS[m]
        click.echo(f"  [{m.upper()}] timeframe={cfg['timeframe']} | days={cfg['days']}")
    bootstrap_all(models=target)
    click.echo("\nDone.")


@cli.command()
@click.option(
    "--models", default="all", show_default=True,
    help="Comma-separated models to append: m1,m2,m3 or 'all'"
)
def append(models):
    """Append latest candles to existing data store."""
    target = list(MODEL_CONFIGS.keys()) if models == "all" else models.split(",")
    invalid = [m for m in target if m not in MODEL_CONFIGS]
    if invalid:
        raise click.BadParameter(f"Unknown models: {invalid}. Valid: {list(MODEL_CONFIGS.keys())}")
    click.echo(f"Appending latest candles for models: {target}")
    append_all(models=target)
    click.echo("\nDone.")


@cli.command()
@click.option(
    "--model", default="all", show_default=True,
    help="Which model to train: m1, m2, m3 or 'all'"
)
@click.option("--epochs", default=150, show_default=True, help="Max training epochs")
@click.option("--window", default=None, type=int, show_default=True,
              help="Lookback window in candles. Defaults to model config value if not set.")
def train(model, epochs, window):
    """Train a new model checkpoint on stored data."""
    targets = list(MODEL_CONFIGS.keys()) if model == "all" else [model]
    invalid = [m for m in targets if m not in MODEL_CONFIGS]
    if invalid:
        raise click.BadParameter(f"Unknown models: {invalid}. Valid: {list(MODEL_CONFIGS.keys())}")

    for m in targets:
        effective_window = window if window is not None else MODEL_CONFIGS[m]["lookback"]
        click.echo(f"\n[{m.upper()}] Training — window={effective_window} | max_epochs={epochs}")
        result = run_training(model=m, epochs=epochs, window=effective_window)
        click.echo(f"  Val Accuracy : {result['val_accuracy']:.2%}")
        click.echo(f"  Val AUC      : {result['val_auc']:.3f}")
        click.echo(f"  Model saved  : {result['model_dir']}")

    click.echo("\nTraining complete.")


@cli.command()
@click.option("--symbol", default="BTC/USDT", show_default=True, help="e.g. BTC/USDT")
@click.option(
    "--model", default="all", show_default=True,
    help="Which model(s) to use: m1, m2, m3 or 'all' (ensemble)"
)
@click.option("--threshold", default=0.65, show_default=True,
              help="Minimum confidence to mark signal as reliable")
def predict(symbol, model, threshold):
    """Predict next candle direction for a symbol."""
    import math

    targets = list(MODEL_CONFIGS.keys()) if model == "all" else [model]
    invalid = [m for m in targets if m not in MODEL_CONFIGS]
    if invalid:
        raise click.BadParameter(f"Unknown models: {invalid}. Valid: {list(MODEL_CONFIGS.keys())}")

    click.echo(f"\nRunning prediction for {symbol} using models: {targets}")
    click.echo(f"  Started at : {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    results = []
    for m in targets:
        try:
            result = get_prediction(symbol=symbol, model=m, threshold=threshold)

            conf = result.get("confidence")
            if conf is None or (isinstance(conf, float) and math.isnan(conf)):
                click.echo(f"  [{m.upper()}] SKIPPED — model returned invalid confidence (NaN). "
                           f"Retrain with: python cli.py train --model {m}")
                continue

            results.append(result)
            reliable_str = "YES" if result["reliable"] else "NO  (below threshold)"
            click.echo(f"  [{m.upper()}] {result['direction']:<5}  "
                       f"confidence={conf:.1%}  "
                       f"reliable={reliable_str}  "
                       f"window_end={result['window_end']}")

        except FileNotFoundError:
            click.echo(f"  [{m.upper()}] SKIPPED — no trained model found. "
                       f"Run: python cli.py train --model {m}")
        except Exception as e:
            click.echo(f"  [{m.upper()}] ERROR — {e}")

    # Ensemble summary
    if len(targets) > 1:
        click.echo(f"\n  ── Ensemble ──────────────────────────────────")

        if not results:
            click.echo("  No models available. Train all models first:")
            click.echo("  python cli.py train")
            return

        confident = [r for r in results if r["reliable"]]
        click.echo(f"  Models ran     : {len(results)}/{len(targets)}")
        click.echo(f"  Above threshold: {len(confident)}/{len(results)}")

        if not confident:
            click.echo("  Signal         : ABSTAIN — no model confident enough")
            click.echo(f"  (lower --threshold below {threshold} to force a signal)")
        else:
            votes_up   = sum(1 for r in confident if r["signal"] == 1)
            votes_down = len(confident) - votes_up
            direction  = "UP" if votes_up >= votes_down else "DOWN"

            # Average confidence toward the winning direction
            if direction == "UP":
                avg_conf = sum(
                    r["confidence"] if r["signal"] == 1 else 1 - r["confidence"]
                    for r in confident
                ) / len(confident)
            else:
                avg_conf = sum(
                    1 - r["confidence"] if r["signal"] == 1 else r["confidence"]
                    for r in confident
                ) / len(confident)

            click.echo(f"  Signal         : {direction}")
            click.echo(f"  Avg Confidence : {avg_conf:.1%}")
            click.echo(f"  Votes          : {votes_up} UP / {votes_down} DOWN")

    if results:
        click.echo(f"\n  Model date : {results[0]['model_date']}")
    click.echo("")


@cli.command()
def status():
    """Show data availability and latest model dates for all models."""
    from pathlib import Path
    import pandas as pd

    click.echo("\n── Data Status ──────────────────────────────")
    for m, cfg in MODEL_CONFIGS.items():
        model_data_dir = Path("data/raw") / m
        if not model_data_dir.exists():
            click.echo(f"  [{m.upper()}] No data found — run: python cli.py fetch --models {m}")
            continue
        files = list(model_data_dir.glob("*.parquet"))
        total_rows = 0
        date_min, date_max = None, None
        for f in files:
            try:
                df = pd.read_parquet(f)
                total_rows += len(df)
                if "timestamp" in df.columns and len(df) > 0:
                    fmin = df["timestamp"].min()
                    fmax = df["timestamp"].max()
                    if date_min is None or fmin < date_min:
                        date_min = fmin
                    if date_max is None or fmax > date_max:
                        date_max = fmax
            except Exception:
                pass
        date_range = ""
        if date_min and date_max:
            date_range = f" | {str(date_min)[:10]} → {str(date_max)[:10]}"
        click.echo(f"  [{m.upper()}] {len(files)} symbols | {total_rows:,} candles"
                   f" | tf={cfg['timeframe']}{date_range}")

    click.echo("\n── Model Status ─────────────────────────────")
    models_dir = Path("models")
    for m in MODEL_CONFIGS:
        latest_file = models_dir / m / "latest"
        if latest_file.exists():
            date = latest_file.read_text().strip()
            model_path = models_dir / m / date / "model.pt"
            size = ""
            if model_path.exists():
                mb = model_path.stat().st_size / 1024 / 1024
                size = f" ({mb:.1f} MB)"
            click.echo(f"  [{m.upper()}] checkpoint={date}{size}")
        else:
            click.echo(f"  [{m.upper()}] No model — run: python cli.py train --model {m}")
    click.echo("")


if __name__ == "__main__":
    cli()