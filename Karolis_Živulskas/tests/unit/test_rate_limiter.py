"""Unit tests for the token-bucket rate limiter."""

import asyncio
import time

import pytest

from repops.collector.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_immediate_acquire_within_capacity():
    bucket = TokenBucket(rate=10.0, capacity=5.0)
    # Should not block — 5 tokens available
    t0 = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed < 0.5, f"Expected fast acquisition, took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_blocks_when_empty():
    # Very slow rate: 1 token/second, start with 1 token
    bucket = TokenBucket(rate=1.0, capacity=1.0)
    await bucket.acquire()  # consume the one token

    t0 = time.monotonic()
    await bucket.acquire()  # should wait ~1s for refill
    elapsed = time.monotonic() - t0
    assert 0.8 <= elapsed <= 2.0, f"Expected ~1s wait, got {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_capacity_cap():
    # Even if a lot of time passes, tokens should not exceed capacity
    bucket = TokenBucket(rate=100.0, capacity=3.0)
    await asyncio.sleep(0.1)  # let it refill well past capacity
    # We should only be able to acquire up to capacity before blocking
    # Acquire 3 immediately
    for _ in range(3):
        await bucket.acquire()

    # 4th should require a wait
    t0 = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - t0
    # At rate=100/s, ~10ms per token
    assert elapsed > 0.005


@pytest.mark.asyncio
async def test_zero_tokens_raises_no_exception():
    """Acquiring from an empty bucket eventually succeeds (no infinite loop)."""
    bucket = TokenBucket(rate=50.0, capacity=1.0)
    await bucket.acquire()
    # Next acquire should refill at 50/s → ~20ms wait
    await asyncio.wait_for(bucket.acquire(), timeout=1.0)
