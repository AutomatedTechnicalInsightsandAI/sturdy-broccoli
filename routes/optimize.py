"""Virtual Optimization Layer routes."""
from __future__ import annotations

import json

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Client, OptimizationRun, Project

optimize_bp = Blueprint("optimize", __name__)


def _get_user_projects() -> list[Project]:
    return (
        Project.query.join(Client)
        .filter(Client.user_id == current_user.id)
        .order_by(Project.name)
        .all()
    )


@optimize_bp.route("/")
@login_required
def index():
    projects = _get_user_projects()
    return render_template("optimize/index.html", projects=projects)


@optimize_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    """Generate optimisation payload and injection script for a page URL."""
    data = request.get_json(silent=True) or {}
    page_url: str = (data.get("page_url") or request.form.get("page_url", "")).strip()
    project_id: int | None = data.get("project_id") or request.form.get("project_id")

    if not page_url:
        return jsonify({"error": "page_url is required"}), 400
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    project = (
        Project.query.join(Client)
        .filter(Project.id == int(project_id), Client.user_id == current_user.id)
        .first_or_404()
    )
    client = project.client

    from flask import current_app
    from services.optimization_layer import build_injection_script, generate_optimization_payload

    api_key = current_app.config.get("OPENAI_API_KEY", "")
    client_data = {
        "name": client.name,
        "business_type": client.business_type or "",
        "niche": client.niche or "",
        "location": client.location or "",
        "phone": client.phone or "",
        "website": client.website or "",
    }

    payload = generate_optimization_payload(page_url, client_data, api_key)
    script_tag = build_injection_script(payload)

    # Persist to DB
    run = OptimizationRun(
        project_id=project.id,
        page_url=page_url,
        title=payload.get("title", ""),
        meta_description=payload.get("meta_description", ""),
        schema_json=json.dumps(payload.get("schema_json", {})),
        og_tags=json.dumps(payload.get("og_tags", {})),
        script_tag=script_tag,
    )
    db.session.add(run)
    db.session.commit()

    return jsonify(
        {
            "payload": payload,
            "script_tag": script_tag,
            "char_count": len(script_tag),
            "run_id": run.id,
        }
    )


@optimize_bp.route("/history/<int:project_id>")
@login_required
def history(project_id: int):
    project = (
        Project.query.join(Client)
        .filter(Project.id == project_id, Client.user_id == current_user.id)
        .first_or_404()
    )
    runs = (
        OptimizationRun.query.filter_by(project_id=project_id)
        .order_by(OptimizationRun.created_at.desc())
        .all()
    )
    return render_template("optimize/history.html", project=project, runs=runs)
