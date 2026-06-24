from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.security import get_current_user_id
from ....models.job import Job
from ....schemas.generate import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    job = await _fetch_job(db, job_id, user_id)
    return JobResponse.model_validate(job)


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[JobResponse]:
    result = await db.execute(
        select(Job)
        .where(Job.user_id == uuid.UUID(user_id))
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.delete("/{job_id}")
async def cancel_job(
    job_id: uuid.UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from ....models.job import JobStatus
    job = await _fetch_job(db, job_id, user_id)
    cancellable = {JobStatus.QUEUED, JobStatus.PROCESSING}
    if job.status not in cancellable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot cancel job with status '{job.status}'",
        )
    job.status = JobStatus.CANCELLED
    job.current_step = None
    await db.commit()
    return Response(status_code=204)


async def _fetch_job(db: AsyncSession, job_id: uuid.UUID, user_id: str) -> Job:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == uuid.UUID(user_id))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job
