"""
database.py

SQLite persistence layer for the Sturdy Broccoli SEO content platform.

Replaces in-memory session state with a durable, queryable store that
supports the agency multi-tenant use case.

Schema
------
- ``clients``           — Agency client accounts
- ``pages``             — Generated landing pages with metadata
- ``content_versions``  — Version history for each page's content
- ``competitor_cache``  — Cached competitor analysis results
- ``quality_scores``    — Multi-dimensional quality scores per page version
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "sturdy_broccoli.db"

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    slug        TEXT    NOT NULL UNIQUE,
    website     TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    service_type    TEXT    NOT NULL,
    topic           TEXT    NOT NULL,
    primary_keyword TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'draft'
                            CHECK(status IN ('draft','review','published','archived')),
    page_type       TEXT    NOT NULL DEFAULT 'landing_page',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    metadata        TEXT    NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS content_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 1,
    content_html    TEXT    NOT NULL DEFAULT '',
    content_markdown TEXT   NOT NULL DEFAULT '',
    word_count      INTEGER NOT NULL DEFAULT 0,
    quality_report  TEXT    NOT NULL DEFAULT '{}',
    created_at      TEXT    NOT NULL,
    UNIQUE(page_id, version)
);

CREATE TABLE IF NOT EXISTS competitor_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_topic   TEXT    NOT NULL,
    analysis        TEXT    NOT NULL DEFAULT '{}',
    created_at      TEXT    NOT NULL,
    expires_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id             INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    version_id          INTEGER REFERENCES content_versions(id) ON DELETE CASCADE,
    authority_score     REAL    NOT NULL DEFAULT 0,
    semantic_score      REAL    NOT NULL DEFAULT 0,
    structure_score     REAL    NOT NULL DEFAULT 0,
    engagement_score    REAL    NOT NULL DEFAULT 0,
    uniqueness_score    REAL    NOT NULL DEFAULT 0,
    overall_score       REAL    NOT NULL DEFAULT 0,
    computed_at         TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pages_client       ON pages(client_id);
CREATE INDEX IF NOT EXISTS idx_pages_status       ON pages(status);
CREATE INDEX IF NOT EXISTS idx_versions_page      ON content_versions(page_id);
CREATE INDEX IF NOT EXISTS idx_quality_page       ON quality_scores(page_id);
CREATE INDEX IF NOT EXISTS idx_competitor_topic   ON competitor_cache(service_topic);
"""

# ---------------------------------------------------------------------------
# Staging / batch schema DDL
# ---------------------------------------------------------------------------

_STAGING_SCHEMA_SQL = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS batches (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL,
    description           TEXT    NOT NULL DEFAULT '',
    created_by            TEXT    NOT NULL DEFAULT '',
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    batch_primary_color   TEXT,
    batch_logo_url        TEXT,
    batch_font_family     TEXT,
    batch_global_cta_text TEXT,
    batch_global_cta_link TEXT,
    total_pages           INTEGER NOT NULL DEFAULT 0,
    pages_draft           INTEGER NOT NULL DEFAULT 0,
    pages_pending         INTEGER NOT NULL DEFAULT 0,
    pages_approved        INTEGER NOT NULL DEFAULT 0,
    pages_deployed        INTEGER NOT NULL DEFAULT 0,
    pages_rejected        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS templates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL DEFAULT '',
    template_html TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_pages (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id             INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    title                TEXT    NOT NULL,
    slug                 TEXT    NOT NULL UNIQUE,
    h1_content           TEXT    NOT NULL DEFAULT '',
    meta_title           TEXT    NOT NULL DEFAULT '',
    meta_description     TEXT    NOT NULL DEFAULT '',
    content_markdown     TEXT    NOT NULL DEFAULT '',
    template_id          INTEGER REFERENCES templates(id),
    quality_scores       TEXT    NOT NULL DEFAULT '{}',
    competitor_benchmark TEXT    NOT NULL DEFAULT '',
    hub_page_id          INTEGER REFERENCES content_pages(id),
    review_status        TEXT    NOT NULL DEFAULT 'draft',
    reviewer_notes       TEXT    NOT NULL DEFAULT '',
    reviewed_by          TEXT    NOT NULL DEFAULT '',
    reviewed_at          TEXT,
    last_modified_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    deployed_at          TEXT,
    brand_color_override TEXT,
    custom_logo_url      TEXT,
    cta_text_override    TEXT,
    cta_link_override    TEXT,
    internal_links       TEXT    NOT NULL DEFAULT '{}',
    created_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS page_revisions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id          INTEGER NOT NULL REFERENCES content_pages(id) ON DELETE CASCADE,
    revision_number  INTEGER NOT NULL DEFAULT 1,
    content_markdown TEXT    NOT NULL DEFAULT '',
    changed_by       TEXT    NOT NULL DEFAULT '',
    change_reason    TEXT    NOT NULL DEFAULT '',
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS batch_pages (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id          INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    title             TEXT    NOT NULL,
    slug              TEXT    NOT NULL,
    topic             TEXT    NOT NULL DEFAULT '',
    primary_keyword   TEXT    NOT NULL DEFAULT '',
    status            TEXT    NOT NULL DEFAULT 'pending_review',
    preview_state     TEXT    NOT NULL DEFAULT '{}',
    assigned_template TEXT    NOT NULL DEFAULT 'modern_saas',
    h1_content        TEXT    NOT NULL DEFAULT '',
    meta_title        TEXT    NOT NULL DEFAULT '',
    meta_description  TEXT    NOT NULL DEFAULT '',
    content_markdown  TEXT    NOT NULL DEFAULT '',
    content_html      TEXT    NOT NULL DEFAULT '',
    quality_scores    TEXT    NOT NULL DEFAULT '{}',
    word_count        INTEGER NOT NULL DEFAULT 0,
    assigned_by       TEXT    NOT NULL DEFAULT '',
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(batch_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_content_pages_batch   ON content_pages(batch_id);
CREATE INDEX IF NOT EXISTS idx_content_pages_status  ON content_pages(review_status);
CREATE INDEX IF NOT EXISTS idx_batch_pages_batch     ON batch_pages(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_pages_status    ON batch_pages(status);
CREATE INDEX IF NOT EXISTS idx_page_revisions_page   ON page_revisions(page_id);
"""

# Five standard templates seeded on first init.
_TEMPLATE_SEEDS = [
    ("modern_saas",         "Modern SaaS"),
    ("professional_service","Professional Service"),
    ("content_guide",       "Content-Heavy Guide"),
    ("ecommerce",           "E-commerce"),
    ("enterprise",          "Enterprise"),
]

_TEMPLATE_HTML = (
    "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'/>"
    "<title>{{h1}}</title></head><body>"
    "<h1>{{h1}}</h1><div class='content'>{{content}}</div>"
    "<a href='{{cta_link}}'>{{cta_text}}</a></body></html>"
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------


class Database:
    """
    SQLite wrapper with per-call connections for file databases and a
    persistent connection for in-memory databases (``':memory:'``).

    Parameters
    ----------
    db_path:
        Path to the SQLite file.  Defaults to ``sturdy_broccoli.db`` in the
        repository root.  Pass ``':memory:'`` for an in-memory database
        (useful in tests).
    """

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = str(db_path)
        self._in_memory = self._db_path == ":memory:"

        # For in-memory databases a single persistent connection must be used;
        # creating a new connection each call would produce an empty database.
        # NOTE: The persistent in-memory connection uses check_same_thread=False
        # for compatibility with Streamlit's execution model.  In-memory databases
        # are intended for testing only; production use should use a file-based
        # database where per-call connections are used instead.
        if self._in_memory:
            self._memory_conn: sqlite3.Connection | None = sqlite3.connect(
                ":memory:", check_same_thread=False
            )
            self._memory_conn.row_factory = sqlite3.Row
        else:
            self._memory_conn = None

        self._init_schema()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)
        with self._connect() as conn:
            conn.executescript(_STAGING_SCHEMA_SQL)
        # Seed the five standard templates (idempotent).
        with self._connect() as conn:
            for name, display_name in _TEMPLATE_SEEDS:
                conn.execute(
                    "INSERT OR IGNORE INTO templates (name, display_name, template_html)"
                    " VALUES (?, ?, ?)",
                    (name, display_name, _TEMPLATE_HTML),
                )

    # Public alias required by tests and external callers.
    def init_schema(self) -> None:
        """Re-run schema initialisation (idempotent)."""
        self._init_schema()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        if self._in_memory:
            # Yield the persistent in-memory connection without closing it.
            conn = self._memory_conn
            assert conn is not None
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        else:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            # Enable WAL mode and foreign keys for file-based databases.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Low-level query helpers (used by StagingReviewManager)
    # ------------------------------------------------------------------

    def fetchone(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> dict[str, Any] | None:
        """Execute *sql* and return the first row as a dict, or ``None``."""
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return all rows as a list of dicts."""
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        """Execute a DML statement without returning a result."""
        with self._connect() as conn:
            conn.execute(sql, params)

    def commit(self) -> None:
        """Explicit commit (for callers that manage their own transaction)."""
        if self._in_memory and self._memory_conn is not None:
            self._memory_conn.commit()
        # For file-based databases each _connect() call auto-commits on exit;
        # a no-op commit is safe here.

    def lastrowid(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Execute an INSERT statement and return the new row's id."""
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Batch management (staging workflow)
    # ------------------------------------------------------------------

    def create_batch(
        self,
        name: str,
        description: str = "",
        created_by: str = "",
    ) -> int:
        """Insert a batch record and return its id."""
        return self.lastrowid(
            "INSERT INTO batches (name, description, created_by) VALUES (?, ?, ?)",
            (name, description, created_by),
        )

    def get_batch(self, batch_id: int) -> dict[str, Any] | None:
        """Return a batch record by id, or ``None``."""
        return self.fetchone("SELECT * FROM batches WHERE id = ?", (batch_id,))

    def list_batches(self) -> list[dict[str, Any]]:
        """Return all batches ordered by creation date descending."""
        return self.fetchall("SELECT * FROM batches ORDER BY created_at DESC")

    def update_batch_counts(self, batch_id: int) -> None:
        """Recount ``batch_pages`` rows and update the batch counters."""
        statuses = ["pending_review", "approved", "deployed", "draft", "rejected"]
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS cnt FROM batch_pages WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()["cnt"]
            counts: dict[str, int] = {}
            for st in statuses:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM batch_pages"
                    " WHERE batch_id = ? AND status = ?",
                    (batch_id, st),
                ).fetchone()
                counts[st] = row["cnt"]
            conn.execute(
                """UPDATE batches SET
                       total_pages    = ?,
                       pages_pending  = ?,
                       pages_approved = ?,
                       pages_deployed = ?,
                       pages_draft    = ?,
                       pages_rejected = ?
                   WHERE id = ?""",
                (
                    total,
                    counts.get("pending_review", 0),
                    counts.get("approved", 0),
                    counts.get("deployed", 0),
                    counts.get("draft", 0),
                    counts.get("rejected", 0),
                    batch_id,
                ),
            )

    # ------------------------------------------------------------------
    # Staging page CRUD (batch_pages table)
    # ------------------------------------------------------------------

    def _create_staging_page(self, page_data: dict[str, Any]) -> int:
        """Insert a row into ``batch_pages`` and return its id."""
        now = _now()
        qs = page_data.get("quality_scores", {})
        ps = page_data.get("preview_state", {})
        return self.lastrowid(
            """INSERT INTO batch_pages
               (batch_id, title, slug, topic, primary_keyword, status,
                preview_state, assigned_template, h1_content, meta_title,
                meta_description, content_markdown, content_html,
                quality_scores, word_count, assigned_by,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                page_data["batch_id"],
                page_data.get("title", ""),
                page_data.get("slug", ""),
                page_data.get("topic", ""),
                page_data.get("primary_keyword", ""),
                page_data.get("status", "pending_review"),
                json.dumps(ps) if isinstance(ps, dict) else (ps or "{}"),
                page_data.get("assigned_template", "modern_saas"),
                page_data.get("h1_content", ""),
                page_data.get("meta_title", ""),
                page_data.get("meta_description", ""),
                page_data.get("content_markdown", ""),
                page_data.get("content_html", ""),
                json.dumps(qs) if isinstance(qs, dict) else (qs or "{}"),
                page_data.get("word_count", 0),
                page_data.get("assigned_by", ""),
                now,
                now,
            ),
        )

    def _get_staging_page(self, page_id: int) -> dict[str, Any] | None:
        """Return a ``batch_pages`` row with JSON fields deserialised."""
        row = self.fetchone(
            "SELECT * FROM batch_pages WHERE id = ?", (page_id,)
        )
        if row is None:
            return None
        for field in ("preview_state", "quality_scores"):
            raw = row.get(field)
            if isinstance(raw, str) and raw:
                try:
                    row[field] = json.loads(raw)
                except json.JSONDecodeError:
                    row[field] = {}
            elif not raw:
                row[field] = {}
        return row

    def update_page(self, page_id: int, fields: dict[str, Any]) -> None:
        """Update arbitrary columns of a ``batch_pages`` row."""
        if not fields:
            return
        safe_cols = {
            "content_markdown", "content_html", "word_count", "quality_scores",
            "status", "preview_state", "assigned_template", "h1_content",
            "meta_title", "meta_description", "title", "slug",
        }
        set_parts: list[str] = []
        params: list[Any] = []
        for col, val in fields.items():
            if col not in safe_cols:
                continue
            if col in ("quality_scores", "preview_state") and isinstance(val, dict):
                val = json.dumps(val)
            set_parts.append(f"{col} = ?")
            params.append(val)
        if not set_parts:
            return
        set_parts.append("updated_at = ?")
        params.append(_now())
        params.append(page_id)
        self.execute(
            f"UPDATE batch_pages SET {', '.join(set_parts)} WHERE id = ?",  # noqa: S608
            tuple(params),
        )

    def bulk_update_preview_state(
        self, page_ids: list[int], patch: dict[str, Any]
    ) -> None:
        """Merge *patch* into the ``preview_state`` JSON for each page."""
        for pid in page_ids:
            row = self.fetchone(
                "SELECT preview_state FROM batch_pages WHERE id = ?", (pid,)
            )
            if row is None:
                continue
            raw = row.get("preview_state") or "{}"
            try:
                state: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                state = {}
            state.update(patch)
            self.execute(
                "UPDATE batch_pages SET preview_state = ?, updated_at = ? WHERE id = ?",
                (json.dumps(state), _now(), pid),
            )

    def bulk_set_template(self, page_ids: list[int], template: str) -> None:
        """Set ``assigned_template`` for all listed pages."""
        now = _now()
        for pid in page_ids:
            self.execute(
                "UPDATE batch_pages SET assigned_template = ?, updated_at = ? WHERE id = ?",
                (template, now, pid),
            )

    def bulk_set_status(self, page_ids: list[int], status: str) -> None:
        """Set ``status`` for all listed pages."""
        now = _now()
        for pid in page_ids:
            self.execute(
                "UPDATE batch_pages SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, pid),
            )

    def deploy_approved_pages(self, batch_id: int) -> list[dict[str, Any]]:
        """
        Mark all ``approved`` pages in *batch_id* as ``deployed``.

        Updates the batch ``pages_deployed`` counter and returns the deployed
        page records.
        """
        now = _now()
        approved = self.fetchall(
            "SELECT * FROM batch_pages WHERE batch_id = ? AND status = 'approved'",
            (batch_id,),
        )
        if not approved:
            return []
        ids = [r["id"] for r in approved]
        for pid in ids:
            self.execute(
                "UPDATE batch_pages SET status = 'deployed', updated_at = ? WHERE id = ?",
                (now, pid),
            )
        count = len(ids)
        self.execute(
            """UPDATE batches SET
                   pages_approved = MAX(0, pages_approved - ?),
                   pages_deployed = pages_deployed + ?
               WHERE id = ?""",
            (count, count, batch_id),
        )
        deployed = []
        for pid in ids:
            row = self._get_staging_page(pid)
            if row:
                deployed.append(row)
        return deployed

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------

    def create_client(self, name: str, slug: str, website: str = "") -> int:
        """
        Insert a new client record and return its id.

        Parameters
        ----------
        name:
            Human-readable client name (e.g. ``'Acme Corp'``).
        slug:
            URL-safe unique identifier (e.g. ``'acme-corp'``).
        website:
            Optional client website URL.

        Returns
        -------
        int
            The ``id`` of the newly created client row.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO clients (name, slug, website, created_at) VALUES (?,?,?,?)",
                (name, slug, website, _now()),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_client(self, client_id: int) -> dict[str, Any] | None:
        """Return a client record by id, or ``None`` if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_clients(self) -> list[dict[str, Any]]:
        """Return all clients ordered by name."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM clients ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Page management
    # ------------------------------------------------------------------

    def create_page(
        self,
        service_type_or_data: "str | dict[str, Any]",
        topic: str = "",
        primary_keyword: str = "",
        page_type: str = "landing_page",
        client_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Insert a new page record and return its id.

        When called with a *dict* as the first argument the page is inserted
        into ``batch_pages`` (staging workflow).  When called with a string
        ``service_type`` the page is inserted into the legacy ``pages`` table.

        Parameters
        ----------
        service_type_or_data:
            Either a service-category key (``str``, legacy) or a full page-
            data dict for the staging workflow.
        """
        if isinstance(service_type_or_data, dict):
            return self._create_staging_page(service_type_or_data)

        # --- Legacy path: insert into ``pages`` table ---
        service_type = service_type_or_data
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO pages
                   (client_id, service_type, topic, primary_keyword,
                    page_type, created_at, updated_at, metadata)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    client_id,
                    service_type,
                    topic,
                    primary_keyword,
                    page_type,
                    now,
                    now,
                    json.dumps(metadata or {}),
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_page(self, page_id: int) -> dict[str, Any] | None:
        """Return a page record by id, or ``None`` if not found.

        Checks ``batch_pages`` first; falls back to the legacy ``pages`` table.
        """
        staging = self._get_staging_page(page_id)
        if staging is not None:
            return staging
        # Legacy table
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM pages WHERE id = ?", (page_id,)
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d["metadata"])
            return d

    def list_pages(
        self,
        client_id: int | None = None,
        status: str | None = None,
        service_type: str | None = None,
        batch_id: int | None = None,
        template: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return pages, optionally filtered by client, status, or service type.

        When *batch_id* is provided the query is run against the staging
        ``batch_pages`` table; otherwise the legacy ``pages`` table is used.

        Parameters
        ----------
        client_id:
            Filter to a specific client (legacy path only).
        status:
            Status filter.
        service_type:
            Filter to a specific service category (legacy path only).
        batch_id:
            Staging-workflow batch filter.
        template:
            Filter by ``assigned_template`` (staging path only).

        Returns
        -------
        list[dict]
            Pages ordered by creation date descending.
        """
        if batch_id is not None:
            # Staging path
            clauses: list[str] = ["batch_id = ?"]
            params: list[Any] = [batch_id]
            if status is not None:
                clauses.append("status = ?")
                params.append(status)
            if template is not None:
                clauses.append("assigned_template = ?")
                params.append(template)
            sql = (
                "SELECT * FROM batch_pages WHERE "
                + " AND ".join(clauses)
                + " ORDER BY created_at ASC"
            )
            rows = self.fetchall(sql, tuple(params))
            result = []
            for row in rows:
                for field in ("preview_state", "quality_scores"):
                    raw = row.get(field)
                    if isinstance(raw, str) and raw:
                        try:
                            row[field] = json.loads(raw)
                        except json.JSONDecodeError:
                            row[field] = {}
                    elif not raw:
                        row[field] = {}
                result.append(row)
            return result

        # Legacy path
        legacy_clauses: list[str] = []
        legacy_params: list[Any] = []
        if client_id is not None:
            legacy_clauses.append("client_id = ?")
            legacy_params.append(client_id)
        if status is not None:
            legacy_clauses.append("status = ?")
            legacy_params.append(status)
        if service_type is not None:
            legacy_clauses.append("service_type = ?")
            legacy_params.append(service_type)

        where = ("WHERE " + " AND ".join(legacy_clauses)) if legacy_clauses else ""
        sql_legacy = f"SELECT * FROM pages {where} ORDER BY created_at DESC"  # noqa: S608

        with self._connect() as conn:
            rows_legacy = conn.execute(sql_legacy, legacy_params).fetchall()
            legacy_result = []
            for row in rows_legacy:
                d = dict(row)
                d["metadata"] = json.loads(d["metadata"])
                legacy_result.append(d)
            return legacy_result

    def update_page_status(self, page_id: int, status: str) -> None:
        """Update the status of a page and refresh ``updated_at``."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE pages SET status = ?, updated_at = ? WHERE id = ?",
                (status, _now(), page_id),
            )

    def update_page_metadata(
        self, page_id: int, metadata: dict[str, Any]
    ) -> None:
        """Merge *metadata* into the existing page metadata."""
        page = self.get_page(page_id)
        if page is None:
            raise ValueError(f"Page {page_id} not found")
        merged = {**page["metadata"], **metadata}
        with self._connect() as conn:
            conn.execute(
                "UPDATE pages SET metadata = ?, updated_at = ? WHERE id = ?",
                (json.dumps(merged), _now(), page_id),
            )

    def delete_page(self, page_id: int) -> None:
        """Delete a page from ``batch_pages`` or the legacy ``pages`` table."""
        if self._get_staging_page(page_id) is not None:
            self.execute("DELETE FROM batch_pages WHERE id = ?", (page_id,))
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))

    # ------------------------------------------------------------------
    # Content versions
    # ------------------------------------------------------------------

    def save_content_version(
        self,
        page_id: int,
        content_html: str = "",
        content_markdown: str = "",
        quality_report: dict[str, Any] | None = None,
    ) -> int:
        """
        Append a new content version for *page_id* and return its id.

        The version number is auto-incremented (1, 2, 3 …) per page.

        Parameters
        ----------
        page_id:
            Foreign key to the ``pages`` table.
        content_html:
            Rendered HTML for this version.
        content_markdown:
            Markdown source for this version.
        quality_report:
            JSON-serialisable quality report dict from the generation
            pipeline.

        Returns
        -------
        int
            The ``id`` of the newly created version row.
        """
        word_count = len(content_markdown.split()) if content_markdown else 0
        with self._connect() as conn:
            # Determine next version number
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS max_v FROM content_versions WHERE page_id = ?",
                (page_id,),
            ).fetchone()
            next_version = row["max_v"] + 1

            cur = conn.execute(
                """INSERT INTO content_versions
                   (page_id, version, content_html, content_markdown,
                    word_count, quality_report, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    page_id,
                    next_version,
                    content_html,
                    content_markdown,
                    word_count,
                    json.dumps(quality_report or {}),
                    _now(),
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_latest_version(
        self, page_id: int
    ) -> dict[str, Any] | None:
        """Return the most recent content version for *page_id*."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM content_versions
                   WHERE page_id = ?
                   ORDER BY version DESC
                   LIMIT 1""",
                (page_id,),
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["quality_report"] = json.loads(d["quality_report"])
            return d

    def list_versions(self, page_id: int) -> list[dict[str, Any]]:
        """Return all content versions for *page_id* in ascending order."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM content_versions WHERE page_id = ? ORDER BY version ASC",
                (page_id,),
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["quality_report"] = json.loads(d["quality_report"])
                result.append(d)
            return result

    # ------------------------------------------------------------------
    # Competitor cache
    # ------------------------------------------------------------------

    def cache_competitor_analysis(
        self,
        service_topic: str,
        analysis: dict[str, Any],
        ttl_hours: int = 24,
    ) -> int:
        """
        Store a competitor analysis result for *service_topic*.

        Parameters
        ----------
        service_topic:
            The service or topic that was analysed.
        analysis:
            The ``CompetitorReport`` as a plain dict.
        ttl_hours:
            Cache time-to-live in hours.  Defaults to 24.

        Returns
        -------
        int
            The ``id`` of the cache row.
        """
        from datetime import timedelta

        now = datetime.now(tz=timezone.utc)
        expires = now + timedelta(hours=ttl_hours)

        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO competitor_cache
                   (service_topic, analysis, created_at, expires_at)
                   VALUES (?,?,?,?)""",
                (
                    service_topic,
                    json.dumps(analysis),
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_competitor_analysis(
        self, service_topic: str
    ) -> dict[str, Any] | None:
        """
        Return the most recent non-expired analysis for *service_topic*, or
        ``None`` if no valid cache entry exists.
        """
        now = _now()
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM competitor_cache
                   WHERE service_topic = ? AND expires_at > ?
                   ORDER BY created_at DESC
                   LIMIT 1""",
                (service_topic, now),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row["analysis"])

    # ------------------------------------------------------------------
    # Quality scores
    # ------------------------------------------------------------------

    def save_quality_scores(
        self,
        page_id: int,
        scores: dict[str, float],
        version_id: int | None = None,
    ) -> int:
        """
        Persist multi-dimensional quality scores for a page version.

        Parameters
        ----------
        page_id:
            Foreign key to the ``pages`` table.
        scores:
            Dict with keys ``authority``, ``semantic``, ``structure``,
            ``engagement``, ``uniqueness``, ``overall`` (all floats 0–100).
        version_id:
            Optional foreign key to the ``content_versions`` table.

        Returns
        -------
        int
            The ``id`` of the quality score row.
        """
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO quality_scores
                   (page_id, version_id, authority_score, semantic_score,
                    structure_score, engagement_score, uniqueness_score,
                    overall_score, computed_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    page_id,
                    version_id,
                    scores.get("authority", 0),
                    scores.get("semantic", 0),
                    scores.get("structure", 0),
                    scores.get("engagement", 0),
                    scores.get("uniqueness", 0),
                    scores.get("overall", 0),
                    _now(),
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_latest_quality_scores(
        self, page_id: int
    ) -> dict[str, float] | None:
        """Return the most recent quality score record for *page_id*."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM quality_scores
                   WHERE page_id = ?
                   ORDER BY computed_at DESC
                   LIMIT 1""",
                (page_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "authority": row["authority_score"],
                "semantic": row["semantic_score"],
                "structure": row["structure_score"],
                "engagement": row["engagement_score"],
                "uniqueness": row["uniqueness_score"],
                "overall": row["overall_score"],
            }

    # ------------------------------------------------------------------
    # Dashboard / analytics helpers
    # ------------------------------------------------------------------

    def get_dashboard_stats(
        self, client_id: int | None = None
    ) -> dict[str, Any]:
        """
        Return aggregate statistics for the dashboard.

        Parameters
        ----------
        client_id:
            When supplied, stats are scoped to this client only.

        Returns
        -------
        dict
            Keys: ``total_pages``, ``published_pages``, ``draft_pages``,
            ``review_pages``, ``total_words``, ``avg_quality_score``.
        """
        client_filter = "WHERE p.client_id = ?" if client_id is not None else ""
        params: list[Any] = [client_id] if client_id is not None else []

        with self._connect() as conn:
            row = conn.execute(
                f"""SELECT
                    COUNT(DISTINCT p.id)                         AS total_pages,
                    SUM(CASE WHEN p.status='published' THEN 1 ELSE 0 END) AS published_pages,
                    SUM(CASE WHEN p.status='draft'     THEN 1 ELSE 0 END) AS draft_pages,
                    SUM(CASE WHEN p.status='review'    THEN 1 ELSE 0 END) AS review_pages,
                    COALESCE(SUM(cv.word_count), 0)              AS total_words
                FROM pages p
                LEFT JOIN content_versions cv
                    ON cv.id = (
                        SELECT id FROM content_versions
                        WHERE page_id = p.id
                        ORDER BY version DESC LIMIT 1
                    )
                {client_filter}""",
                params,
            ).fetchone()

            q_row = conn.execute(
                f"""SELECT AVG(qs.overall_score) AS avg_quality
                FROM quality_scores qs
                JOIN pages p ON p.id = qs.page_id
                {client_filter}""",
                params,
            ).fetchone()

        avg_quality = q_row["avg_quality"] if q_row and q_row["avg_quality"] else 0.0
        return {
            "total_pages": row["total_pages"] or 0,
            "published_pages": row["published_pages"] or 0,
            "draft_pages": row["draft_pages"] or 0,
            "review_pages": row["review_pages"] or 0,
            "total_words": row["total_words"] or 0,
            "avg_quality_score": round(avg_quality, 1),
        }
