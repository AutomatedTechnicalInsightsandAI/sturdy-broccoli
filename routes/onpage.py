"""On-page optimizer routes."""
from __future__ import annotations

import json

from flask import Blueprint, jsonify, redirect, render_template, url_for, flash
from flask_login import current_user, login_required

from extensions import db
from models import Client, ContentPage, EntityAnalysis, Project

onpage_bp = Blueprint("onpage", __name__)


def _user_project_ids() -> list[int]:
    return [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]


@onpage_bp.route("/")
@login_required
def index():
    project_ids = _user_project_ids()
    pages = (
        ContentPage.query.filter(ContentPage.project_id.in_(project_ids))
        .order_by(ContentPage.created_at.desc())
        .all()
    ) if project_ids else []
    return render_template("onpage/index.html", pages=pages)


@onpage_bp.route("/analyze/<int:content_id>", methods=["POST"])
@login_required
def analyze(content_id: int):
    project_ids = _user_project_ids()
    page = ContentPage.query.filter(
        ContentPage.id == content_id,
        ContentPage.project_id.in_(project_ids),
    ).first_or_404()

    # Resolve target entities from the latest EntityAnalysis for this project
    target_entities: list[str] = []
    latest_analysis = (
        EntityAnalysis.query.filter_by(project_id=page.project_id)
        .order_by(EntityAnalysis.created_at.desc())
        .first()
    )
    if latest_analysis and latest_analysis.entities_json:
        raw = json.loads(latest_analysis.entities_json)
        excluded = json.loads(latest_analysis.excluded_entities or "[]")
        target_entities = [
            e["entity"] for e in raw if e.get("entity") not in excluded
        ]

    from src.quality_scorer import QualityScorer

    scorer = QualityScorer()
    result = scorer.score(
        page.content or "",
        page_data={
            "primary_keyword": page.title,
            "target_entities": target_entities,
        },
    )

    page.quality_score = result.overall
    page.score_breakdown = json.dumps(result.as_dict())
    db.session.commit()

    return jsonify(result.as_dict())


@onpage_bp.route("/score/<int:content_id>")
@login_required
def score(content_id: int):
    """Return stored score_breakdown JSON for a content page."""
    project_ids = _user_project_ids()
    page = ContentPage.query.filter(
        ContentPage.id == content_id,
        ContentPage.project_id.in_(project_ids),
    ).first_or_404()

    if not page.score_breakdown:
        return jsonify({"error": "No score data available. Run /analyze first."}), 404

    return jsonify(json.loads(page.score_breakdown))
