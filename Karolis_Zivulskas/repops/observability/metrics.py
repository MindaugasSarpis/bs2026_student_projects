"""Prometheus metrics definitions.

Import and increment these from anywhere in the codebase.
When PROMETHEUS_MULTIPROC_DIR is set (required for Celery workers), each
process writes to files in that directory and the HTTP server aggregates
them via MultiProcessCollector.
"""

from __future__ import annotations

import os
import threading

# Create multiprocess dir BEFORE any metrics objects are instantiated —
# prometheus_client opens mmap files at Counter/Histogram construction time.
_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _multiproc_dir:
    os.makedirs(_multiproc_dir, exist_ok=True)

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from repops.settings import settings

# Collection
posts_collected_total = Counter(
    "repops_posts_collected_total",
    "Total posts collected from all sources",
    ["target_id", "post_type"],
)
collection_errors_total = Counter(
    "repops_collection_errors_total",
    "Total collection errors",
    ["target_id", "error_type"],
)
collection_duration_seconds = Histogram(
    "repops_collection_duration_seconds",
    "Time (seconds) spent in a single collection run",
    ["target_id"],
    buckets=(1, 5, 10, 30, 60, 120, 300),
)

# Analysis
posts_analyzed_total = Counter(
    "repops_posts_analyzed_total",
    "Total posts that completed the analysis pipeline",
    ["language"],
)
keyword_matches_total = Counter(
    "repops_keyword_matches_total",
    "Total keyword matches across all posts",
    ["keyword_set"],
)
keyword_hits_by_pattern = Counter(
    "repops_keyword_hits_total",
    "Hits per individual keyword pattern",
    ["pattern", "severity"],
)
posts_flagged_total = Counter(
    "repops_posts_flagged_total",
    "Posts that were flagged (score >= flag threshold)",
    ["severity"],  # low | medium | high
)
analysis_score_histogram = Histogram(
    "repops_analysis_hate_speech_score",
    "Distribution of hate speech model scores (0-1)",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)
analysis_duration_seconds = Histogram(
    "repops_analysis_duration_seconds",
    "Time (seconds) spent on a single post analysis",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
)

# Queue
queue_depth = Gauge(
    "repops_queue_depth",
    "Current task queue depth",
    ["queue_name"],
)

# Startup helper
_metrics_server_started = False


def start_metrics_server(port: int | None = None) -> None:
    """Start Prometheus HTTP server.

    When PROMETHEUS_MULTIPROC_DIR is set, uses MultiProcessCollector so that
    metrics incremented in Celery forked child processes are aggregated and
    visible. The directory is created automatically if it doesn't exist.
    """
    global _metrics_server_started
    if _metrics_server_started:
        return

    p = port if port is not None else settings.prometheus_port
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")

    if multiproc_dir:
        os.makedirs(multiproc_dir, exist_ok=True)
        from prometheus_client import CollectorRegistry, make_wsgi_app
        from prometheus_client.multiprocess import MultiProcessCollector
        from wsgiref.simple_server import WSGIRequestHandler, make_server

        registry = CollectorRegistry()
        MultiProcessCollector(registry)
        wsgi_app = make_wsgi_app(registry)

        class _Silent(WSGIRequestHandler):
            def log_message(self, *_a: object, **_kw: object) -> None:
                pass

        def _serve() -> None:
            with make_server("0.0.0.0", p, wsgi_app, handler_class=_Silent) as srv:
                srv.serve_forever()

        threading.Thread(target=_serve, daemon=True).start()
    else:
        start_http_server(p)

    _metrics_server_started = True
