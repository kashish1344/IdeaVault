from celery import Celery

from ..core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ideavault",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,                # fair dispatch for GPU tasks
    task_soft_time_limit=settings.job_timeout_seconds,
    task_time_limit=settings.job_timeout_seconds + 60,
    broker_connection_retry_on_startup=True,     # suppress Celery 6.0 deprecation warning
    task_routes={
        "app.workers.tasks.generate_media_task": {"queue": "generation"},
    },
)
