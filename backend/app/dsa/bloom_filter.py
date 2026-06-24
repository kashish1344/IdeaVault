"""
Bloom filter for duplicate prompt detection.

Space-efficient probabilistic set: O(1) insert & lookup, no false negatives.
False positive rate is bounded by capacity and error_rate parameters.

Uses k independent hash functions derived from MurmurHash3 + index seed.
Bit array is stored as a bytearray for compact memory layout.
"""

from __future__ import annotations

import math
import struct
import threading
from hashlib import md5, sha256


class BloomFilter:
    """
    Counting Bloom filter with configurable capacity and error rate.

    Parameters
    ----------
    capacity:   expected number of elements
    error_rate: desired false-positive probability (e.g. 0.01 = 1%)
    """

    def __init__(self, capacity: int = 100_000, error_rate: float = 0.01) -> None:
        if not (0 < error_rate < 1):
            raise ValueError("error_rate must be between 0 and 1")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._capacity = capacity
        self._error_rate = error_rate
        self._size = self._optimal_size(capacity, error_rate)
        self._num_hashes = self._optimal_hashes(self._size, capacity)
        self._bits = bytearray(math.ceil(self._size / 8))
        self._count = 0
        self._lock = threading.RLock()

    # ──────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────

    def add(self, item: str) -> None:
        with self._lock:
            for pos in self._hashes(item):
                self._set_bit(pos)
            self._count += 1

    def contains(self, item: str) -> bool:
        """Returns True if item *might* be in the set (may false-positive)."""
        with self._lock:
            return all(self._get_bit(pos) for pos in self._hashes(item))

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    @property
    def saturation(self) -> float:
        """Fraction of bits set — useful for monitoring filter health."""
        with self._lock:
            set_bits = sum(bin(b).count("1") for b in self._bits)
            return set_bits / self._size

    # ──────────────────────────────────────────────────────────────
    # Hash functions
    # ──────────────────────────────────────────────────────────────

    def _hashes(self, item: str) -> list[int]:
        encoded = item.encode("utf-8")
        h1 = int(md5(encoded).hexdigest(), 16)
        h2 = int(sha256(encoded).hexdigest(), 16)
        # Double hashing: h_i = (h1 + i*h2) mod m
        return [(h1 + i * h2) % self._size for i in range(self._num_hashes)]

    # ──────────────────────────────────────────────────────────────
    # Bit operations
    # ──────────────────────────────────────────────────────────────

    def _set_bit(self, pos: int) -> None:
        self._bits[pos // 8] |= 1 << (pos % 8)

    def _get_bit(self, pos: int) -> bool:
        return bool(self._bits[pos // 8] & (1 << (pos % 8)))

    # ──────────────────────────────────────────────────────────────
    # Math
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        return int(-n * math.log(p) / (math.log(2) ** 2))

    @staticmethod
    def _optimal_hashes(m: int, n: int) -> int:
        return max(1, int(m / n * math.log(2)))
