"""Batch deploy — Human-Mimicry Scheduler routes."""
from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Client, ContentPage, ContentSchedule, Project, SystemHealth

batch_bp = Blueprint("batch", __name__)


def _get_user_projects() -> list[Project]:
    return (
        Project.query.join(Client)
        .filter(Client.user_id == current_user.id)
        .order_by(Project.name)
        .all()
    )


@batch_bp.route("/")
@login_required
def index():
    projects = _get_user_projects()
    project_ids = [p.id for p in projects]

    schedules = (
        ContentSchedule.query.filter(ContentSchedule.project_id.in_(project_ids))
        .order_by(ContentSchedule.scheduled_at.asc())
        .all()
    ) if project_ids else []

    health = SystemHealth.query.first()
    return render_template(
        "batch/index.html",
        schedules=schedules,
        projects=projects,
        health=health,
    )


@batch_bp.route("/preview")
@login_required
def preview():
    """Return a preview schedule without saving (for UI confirmation)."""
    project_id = request.args.get("project_id")
    content_ids_raw = request.args.getlist("content_ids")
    base_date_str = request.args.get("base_date")

    if not project_id or not content_ids_raw:
        return jsonify({"error": "project_id and content_ids are required"}), 400

    project = (
        Project.query.join(Client)
        .filter(Project.id == int(project_id), Client.user_id == current_user.id)
        .first_or_404()
    )

    content_ids = [int(c) for c in content_ids_raw]
    base_date = None
    if base_date_str:
        try:
            base_date = datetime.fromisoformat(base_date_str)
        except ValueError:
            pass

    from services.scheduler import calculate_human_schedule

    slots = calculate_human_schedule(
        content_ids=content_ids,
        project_location=project.client.location or "",
        base_date=base_date,
    )

    serialisable = [
        {
            "content_page_id": s["content_page_id"],
            "scheduled_at_utc": s["scheduled_at_utc"].isoformat(),
        }
        for s in slots
    ]
    return jsonify({"preview": serialisable})


@batch_bp.route("/schedule", methods=["POST"])
@login_required
def schedule():
    """Create ContentSchedule records and register APScheduler jobs."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or request.form.get("project_id")
    content_ids_raw = data.get("content_ids") or request.form.getlist("content_ids")
    base_date_str = data.get("base_date") or request.form.get("base_date")

    if not project_id or not content_ids_raw:
        return jsonify({"error": "project_id and content_ids are required"}), 400

    project = (
        Project.query.join(Client)
        .filter(Project.id == int(project_id), Client.user_id == current_user.id)
        .first_or_404()
    )

    # Validate content pages belong to this project
    content_ids = [int(c) for c in content_ids_raw]
    valid_pages = ContentPage.query.filter(
        ContentPage.id.in_(content_ids),
        ContentPage.project_id == project.id,
    ).all()
    valid_ids = [p.id for p in valid_pages]

    base_date = None
    if base_date_str:
        try:
            base_date = datetime.fromisoformat(base_date_str)
        except ValueError:
            pass

    from services.scheduler import calculate_human_schedule, get_scheduler, validate_queue

    proposed = calculate_human_schedule(
        content_ids=valid_ids,
        project_location=project.client.location or "",
        base_date=base_date,
    )

    validation = validate_queue(project.id, proposed)
    if not validation["valid"]:
        return jsonify({"error": "Schedule conflicts detected", "conflicts": validation["conflicts"]}), 409

    scheduler = get_scheduler()
    created_schedules = []

    for slot in proposed:
        job_id = f"deploy_{project.id}_{slot['content_page_id']}_{int(slot['scheduled_at_utc'].timestamp())}"
        record = ContentSchedule(
            project_id=project.id,
            content_page_id=slot["content_page_id"],
            scheduled_at=slot["scheduled_at_utc"],
            status="scheduled",
            job_id=job_id,
        )
        db.session.add(record)
        db.session.flush()  # get record.id

        from flask import current_app
        from apscheduler.triggers.date import DateTrigger
        from services.scheduler import _execute_scheduled_deploy

        scheduler.add_job(
            func=_execute_scheduled_deploy,
            args=[record.id, current_app._get_current_object()],
            trigger=DateTrigger(run_date=slot["scheduled_at_utc"]),
            id=job_id,
            replace_existing=True,
        )
        created_schedules.append({
            "content_page_id": slot["content_page_id"],
            "scheduled_at_utc": slot["scheduled_at_utc"].isoformat(),
            "job_id": job_id,
        })

    db.session.commit()
    return jsonify({"scheduled": len(created_schedules), "slots": created_schedules})


@batch_bp.route("/cancel/<int:schedule_id>", methods=["POST"])
@login_required
def cancel(schedule_id: int):
    """Cancel a scheduled job and mark record as cancelled."""
    record = ContentSchedule.query.filter_by(id=schedule_id).first_or_404()
    project = (
        Project.query.join(Client)
        .filter(Project.id == record.project_id, Client.user_id == current_user.id)
        .first_or_404()
    )

    from services.scheduler import get_scheduler

    if record.job_id:
        scheduler = get_scheduler()
        try:
            scheduler.remove_job(record.job_id)
        except Exception:
            pass

    record.status = "cancelled"
    db.session.commit()
    return jsonify({"status": "cancelled", "schedule_id": schedule_id})
