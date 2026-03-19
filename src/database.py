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
        service_type: str,
        topic: str,
        primary_keyword: str = "",
        page_type: str = "landing_page",
        client_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Insert a new page record and return its id.

        Parameters
        ----------
        service_type:
            Service category key (e.g. ``'local_seo'``).
        topic:
            Human-readable page topic.
        primary_keyword:
            Target SEO keyword for this page.
        page_type:
            One of ``'landing_page'``, ``'blog_post'``, ``'case_study'``.
        client_id:
            Optional foreign key to the ``clients`` table.
        metadata:
            Arbitrary JSON-serialisable metadata.

        Returns
        -------
        int
            The ``id`` of the newly created page row.
        """
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
        """Return a page record by id, or ``None`` if not found."""
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
    ) -> list[dict[str, Any]]:
        """
        Return pages, optionally filtered by client, status, or service type.

        Parameters
        ----------
        client_id:
            Filter to a specific client.
        status:
            Filter to ``'draft'``, ``'review'``, ``'published'``, or
            ``'archived'``.
        service_type:
            Filter to a specific service category.

        Returns
        -------
        list[dict]
            Pages ordered by creation date descending.
        """
        clauses: list[str] = []
        params: list[Any] = []

        if client_id is not None:
            clauses.append("client_id = ?")
            params.append(client_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if service_type is not None:
            clauses.append("service_type = ?")
            params.append(service_type)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM pages {where} ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["metadata"] = json.loads(d["metadata"])
                result.append(d)
            return result

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
        """Delete a page and all its associated content versions and scores."""
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
