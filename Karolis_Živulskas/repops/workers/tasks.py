"""Generic worker-level Celery tasks (not domain-specific)."""

from __future__ import annotations

import redis

from repops.observability.metrics import queue_depth
from repops.settings import settings
from repops.workers.app import app


@app.task(name="repops.workers.tasks.update_queue_depth_metric", bind=True)
def update_queue_depth_metric(self: object) -> None:  # noqa: ARG001
    """Sample Celery queue depths and push them to Prometheus."""
    r = redis.from_url(settings.redis_url)
    for queue_name in ("collection", "analysis", "reporting", "default"):
        depth = r.llen(queue_name)
        queue_depth.labels(queue_name=queue_name).set(depth)
