"""Celery application factory.

Usage:
    celery -A repops.workers.app worker -Q collection,analysis,default
    celery -A repops.workers.app beat
"""

from __future__ import annotations

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from repops.observability.logging import configure_logging, get_logger
from repops.observability.metrics import start_metrics_server
from repops.settings import settings

logger = get_logger(__name__)

app = Celery("repops")

app.config_from_object(
    {
        "broker_url": settings.redis_url,
        "result_backend": settings.redis_url,
        "timezone": settings.celery_timezone,
        "enable_utc": True,
        # Serialisation
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        # Routing
        "task_routes": {
            "repops.collector.tasks.*": {"queue": "collection"},
            "repops.analyzer.tasks.*": {"queue": "analysis"},
        },
        # Reliability
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "beat_schedule_filename": ".celerybeat-schedule",
    }
)

# Autodiscover tasks from all sub-packages
app.autodiscover_tasks(
    ["repops.collector", "repops.analyzer", "repops.workers"],
    force=True,
)


@worker_ready.connect
def on_worker_ready(**_kwargs: object) -> None:
    configure_logging()
    start_metrics_server(port=settings.prometheus_worker_port)
    logger.info("celery_worker_ready", queues=["collection", "analysis"])


@worker_shutdown.connect
def on_worker_shutdown(**_kwargs: object) -> None:
    logger.info("celery_worker_shutdown")


from repops.workers import schedules as _schedules  # noqa: E402, F401 — registers beat schedule


def run() -> None:
    """Entrypoint for `repops-worker` CLI script."""
    app.worker_main(argv=["worker", "--loglevel=info", "-Q", "collection,analysis,default"])
