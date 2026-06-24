"""
MinHeap-based priority queue for job scheduling.

Time complexity:  push O(log n) | pop O(log n) | peek O(1)
Space complexity: O(n)

Jobs with lower priority value are processed first (min-heap).
Ties are broken by insertion timestamp (FIFO within same priority).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class JobPriority(IntEnum):
    CRITICAL = 0  # system retries, admin tasks
    HIGH = 1      # premium users
    NORMAL = 2    # standard users
    LOW = 3       # background / batch


@dataclass(order=True)
class HeapEntry(Generic[T]):
    priority: int
    timestamp: float = field(compare=True)
    sequence: int = field(compare=True)   # monotonic counter for total ordering
    item: T = field(compare=False)


class MinHeap(Generic[T]):
    """Thread-safe min-heap priority queue."""

    def __init__(self) -> None:
        self._heap: list[HeapEntry[T]] = []
        self._sequence: int = 0
        self._lock = threading.Lock()

    # ──────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────

    def push(self, item: T, priority: int = JobPriority.NORMAL) -> None:
        with self._lock:
            entry = HeapEntry(
                priority=priority,
                timestamp=time.monotonic(),
                sequence=self._sequence,
                item=item,
            )
            self._sequence += 1
            self._heap.append(entry)
            self._sift_up(len(self._heap) - 1)

    def pop(self) -> Optional[T]:
        with self._lock:
            if not self._heap:
                return None
            self._swap(0, len(self._heap) - 1)
            entry = self._heap.pop()
            if self._heap:
                self._sift_down(0)
            return entry.item

    def peek(self) -> Optional[T]:
        with self._lock:
            return self._heap[0].item if self._heap else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    def is_empty(self) -> bool:
        return len(self) == 0

    # ──────────────────────────────────────────────────────────────
    # Internal heap operations
    # ──────────────────────────────────────────────────────────────

    def _sift_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) // 2
            if self._heap[idx] < self._heap[parent]:
                self._swap(idx, parent)
                idx = parent
            else:
                break

    def _sift_down(self, idx: int) -> None:
        n = len(self._heap)
        while True:
            smallest = idx
            left = 2 * idx + 1
            right = 2 * idx + 2

            if left < n and self._heap[left] < self._heap[smallest]:
                smallest = left
            if right < n and self._heap[right] < self._heap[smallest]:
                smallest = right

            if smallest == idx:
                break
            self._swap(idx, smallest)
            idx = smallest

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
