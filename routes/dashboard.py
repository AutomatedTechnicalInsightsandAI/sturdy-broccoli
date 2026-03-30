"""Dashboard routes."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db
from models import Client, Project, ContentPage

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    total_clients = Client.query.filter_by(user_id=current_user.id).count()
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    total_projects = len(project_ids)
    total_content = ContentPage.query.filter(
        ContentPage.project_id.in_(project_ids)
    ).count() if project_ids else 0
    pages_deployed = ContentPage.query.filter(
        ContentPage.project_id.in_(project_ids),
        ContentPage.status == 'published'
    ).count() if project_ids else 0

    recent_content = ContentPage.query.filter(
        ContentPage.project_id.in_(project_ids)
    ).order_by(ContentPage.created_at.desc()).limit(10).all() if project_ids else []

    recent_clients = Client.query.filter_by(user_id=current_user.id)\
        .order_by(Client.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard/index.html',
        total_clients=total_clients,
        total_projects=total_projects,
        total_content=total_content,
        pages_deployed=pages_deployed,
        recent_content=recent_content,
        recent_clients=recent_clients,
    )
