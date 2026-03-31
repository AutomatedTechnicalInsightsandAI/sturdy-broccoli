"""
app.py — Self-managing Flask application factory.

Features:
- Dynamic blueprint discovery (scans routes/ folder automatically)
- Pre-flight health check (DB, API keys, uploads/)
- Persistent scheduler (resumes pending queue on startup)
- Heartbeat monitor (logs system pulse every 15 minutes)
- Graceful shutdown
"""
from __future__ import annotations

import atexit
import importlib
import logging
import os
import pkgutil
from datetime import datetime

from flask import Blueprint, Flask

logger = logging.getLogger(__name__)


def _register_blueprints(app: Flask) -> None:
    """Auto-discover and register all blueprints in the routes/ package."""
    import routes

    # Explicit prefix map for modules whose prefix differs from /<module_name>
    _PREFIX_OVERRIDES: dict[str, str] = {
        "auth": "/auth",
        "dashboard": "/",
        "entity_analysis": "/entity",
        "batch_deploy": "/batch",
    }

    for _finder, name, _ispkg in pkgutil.iter_modules(routes.__path__):
        try:
            module = importlib.import_module(f"routes.{name}")
        except Exception as exc:
            logger.warning("Failed to import routes.%s: %s", name, exc)
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, Blueprint):
                continue
            if attr.name in app.blueprints:
                continue  # already registered

            prefix = _PREFIX_OVERRIDES.get(name, f"/{name.replace('_', '-')}")
            try:
                app.register_blueprint(attr, url_prefix=prefix)
                logger.debug("Registered blueprint '%s' at %s", attr.name, prefix)
            except Exception as exc:
                logger.warning(
                    "Failed to register blueprint '%s' at %s: %s", attr.name, prefix, exc
                )


def _run_preflight_check(app: Flask) -> dict:
    """Validate system dependencies before serving requests."""
    from extensions import db
    from models import SystemHealth

    results: dict = {}

    # 1. Database connectivity
    try:
        db.session.execute(db.text("SELECT 1"))
        results["db"] = "ok"
    except Exception as exc:
        results["db"] = f"error: {exc}"

    # 2. OpenAI API key present
    results["openai_key"] = "ok" if app.config.get("OPENAI_API_KEY") else "missing"

    # 3. uploads/ directory writable
    uploads_path = os.path.join(app.root_path, "uploads")
    os.makedirs(uploads_path, exist_ok=True)
    results["uploads_writable"] = os.access(uploads_path, os.W_OK)

    # 4. Update SystemHealth record
    try:
        health = SystemHealth.query.first()
        if not health:
            health = SystemHealth()
            db.session.add(health)
        health.db_status = results["db"]
        health.uploads_writable = bool(results["uploads_writable"])
        health.last_health_check = datetime.utcnow()
        db.session.commit()
    except Exception as exc:
        logger.warning("SystemHealth update failed: %s", exc)

    for key, val in results.items():
        status = "✅" if val in ("ok", True) else "⚠️"
        app.logger.info("Pre-flight [%s]: %s %s", key, status, val)

    return results


def _heartbeat(app: Flask) -> None:
    """Scheduled every 15 minutes. Updates SystemHealth and checks scheduler."""
    with app.app_context():
        try:
            from extensions import db
            from models import SystemHealth
            from services.scheduler import get_scheduler

            health = SystemHealth.query.first()
            if health:
                health.last_health_check = datetime.utcnow()
                scheduler = get_scheduler()
                health.scheduler_alive = scheduler.running
                db.session.commit()
        except Exception as exc:
            logger.warning("Heartbeat failed: %s", exc)


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    from config import config as _config
    app.config.from_object(_config[config_name])

    from extensions import db, login_manager, bcrypt, migrate, mail

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    import models  # noqa: F401 — registers all models with SQLAlchemy

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(models.User, int(user_id))

    with app.app_context():
        db.create_all()
        _run_preflight_check(app)

    _register_blueprints(app)

    from services.scheduler import start_scheduler, stop_scheduler

    start_scheduler(app)
    atexit.register(stop_scheduler)

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=8080)
