"""Celery beat periodic task schedules."""

from __future__ import annotations

from celery.schedules import crontab

from repops.workers.app import app

app.conf.beat_schedule = {
    # Scan all active targets every 15 minutes
    "collect-all-targets": {
        "task": "repops.collector.tasks.collect_all_active_targets",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "collection"},
    },
    # Safety net: re-queue RAW posts that weren't picked up inline by collection
    "requeue-raw-posts": {
        "task": "repops.analyzer.tasks.requeue_raw_posts",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "analysis"},
    },
    # Recalculate profile risk scores hourly
    "recalculate-profile-scores": {
        "task": "repops.analyzer.tasks.recalculate_all_profile_scores",
        "schedule": crontab(minute=0),
        "options": {"queue": "analysis"},
    },
    # Update Prometheus queue-depth gauge every minute
    "update-queue-depth-metric": {
        "task": "repops.workers.tasks.update_queue_depth_metric",
        "schedule": crontab(minute="*"),
        "options": {"queue": "default"},
    },
}
