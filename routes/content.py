"""Content generation and management routes."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Client, Project, ContentPage
from services.openai_service import generate_content, generate_schema_markup
from services.wordpress_service import publish_content

content_bp = Blueprint('content', __name__)


@content_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    clients = Client.query.filter_by(user_id=current_user.id).all()
    generated = None
    if request.method == 'POST':
        action = request.form.get('action', 'generate')
        client_id = request.form.get('client_id')
        client = Client.query.filter_by(id=client_id, user_id=current_user.id).first() if client_id else None

        client_name = client.name if client else request.form.get('client_name', '').strip()
        business_type = client.business_type if client else request.form.get('business_type', '').strip()
        niche = client.niche if client else request.form.get('niche', '').strip()
        location = client.location if client else request.form.get('location', '').strip()
        target_keywords = client.target_keywords if client else request.form.get('target_keywords', '').strip()
        content_type = request.form.get('content_type', 'article')
        tone = request.form.get('tone', 'professional')

        api_key = current_app.config.get('OPENAI_API_KEY', '')
        if not api_key:
            flash('OpenAI API key not configured.', 'warning')
            return render_template('content/generate.html', clients=clients)

        try:
            generated = generate_content(
                client_name=client_name,
                business_type=business_type,
                niche=niche,
                location=location,
                target_keywords=target_keywords,
                content_type=content_type,
                tone=tone,
                api_key=api_key,
            )
        except Exception as exc:
            flash(f'Content generation failed: {exc}', 'danger')
            return render_template('content/generate.html', clients=clients, generated=None)

        if action == 'save' and generated:
            project_id = request.form.get('project_id')
            title = request.form.get('title', f'{content_type.replace("_", " ").title()} — {client_name}').strip()
            page = ContentPage(
                project_id=project_id,
                title=title,
                content=generated,
                content_type=content_type,
                status='draft',
                meta_description=request.form.get('meta_description', '').strip(),
            )
            db.session.add(page)
            db.session.commit()
            flash('Content saved to library.', 'success')
            return redirect(url_for('content.view_content', content_id=page.id))

    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('content/generate.html', clients=clients, projects=projects, generated=generated)


@content_bp.route('/library')
@login_required
def library():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    pages = ContentPage.query.filter(
        ContentPage.project_id.in_(project_ids)
    ).order_by(ContentPage.created_at.desc()).all() if project_ids else []
    return render_template('content/library.html', pages=pages)


@content_bp.route('/<int:content_id>')
@login_required
def view_content(content_id):
    page = _get_content_or_404(content_id)
    return render_template('content/detail.html', page=page)


@content_bp.route('/<int:content_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_content(content_id):
    page = _get_content_or_404(content_id)
    if request.method == 'POST':
        page.title = request.form.get('title', page.title).strip()
        page.content = request.form.get('content', page.content)
        page.meta_description = request.form.get('meta_description', page.meta_description).strip()
        page.status = request.form.get('status', page.status)
        page.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Content updated.', 'success')
        return redirect(url_for('content.view_content', content_id=page.id))
    return render_template('content/edit.html', page=page)


@content_bp.route('/<int:content_id>/deploy', methods=['POST'])
@login_required
def deploy_content(content_id):
    page = _get_content_or_404(content_id)
    project = page.project
    if not project.wp_url:
        flash('No WordPress connection configured for this project.', 'danger')
        return redirect(url_for('content.view_content', content_id=page.id))
    try:
        result = publish_content(
            wp_url=project.wp_url,
            username=project.wp_username,
            app_password=project.wp_app_password,
            title=page.title,
            content=page.content,
            content_type='post',
            status='draft',
        )
        page.wp_post_id = result.get('post_id')
        page.wp_post_url = result.get('post_url')
        page.status = 'published'
        page.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Deployed to WordPress: {page.wp_post_url}', 'success')
    except Exception as exc:
        flash(f'Deploy failed: {exc}', 'danger')
    return redirect(url_for('content.view_content', content_id=page.id))


@content_bp.route('/<int:content_id>/delete', methods=['POST'])
@login_required
def delete_content(content_id):
    page = _get_content_or_404(content_id)
    db.session.delete(page)
    db.session.commit()
    flash('Content deleted.', 'info')
    return redirect(url_for('content.library'))


def _get_content_or_404(content_id):
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    return ContentPage.query.filter(
        ContentPage.id == content_id,
        ContentPage.project_id.in_(project_ids)
    ).first_or_404()
