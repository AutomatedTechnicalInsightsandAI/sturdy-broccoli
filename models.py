"""SQLAlchemy models for the Sturdy Broccoli SEO platform."""
from datetime import datetime
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    clients = db.relationship('Client', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    business_type = db.Column(db.String(100))
    niche = db.Column(db.String(100))
    location = db.Column(db.String(200))
    target_keywords = db.Column(db.Text)
    phone = db.Column(db.String(50))
    website = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship('Project', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.name}>'


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    wp_url = db.Column(db.String(255))
    wp_username = db.Column(db.String(100))
    wp_app_password = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    content_pages = db.relationship('ContentPage', backref='project', lazy=True)
    seo_audits = db.relationship('SeoAudit', backref='project', lazy=True)
    keyword_sets = db.relationship('KeywordSet', backref='project', lazy=True)
    backlink_records = db.relationship('BacklinkRecord', backref='project', lazy=True)
    schedules = db.relationship('ContentSchedule', backref='project', lazy=True)
    lead_submissions = db.relationship('LeadSubmission', backref='project', lazy=True)
    gbp_posts = db.relationship('GbpPost', backref='project', lazy=True)

    def __repr__(self):
        return f'<Project {self.name}>'


class ContentPage(db.Model):
    __tablename__ = 'content_pages'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text)
    content_type = db.Column(db.String(50), default='article')  # landing_page/blog/article/hub_page/spoke_article
    status = db.Column(db.String(20), default='draft')  # draft/review/published/archived
    quality_score = db.Column(db.Float)
    wp_post_id = db.Column(db.Integer)
    wp_post_url = db.Column(db.String(500))
    schema_markup = db.Column(db.Text)
    meta_description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schedules = db.relationship('ContentSchedule', backref='content_page', lazy=True)

    def __repr__(self):
        return f'<ContentPage {self.title}>'


class SeoAudit(db.Model):
    __tablename__ = 'seo_audits'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    issues = db.Column(db.Text)  # JSON text
    audit_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SeoAudit {self.domain}>'


class KeywordSet(db.Model):
    __tablename__ = 'keyword_sets'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    seed_keyword = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(200))
    keywords_data = db.Column(db.Text)  # JSON text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<KeywordSet {self.seed_keyword}>'


class BacklinkRecord(db.Model):
    __tablename__ = 'backlink_records'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    backlinks_data = db.Column(db.Text)  # JSON text
    new_count = db.Column(db.Integer, default=0)
    lost_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BacklinkRecord {self.domain}>'


class ContentSchedule(db.Model):
    __tablename__ = 'content_schedules'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    content_page_id = db.Column(db.Integer, db.ForeignKey('content_pages.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled/deployed/draft
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContentSchedule {self.id} {self.status}>'


class LeadSubmission(db.Model):
    __tablename__ = 'lead_submissions'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    message = db.Column(db.Text)
    service_interest = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LeadSubmission {self.email}>'


class GbpPost(db.Model):
    __tablename__ = 'gbp_posts'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    content_text = db.Column(db.Text, nullable=False)
    cta = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    scheduled_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending/posted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GbpPost {self.id} {self.status}>'
