"""Token-bucket rate limiter for polite scraping."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from repops.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """Async token-bucket rate limiter.

    rate:     tokens added per second (refill rate)
    capacity: max token capacity (burst allowance)
    """

    rate: float
    capacity: float
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0) -> None:
        """Block until `tokens` are available, then consume them."""
        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            wait_time = (tokens - self._tokens) / self.rate

        logger.debug("rate_limit_backoff", wait_seconds=round(wait_time, 2))
        await asyncio.sleep(wait_time)

        async with self._lock:
            self._refill()
            self._tokens -= tokens


# ~200 page loads/hour, burst of 5 for quick successive requests
facebook_scrape_limiter = TokenBucket(rate=200 / 3600, capacity=5)
