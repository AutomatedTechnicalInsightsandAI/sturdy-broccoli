"""
Human-Mimicry Scheduler — variable intervals, timezone-aware, queue-persistent.

Features:
- Variable 18-30 hour intervals between posts (not fixed 24h)
- Dead hours blackout: no posts between 2 AM and 6 AM local time
- Peak hours boost: 9-11 AM and 6-8 PM get +20% selection probability
- Minimum 45-minute gap between posts
- ±2-28 minute random jitter on each slot
- Reboot-proof: resumes pending queue from DB on startup
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timezone resolution map (common US cities → pytz timezone strings)
# ---------------------------------------------------------------------------

_TZ_MAP: dict[str, str] = {
    "sarasota": "America/New_York",
    "tampa": "America/New_York",
    "miami": "America/New_York",
    "orlando": "America/New_York",
    "jacksonville": "America/New_York",
    "new york": "America/New_York",
    "boston": "America/New_York",
    "philadelphia": "America/New_York",
    "atlanta": "America/New_York",
    "charlotte": "America/New_York",
    "detroit": "America/Detroit",
    "chicago": "America/Chicago",
    "houston": "America/Chicago",
    "dallas": "America/Chicago",
    "austin": "America/Chicago",
    "san antonio": "America/Chicago",
    "minneapolis": "America/Chicago",
    "kansas city": "America/Chicago",
    "denver": "America/Denver",
    "phoenix": "America/Phoenix",
    "salt lake city": "America/Denver",
    "albuquerque": "America/Denver",
    "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "portland": "America/Los_Angeles",
    "san diego": "America/Los_Angeles",
    "las vegas": "America/Los_Angeles",
    "sacramento": "America/Los_Angeles",
    "honolulu": "Pacific/Honolulu",
    "anchorage": "America/Anchorage",
}

_DEFAULT_TZ = "America/New_York"

# Dead hours: no posting between 2 AM and 6 AM local
_DEAD_HOUR_START = 2
_DEAD_HOUR_END = 6

# Peak windows (hour ranges, inclusive start exclusive end)
_PEAK_WINDOWS = [(9, 11), (18, 20)]

# ---------------------------------------------------------------------------
# APScheduler singleton
# ---------------------------------------------------------------------------

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler(app: Any) -> BackgroundScheduler:
    """Start the background scheduler, register heartbeat, and resume queue."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()

    # Register 15-minute heartbeat (best-effort — don't crash startup)
    try:
        from app import _heartbeat  # imported lazily to avoid circular import
        scheduler.add_job(
            func=_heartbeat,
            args=[app],
            trigger=IntervalTrigger(minutes=15),
            id="system_heartbeat",
            replace_existing=True,
        )
    except Exception:
        pass

    resume_pending_queue(app)
    return scheduler


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Human-mimicry schedule calculation
# ---------------------------------------------------------------------------

def _resolve_timezone(project_location: str) -> pytz.BaseTzInfo:
    """Map a location string to a pytz timezone."""
    location_lower = project_location.lower()
    for city, tz_str in _TZ_MAP.items():
        if city in location_lower:
            return pytz.timezone(tz_str)
    return pytz.timezone(_DEFAULT_TZ)


def _is_dead_hour(dt_local: datetime) -> bool:
    return _DEAD_HOUR_START <= dt_local.hour < _DEAD_HOUR_END


def _is_peak_hour(dt_local: datetime) -> bool:
    return any(start <= dt_local.hour < end for start, end in _PEAK_WINDOWS)


def _advance_past_dead_hours(dt_local: datetime) -> datetime:
    if _is_dead_hour(dt_local):
        dt_local = dt_local.replace(
            hour=_DEAD_HOUR_END,
            minute=random.randint(0, 30),
            second=0,
            microsecond=0,
        )
    return dt_local


def calculate_human_schedule(
    content_ids: list[int],
    project_location: str,
    base_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Calculate a human-mimicry posting schedule for a list of content IDs.

    Parameters
    ----------
    content_ids:
        List of ContentPage IDs to schedule.
    project_location:
        Location string used for timezone resolution (e.g. "Sarasota, FL").
    base_date:
        Starting datetime (UTC). Defaults to now + 1 hour.

    Returns
    -------
    List of dicts: [{"content_page_id": int, "scheduled_at_utc": datetime}, ...]
    """
    tz = _resolve_timezone(project_location)

    if base_date is None:
        base_date = datetime.utcnow() + timedelta(hours=1)

    base_utc = pytz.utc.localize(base_date) if base_date.tzinfo is None else base_date
    current_local = base_utc.astimezone(tz)
    current_local = _advance_past_dead_hours(current_local)

    slots: list[dict[str, Any]] = []
    last_utc: datetime | None = None

    for content_id in content_ids:
        interval_hours = random.uniform(18, 30)
        if slots:
            candidate_local = current_local + timedelta(hours=interval_hours)
        else:
            candidate_local = current_local

        jitter_minutes = random.randint(2, 28) * random.choice([-1, 1])
        candidate_local = candidate_local + timedelta(minutes=jitter_minutes)
        candidate_local = _advance_past_dead_hours(candidate_local)

        # Peak-hour boost: 20% chance to snap to next peak window
        if not _is_peak_hour(candidate_local) and random.random() < 0.20:
            for start, _ in _PEAK_WINDOWS:
                peak_candidate = candidate_local.replace(
                    hour=start, minute=random.randint(0, 30), second=0, microsecond=0
                )
                if peak_candidate > candidate_local:
                    candidate_local = peak_candidate
                    break

        candidate_utc = candidate_local.astimezone(pytz.utc).replace(tzinfo=None)

        if last_utc is not None:
            gap = (candidate_utc - last_utc).total_seconds() / 60
            if gap < 45:
                candidate_utc = last_utc + timedelta(minutes=45 + random.randint(0, 15))
                candidate_local = pytz.utc.localize(candidate_utc).astimezone(tz)

        slots.append({
            "content_page_id": content_id,
            "scheduled_at_utc": candidate_utc,
        })
        last_utc = candidate_utc
        current_local = candidate_local

    return slots


# ---------------------------------------------------------------------------
# Queue validation
# ---------------------------------------------------------------------------

def validate_queue(
    project_id: int,
    proposed_schedule: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Check proposed schedule slots against existing DB schedules for conflicts.

    Returns {"valid": bool, "conflicts": list}.
    """
    from models import ContentSchedule

    existing = ContentSchedule.query.filter_by(
        project_id=project_id, status="scheduled"
    ).all()
    existing_times = [s.scheduled_at for s in existing]

    conflicts: list[dict[str, Any]] = []
    for slot in proposed_schedule:
        proposed_dt: datetime = slot["scheduled_at_utc"]
        for ex_dt in existing_times:
            gap_minutes = abs((proposed_dt - ex_dt).total_seconds()) / 60
            if gap_minutes < 45:
                conflicts.append({
                    "content_page_id": slot["content_page_id"],
                    "proposed_at": proposed_dt.isoformat(),
                    "conflicts_with": ex_dt.isoformat(),
                    "gap_minutes": round(gap_minutes, 1),
                })
                break

    return {"valid": len(conflicts) == 0, "conflicts": conflicts}


# ---------------------------------------------------------------------------
# Reboot-proof queue resumption
# ---------------------------------------------------------------------------

def resume_pending_queue(app: Any) -> None:
    """
    On startup, re-register APScheduler jobs for all pending ContentSchedule
    records so the queue survives server restarts.
    """
    scheduler = get_scheduler()
    with app.app_context():
        try:
            from models import ContentSchedule
            now = datetime.utcnow()
            pending = ContentSchedule.query.filter(
                ContentSchedule.status == "scheduled",
                ContentSchedule.scheduled_at > now,
            ).all()

            for record in pending:
                job_id = record.job_id or f"deploy_{record.id}"
                if scheduler.get_job(job_id):
                    continue
                scheduler.add_job(
                    func=_execute_scheduled_deploy,
                    args=[record.id, app],
                    trigger=DateTrigger(run_date=record.scheduled_at),
                    id=job_id,
                    replace_existing=True,
                )
            logger.info("Resumed %d pending schedule job(s).", len(pending))
        except Exception as exc:
            logger.warning("resume_pending_queue failed: %s", exc)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _execute_scheduled_deploy(schedule_id: int, app: Any) -> None:
    """Execute a scheduled deploy inside the app context."""
    with app.app_context():
        from extensions import db
        from models import ContentSchedule, SystemHealth
        from services import wordpress_service

        record = db.session.get(ContentSchedule, schedule_id)
        if record is None:
            logger.warning("ContentSchedule %d not found — skipping.", schedule_id)
            return

        if record.status != "scheduled":
            logger.info(
                "ContentSchedule %d already '%s' — skipping.", schedule_id, record.status
            )
            return

        try:
            content_page = record.content_page
            project = record.project
            wordpress_service.publish_content(content_page, project)
            record.status = "deployed"
            logger.info("ContentSchedule %d deployed successfully.", schedule_id)
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)
            logger.error("ContentSchedule %d failed: %s", schedule_id, exc)

        try:
            health = SystemHealth.query.first()
            if health:
                health.last_scheduler_run = datetime.utcnow()
            db.session.commit()
        except Exception as exc:
            logger.warning("Failed to update SystemHealth: %s", exc)
            db.session.rollback()
