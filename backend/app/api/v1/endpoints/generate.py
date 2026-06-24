"""
Generation API endpoints.

POST /api/v1/generate/image  — queue an image generation job
POST /api/v1/generate/video  — queue a video generation job
GET  /api/v1/generate/autocomplete — Trie-based prompt autocomplete
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.security import get_current_user_id
from ....dsa import BloomFilter, LRUCache, MinHeap, RateLimiter, Trie
from ....models.job import Job, JobStatus, MediaType
from ....schemas.generate import (
    AutocompleteResponse,
    GenerateRequest,
    GenerateResponse,
)
from ....workers.tasks import generate_media_task

router = APIRouter(prefix="/generate", tags=["generation"])

# Module-level DSA singletons (shared across requests in a single worker process)
_rate_limiter = RateLimiter(capacity=10.0, refill_rate=1.0)
_result_cache: LRUCache[str, GenerateResponse] = LRUCache(capacity=512)
_bloom = BloomFilter(capacity=100_000, error_rate=0.01)
_trie = Trie()
_job_queue: MinHeap = MinHeap()


def _cache_key(user_id: str, media_type: str, req: GenerateRequest) -> str:
    dur = req.duration_seconds if media_type == "video" else ""
    return f"{user_id}:{media_type}:{req.quality_preset}:{dur}:{req.prompt.lower()}"


@router.post("/image", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_image(
    req: GenerateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenerateResponse:
    return await _enqueue_job(req, user_id, MediaType.IMAGE, db)


@router.post("/video", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_video(
    req: GenerateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenerateResponse:
    return await _enqueue_job(req, user_id, MediaType.VIDEO, db)


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    prefix: Annotated[str, Query(min_length=2, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> AutocompleteResponse:
    suggestions = _trie.get_suggestions(prefix, top_k=limit)
    return AutocompleteResponse(prefix=prefix, suggestions=suggestions)


# ──────────────────────────────────────────────────────────────────────────────


async def _enqueue_job(
    req: GenerateRequest,
    user_id: str,
    media_type: MediaType,
    db: AsyncSession,
) -> GenerateResponse:
    # Rate limiting via Token Bucket
    if not _rate_limiter.is_allowed(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded — please wait before generating more",
        )

    media_type_value = media_type.value
    cache_key = _cache_key(user_id, media_type_value, req)

    # Bloom filter + LRU cache: short-circuit duplicate requests
    if cache_key in _bloom:
        cached = _result_cache.get(cache_key)
        if cached is not None:
            return cached

    estimated = {"draft": 10, "standard": 30, "ultra": 90}.get(req.quality_preset, 30)
    if media_type == MediaType.VIDEO:
        estimated = 120

    # Persist job to DB
    job = Job(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        status=JobStatus.QUEUED,
        media_type=media_type_value,
        priority=req.priority,
        raw_prompt=req.prompt,
        quality_preset=req.quality_preset,
        style_hints=req.style_hints,
        duration_seconds=req.duration_seconds if media_type == MediaType.VIDEO else None,
    )
    db.add(job)
    await db.flush()

    # Commit BEFORE dispatching to Celery — worker reads this row immediately
    await db.commit()

    # Register prompt in Trie for autocomplete
    _trie.insert(req.prompt)

    # Push to priority queue (local ordering before Celery picks it up)
    _job_queue.push(str(job.id), priority=req.priority)

    # Dispatch to Celery
    generate_media_task.apply_async(
        args=[str(job.id)],
        priority=req.priority,
        queue="generation",
    )

    response = GenerateResponse(
        job_id=job.id,
        status=JobStatus.QUEUED,
        message="job queued successfully",
        estimated_seconds=estimated,
    )

    # Cache for dedup — populate AFTER successful job creation
    _bloom.add(cache_key)
    _result_cache.put(cache_key, response)

    return response
