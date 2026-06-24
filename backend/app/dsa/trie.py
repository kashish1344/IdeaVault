"""
Trie (prefix tree) for prompt autocomplete.

Each node stores:
  - children: char → TrieNode
  - is_end: marks a complete prompt
  - frequency: how often this prompt was used (for ranked suggestions)

get_suggestions returns the top-k completions for a prefix,
ranked by frequency using a max-heap.
"""

from __future__ import annotations

import heapq
import threading
from typing import Optional


class TrieNode:
    __slots__ = ("children", "is_end", "frequency", "prompt")

    def __init__(self) -> None:
        self.children: dict[str, "TrieNode"] = {}
        self.is_end: bool = False
        self.frequency: int = 0
        self.prompt: str = ""   # full prompt stored at terminal node


class Trie:
    """
    Case-insensitive prefix trie for prompt autocomplete.
    Thread-safe via a read-write pattern (RLock).
    """

    def __init__(self) -> None:
        self._root = TrieNode()
        self._lock = threading.RLock()

    # ──────────────────────────────────────────────────────────────
    # Insert / increment
    # ──────────────────────────────────────────────────────────────

    def insert(self, prompt: str, frequency: int = 1) -> None:
        prompt = prompt.strip()
        if not prompt:
            return
        key = prompt.lower()
        with self._lock:
            node = self._root
            for ch in key:
                if ch not in node.children:
                    node.children[ch] = TrieNode()
                node = node.children[ch]
            node.is_end = True
            node.frequency += frequency
            node.prompt = prompt   # preserve original casing

    def increment(self, prompt: str) -> None:
        """Increase frequency for an existing prompt (called on user selection)."""
        key = prompt.strip().lower()
        with self._lock:
            node = self._traverse(key)
            if node and node.is_end:
                node.frequency += 1

    # ──────────────────────────────────────────────────────────────
    # Search / autocomplete
    # ──────────────────────────────────────────────────────────────

    def search(self, prompt: str) -> bool:
        key = prompt.strip().lower()
        with self._lock:
            node = self._traverse(key)
            return node is not None and node.is_end

    def starts_with(self, prefix: str) -> bool:
        key = prefix.strip().lower()
        with self._lock:
            return self._traverse(key) is not None

    def get_suggestions(self, prefix: str, top_k: int = 10) -> list[str]:
        """
        Return up to top_k prompt completions for prefix,
        ranked by descending frequency.
        O(P + N) where P = prefix length, N = subtree size.
        """
        key = prefix.strip().lower()
        with self._lock:
            start = self._traverse(key)
            if start is None:
                return []

            # Collect all terminals in the subtree via DFS
            # Use a max-heap (negate frequency for Python's min-heap)
            candidates: list[tuple[int, str]] = []
            self._dfs(start, candidates)

            # Return top-k by frequency
            top = heapq.nlargest(top_k, candidates, key=lambda x: x[0])
            return [prompt for _, prompt in top]

    # ──────────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────────

    def _traverse(self, key: str) -> Optional[TrieNode]:
        node = self._root
        for ch in key:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def _dfs(self, node: TrieNode, results: list[tuple[int, str]]) -> None:
        if node.is_end:
            results.append((node.frequency, node.prompt))
        for child in node.children.values():
            self._dfs(child, results)

    def delete(self, prompt: str) -> bool:
        key = prompt.strip().lower()
        with self._lock:
            return self._delete_rec(self._root, key, 0)

    def _delete_rec(self, node: TrieNode, key: str, depth: int) -> bool:
        if depth == len(key):
            if not node.is_end:
                return False
            node.is_end = False
            return len(node.children) == 0

        ch = key[depth]
        if ch not in node.children:
            return False
        should_delete_child = self._delete_rec(node.children[ch], key, depth + 1)
        if should_delete_child:
            del node.children[ch]
            return not node.is_end and len(node.children) == 0
        return False
