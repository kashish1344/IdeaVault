"""
LRU Cache — O(1) get & put via doubly-linked list + hash map.

Used to cache generated media metadata so identical requests
skip expensive AI inference.

Eviction: least-recently-used entry is removed when capacity is reached.
Thread-safe via a single reentrant lock.
"""

from __future__ import annotations

import threading
from typing import Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class _Node(Generic[K, V]):
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: K, value: V) -> None:
        self.key = key
        self.value = value
        self.prev: Optional[_Node[K, V]] = None
        self.next: Optional[_Node[K, V]] = None


class LRUCache(Generic[K, V]):
    """
    Capacity-bounded LRU cache.

    Internal layout:
        head <-> [MRU] ... [LRU] <-> tail

    head.next  = most-recently used
    tail.prev  = least-recently used
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._map: dict[K, _Node[K, V]] = {}
        self._lock = threading.RLock()

        # Sentinel nodes — never hold real data
        self._head: _Node = _Node(None, None)  # type: ignore[arg-type]
        self._tail: _Node = _Node(None, None)  # type: ignore[arg-type]
        self._head.next = self._tail
        self._tail.prev = self._head

    # ──────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            if key not in self._map:
                return None
            node = self._map[key]
            self._move_to_front(node)
            return node.value

    def put(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._map:
                node = self._map[key]
                node.value = value
                self._move_to_front(node)
            else:
                if len(self._map) == self._capacity:
                    self._evict_lru()
                node = _Node(key, value)
                self._map[key] = node
                self._insert_at_front(node)

    def delete(self, key: K) -> bool:
        with self._lock:
            if key not in self._map:
                return False
            self._remove(self._map.pop(key))
            return True

    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._map

    def __len__(self) -> int:
        with self._lock:
            return len(self._map)

    @property
    def capacity(self) -> int:
        return self._capacity

    # ──────────────────────────────────────────────────────────────
    # Internal list operations
    # ──────────────────────────────────────────────────────────────

    def _insert_at_front(self, node: _Node) -> None:
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node  # type: ignore[union-attr]
        self._head.next = node

    def _remove(self, node: _Node) -> None:
        node.prev.next = node.next   # type: ignore[union-attr]
        node.next.prev = node.prev   # type: ignore[union-attr]

    def _move_to_front(self, node: _Node) -> None:
        self._remove(node)
        self._insert_at_front(node)

    def _evict_lru(self) -> None:
        lru = self._tail.prev
        if lru is self._head:
            return
        self._remove(lru)           # type: ignore[arg-type]
        del self._map[lru.key]      # type: ignore[union-attr]
