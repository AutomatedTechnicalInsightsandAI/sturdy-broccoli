"""Keyword research routes."""
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Client, Project, KeywordSet
from services.serpapi_service import keyword_research

keywords_bp = Blueprint('keywords', __name__)


@keywords_bp.route('/')
@login_required
def research():
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('keywords/research.html', projects=projects, results=None)


@keywords_bp.route('/research', methods=['POST'])
@login_required
def run_research():
    seed = request.form.get('seed_keyword', '').strip()
    location = request.form.get('location', '').strip()
    project_id = request.form.get('project_id')
    api_key = current_app.config.get('SERPAPI_KEY', '')
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    if not seed:
        flash('Seed keyword is required.', 'danger')
        return render_template('keywords/research.html', projects=projects, results=None)
    try:
        results = keyword_research(seed, location, api_key)
        kw_set = KeywordSet(
            project_id=project_id,
            seed_keyword=seed,
            location=location,
            keywords_data=json.dumps(results),
        )
        db.session.add(kw_set)
        db.session.commit()
        return render_template('keywords/research.html', projects=projects, results=results, saved=True)
    except Exception as exc:
        flash(f'Keyword research failed: {exc}', 'danger')
        return render_template('keywords/research.html', projects=projects, results=None)


@keywords_bp.route('/saved')
@login_required
def saved():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    keyword_sets = KeywordSet.query.filter(
        KeywordSet.project_id.in_(project_ids)
    ).order_by(KeywordSet.created_at.desc()).all() if project_ids else []
    return render_template('keywords/saved.html', keyword_sets=keyword_sets)
