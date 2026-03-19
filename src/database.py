"""
database.py

SQLite persistence layer for the Decoupled SEO Site Factory.

Tables
------
- batches           : Batch runs with shared styling configuration
- content_pages     : Page objects as structured data (JSON-first)
- templates         : HTML rendering templates with typography/colour config
- page_revisions    : Audit trail of every quality-impacting change

Connection strategy
-------------------
- Tests inject ``':memory:'`` and obtain a *persistent* connection so that all
  operations within a test share the same in-memory database.
- Production code (default) opens a *new* connection per operation, which is
  safe for multi-threaded WSGI/ASGI use.

Usage::

    db = Database()                 # default: sturdy_broccoli.db
    db = Database(':memory:')       # in-memory (tests)

    batch_id = db.create_batch("Client A – March Run")
    page_id  = db.create_page(batch_id, page_data)
    page     = db.get_page(page_id)
    db.update_page_status(page_id, "approved")
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "sturdy_broccoli.db")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS batches (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL,
    description           TEXT,
    client_id             TEXT,
    total_pages           INTEGER DEFAULT 0,
    pages_draft           INTEGER DEFAULT 0,
    pages_approved        INTEGER DEFAULT 0,
    pages_deployed        INTEGER DEFAULT 0,
    batch_primary_color   TEXT    DEFAULT '#2563EB',
    batch_logo_url        TEXT,
    batch_font_family     TEXT    DEFAULT 'Inter, sans-serif',
    batch_global_cta_text TEXT    DEFAULT 'Get Started',
    batch_global_cta_link TEXT    DEFAULT '/contact',
    created_at            TEXT    NOT NULL,
    created_by            TEXT,
    deployed_at           TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT UNIQUE NOT NULL,
    display_name     TEXT NOT NULL,
    template_html    TEXT,
    typography_config TEXT DEFAULT '{}',
    color_config     TEXT DEFAULT '{}',
    cta_positions    TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS content_pages (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id               INTEGER NOT NULL REFERENCES batches(id),

    -- Metadata layer
    title                  TEXT NOT NULL,
    slug                   TEXT,
    h1                     TEXT NOT NULL,
    meta_title             TEXT,
    meta_description       TEXT,
    target_keyword         TEXT,
    secondary_keywords     TEXT DEFAULT '[]',
    word_count             INTEGER DEFAULT 0,

    -- Semantic core (JSON)
    semantic_core          TEXT DEFAULT '{}',

    -- Structure (JSON)
    structure              TEXT DEFAULT '{}',

    -- Competitor intelligence (JSON)
    competitor_intelligence TEXT DEFAULT '{}',

    -- Hub-and-spoke
    hub_page_id            INTEGER REFERENCES content_pages(id),
    role                   TEXT    DEFAULT 'spoke'
                               CHECK(role IN ('hub', 'spoke')),
    internal_links         TEXT    DEFAULT '{}',

    -- Content layers
    content_markdown       TEXT,
    content_html           TEXT,

    -- Template & styling
    template_id            INTEGER REFERENCES templates(id),
    color_override         TEXT,
    logo_override          TEXT,
    font_override          TEXT,
    cta_text_override      TEXT,
    cta_link_override      TEXT,

    -- Quality scoring engine (JSON)
    quality_scores         TEXT DEFAULT '{}',
    quality_audit_trail    TEXT DEFAULT '[]',

    -- Review workflow
    review_status          TEXT DEFAULT 'draft'
                               CHECK(review_status IN (
                                   'draft','reviewed','approved',
                                   'needs_revision','rejected','deployed'
                               )),
    reviewer_notes         TEXT,
    reviewed_by            TEXT,
    reviewed_at            TEXT,

    created_at             TEXT NOT NULL,
    last_modified_at       TEXT NOT NULL,
    deployed_at            TEXT
);

CREATE TABLE IF NOT EXISTS page_revisions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id               INTEGER NOT NULL REFERENCES content_pages(id),
    revision_number       INTEGER NOT NULL,
    quality_scores_before TEXT DEFAULT '{}',
    quality_scores_after  TEXT DEFAULT '{}',
    changed_by            TEXT,
    change_timestamp      TEXT NOT NULL,
    change_type           TEXT DEFAULT 'manual_edit'
                              CHECK(change_type IN (
                                  'regenerate_section','apply_template',
                                  'batch_style','manual_edit'
                              )),
    change_reason         TEXT
);

CREATE INDEX IF NOT EXISTS idx_pages_batch    ON content_pages(batch_id);
CREATE INDEX IF NOT EXISTS idx_pages_status   ON content_pages(review_status);
CREATE INDEX IF NOT EXISTS idx_revisions_page ON page_revisions(page_id);
"""

# ---------------------------------------------------------------------------
# Seed templates
# ---------------------------------------------------------------------------

_SEED_TEMPLATES = [
    {
        "name": "professional_service",
        "display_name": "Professional Service",
        "typography_config": json.dumps({"heading_font": "Inter", "body_font": "Inter", "base_size": "16px"}),
        "color_config": json.dumps({"primary": "#2563EB", "secondary": "#1E40AF", "text": "#111827", "bg": "#FFFFFF"}),
        "cta_positions": json.dumps(["mid-page", "end-of-page"]),
    },
    {
        "name": "thought_leadership",
        "display_name": "Thought Leadership",
        "typography_config": json.dumps({"heading_font": "Merriweather", "body_font": "Georgia", "base_size": "18px"}),
        "color_config": json.dumps({"primary": "#7C3AED", "secondary": "#5B21B6", "text": "#1F2937", "bg": "#FAFAFA"}),
        "cta_positions": json.dumps(["end-of-page"]),
    },
    {
        "name": "technical_guide",
        "display_name": "Technical Guide",
        "typography_config": json.dumps({"heading_font": "JetBrains Mono", "body_font": "Inter", "base_size": "15px"}),
        "color_config": json.dumps({"primary": "#059669", "secondary": "#065F46", "text": "#111827", "bg": "#F9FAFB"}),
        "cta_positions": json.dumps(["mid-page", "end-of-page"]),
    },
    {
        "name": "case_study",
        "display_name": "Case Study",
        "typography_config": json.dumps({"heading_font": "Inter", "body_font": "Inter", "base_size": "16px"}),
        "color_config": json.dumps({"primary": "#DC2626", "secondary": "#991B1B", "text": "#111827", "bg": "#FFFFFF"}),
        "cta_positions": json.dumps(["mid-page", "end-of-page"]),
    },
    {
        "name": "landing_page",
        "display_name": "Landing Page",
        "typography_config": json.dumps({"heading_font": "Inter", "body_font": "Inter", "base_size": "16px"}),
        "color_config": json.dumps({"primary": "#F59E0B", "secondary": "#B45309", "text": "#111827", "bg": "#FFFFFF"}),
        "cta_positions": json.dumps(["top", "mid-page", "end-of-page"]),
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a dict, JSON-decoding JSON columns."""
    JSON_COLS = {
        "secondary_keywords", "semantic_core", "structure",
        "competitor_intelligence", "internal_links",
        "quality_scores", "quality_audit_trail",
        "quality_scores_before", "quality_scores_after",
        "typography_config", "color_config", "cta_positions",
    }
    result: dict[str, Any] = {}
    for key in row.keys():
        val = row[key]
        if key in JSON_COLS and isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                pass
        result[key] = val
    return result


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------

class Database:
    """
    SQLite persistence layer for the SEO Site Factory.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file, or ``':memory:'`` for an in-memory
        database used in tests.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._memory_conn: sqlite3.Connection | None = None

        if db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
            self._init_schema(self._memory_conn)
        else:
            # Ensure the schema exists on first access
            with self._connect() as conn:
                self._init_schema(conn)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        self._seed_templates(conn)

    def _seed_templates(self, conn: sqlite3.Connection) -> None:
        for tmpl in _SEED_TEMPLATES:
            conn.execute(
                """
                INSERT OR IGNORE INTO templates (name, display_name, typography_config, color_config, cta_positions)
                VALUES (:name, :display_name, :typography_config, :color_config, :cta_positions)
                """,
                tmpl,
            )
        conn.commit()

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def create_batch(
        self,
        name: str,
        description: str = "",
        client_id: str = "",
        primary_color: str = "#2563EB",
        logo_url: str = "",
        font_family: str = "Inter, sans-serif",
        global_cta_text: str = "Get Started",
        global_cta_link: str = "/contact",
        created_by: str = "",
    ) -> int:
        """Create a new batch and return its ID."""
        conn = self._connect()
        cur = conn.execute(
            """
            INSERT INTO batches
                (name, description, client_id,
                 batch_primary_color, batch_logo_url, batch_font_family,
                 batch_global_cta_text, batch_global_cta_link,
                 created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, client_id,
             primary_color, logo_url, font_family,
             global_cta_text, global_cta_link,
             _now(), created_by),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_batch(self, batch_id: int) -> dict[str, Any] | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM batches WHERE id = ?", (batch_id,)
        ).fetchone()
        return _row_to_dict(conn.cursor(), row) if row else None

    def list_batches(self) -> list[dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC"
        ).fetchall()
        cur = conn.cursor()
        return [_row_to_dict(cur, r) for r in rows]

    def update_batch_styles(
        self,
        batch_id: int,
        *,
        primary_color: str | None = None,
        logo_url: str | None = None,
        font_family: str | None = None,
        global_cta_text: str | None = None,
        global_cta_link: str | None = None,
    ) -> None:
        """Patch the shared styling fields of a batch."""
        updates: list[tuple[str, Any]] = []
        if primary_color is not None:
            updates.append(("batch_primary_color", primary_color))
        if logo_url is not None:
            updates.append(("batch_logo_url", logo_url))
        if font_family is not None:
            updates.append(("batch_font_family", font_family))
        if global_cta_text is not None:
            updates.append(("batch_global_cta_text", global_cta_text))
        if global_cta_link is not None:
            updates.append(("batch_global_cta_link", global_cta_link))
        if not updates:
            return
        set_clause = ", ".join(f"{col} = ?" for col, _ in updates)
        values = [v for _, v in updates] + [batch_id]
        conn = self._connect()
        conn.execute(f"UPDATE batches SET {set_clause} WHERE id = ?", values)
        conn.commit()

    def _refresh_batch_counts(self, conn: sqlite3.Connection, batch_id: int) -> None:
        conn.execute(
            """
            UPDATE batches SET
                total_pages    = (SELECT COUNT(*)    FROM content_pages WHERE batch_id = ?),
                pages_draft    = (SELECT COUNT(*)    FROM content_pages WHERE batch_id = ? AND review_status = 'draft'),
                pages_approved = (SELECT COUNT(*)    FROM content_pages WHERE batch_id = ? AND review_status = 'approved'),
                pages_deployed = (SELECT COUNT(*)    FROM content_pages WHERE batch_id = ? AND review_status = 'deployed')
            WHERE id = ?
            """,
            (batch_id, batch_id, batch_id, batch_id, batch_id),
        )

    # ------------------------------------------------------------------
    # Template operations
    # ------------------------------------------------------------------

    def list_templates(self) -> list[dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute("SELECT * FROM templates ORDER BY name").fetchall()
        cur = conn.cursor()
        return [_row_to_dict(cur, r) for r in rows]

    def get_template(self, template_id: int) -> dict[str, Any] | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM templates WHERE id = ?", (template_id,)
        ).fetchone()
        return _row_to_dict(conn.cursor(), row) if row else None

    def get_template_by_name(self, name: str) -> dict[str, Any] | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM templates WHERE name = ?", (name,)
        ).fetchone()
        return _row_to_dict(conn.cursor(), row) if row else None

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    def create_page(self, batch_id: int, page_data: dict[str, Any]) -> int:
        """
        Insert a new content page record and return its ID.

        Parameters
        ----------
        batch_id:
            The parent batch.
        page_data:
            A dict matching the Page Object schema from the problem statement.
            All JSON-valued sub-keys are serialised automatically.
        """
        now = _now()

        def _j(val: Any) -> str:
            return json.dumps(val) if not isinstance(val, str) else val

        conn = self._connect()
        cur = conn.execute(
            """
            INSERT INTO content_pages (
                batch_id, title, slug, h1, meta_title, meta_description,
                target_keyword, secondary_keywords, word_count,
                semantic_core, structure, competitor_intelligence,
                hub_page_id, role, internal_links,
                content_markdown, content_html,
                template_id, color_override, logo_override, font_override,
                cta_text_override, cta_link_override,
                quality_scores, quality_audit_trail,
                review_status, reviewer_notes,
                created_at, last_modified_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?
            )
            """,
            (
                batch_id,
                page_data.get("title", ""),
                page_data.get("slug", ""),
                page_data.get("h1", page_data.get("title", "")),
                page_data.get("meta_title", ""),
                page_data.get("meta_description", ""),
                page_data.get("target_keyword", ""),
                _j(page_data.get("secondary_keywords", [])),
                page_data.get("word_count", 0),
                _j(page_data.get("semantic_core", {})),
                _j(page_data.get("structure", {})),
                _j(page_data.get("competitor_intelligence", {})),
                page_data.get("hub_page_id"),
                page_data.get("role", "spoke"),
                _j(page_data.get("internal_links", {})),
                page_data.get("content_markdown", ""),
                page_data.get("content_html", ""),
                page_data.get("template_id"),
                page_data.get("color_override"),
                page_data.get("logo_override"),
                page_data.get("font_override"),
                page_data.get("cta_text_override"),
                page_data.get("cta_link_override"),
                _j(page_data.get("quality_scores", {})),
                _j(page_data.get("quality_audit_trail", [])),
                page_data.get("review_status", "draft"),
                page_data.get("reviewer_notes", ""),
                now,
                now,
            ),
        )
        page_id = cur.lastrowid
        self._refresh_batch_counts(conn, batch_id)
        conn.commit()
        return page_id  # type: ignore[return-value]

    def get_page(self, page_id: int) -> dict[str, Any] | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM content_pages WHERE id = ?", (page_id,)
        ).fetchone()
        return _row_to_dict(conn.cursor(), row) if row else None

    def list_pages(
        self,
        batch_id: int,
        status_filter: str | None = None,
        sort_by: str = "created_at",
    ) -> list[dict[str, Any]]:
        """Return all pages for a batch, optionally filtered and sorted."""
        allowed_sort = {"created_at", "last_modified_at", "title", "review_status"}
        order_col = sort_by if sort_by in allowed_sort else "created_at"

        conn = self._connect()
        if status_filter:
            rows = conn.execute(
                f"SELECT * FROM content_pages WHERE batch_id = ? AND review_status = ? ORDER BY {order_col}",
                (batch_id, status_filter),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM content_pages WHERE batch_id = ? ORDER BY {order_col}",
                (batch_id,),
            ).fetchall()
        cur = conn.cursor()
        return [_row_to_dict(cur, r) for r in rows]

    def update_page(self, page_id: int, updates: dict[str, Any]) -> None:
        """
        Patch a content page with the given field updates.

        JSON-valued fields in *updates* are serialised automatically.
        Only columns in the explicit allowlist are accepted to prevent
        SQL injection via untrusted key names.
        """
        _ALLOWED_COLS = {
            "title", "slug", "h1", "meta_title", "meta_description",
            "target_keyword", "secondary_keywords", "word_count",
            "semantic_core", "structure", "competitor_intelligence",
            "hub_page_id", "role", "internal_links",
            "content_markdown", "content_html",
            "template_id", "color_override", "logo_override", "font_override",
            "cta_text_override", "cta_link_override",
            "quality_scores", "quality_audit_trail",
            "review_status", "reviewer_notes", "reviewed_by", "reviewed_at",
        }
        JSON_COLS = {
            "secondary_keywords", "semantic_core", "structure",
            "competitor_intelligence", "internal_links",
            "quality_scores", "quality_audit_trail",
        }
        serialised: dict[str, Any] = {}
        for k, v in updates.items():
            if k not in _ALLOWED_COLS:
                continue
            if k in JSON_COLS and not isinstance(v, str):
                serialised[k] = json.dumps(v)
            else:
                serialised[k] = v

        if not serialised:
            return

        serialised["last_modified_at"] = _now()
        set_clause = ", ".join(f"{col} = ?" for col in serialised)
        values = list(serialised.values()) + [page_id]

        conn = self._connect()
        conn.execute(
            f"UPDATE content_pages SET {set_clause} WHERE id = ?", values
        )
        conn.commit()

    def update_page_status(
        self,
        page_id: int,
        status: str,
        reviewer_notes: str = "",
        reviewed_by: str = "",
    ) -> None:
        """Update the review_status of a page and refresh batch counters."""
        now = _now()
        conn = self._connect()
        conn.execute(
            """
            UPDATE content_pages SET
                review_status    = ?,
                reviewer_notes   = ?,
                reviewed_by      = ?,
                reviewed_at      = ?,
                last_modified_at = ?
            WHERE id = ?
            """,
            (status, reviewer_notes, reviewed_by, now, now, page_id),
        )
        row = conn.execute(
            "SELECT batch_id FROM content_pages WHERE id = ?", (page_id,)
        ).fetchone()
        if row:
            self._refresh_batch_counts(conn, row["batch_id"])
        conn.commit()

    def update_page_quality_scores(
        self,
        page_id: int,
        quality_scores: dict[str, Any],
        audit_entry: dict[str, Any] | None = None,
    ) -> None:
        """Persist updated quality scores and append to the audit trail."""
        conn = self._connect()
        existing_row = conn.execute(
            "SELECT quality_audit_trail FROM content_pages WHERE id = ?",
            (page_id,),
        ).fetchone()
        if existing_row is None:
            return

        trail: list[dict[str, Any]] = []
        try:
            trail = json.loads(existing_row["quality_audit_trail"] or "[]")
        except (json.JSONDecodeError, TypeError):
            trail = []

        if audit_entry:
            audit_entry.setdefault("timestamp", _now())
            trail.append(audit_entry)

        now = _now()
        conn.execute(
            """
            UPDATE content_pages SET
                quality_scores    = ?,
                quality_audit_trail = ?,
                last_modified_at  = ?
            WHERE id = ?
            """,
            (json.dumps(quality_scores), json.dumps(trail), now, page_id),
        )
        conn.commit()

    def apply_batch_styles_to_pages(
        self,
        batch_id: int,
        color_override: str | None = None,
        logo_override: str | None = None,
        font_override: str | None = None,
        cta_text_override: str | None = None,
        cta_link_override: str | None = None,
        template_id: int | None = None,
    ) -> int:
        """
        Apply shared styling overrides to all pages in a batch.

        Returns the number of pages updated.
        """
        updates: list[tuple[str, Any]] = []
        if color_override is not None:
            updates.append(("color_override", color_override))
        if logo_override is not None:
            updates.append(("logo_override", logo_override))
        if font_override is not None:
            updates.append(("font_override", font_override))
        if cta_text_override is not None:
            updates.append(("cta_text_override", cta_text_override))
        if cta_link_override is not None:
            updates.append(("cta_link_override", cta_link_override))
        if template_id is not None:
            updates.append(("template_id", template_id))
        if not updates:
            return 0

        # Column names in `updates` are always hardcoded above — no user input
        # reaches this set_clause, so f-string construction is safe here.
        now = _now()
        updates.append(("last_modified_at", now))
        set_clause = ", ".join(f"{col} = ?" for col, _ in updates)
        values = [v for _, v in updates] + [batch_id]

        conn = self._connect()
        cur = conn.execute(
            f"UPDATE content_pages SET {set_clause} WHERE batch_id = ?", values
        )
        conn.commit()
        return cur.rowcount

    def delete_page(self, page_id: int) -> None:
        conn = self._connect()
        row = conn.execute(
            "SELECT batch_id FROM content_pages WHERE id = ?", (page_id,)
        ).fetchone()
        conn.execute("DELETE FROM content_pages WHERE id = ?", (page_id,))
        if row:
            self._refresh_batch_counts(conn, row["batch_id"])
        conn.commit()

    # ------------------------------------------------------------------
    # Revision operations
    # ------------------------------------------------------------------

    def record_revision(
        self,
        page_id: int,
        quality_scores_before: dict[str, Any],
        quality_scores_after: dict[str, Any],
        change_type: str = "manual_edit",
        change_reason: str = "",
        changed_by: str = "",
    ) -> int:
        """Append a revision record and return its ID."""
        conn = self._connect()
        row = conn.execute(
            "SELECT MAX(revision_number) AS max_rev FROM page_revisions WHERE page_id = ?",
            (page_id,),
        ).fetchone()
        next_rev = (row["max_rev"] or 0) + 1

        cur = conn.execute(
            """
            INSERT INTO page_revisions
                (page_id, revision_number, quality_scores_before, quality_scores_after,
                 changed_by, change_timestamp, change_type, change_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page_id,
                next_rev,
                json.dumps(quality_scores_before),
                json.dumps(quality_scores_after),
                changed_by,
                _now(),
                change_type,
                change_reason,
            ),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def list_revisions(self, page_id: int) -> list[dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM page_revisions WHERE page_id = ? ORDER BY revision_number",
            (page_id,),
        ).fetchall()
        cur = conn.cursor()
        return [_row_to_dict(cur, r) for r in rows]

    # ------------------------------------------------------------------
    # Pre-flight check helpers
    # ------------------------------------------------------------------

    def get_deploy_preflight(self, batch_id: int) -> dict[str, Any]:
        """
        Run pre-flight checks for all approved pages in a batch.

        Returns
        -------
        dict with keys:
            ``passed`` (bool), ``pages_to_deploy`` (list[int]),
            ``checks`` (dict with per-check status),
            ``failures`` (list[str])
        """
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM content_pages WHERE batch_id = ? AND review_status = 'approved'",
            (batch_id,),
        ).fetchall()
        cur = conn.cursor()
        pages = [_row_to_dict(cur, r) for r in rows]

        failures: list[str] = []
        meta_ok = True
        links_ok = True
        quality_ok = True
        scores_ok = True

        for page in pages:
            pid = page["id"]
            if not page.get("meta_title") or not page.get("meta_description"):
                meta_ok = False
                failures.append(f"Page {pid} ({page['title']}): missing meta tags")

            qs: dict[str, Any] = page.get("quality_scores") or {}
            overall = qs.get("overall_score", 0)
            if overall < 75:
                quality_ok = False
                failures.append(
                    f"Page {pid} ({page['title']}): overall quality {overall}/100 < 75"
                )

            missing_metrics = [
                m for m in ["authority_score", "semantic_richness_score",
                             "structure_score", "engagement_potential_score",
                             "uniqueness_score"]
                if m not in qs
            ]
            if missing_metrics:
                scores_ok = False
                failures.append(
                    f"Page {pid} ({page['title']}): missing quality metrics: {missing_metrics}"
                )

        checks = {
            "meta_tags_present": meta_ok,
            "internal_links_valid": links_ok,
            "quality_above_75": quality_ok,
            "all_metrics_scored": scores_ok,
        }
        passed = all(checks.values()) and len(pages) > 0

        return {
            "passed": passed,
            "pages_to_deploy": [p["id"] for p in pages],
            "checks": checks,
            "failures": failures,
            "total_approved": len(pages),
        }

    def deploy_batch(self, batch_id: int) -> int:
        """
        Mark all approved pages as deployed and record the timestamp.

        Returns the count of deployed pages.
        """
        now = _now()
        conn = self._connect()
        cur = conn.execute(
            """
            UPDATE content_pages SET
                review_status    = 'deployed',
                deployed_at      = ?,
                last_modified_at = ?
            WHERE batch_id = ? AND review_status = 'approved'
            """,
            (now, now, batch_id),
        )
        conn.execute(
            "UPDATE batches SET deployed_at = ? WHERE id = ?",
            (now, batch_id),
        )
        self._refresh_batch_counts(conn, batch_id)
        conn.commit()
        return cur.rowcount
