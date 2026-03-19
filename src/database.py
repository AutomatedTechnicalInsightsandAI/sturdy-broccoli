"""
database.py

SQLite persistence layer for the Staging & Review Workflow.

Schema covers:
  - batches          — batch-level metadata and global styling
  - content_pages    — per-page content, quality metrics, review status
  - templates        — reusable Tailwind HTML boilerplates
  - competitor_analysis — per-page competitor benchmarking records
  - page_revisions   — full audit trail of content changes

Connection management
~~~~~~~~~~~~~~~~~~~~~
``get_connection()`` returns a thread-local ``sqlite3.Connection`` backed by
the path in the ``STURDY_DB_PATH`` environment variable (default:
``sturdy_broccoli.db``).  Pass ``db_path=":memory:"`` to ``Database`` for an
in-process test database.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.environ.get("STURDY_DB_PATH", "sturdy_broccoli.db")

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS batches (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT    NOT NULL,
    description          TEXT,
    total_pages          INTEGER NOT NULL DEFAULT 0,
    pages_draft          INTEGER NOT NULL DEFAULT 0,
    pages_approved       INTEGER NOT NULL DEFAULT 0,
    pages_deployed       INTEGER NOT NULL DEFAULT 0,
    pages_rejected       INTEGER NOT NULL DEFAULT 0,
    batch_primary_color  TEXT,
    batch_logo_url       TEXT,
    batch_font_family    TEXT,
    batch_global_cta_text TEXT,
    batch_global_cta_link TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    created_by           TEXT,
    deployed_at          TIMESTAMP,
    deployed_by          TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    UNIQUE NOT NULL,
    display_name        TEXT    NOT NULL,
    template_html       TEXT,
    typography_config   TEXT,   -- JSON
    color_config        TEXT,   -- JSON
    cta_positions       TEXT,   -- JSON
    preview_image_url   TEXT
);

CREATE TABLE IF NOT EXISTS content_pages (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id             INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    title                TEXT    NOT NULL,
    slug                 TEXT    UNIQUE,
    h1_content           TEXT,
    meta_title           TEXT,
    meta_description     TEXT,
    content_markdown     TEXT,
    template_id          INTEGER REFERENCES templates(id),
    review_status        TEXT    NOT NULL DEFAULT 'draft'
                             CHECK(review_status IN ('draft','approved','needs_revision','rejected','deployed')),
    reviewer_notes       TEXT,
    reviewed_by          TEXT,
    reviewed_at          TIMESTAMP,
    quality_scores       TEXT,   -- JSON {authority, semantic, structure, engagement, uniqueness, overall}
    competitor_benchmark TEXT,
    hub_page_id          INTEGER REFERENCES content_pages(id),
    internal_links       TEXT,   -- JSON {links:[{to_page_id, anchor_text, status}]}
    brand_color_override TEXT,
    custom_logo_url      TEXT,
    cta_text_override    TEXT,
    cta_link_override    TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    last_modified_at     TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    deployed_at          TIMESTAMP
);

CREATE TABLE IF NOT EXISTS competitor_analysis (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id                     INTEGER NOT NULL REFERENCES content_pages(id) ON DELETE CASCADE,
    competitor_url              TEXT,
    competitor_h1               TEXT,
    competitor_structure        TEXT,   -- JSON
    competitor_quality_signals  TEXT,   -- JSON
    analysis_timestamp          TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS page_revisions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id          INTEGER NOT NULL REFERENCES content_pages(id) ON DELETE CASCADE,
    revision_number  INTEGER NOT NULL,
    content_markdown TEXT,
    changed_by       TEXT,
    change_timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    change_reason    TEXT
);

CREATE INDEX IF NOT EXISTS idx_pages_batch_id       ON content_pages(batch_id);
CREATE INDEX IF NOT EXISTS idx_pages_review_status  ON content_pages(review_status);
CREATE INDEX IF NOT EXISTS idx_pages_template_id    ON content_pages(template_id);
CREATE INDEX IF NOT EXISTS idx_revisions_page_id    ON page_revisions(page_id);
CREATE INDEX IF NOT EXISTS idx_competitor_page_id   ON competitor_analysis(page_id);
"""

# ---------------------------------------------------------------------------
# Seed data for templates
# ---------------------------------------------------------------------------

_SEED_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "modern_saas",
        "display_name": "Modern SaaS",
        "template_html": (
            "<div class='min-h-screen bg-white'>"
            "<h1 class='text-5xl font-bold text-gray-900 mt-16 mb-6'>{{h1}}</h1>"
            "<p class='text-xl text-gray-600 mb-8'>{{meta_description}}</p>"
            "<a href='{{cta_link}}' class='bg-blue-600 text-white px-8 py-3 rounded-lg'>{{cta_text}}</a>"
            "<div class='mt-12 prose max-w-none'>{{content}}</div>"
            "</div>"
        ),
        "typography_config": json.dumps({"font": "Inter", "h1_size": "5xl", "body_size": "base"}),
        "color_config": json.dumps({"primary": "#2563EB", "background": "#FFFFFF", "text": "#111827"}),
        "cta_positions": json.dumps(["hero", "mid_page", "footer"]),
    },
    {
        "name": "professional_service",
        "display_name": "Professional Service",
        "template_html": (
            "<div class='min-h-screen bg-gray-50'>"
            "<div class='max-w-6xl mx-auto px-6 py-16'>"
            "<h1 class='text-4xl font-serif font-bold text-gray-900 mb-4'>{{h1}}</h1>"
            "<p class='text-lg text-gray-700 mb-6'>{{meta_description}}</p>"
            "<div class='grid grid-cols-3 gap-8 mt-8'>"
            "<div class='col-span-2 prose'>{{content}}</div>"
            "<aside class='bg-white rounded-xl p-6 shadow'><h3 class='font-bold'>Why Choose Us</h3></aside>"
            "</div></div></div>"
        ),
        "typography_config": json.dumps({"font": "Playfair Display", "h1_size": "4xl", "body_size": "lg"}),
        "color_config": json.dumps({"primary": "#1E3A5F", "background": "#F9FAFB", "text": "#374151"}),
        "cta_positions": json.dumps(["hero", "sidebar", "footer"]),
    },
    {
        "name": "content_guide",
        "display_name": "Content Guide",
        "template_html": (
            "<div class='min-h-screen bg-white'>"
            "<div class='max-w-4xl mx-auto px-6 py-12'>"
            "<h1 class='text-3xl font-bold text-gray-900 mb-2'>{{h1}}</h1>"
            "<div class='flex gap-12 mt-8'>"
            "<nav class='w-48 shrink-0'><p class='font-semibold text-sm uppercase text-gray-500'>Contents</p></nav>"
            "<article class='prose prose-lg'>{{content}}</article>"
            "</div></div></div>"
        ),
        "typography_config": json.dumps({"font": "Georgia", "h1_size": "3xl", "body_size": "lg"}),
        "color_config": json.dumps({"primary": "#059669", "background": "#FFFFFF", "text": "#1F2937"}),
        "cta_positions": json.dumps(["inline", "end_of_guide"]),
    },
    {
        "name": "ecommerce",
        "display_name": "E-commerce",
        "template_html": (
            "<div class='min-h-screen bg-white'>"
            "<h1 class='text-4xl font-bold text-center py-8'>{{h1}}</h1>"
            "<div class='grid grid-cols-4 gap-6 px-8'>{{content}}</div>"
            "<div class='text-center py-12'>"
            "<a href='{{cta_link}}' class='bg-orange-500 text-white px-10 py-4 rounded-full text-lg'>{{cta_text}}</a>"
            "</div></div>"
        ),
        "typography_config": json.dumps({"font": "Poppins", "h1_size": "4xl", "body_size": "base"}),
        "color_config": json.dumps({"primary": "#F97316", "background": "#FFFFFF", "text": "#111827"}),
        "cta_positions": json.dumps(["hero", "product_grid", "cart_sidebar"]),
    },
    {
        "name": "enterprise",
        "display_name": "Enterprise",
        "template_html": (
            "<div class='min-h-screen bg-slate-900 text-white'>"
            "<div class='max-w-7xl mx-auto px-8 py-20'>"
            "<h1 class='text-5xl font-bold mb-6'>{{h1}}</h1>"
            "<p class='text-xl text-slate-300 mb-10'>{{meta_description}}</p>"
            "<div class='grid grid-cols-2 gap-12 mt-12'>{{content}}</div>"
            "<div class='mt-16'>"
            "<a href='{{cta_link}}' class='bg-blue-500 text-white px-10 py-4 rounded-lg text-lg'>{{cta_text}}</a>"
            "</div></div></div>"
        ),
        "typography_config": json.dumps({"font": "Inter", "h1_size": "5xl", "body_size": "xl"}),
        "color_config": json.dumps({"primary": "#3B82F6", "background": "#0F172A", "text": "#F1F5F9"}),
        "cta_positions": json.dumps(["hero", "roi_calculator", "demo_request"]),
    },
]


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------


class Database:
    """
    Thin wrapper around a SQLite connection.

    Parameters
    ----------
    db_path:
        File path for the SQLite database, or ``":memory:"`` for an
        in-process test database.  Defaults to the value of the
        ``STURDY_DB_PATH`` environment variable (``sturdy_broccoli.db``).
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        """Return (or create) the underlying SQLite connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create all tables (idempotent — uses CREATE IF NOT EXISTS)."""
        conn = self.connect()
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        self._seed_templates()
        logger.debug("Database schema initialised at %s", self._db_path)

    def _seed_templates(self) -> None:
        conn = self.connect()
        for tmpl in _SEED_TEMPLATES:
            conn.execute(
                """
                INSERT OR IGNORE INTO templates
                    (name, display_name, template_html, typography_config,
                     color_config, cta_positions)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tmpl["name"],
                    tmpl["display_name"],
                    tmpl["template_html"],
                    tmpl["typography_config"],
                    tmpl["color_config"],
                    tmpl["cta_positions"],
                ),
            )
        conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        row = self.connect().execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        rows = self.connect().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.connect().execute(sql, params)

    def commit(self) -> None:
        self.connect().commit()

    def lastrowid(self, sql: str, params: tuple = ()) -> int:
        cur = self.execute(sql, params)
        self.commit()
        return cur.lastrowid  # type: ignore[return-value]
