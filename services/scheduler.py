"""APScheduler integration for background jobs."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler(app):
    """Start the background scheduler with the Flask app context."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
    return scheduler


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
