"""Projects and clients routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import Client, Project

projects_bp = Blueprint('projects', __name__)


# ── Clients ──────────────────────────────────────────────────────────────────

@projects_bp.route('/clients')
@login_required
def clients_list():
    clients = Client.query.filter_by(user_id=current_user.id)\
        .order_by(Client.created_at.desc()).all()
    return render_template('projects/clients.html', clients=clients)


@projects_bp.route('/clients/new', methods=['GET', 'POST'])
@login_required
def new_client():
    if request.method == 'POST':
        client = Client(
            user_id=current_user.id,
            name=request.form.get('name', '').strip(),
            business_type=request.form.get('business_type', '').strip(),
            niche=request.form.get('niche', '').strip(),
            location=request.form.get('location', '').strip(),
            target_keywords=request.form.get('target_keywords', '').strip(),
            phone=request.form.get('phone', '').strip(),
            website=request.form.get('website', '').strip(),
        )
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{client.name}" created.', 'success')
        return redirect(url_for('projects.clients_list'))
    return render_template('projects/new_client.html')


@projects_bp.route('/clients/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    return render_template('projects/client_detail.html', client=client)


# ── Projects ─────────────────────────────────────────────────────────────────

@projects_bp.route('/')
@login_required
def list_projects():
    clients = Client.query.filter_by(user_id=current_user.id)\
        .order_by(Client.name).all()
    return render_template('projects/list.html', clients=clients)


@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_project():
    clients = Client.query.filter_by(user_id=current_user.id).all()
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        client = Client.query.filter_by(id=client_id, user_id=current_user.id).first()
        if not client:
            flash('Invalid client selected.', 'danger')
            return render_template('projects/new.html', clients=clients)
        project = Project(
            client_id=client_id,
            name=request.form.get('name', '').strip(),
            wp_url=request.form.get('wp_url', '').strip(),
            wp_username=request.form.get('wp_username', '').strip(),
            wp_app_password=request.form.get('wp_app_password', '').strip(),
        )
        db.session.add(project)
        db.session.commit()
        flash(f'Project "{project.name}" created.', 'success')
        return redirect(url_for('projects.project_detail', project_id=project.id))
    return render_template('projects/new.html', clients=clients)


@projects_bp.route('/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    return render_template('projects/detail.html', project=project)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    clients = Client.query.filter_by(user_id=current_user.id).all()
    if request.method == 'POST':
        project.name = request.form.get('name', project.name).strip()
        project.wp_url = request.form.get('wp_url', project.wp_url).strip()
        project.wp_username = request.form.get('wp_username', project.wp_username).strip()
        project.wp_app_password = request.form.get('wp_app_password', project.wp_app_password).strip()
        db.session.commit()
        flash('Project updated.', 'success')
        return redirect(url_for('projects.project_detail', project_id=project.id))
    return render_template('projects/edit.html', project=project, clients=clients)


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted.', 'info')
    return redirect(url_for('projects.list_projects'))
