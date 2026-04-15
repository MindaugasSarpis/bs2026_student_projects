from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline.fetch import append_all
from pipeline.train import run_training
import logging

logging.basicConfig(level=logging.INFO)
scheduler = BlockingScheduler(timezone="UTC")


@scheduler.scheduled_job("cron", hour=0, minute=10)
def daily_append():
    """Runs at 00:10 UTC — appends yesterday's closed candle."""
    logging.info("Running daily append...")
    append_all()
    logging.info("Append complete.")


@scheduler.scheduled_job("cron", hour=0, minute=30)
def daily_train():
    """Runs at 00:30 UTC — retrains model on updated data."""
    logging.info("Running daily training...")
    result = run_training()
    logging.info(f"Training done — Val Acc: {result['val_accuracy']:.2%}")


if __name__ == "__main__":
    logging.info("Scheduler started.")
    scheduler.start()
