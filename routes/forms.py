"""Lead capture form routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import Client, Project, LeadSubmission

forms_bp = Blueprint('forms', __name__)


@forms_bp.route('/')
@login_required
def index():
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('forms/index.html', projects=projects)


@forms_bp.route('/create', methods=['POST'])
@login_required
def create():
    flash('Form builder feature coming soon.', 'info')
    return redirect(url_for('forms.index'))


@forms_bp.route('/<int:project_id>')
@login_required
def submissions(project_id):
    project = Project.query.join(Client)\
        .filter(Project.id == project_id, Client.user_id == current_user.id)\
        .first_or_404()
    leads = LeadSubmission.query.filter_by(project_id=project_id)\
        .order_by(LeadSubmission.created_at.desc()).all()
    return render_template('forms/submissions.html', project=project, leads=leads)
