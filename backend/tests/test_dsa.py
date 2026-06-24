"""
Unit tests for all DSA implementations.
pytest backend/tests/test_dsa.py -v
"""

import asyncio
import threading
import time

import pytest

from app.dsa import (
    BloomFilter,
    DAGPipeline,
    JobPriority,
    LRUCache,
    MinHeap,
    PipelineNode,
    RateLimiter,
    TokenBucket,
    Trie,
)


# ── MinHeap ───────────────────────────────────────────────────────────────────


class TestMinHeap:
    def test_basic_priority_ordering(self):
        heap = MinHeap()
        heap.push("low", priority=JobPriority.LOW)
        heap.push("high", priority=JobPriority.HIGH)
        heap.push("critical", priority=JobPriority.CRITICAL)
        heap.push("normal", priority=JobPriority.NORMAL)

        assert heap.pop() == "critical"
        assert heap.pop() == "high"
        assert heap.pop() == "normal"
        assert heap.pop() == "low"

    def test_fifo_within_same_priority(self):
        heap = MinHeap()
        for i in range(5):
            heap.push(f"job_{i}", priority=JobPriority.NORMAL)
        popped = [heap.pop() for _ in range(5)]
        assert popped == [f"job_{i}" for i in range(5)]

    def test_empty_pop_returns_none(self):
        assert MinHeap().pop() is None

    def test_thread_safety(self):
        heap = MinHeap()
        errors = []

        def producer():
            try:
                for i in range(100):
                    heap.push(i, priority=i % 4)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=producer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(heap) == 400


# ── LRUCache ──────────────────────────────────────────────────────────────────


class TestLRUCache:
    def test_get_put_basic(self):
        cache = LRUCache(capacity=3)
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.get("a") == 1
        assert cache.get("missing") is None

    def test_eviction_removes_lru(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")          # a is now MRU
        cache.put("c", 3)       # b should be evicted
        assert cache.get("b") is None
        assert cache.get("a") == 1

    def test_update_refreshes_position(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 99)      # refresh a
        cache.put("c", 3)       # b should be evicted, a stays
        assert cache.get("a") == 99
        assert cache.get("b") is None

    def test_capacity_one(self):
        cache = LRUCache(capacity=1)
        cache.put("x", 10)
        cache.put("y", 20)
        assert cache.get("x") is None
        assert cache.get("y") == 20

    def test_delete(self):
        cache = LRUCache(capacity=5)
        cache.put("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None
        assert cache.delete("k") is False


# ── Trie ──────────────────────────────────────────────────────────────────────


class TestTrie:
    def test_insert_and_search(self):
        trie = Trie()
        trie.insert("a beautiful sunset")
        assert trie.search("a beautiful sunset")
        assert not trie.search("a beautiful")

    def test_autocomplete_ranked_by_frequency(self):
        trie = Trie()
        trie.insert("cat on a mat", frequency=5)
        trie.insert("cat in the hat", frequency=10)
        trie.insert("cat cafe vibes", frequency=2)

        results = trie.get_suggestions("cat", top_k=3)
        assert results[0] == "cat in the hat"   # highest frequency first

    def test_starts_with(self):
        trie = Trie()
        trie.insert("dragon flying")
        assert trie.starts_with("dra")
        assert not trie.starts_with("fly")

    def test_delete(self):
        trie = Trie()
        trie.insert("ephemeral cloud")
        assert trie.search("ephemeral cloud")
        trie.delete("ephemeral cloud")
        assert not trie.search("ephemeral cloud")

    def test_increment(self):
        trie = Trie()
        trie.insert("sunset beach", frequency=1)
        trie.increment("sunset beach")
        results = trie.get_suggestions("sunset")
        # frequency is now 2 — just check it returns the prompt
        assert "sunset beach" in results


# ── TokenBucket / RateLimiter ─────────────────────────────────────────────────


class TestTokenBucket:
    def test_consume_within_capacity(self):
        bucket = TokenBucket(capacity=5, refill_rate=1)
        assert bucket.consume(3)
        assert bucket.consume(2)
        assert not bucket.consume(1)    # empty

    def test_refill_over_time(self):
        bucket = TokenBucket(capacity=2, refill_rate=10)  # 10 tokens/sec
        bucket.consume(2)
        time.sleep(0.2)   # 2 tokens refilled
        assert bucket.consume(1)

    def test_rate_limiter_per_user(self):
        rl = RateLimiter(capacity=2, refill_rate=1)
        assert rl.is_allowed("user_A")
        assert rl.is_allowed("user_A")
        assert not rl.is_allowed("user_A")
        assert rl.is_allowed("user_B")   # different user, unaffected


# ── BloomFilter ───────────────────────────────────────────────────────────────


class TestBloomFilter:
    def test_no_false_negatives(self):
        bf = BloomFilter(capacity=1000, error_rate=0.01)
        items = [f"prompt_{i}" for i in range(200)]
        for item in items:
            bf.add(item)
        for item in items:
            assert item in bf

    def test_false_positive_rate_within_bound(self):
        bf = BloomFilter(capacity=10_000, error_rate=0.05)
        for i in range(1_000):
            bf.add(f"real_{i}")

        fp = sum(1 for i in range(10_000) if f"fake_{i}" in bf)
        fp_rate = fp / 10_000
        assert fp_rate < 0.10   # generous bound for test stability

    def test_saturation_monotonic(self):
        bf = BloomFilter(capacity=100, error_rate=0.01)
        prev = bf.saturation
        for i in range(50):
            bf.add(f"item_{i}")
            assert bf.saturation >= prev
            prev = bf.saturation


# ── DAGPipeline ───────────────────────────────────────────────────────────────


class TestDAGPipeline:
    @pytest.mark.asyncio
    async def test_linear_pipeline(self):
        pipeline = DAGPipeline()
        results = []

        async def step_a(context, **_):
            results.append("a")
            return "a_output"

        async def step_b(context, step_a, **_):
            assert step_a == "a_output"
            results.append("b")
            return "b_output"

        pipeline.add_node(PipelineNode("step_a", step_a, deps=[]))
        pipeline.add_node(PipelineNode("step_b", step_b, deps=["step_a"]))

        result = await pipeline.execute({})
        assert result.success
        assert result.outputs["step_b"] == "b_output"
        assert results == ["a", "b"]

    @pytest.mark.asyncio
    async def test_parallel_independent_nodes(self):
        pipeline = DAGPipeline()
        timestamps = {}

        async def node_x(context, **_):
            await asyncio.sleep(0.05)
            timestamps["x"] = time.monotonic()
            return "x"

        async def node_y(context, **_):
            await asyncio.sleep(0.05)
            timestamps["y"] = time.monotonic()
            return "y"

        async def node_z(context, node_x, node_y, **_):
            return f"{node_x}{node_y}"

        pipeline.add_node(PipelineNode("node_x", node_x, deps=[]))
        pipeline.add_node(PipelineNode("node_y", node_y, deps=[]))
        pipeline.add_node(PipelineNode("node_z", node_z, deps=["node_x", "node_y"]))

        start = time.monotonic()
        result = await pipeline.execute({})
        elapsed = time.monotonic() - start

        assert result.success
        assert result.outputs["node_z"] == "xy"
        assert elapsed < 0.15   # parallel: ~50ms, not ~100ms

    @pytest.mark.asyncio
    async def test_cycle_detection(self):
        pipeline = DAGPipeline()

        async def dummy(context, **_):
            return None

        pipeline.add_node(PipelineNode("a", dummy, deps=["b"]))
        pipeline.add_node(PipelineNode("b", dummy, deps=["a"]))

        result = await pipeline.execute({})
        assert not result.success
        assert "dag" in result.errors

    @pytest.mark.asyncio
    async def test_node_failure_propagates(self):
        pipeline = DAGPipeline()

        async def failing(context, **_):
            raise ValueError("intentional failure")

        pipeline.add_node(PipelineNode("bad_node", failing, deps=[]))
        result = await pipeline.execute({})
        assert not result.success
        assert "bad_node" in result.errors
