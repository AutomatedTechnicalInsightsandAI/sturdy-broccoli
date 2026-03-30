"""Backlink tracker routes."""
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Client, Project, BacklinkRecord

backlinks_bp = Blueprint('backlinks', __name__)


@backlinks_bp.route('/')
@login_required
def tracker():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    records = BacklinkRecord.query.filter(
        BacklinkRecord.project_id.in_(project_ids)
    ).order_by(BacklinkRecord.created_at.desc()).all() if project_ids else []
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('backlinks/tracker.html', records=records, projects=projects)


@backlinks_bp.route('/check', methods=['POST'])
@login_required
def check():
    domain = request.form.get('domain', '').strip()
    project_id = request.form.get('project_id')
    if not domain:
        flash('Domain is required.', 'danger')
        return redirect(url_for('backlinks.tracker'))
    record = BacklinkRecord(
        project_id=project_id,
        domain=domain,
        backlinks_data=json.dumps([]),
        new_count=0,
        lost_count=0,
    )
    db.session.add(record)
    db.session.commit()
    flash(f'Backlink check initiated for {domain}.', 'info')
    return redirect(url_for('backlinks.tracker'))
