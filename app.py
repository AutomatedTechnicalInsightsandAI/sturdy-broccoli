"""
app.py — Flask application factory for Sturdy Broccoli SEO platform.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
mail = Mail()


def create_app(config_name=None):
    app = Flask(__name__)

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    from config import config
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.projects import projects_bp
    from routes.content import content_bp
    from routes.wordpress import wordpress_bp
    from routes.audit import audit_bp
    from routes.keywords import keywords_bp
    from routes.backlinks import backlinks_bp
    from routes.onpage import onpage_bp
    from routes.calendar import calendar_bp
    from routes.local_seo import local_seo_bp
    from routes.forms import forms_bp
    from routes.gbp import gbp_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(content_bp, url_prefix='/content')
    app.register_blueprint(wordpress_bp, url_prefix='/wordpress')
    app.register_blueprint(audit_bp, url_prefix='/audit')
    app.register_blueprint(keywords_bp, url_prefix='/keywords')
    app.register_blueprint(backlinks_bp, url_prefix='/backlinks')
    app.register_blueprint(onpage_bp, url_prefix='/onpage')
    app.register_blueprint(calendar_bp, url_prefix='/calendar')
    app.register_blueprint(local_seo_bp, url_prefix='/local-seo')
    app.register_blueprint(forms_bp, url_prefix='/forms')
    app.register_blueprint(gbp_bp, url_prefix='/gbp')

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=8080)
