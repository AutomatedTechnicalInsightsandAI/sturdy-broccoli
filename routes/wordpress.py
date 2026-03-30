"""WordPress connection management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import Client, Project
from services.wordpress_service import test_connection, publish_content
from models import ContentPage
from datetime import datetime

wordpress_bp = Blueprint('wordpress', __name__)


@wordpress_bp.route('/')
@login_required
def index():
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('wordpress/index.html', projects=projects)


@wordpress_bp.route('/connect', methods=['POST'])
@login_required
def connect():
    project_id = request.form.get('project_id')
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    project.wp_url = request.form.get('wp_url', '').strip()
    project.wp_username = request.form.get('wp_username', '').strip()
    project.wp_app_password = request.form.get('wp_app_password', '').strip()
    db.session.commit()
    flash('WordPress connection saved.', 'success')
    return redirect(url_for('wordpress.index'))


@wordpress_bp.route('/test/<int:project_id>', methods=['POST'])
@login_required
def test_wp(project_id):
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    ok = test_connection(project.wp_url, project.wp_username, project.wp_app_password)
    if ok:
        flash('WordPress connection successful!', 'success')
    else:
        flash('WordPress connection failed. Check credentials.', 'danger')
    return redirect(url_for('wordpress.index'))


@wordpress_bp.route('/deploy/<int:content_id>', methods=['POST'])
@login_required
def deploy(content_id):
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    page = ContentPage.query.filter(
        ContentPage.id == content_id,
        ContentPage.project_id.in_(project_ids)
    ).first_or_404()
    project = page.project
    try:
        result = publish_content(
            wp_url=project.wp_url,
            username=project.wp_username,
            app_password=project.wp_app_password,
            title=page.title,
            content=page.content,
        )
        page.wp_post_id = result.get('post_id')
        page.wp_post_url = result.get('post_url')
        page.status = 'published'
        page.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Content deployed to WordPress.', 'success')
    except Exception as exc:
        flash(f'Deploy failed: {exc}', 'danger')
    return redirect(url_for('content.view_content', content_id=content_id))
