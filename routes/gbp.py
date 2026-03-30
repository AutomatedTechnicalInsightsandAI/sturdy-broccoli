"""Google Business Profile post automation routes."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import Client, Project, GbpPost

gbp_bp = Blueprint('gbp', __name__)


@gbp_bp.route('/')
@login_required
def index():
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    project_ids = [p.id for p in projects]
    posts = GbpPost.query.filter(
        GbpPost.project_id.in_(project_ids)
    ).order_by(GbpPost.created_at.desc()).limit(20).all() if project_ids else []
    return render_template('gbp/index.html', projects=projects, posts=posts)


@gbp_bp.route('/schedule', methods=['POST'])
@login_required
def schedule():
    project_id = request.form.get('project_id')
    content_text = request.form.get('content_text', '').strip()
    cta = request.form.get('cta', '').strip()
    image_url = request.form.get('image_url', '').strip()
    scheduled_at_str = request.form.get('scheduled_at', '')
    if not content_text:
        flash('Post content is required.', 'danger')
        return redirect(url_for('gbp.index'))
    scheduled_at = None
    if scheduled_at_str:
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('gbp.index'))
    post = GbpPost(
        project_id=project_id,
        content_text=content_text,
        cta=cta,
        image_url=image_url,
        scheduled_at=scheduled_at,
        status='pending',
    )
    db.session.add(post)
    db.session.commit()
    flash('GBP post scheduled.', 'success')
    return redirect(url_for('gbp.history'))


@gbp_bp.route('/history')
@login_required
def history():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    posts = GbpPost.query.filter(
        GbpPost.project_id.in_(project_ids)
    ).order_by(GbpPost.created_at.desc()).all() if project_ids else []
    return render_template('gbp/history.html', posts=posts)
