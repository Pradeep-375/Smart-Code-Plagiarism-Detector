"""Background execution of analysis jobs (Celery in production, BackgroundTasks for local dev)."""
from ..core.config import get_settings
from ..database import SessionLocal
from ..services.analysis_service import run_job


def run_analysis_sync(job_id: int) -> None:
    """Uses its own DB session; safe to call from BackgroundTasks or a Celery worker."""
    db = SessionLocal()
    try:
        run_job(db, job_id)
    finally:
        db.close()


run_analysis_task = None
if get_settings().use_celery:
    from .celery_app import celery_app

    @celery_app.task(name="scpds.run_analysis", max_retries=0)
    def run_analysis_task(job_id: int):  # noqa: F811
        run_analysis_sync(job_id)


def dispatch_analysis(job_id: int, background_tasks=None) -> None:
    """Queue a job: Celery when USE_CELERY=true, otherwise FastAPI BackgroundTasks."""
    if run_analysis_task is not None:
        run_analysis_task.delay(job_id)
    elif background_tasks is not None:
        background_tasks.add_task(run_analysis_sync, job_id)
    else:
        run_analysis_sync(job_id)
