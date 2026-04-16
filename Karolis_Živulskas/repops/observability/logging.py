from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog
from structlog.types import Processor

from repops.settings import settings

_configured = False


def configure_logging() -> None:
    """Configure structlog once at application start-up."""
    global _configured
    if _configured:
        return

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Resolve log file path: env var takes priority, then default alongside package
    if settings.log_file:
        _log_file = Path(settings.log_file)
    else:
        _log_file = Path(__file__).resolve().parents[2] / "logs" / "repops.log"

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    json_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    # Console handler — human-friendly in dev, JSON in production
    if settings.is_production:
        console_formatter = json_formatter
    else:
        console_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # File handler — always JSON so Loki/Promtail can parse it
    try:
        _log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_log_file, encoding="utf-8")
        file_handler.setFormatter(json_formatter)
    except OSError:
        file_handler = None  # type: ignore[assignment]

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    if file_handler:
        root.addHandler(file_handler)
    root.setLevel(log_level)

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "playwright", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)  # type: ignore[return-value]
