"""Entity Gap Analysis routes."""
from __future__ import annotations

import json

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Client, EntityAnalysis, Project

entity_bp = Blueprint("entity", __name__)


def _get_user_projects() -> list[Project]:
    return (
        Project.query.join(Client)
        .filter(Client.user_id == current_user.id)
        .order_by(Project.name)
        .all()
    )


@entity_bp.route("/")
@login_required
def index():
    projects = _get_user_projects()
    return render_template("entity/index.html", projects=projects, analysis=None)


@entity_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """Run entity gap analysis and save results."""
    project_id = request.form.get("project_id") or (request.get_json(silent=True) or {}).get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    project = (
        Project.query.join(Client)
        .filter(Project.id == int(project_id), Client.user_id == current_user.id)
        .first_or_404()
    )
    client = project.client

    niche = (request.form.get("niche") or client.niche or "").strip()
    location = (request.form.get("location") or client.location or "").strip()

    from flask import current_app
    from services.openai_service import generate_entity_strategy_summary, perform_entity_gap_analysis

    api_key = current_app.config.get("OPENAI_API_KEY", "")
    entities = perform_entity_gap_analysis(niche, location, api_key)
    summary = generate_entity_strategy_summary(entities, niche, location, api_key)

    record = EntityAnalysis(
        project_id=project.id,
        niche=niche,
        location=location,
        entities_json=json.dumps(entities),
        excluded_entities=json.dumps([]),
        strategy_summary=summary,
    )
    db.session.add(record)
    db.session.commit()

    projects = _get_user_projects()
    return render_template(
        "entity/index.html",
        projects=projects,
        analysis=record,
        entities=entities,
        summary=summary,
        project=project,
    )


@entity_bp.route("/apply/<int:analysis_id>", methods=["POST"])
@login_required
def apply(analysis_id: int):
    """Update excluded entities for an analysis record."""
    record = EntityAnalysis.query.filter_by(id=analysis_id).first_or_404()
    project = (
        Project.query.join(Client)
        .filter(Project.id == record.project_id, Client.user_id == current_user.id)
        .first_or_404()
    )

    data = request.get_json(silent=True) or {}
    excluded = data.get("excluded_entities", [])
    record.excluded_entities = json.dumps(excluded)
    db.session.commit()
    return jsonify({"status": "ok", "excluded_count": len(excluded)})


@entity_bp.route("/history/<int:project_id>")
@login_required
def history(project_id: int):
    project = (
        Project.query.join(Client)
        .filter(Project.id == project_id, Client.user_id == current_user.id)
        .first_or_404()
    )
    analyses = (
        EntityAnalysis.query.filter_by(project_id=project_id)
        .order_by(EntityAnalysis.created_at.desc())
        .all()
    )
    return render_template("entity/history.html", project=project, analyses=analyses)
