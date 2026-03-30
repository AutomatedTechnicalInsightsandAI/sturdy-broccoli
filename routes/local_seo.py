"""Local SEO silo generator routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from models import Client, Project, ContentPage
from services.openai_service import generate_content
from services.wordpress_service import publish_content
from datetime import datetime

local_seo_bp = Blueprint('local_seo', __name__)


@local_seo_bp.route('/')
@login_required
def index():
    clients = Client.query.filter_by(user_id=current_user.id).all()
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('local_seo/silo.html', clients=clients, projects=projects)


@local_seo_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    cities = [c.strip() for c in request.form.get('cities', '').split(',') if c.strip()]
    project_id = request.form.get('project_id')
    client_id = request.form.get('client_id')
    service = request.form.get('service', '').strip()
    api_key = current_app.config.get('OPENAI_API_KEY', '')

    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first() if client_id else None
    if not cities or not project_id:
        flash('Cities and project are required.', 'danger')
        return redirect(url_for('local_seo.index'))

    created = 0
    for city in cities:
        try:
            content = generate_content(
                client_name=client.name if client else service,
                business_type=client.business_type if client else '',
                niche=client.niche if client else service,
                location=city,
                target_keywords=f'{service} {city}',
                content_type='landing_page',
                tone='professional',
                api_key=api_key,
            )
            page = ContentPage(
                project_id=project_id,
                title=f'{service} in {city}',
                content=content,
                content_type='landing_page',
                status='draft',
            )
            db.session.add(page)
            created += 1
        except Exception:
            pass

    db.session.commit()
    flash(f'{created} silo page(s) generated.', 'success')
    return redirect(url_for('content.library'))


@local_seo_bp.route('/deploy-all', methods=['POST'])
@login_required
def deploy_all():
    project_id = request.form.get('project_id')
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    pages = ContentPage.query.filter_by(project_id=project_id, status='draft').all()
    deployed = 0
    for page in pages:
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
            deployed += 1
        except Exception:
            pass
    db.session.commit()
    flash(f'{deployed} page(s) deployed to WordPress.', 'success')
    return redirect(url_for('content.library'))
