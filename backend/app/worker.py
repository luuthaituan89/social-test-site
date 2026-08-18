from celery import Celery

from .config import settings

celery_app = Celery("socialn", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.update(
    task_serializer="json", result_serializer="json", accept_content=["json"],
    timezone="UTC", task_track_started=True,
    beat_schedule={"purge-due-accounts-hourly": {"task": "accounts.purge_due", "schedule": 3600.0}},
)
celery_app.autodiscover_tasks(["app"])
