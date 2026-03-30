"""SEO audit routes."""
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from models import Client, Project, SeoAudit
from services.serpapi_service import site_audit

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/')
@login_required
def dashboard():
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    audits = SeoAudit.query.filter(
        SeoAudit.project_id.in_(project_ids)
    ).order_by(SeoAudit.created_at.desc()).all() if project_ids else []
    projects = Project.query.join(Client)\
        .filter(Client.user_id == current_user.id).all()
    return render_template('audit/dashboard.html', audits=audits, projects=projects)


@audit_bp.route('/run', methods=['POST'])
@login_required
def run_audit():
    domain = request.form.get('domain', '').strip()
    project_id = request.form.get('project_id')
    api_key = current_app.config.get('SERPAPI_KEY', '')
    if not domain:
        flash('Domain is required.', 'danger')
        return redirect(url_for('audit.dashboard'))
    try:
        issues = site_audit(domain, api_key)
        score = max(0.0, 100.0 - len(issues) * 5)
        audit = SeoAudit(
            project_id=project_id,
            domain=domain,
            issues=json.dumps(issues),
            audit_score=score,
        )
        db.session.add(audit)
        db.session.commit()
        flash(f'Audit complete for {domain}. Score: {score:.0f}/100', 'success')
        return redirect(url_for('audit.audit_detail', audit_id=audit.id))
    except Exception as exc:
        flash(f'Audit failed: {exc}', 'danger')
        return redirect(url_for('audit.dashboard'))


@audit_bp.route('/<int:audit_id>')
@login_required
def audit_detail(audit_id):
    project_ids = [
        p.id for p in Project.query.join(Client)
        .filter(Client.user_id == current_user.id).all()
    ]
    audit = SeoAudit.query.filter(
        SeoAudit.id == audit_id,
        SeoAudit.project_id.in_(project_ids)
    ).first_or_404()
    issues = json.loads(audit.issues) if audit.issues else []
    return render_template('audit/detail.html', audit=audit, issues=issues)
