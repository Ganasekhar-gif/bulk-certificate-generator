import sys

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "certificate_generator",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_conf = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "task_time_limit": 30 * 60,
    "task_soft_time_limit": 25 * 60,
}

# Celery's default prefork pool uses semaphores that often fail on Windows.
if sys.platform == "win32":
    celery_conf["worker_pool"] = "solo"

celery_app.conf.update(celery_conf)
