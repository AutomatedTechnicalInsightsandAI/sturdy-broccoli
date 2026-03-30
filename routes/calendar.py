"""Content calendar routes."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import Client, Project, ContentPage, ContentSchedule

calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/')
@login_required
def view():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    schedules = ContentSchedule.query.filter(
        ContentSchedule.project_id.in_(project_ids)
    ).order_by(ContentSchedule.scheduled_at).all() if project_ids else []
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    pages = ContentPage.query.filter(
        ContentPage.project_id.in_(project_ids)
    ).all() if project_ids else []
    return render_template('calendar/view.html', schedules=schedules, projects=projects, pages=pages)


@calendar_bp.route('/schedule', methods=['POST'])
@login_required
def schedule():
    content_page_id = request.form.get('content_page_id')
    project_id = request.form.get('project_id')
    scheduled_at_str = request.form.get('scheduled_at', '')
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
    except ValueError:
        flash('Invalid date/time format.', 'danger')
        return redirect(url_for('calendar.view'))
    entry = ContentSchedule(
        project_id=project_id,
        content_page_id=content_page_id,
        scheduled_at=scheduled_at,
        status='scheduled',
    )
    db.session.add(entry)
    db.session.commit()
    flash('Content scheduled.', 'success')
    return redirect(url_for('calendar.view'))


@calendar_bp.route('/schedule/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    entry = ContentSchedule.query.filter(
        ContentSchedule.id == schedule_id,
        ContentSchedule.project_id.in_(project_ids)
    ).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash('Schedule entry removed.', 'info')
    return redirect(url_for('calendar.view'))
