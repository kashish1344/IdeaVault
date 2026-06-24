"""
Celery task — drives the local generation pipeline.

Flow:
  1. Mark job PROCESSING
  2. Run GenerationOrchestrator (Ollama + local diffusers)
  3. Serve the output file via FastAPI static endpoint
  4. Mark job COMPLETED / FAILED
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from ..agents.orchestrator import GenerationOrchestrator
from ..core.config import get_settings
from ..models.job import Job, JobStatus
from .celery_app import celery_app

# NullPool: each asyncio.run() call creates a fresh event loop. With a
# pooled engine the asyncpg connections stay bound to the previous
# (closed) loop, causing "Future attached to a different loop" errors.
# NullPool opens and closes a connection per transaction, so there are
# never stale loop references.
_worker_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
_WorkerSession = async_sessionmaker(
    bind=_worker_engine, class_=AsyncSession, expire_on_commit=False
)

logger = logging.getLogger("ideavault.worker")


class GenerationTask(Task):
    _orchestrator: GenerationOrchestrator | None = None

    @property
    def orchestrator(self) -> GenerationOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = GenerationOrchestrator()
        return self._orchestrator


@celery_app.task(
    bind=True,
    base=GenerationTask,
    name="app.workers.tasks.generate_media_task",
    max_retries=1,
    default_retry_delay=10,
)
def generate_media_task(self: GenerationTask, job_id: str) -> dict:
    return asyncio.run(_generate(self, job_id))


async def _generate(task: GenerationTask, job_id: str) -> dict:
    async with _WorkerSession() as session:
        job = await _get_job(session, job_id)
        if job is None:
            return {"error": "job not found"}

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        job.celery_task_id = task.request.id
        await session.commit()

        try:
            context = {
                "raw_prompt": job.raw_prompt,
                "media_type": job.media_type,
                "quality_preset": job.quality_preset,
                "style_hints": job.style_hints or [],
                "duration_seconds": job.duration_seconds or 4,
            }

            async def _on_step(step_names: list[str]) -> None:
                async with _WorkerSession() as step_session:
                    step_job = await _get_job(step_session, job_id)
                    if step_job is not None:
                        step_job.current_step = ",".join(step_names)
                        await step_session.commit()

            result = await task.orchestrator.run(context, on_step=_on_step)

            if not result.get("success"):
                raise RuntimeError(str(result.get("errors", "generation failed")))

            # Convert local file path to a URL the frontend can reach
            output_path = result.get("output_path", "")
            output_url = _path_to_url(output_path, job.media_type)

            job.status = JobStatus.COMPLETED
            job.current_step = None
            job.output_url = output_url
            job.enhanced_prompt = result.get("enhanced_prompt")
            job.model_id = result.get("model_id")
            job.quality_score = result.get("quality_score")
            job.pipeline_result = {"execution_order": result.get("execution_order")}
            job.completed_at = datetime.now(UTC)
            await session.commit()

            return {"status": "completed", "url": output_url}

        except Exception as exc:
            logger.exception("job %s failed: %s", job_id, exc)
            job.status = JobStatus.FAILED
            job.current_step = None
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            await session.commit()
            return {"status": "failed", "error": str(exc)}


def _path_to_url(file_path: str, media_type: str) -> str:
    """Convert a local /tmp path to a FastAPI static-file URL."""
    if not file_path:
        return ""
    name = Path(file_path).name
    folder = "videos" if media_type == "video" else "images"
    return f"/media/{folder}/{name}"


async def _get_job(session, job_id: str) -> Job | None:
    result = await session.execute(
        select(Job).where(Job.id == uuid.UUID(job_id))
    )
    return result.scalar_one_or_none()
