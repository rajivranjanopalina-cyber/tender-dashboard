import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import settings

_scheduler = BackgroundScheduler(timezone=settings.tz)
_is_running = False
_lock = threading.Lock()


def _run_scrape_job():
    global _is_running
    from backend.database import SessionLocal
    from backend.scraper.engine import run_all_portals
    with _lock:
        if _is_running:
            return
        _is_running = True
    try:
        db = SessionLocal()
        try:
            run_all_portals(db=db)
        finally:
            db.close()
    finally:
        with _lock:
            _is_running = False


def start_scheduler():
    _scheduler.add_job(_run_scrape_job, CronTrigger(hour=23, minute=59, timezone=settings.tz), id="nightly_scrape")
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown(wait=False)


def get_is_running() -> bool:
    with _lock:
        return _is_running


def get_next_run_time():
    job = _scheduler.get_job("nightly_scrape")
    return job.next_run_time if job else None


def trigger_scrape(portal_id=None):
    """Trigger a manual scrape. Returns False if already running."""
    global _is_running
    with _lock:
        if _is_running:
            return False
        _is_running = True

    def _run():
        global _is_running
        from backend.database import SessionLocal
        from backend.scraper.engine import scrape_portal, run_all_portals
        try:
            db = SessionLocal()
            try:
                if portal_id:
                    scrape_portal(portal_id=portal_id, db=db)
                else:
                    run_all_portals(db=db)
            finally:
                db.close()
        finally:
            with _lock:
                _is_running = False

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return True
