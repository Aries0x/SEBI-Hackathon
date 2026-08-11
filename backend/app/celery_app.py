"""
MarketTrust AI — Celery Application.

Configures Celery with Redis broker for async task processing
across all media pipelines.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "markettrust",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task settings
    task_track_started=True,
    task_time_limit=600,       # 10 min hard timeout
    task_soft_time_limit=540,  # 9 min soft timeout
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    # Result settings
    result_expires=3600,  # 1 hour
)

# Auto-discover tasks from all pipeline modules
celery_app.autodiscover_tasks([
    "app.video",
    "app.image",
    "app.email",
    "app.website",
])
