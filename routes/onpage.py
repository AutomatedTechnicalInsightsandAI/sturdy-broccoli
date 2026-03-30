"""On-page optimizer routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import Client, Project, ContentPage

onpage_bp = Blueprint('onpage', __name__)


@onpage_bp.route('/')
@login_required
def index():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    pages = ContentPage.query.filter(
        ContentPage.project_id.in_(project_ids)
    ).order_by(ContentPage.created_at.desc()).all() if project_ids else []
    return render_template('onpage/index.html', pages=pages)


@onpage_bp.route('/analyze/<int:content_id>', methods=['POST'])
@login_required
def analyze(content_id):
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    page = ContentPage.query.filter(
        ContentPage.id == content_id,
        ContentPage.project_id.in_(project_ids)
    ).first_or_404()

    # Basic on-page scoring heuristic
    content = page.content or ''
    word_count = len(content.split())
    score = min(100.0, (word_count / 10))
    page.quality_score = round(score, 1)
    db.session.commit()
    flash(f'On-page score updated: {page.quality_score}/100', 'success')
    return redirect(url_for('content.view_content', content_id=page.id))
