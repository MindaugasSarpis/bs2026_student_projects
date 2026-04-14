import click
from pipeline.fetch import bootstrap_all, append_all, SYMBOLS, MODEL_CONFIGS
from pipeline.train import run_training
from api.predict import get_prediction


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
        raise click.BadParameter(f"Unknown models: {invalid}. Valid options: {list(MODEL_CONFIGS.keys())}")
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
        raise click.BadParameter(f"Unknown models: {invalid}. Valid options: {list(MODEL_CONFIGS.keys())}")
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
        raise click.BadParameter(f"Unknown models: {invalid}. Valid options: {list(MODEL_CONFIGS.keys())}")

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
    help="Which model(s) to run inference with: m1, m2, m3 or 'all' (ensemble)"
)
@click.option("--threshold", default=0.65, show_default=True,
              help="Minimum confidence to mark signal as reliable")
def predict(symbol, model, threshold):
    """Predict next candle direction for a symbol."""
    targets = list(MODEL_CONFIGS.keys()) if model == "all" else [model]
    invalid = [m for m in targets if m not in MODEL_CONFIGS]
    if invalid:
        raise click.BadParameter(f"Unknown models: {invalid}. Valid options: {list(MODEL_CONFIGS.keys())}")

    click.echo(f"\nRunning prediction for {symbol} using models: {targets}\n")

    results = []
    for m in targets:
        try:
            result = get_prediction(symbol=symbol, model=m, threshold=threshold)
            results.append(result)
            reliable_str = "YES" if result["reliable"] else "NO  (below threshold)"
            click.echo(f"  [{m.upper()}] {result['direction']:<5}  "
                       f"confidence={result['confidence']:.1%}  "
                       f"reliable={reliable_str}  "
                       f"window_end={result['window_end']}")
        except FileNotFoundError as e:
            click.echo(f"  [{m.upper()}] SKIPPED — {e}")

    # Ensemble summary if multiple models ran
    if len(results) > 1:
        confident = [r for r in results if r["reliable"]]
        click.echo(f"\n  Ensemble: {len(confident)}/{len(results)} models above threshold")

        if len(confident) == 0:
            click.echo("  Signal    : ABSTAIN — no model reached confidence threshold")
        else:
            avg_conf = sum(r["confidence"] for r in confident) / len(confident)
            direction = "UP" if avg_conf >= 0.5 else "DOWN"
            click.echo(f"  Signal    : {direction}")
            click.echo(f"  Avg Conf  : {avg_conf:.1%}")

    click.echo(f"\n  Model date : {results[0]['model_date'] if results else 'N/A'}")


@cli.command()
def status():
    """Show data availability and latest model dates for all models."""
    import os
    from pathlib import Path

    click.echo("\n── Data Status ──────────────────────────────")
    for m, cfg in MODEL_CONFIGS.items():
        model_data_dir = Path("data/raw") / m
        if not model_data_dir.exists():
            click.echo(f"  [{m.upper()}] No data found — run: python cli.py fetch --models {m}")
            continue
        files = list(model_data_dir.glob("*.parquet"))
        total_rows = 0
        for f in files:
            try:
                import pandas as pd
                df = pd.read_parquet(f)
                total_rows += len(df)
            except Exception:
                pass
        click.echo(f"  [{m.upper()}] {len(files)} symbols | {total_rows:,} total candles "
                   f"| timeframe={cfg['timeframe']}")

    click.echo("\n── Model Status ─────────────────────────────")
    models_dir = Path("models")
    for m in MODEL_CONFIGS:
        latest_file = models_dir / m / "latest"
        if latest_file.exists():
            date = latest_file.read_text().strip()
            click.echo(f"  [{m.upper()}] Latest checkpoint: {date}")
        else:
            click.echo(f"  [{m.upper()}] No trained model — run: python cli.py train --model {m}")
    click.echo("")


if __name__ == "__main__":
    cli()
