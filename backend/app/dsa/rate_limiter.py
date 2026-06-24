"""
Token Bucket rate limiter — per-user API call throttling.

Each user gets a bucket with:
  - capacity:     max burst size
  - refill_rate:  tokens added per second

consume(n) removes n tokens if available, else returns False.
Tokens are refilled lazily on each consume() call.

RateLimiter is a registry mapping user_id → TokenBucket,
backed by the LRU cache to bound memory usage.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from .lru_cache import LRUCache


class TokenBucket:
    """Single token bucket. Thread-safe."""

    def __init__(self, capacity: float, refill_rate: float) -> None:
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("capacity and refill_rate must be positive")
        self._capacity = capacity
        self._refill_rate = refill_rate          # tokens / second
        self._tokens: float = capacity           # start full
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume `tokens`. Returns True on success."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    @property
    def available(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now


class RateLimiter:
    """
    Per-entity rate limiter backed by an LRU cache.

    Entities not seen recently are evicted from the cache;
    their bucket resets when they next appear.
    """

    def __init__(
        self,
        capacity: float = 10.0,
        refill_rate: float = 1.0,
        cache_size: int = 10_000,
    ) -> None:
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._cache: LRUCache[str, TokenBucket] = LRUCache(cache_size)
        self._lock = threading.Lock()

    def is_allowed(self, entity_id: str, tokens: float = 1.0) -> bool:
        bucket = self._get_or_create(entity_id)
        return bucket.consume(tokens)

    def available_tokens(self, entity_id: str) -> float:
        return self._get_or_create(entity_id).available

    def _get_or_create(self, entity_id: str) -> TokenBucket:
        bucket = self._cache.get(entity_id)
        if bucket is None:
            with self._lock:
                # Double-checked locking
                bucket = self._cache.get(entity_id)
                if bucket is None:
                    bucket = TokenBucket(self._capacity, self._refill_rate)
                    self._cache.put(entity_id, bucket)
        return bucket
