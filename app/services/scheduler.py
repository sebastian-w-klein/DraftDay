from apscheduler.schedulers.background import BackgroundScheduler

from app.ingestion.runner import run_all_active_ingestion_sync

def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_all_active_ingestion_sync,
        trigger="interval",
        minutes=30,
        id="automated-source-ingestion",
        replace_existing=True,
        max_instances=1,
    )
    return scheduler
