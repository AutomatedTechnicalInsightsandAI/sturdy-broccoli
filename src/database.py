"""
database.py

SQLite persistence layer for the SEO Site Factory.

Manages three primary tables:
  - pages       — individual generated landing pages with full lifecycle tracking
  - batches     — groups of pages generated together
  - templates   — Tailwind CSS layout templates

Schema mirrors the specification in the problem statement, using SQLite's
built-in JSON1 extension for JSON columns.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

# ---------------------------------------------------------------------------
# Default database path
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "seo_factory.db"

# ---------------------------------------------------------------------------
# Thread-local connection cache
# ---------------------------------------------------------------------------

_local = threading.local()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS batches (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    description          TEXT DEFAULT '',
    total_pages          INTEGER DEFAULT 0,
    pages_pending        INTEGER DEFAULT 0,
    pages_reviewed       INTEGER DEFAULT 0,
    pages_approved       INTEGER DEFAULT 0,
    pages_deployed       INTEGER DEFAULT 0,
    created_at           TEXT NOT NULL,
    created_by           TEXT DEFAULT 'user',
    scheduled_deploy_at  TEXT,
    deployed_at          TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id             INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    title                TEXT NOT NULL,
    slug                 TEXT UNIQUE NOT NULL,
    topic                TEXT NOT NULL,
    primary_keyword      TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'pending_review'
                             CHECK(status IN ('pending_review','reviewed','approved','deployed','archived')),
    preview_state        TEXT DEFAULT '{}',
    assigned_template    TEXT NOT NULL DEFAULT 'modern_saas'
                             CHECK(assigned_template IN ('modern_saas','professional_service',
                                                         'content_guide','ecommerce','enterprise')),
    h1_content           TEXT DEFAULT '',
    meta_title           TEXT DEFAULT '',
    meta_description     TEXT DEFAULT '',
    content_markdown     TEXT DEFAULT '',
    content_html         TEXT DEFAULT '',
    quality_scores       TEXT DEFAULT '{}',
    word_count           INTEGER DEFAULT 0,
    assigned_by          TEXT DEFAULT 'system',
    created_at           TEXT NOT NULL,
    last_reviewed_at     TEXT,
    deployed_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_pages_batch_id ON pages(batch_id);
CREATE INDEX IF NOT EXISTS idx_pages_status   ON pages(status);
CREATE INDEX IF NOT EXISTS idx_pages_template ON pages(assigned_template);

CREATE TABLE IF NOT EXISTS competitor_analysis (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id                  INTEGER REFERENCES pages(id) ON DELETE CASCADE,
    competitor_url           TEXT DEFAULT '',
    competitor_h1            TEXT DEFAULT '',
    competitor_structure     TEXT DEFAULT '[]',
    competitor_quality_signals TEXT DEFAULT '[]',
    analysis_timestamp       TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------


class Database:
    """Thin wrapper around a SQLite connection."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._init_schema()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if not getattr(_local, "conn", None) or getattr(_local, "db_path", None) != str(self._path):
            conn = sqlite3.connect(str(self._path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            _local.conn = conn
            _local.db_path = str(self._path)
        return _local.conn

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _init_schema(self) -> None:
        conn = self._connect()
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        d = dict(row)
        # Decode JSON columns
        for col in ("preview_state", "quality_scores", "competitor_structure", "competitor_quality_signals"):
            if col in d and isinstance(d[col], str):
                try:
                    d[col] = json.loads(d[col])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def create_batch(
        self,
        name: str,
        description: str = "",
        created_by: str = "user",
        scheduled_deploy_at: str | None = None,
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO batches
                   (name, description, created_by, scheduled_deploy_at, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, description, created_by, scheduled_deploy_at, _utcnow()),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_batch(self, batch_id: int) -> dict[str, Any] | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
            return self._row_to_dict(cur.fetchone())

    def list_batches(self) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM batches ORDER BY created_at DESC")
            return [self._row_to_dict(r) for r in cur.fetchall()]  # type: ignore[misc]

    def update_batch_counts(self, batch_id: int) -> None:
        """Recompute page-status counters on the batch row."""
        with self._cursor() as cur:
            cur.execute(
                """UPDATE batches SET
                    total_pages     = (SELECT COUNT(*)  FROM pages WHERE batch_id = ?),
                    pages_pending   = (SELECT COUNT(*)  FROM pages WHERE batch_id = ? AND status = 'pending_review'),
                    pages_reviewed  = (SELECT COUNT(*)  FROM pages WHERE batch_id = ? AND status = 'reviewed'),
                    pages_approved  = (SELECT COUNT(*)  FROM pages WHERE batch_id = ? AND status = 'approved'),
                    pages_deployed  = (SELECT COUNT(*)  FROM pages WHERE batch_id = ? AND status = 'deployed')
                WHERE id = ?""",
                (batch_id,) * 5 + (batch_id,),
            )

    def mark_batch_deployed(self, batch_id: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE batches SET deployed_at = ? WHERE id = ?",
                (_utcnow(), batch_id),
            )

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    def create_page(self, data: dict[str, Any]) -> int:
        now = _utcnow()
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO pages
                   (batch_id, title, slug, topic, primary_keyword,
                    status, preview_state, assigned_template,
                    h1_content, meta_title, meta_description,
                    content_markdown, content_html,
                    quality_scores, word_count,
                    assigned_by, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data.get("batch_id"),
                    data.get("title", ""),
                    data.get("slug", ""),
                    data.get("topic", ""),
                    data.get("primary_keyword", ""),
                    data.get("status", "pending_review"),
                    json.dumps(data.get("preview_state", {})),
                    data.get("assigned_template", "modern_saas"),
                    data.get("h1_content", ""),
                    data.get("meta_title", ""),
                    data.get("meta_description", ""),
                    data.get("content_markdown", ""),
                    data.get("content_html", ""),
                    json.dumps(data.get("quality_scores", {})),
                    data.get("word_count", 0),
                    data.get("assigned_by", "system"),
                    now,
                ),
            )
            page_id = cur.lastrowid
        if data.get("batch_id"):
            self.update_batch_counts(data["batch_id"])
        return page_id  # type: ignore[return-value]

    def get_page(self, page_id: int) -> dict[str, Any] | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
            return self._row_to_dict(cur.fetchone())

    def list_pages(
        self,
        batch_id: int | None = None,
        status: str | None = None,
        template: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if batch_id is not None:
            clauses.append("batch_id = ?")
            params.append(batch_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if template:
            clauses.append("assigned_template = ?")
            params.append(template)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._cursor() as cur:
            cur.execute(f"SELECT * FROM pages {where} ORDER BY created_at ASC", params)
            return [self._row_to_dict(r) for r in cur.fetchall()]  # type: ignore[misc]

    def update_page(self, page_id: int, updates: dict[str, Any]) -> None:
        """Partial update — only supplied keys are written."""
        allowed = {
            "title", "slug", "topic", "primary_keyword", "status",
            "preview_state", "assigned_template",
            "h1_content", "meta_title", "meta_description",
            "content_markdown", "content_html",
            "quality_scores", "word_count", "assigned_by",
            "last_reviewed_at", "deployed_at",
        }
        cols: list[str] = []
        vals: list[Any] = []
        for k, v in updates.items():
            if k not in allowed:
                continue
            cols.append(f"{k} = ?")
            if k in ("preview_state", "quality_scores") and isinstance(v, dict):
                vals.append(json.dumps(v))
            else:
                vals.append(v)
        if not cols:
            return
        vals.append(page_id)
        with self._cursor() as cur:
            cur.execute(f"UPDATE pages SET {', '.join(cols)} WHERE id = ?", vals)
        # Refresh batch counters if status changed
        if "status" in updates:
            page = self.get_page(page_id)
            if page and page.get("batch_id"):
                self.update_batch_counts(page["batch_id"])

    def set_page_status(self, page_id: int, status: str) -> None:
        now = _utcnow()
        extra: dict[str, Any] = {"status": status}
        if status == "reviewed":
            extra["last_reviewed_at"] = now
        elif status == "deployed":
            extra["deployed_at"] = now
        self.update_page(page_id, extra)

    def bulk_set_status(self, page_ids: list[int], status: str) -> None:
        for pid in page_ids:
            self.set_page_status(pid, status)

    def bulk_update_preview_state(
        self, page_ids: list[int], patch: dict[str, Any]
    ) -> None:
        """Merge *patch* into each page's preview_state JSON."""
        for pid in page_ids:
            page = self.get_page(pid)
            if not page:
                continue
            state = page.get("preview_state") or {}
            if isinstance(state, str):
                try:
                    state = json.loads(state)
                except json.JSONDecodeError:
                    state = {}
            state.update(patch)
            self.update_page(pid, {"preview_state": state})

    def bulk_set_template(self, page_ids: list[int], template: str) -> None:
        for pid in page_ids:
            self.update_page(pid, {"assigned_template": template})

    def deploy_approved_pages(self, batch_id: int) -> list[dict[str, Any]]:
        """Mark all approved pages in a batch as deployed; return them."""
        pages = self.list_pages(batch_id=batch_id, status="approved")
        for page in pages:
            self.set_page_status(page["id"], "deployed")
        self.mark_batch_deployed(batch_id)
        self.update_batch_counts(batch_id)
        return pages

    def delete_page(self, page_id: int) -> None:
        page = self.get_page(page_id)
        with self._cursor() as cur:
            cur.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        if page and page.get("batch_id"):
            self.update_batch_counts(page["batch_id"])
