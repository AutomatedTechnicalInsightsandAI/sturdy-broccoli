"""
staging_review.py

Business logic for the Staging & Review Workflow.

Responsibilities
~~~~~~~~~~~~~~~~
- Batch and page CRUD
- Review-status lifecycle (draft → approved / needs_revision / rejected → deployed)
- Quality-score management
- Bulk branding updates (primary colour, logo, CTA text/link, font)
- Hub-and-spoke internal-link validation and SILO checks
- Pre-flight checks before deployment
- HTML + metadata CSV export

All persistence is delegated to :class:`~src.database.Database`.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from typing import Any

from .database import Database

logger = logging.getLogger(__name__)

# Valid review statuses
VALID_STATUSES = frozenset({"draft", "approved", "needs_revision", "rejected", "deployed"})

# Quality thresholds for pre-flight checks
MIN_QUALITY_SCORE_FOR_DEPLOY = 75


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slugify(text: str) -> str:
    """Convert a page title to a URL-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug[:80]


def _render_page_html(page: dict[str, Any], template_html: str) -> str:
    """Substitute template placeholders with page field values."""
    html = template_html
    html = html.replace("{{h1}}", page.get("h1_content") or page.get("title") or "")
    html = html.replace("{{meta_description}}", page.get("meta_description") or "")
    html = html.replace("{{cta_text}}", page.get("cta_text_override") or "Get Started Today")
    html = html.replace("{{cta_link}}", page.get("cta_link_override") or "#contact")

    # Very light Markdown → HTML for content body
    content_md = page.get("content_markdown") or ""
    content_html = _md_to_html(content_md)
    html = html.replace("{{content}}", content_html)

    # Apply brand colour override via inline style injection
    brand_color = page.get("brand_color_override") or ""
    if brand_color:
        html = html.replace("bg-blue-600", "").replace(
            "bg-blue-500", ""
        )
        html = html.replace(
            "<style>",
            f"<style>:root{{--brand-color:{brand_color};}}",
        )
    return html


def _md_to_html(markdown: str) -> str:
    """Minimal Markdown → HTML conversion (headings, bold, bullets, paragraphs)."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_ul = False
    for line in lines:
        if line.startswith("### "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{line[2:]}</li>")
        elif line.strip() == "":
            if in_ul:
                out.append("</ul>")
                in_ul = False
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<p>{line}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# StagingReviewManager
# ---------------------------------------------------------------------------


class StagingReviewManager:
    """
    Facade for all staging-and-review operations.

    Parameters
    ----------
    db:
        A :class:`~src.database.Database` instance.  The caller is
        responsible for calling ``db.init_schema()`` before use.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def create_batch(
        self,
        name: str,
        description: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        """Create a new batch and return its record."""
        row_id = self._db.lastrowid(
            "INSERT INTO batches (name, description, created_by) VALUES (?, ?, ?)",
            (name, description, created_by),
        )
        batch = self._db.fetchone("SELECT * FROM batches WHERE id = ?", (row_id,))
        assert batch is not None
        return batch

    def get_batch(self, batch_id: int) -> dict[str, Any] | None:
        return self._db.fetchone("SELECT * FROM batches WHERE id = ?", (batch_id,))

    def list_batches(self) -> list[dict[str, Any]]:
        return self._db.fetchall("SELECT * FROM batches ORDER BY created_at DESC")

    def update_batch_branding(
        self,
        batch_id: int,
        primary_color: str | None = None,
        logo_url: str | None = None,
        font_family: str | None = None,
        global_cta_text: str | None = None,
        global_cta_link: str | None = None,
    ) -> dict[str, Any]:
        """
        Update the batch-level branding fields.

        Only non-``None`` arguments are written to the database.
        """
        fields: list[str] = []
        params: list[Any] = []

        if primary_color is not None:
            fields.append("batch_primary_color = ?")
            params.append(primary_color)
        if logo_url is not None:
            fields.append("batch_logo_url = ?")
            params.append(logo_url)
        if font_family is not None:
            fields.append("batch_font_family = ?")
            params.append(font_family)
        if global_cta_text is not None:
            fields.append("batch_global_cta_text = ?")
            params.append(global_cta_text)
        if global_cta_link is not None:
            fields.append("batch_global_cta_link = ?")
            params.append(global_cta_link)

        if not fields:
            batch = self.get_batch(batch_id)
            assert batch is not None
            return batch

        params.append(batch_id)
        self._db.execute(
            f"UPDATE batches SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
            tuple(params),
        )
        self._db.commit()
        batch = self.get_batch(batch_id)
        assert batch is not None
        return batch

    # ------------------------------------------------------------------
    # Page CRUD
    # ------------------------------------------------------------------

    def add_page(
        self,
        batch_id: int,
        title: str,
        h1_content: str = "",
        meta_title: str = "",
        meta_description: str = "",
        content_markdown: str = "",
        template_name: str = "modern_saas",
        quality_scores: dict[str, Any] | None = None,
        competitor_benchmark: str = "",
        hub_page_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Insert a new content page into a batch.

        Returns the newly created page record.
        """
        slug = _slugify(title)
        # Ensure slug uniqueness by appending a suffix
        existing = self._db.fetchone(
            "SELECT id FROM content_pages WHERE slug = ?", (slug,)
        )
        if existing:
            slug = f"{slug}-{batch_id}"

        tmpl = self._db.fetchone(
            "SELECT id FROM templates WHERE name = ?", (template_name,)
        )
        template_id = tmpl["id"] if tmpl else None

        scores_json = json.dumps(quality_scores or {})

        row_id = self._db.lastrowid(
            """
            INSERT INTO content_pages
                (batch_id, title, slug, h1_content, meta_title, meta_description,
                 content_markdown, template_id, quality_scores, competitor_benchmark,
                 hub_page_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                title,
                slug,
                h1_content,
                meta_title,
                meta_description,
                content_markdown,
                template_id,
                scores_json,
                competitor_benchmark,
                hub_page_id,
            ),
        )

        # Update batch page counts
        self._db.execute(
            "UPDATE batches SET total_pages = total_pages + 1, pages_draft = pages_draft + 1 WHERE id = ?",
            (batch_id,),
        )
        self._db.commit()

        page = self._db.fetchone("SELECT * FROM content_pages WHERE id = ?", (row_id,))
        assert page is not None
        return self._enrich_page(page)

    def get_page(self, page_id: int) -> dict[str, Any] | None:
        page = self._db.fetchone(
            "SELECT * FROM content_pages WHERE id = ?", (page_id,)
        )
        return self._enrich_page(page) if page else None

    def get_batch_pages(
        self,
        batch_id: int,
        status_filter: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "ASC",
        min_quality: float | None = None,
        template_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return pages for a batch with optional filtering and sorting.

        Parameters
        ----------
        sort_by:
            ``'created_at'``, ``'review_status'``, ``'title'``, or
            ``'quality_overall'`` (computed from JSON field).
        min_quality:
            When provided, only pages whose ``quality_scores.overall``
            is at or above this threshold are returned.
        """
        # Validate and map sort column; only pre-approved column names are used
        # in the ORDER BY clause, preventing SQL injection.
        _SORT_COL_MAP = {
            "created_at":      "created_at",
            "review_status":   "review_status",
            "title":           "title",
            "last_modified_at": "last_modified_at",
        }
        safe_sort_col = _SORT_COL_MAP.get(sort_by, "created_at")
        sort_dir = "DESC" if sort_dir.upper() == "DESC" else "ASC"

        sql = "SELECT * FROM content_pages WHERE batch_id = ?"
        params: list[Any] = [batch_id]

        if status_filter and status_filter in VALID_STATUSES:
            sql += " AND review_status = ?"
            params.append(status_filter)

        if template_name:
            tmpl = self._db.fetchone(
                "SELECT id FROM templates WHERE name = ?", (template_name,)
            )
            if tmpl:
                sql += " AND template_id = ?"
                params.append(tmpl["id"])

        sql += f" ORDER BY {safe_sort_col} {sort_dir}"  # noqa: S608

        pages = self._db.fetchall(sql, tuple(params))
        enriched = [self._enrich_page(p) for p in pages]

        if min_quality is not None:
            enriched = [
                p
                for p in enriched
                if p.get("quality_scores", {}).get("overall", 0) >= min_quality
            ]

        return enriched

    def update_page_content(
        self,
        page_id: int,
        h1_content: str | None = None,
        meta_title: str | None = None,
        meta_description: str | None = None,
        content_markdown: str | None = None,
        changed_by: str = "",
        change_reason: str = "",
    ) -> dict[str, Any]:
        """
        Update editable content fields and save a revision record.
        """
        page = self.get_page(page_id)
        if page is None:
            raise ValueError(f"Page {page_id} not found")

        fields: list[str] = ["last_modified_at = ?"]
        params: list[Any] = [_now_iso()]

        if h1_content is not None:
            fields.append("h1_content = ?")
            params.append(h1_content)
        if meta_title is not None:
            fields.append("meta_title = ?")
            params.append(meta_title)
        if meta_description is not None:
            fields.append("meta_description = ?")
            params.append(meta_description)
        if content_markdown is not None:
            fields.append("content_markdown = ?")
            params.append(content_markdown)

        params.append(page_id)
        self._db.execute(
            f"UPDATE content_pages SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
            tuple(params),
        )

        # Save revision
        revision_content = content_markdown if content_markdown is not None else page.get("content_markdown", "")
        rev_count = self._db.fetchone(
            "SELECT COUNT(*) AS cnt FROM page_revisions WHERE page_id = ?", (page_id,)
        )
        revision_number = (rev_count["cnt"] if rev_count else 0) + 1
        self._db.execute(
            """
            INSERT INTO page_revisions
                (page_id, revision_number, content_markdown, changed_by, change_reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (page_id, revision_number, revision_content, changed_by, change_reason),
        )
        self._db.commit()

        updated = self.get_page(page_id)
        assert updated is not None
        return updated

    def update_page_status(
        self,
        page_id: int,
        status: str,
        reviewer_notes: str = "",
        reviewed_by: str = "",
    ) -> dict[str, Any]:
        """
        Transition a page to a new review status.

        Raises :class:`ValueError` for invalid statuses.
        """
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}"
            )

        page = self.get_page(page_id)
        if page is None:
            raise ValueError(f"Page {page_id} not found")

        old_status = page["review_status"]
        now = _now_iso()

        self._db.execute(
            """
            UPDATE content_pages
               SET review_status  = ?,
                   reviewer_notes = ?,
                   reviewed_by    = ?,
                   reviewed_at    = ?,
                   last_modified_at = ?,
                   deployed_at    = CASE WHEN ? = 'deployed' THEN ? ELSE deployed_at END
             WHERE id = ?
            """,
            (status, reviewer_notes, reviewed_by, now, now, status, now, page_id),
        )

        # Keep batch counters in sync.
        # Column names are drawn exclusively from this validated mapping;
        # the construction below is safe against injection.
        batch_id = page["batch_id"]
        _COUNTER_COLS = {
            "draft":          "pages_draft",
            "approved":       "pages_approved",
            "deployed":       "pages_deployed",
            "rejected":       "pages_rejected",
            "needs_revision": "pages_draft",
        }
        _ALLOWED_BATCH_COLS = frozenset(_COUNTER_COLS.values())
        old_col = _COUNTER_COLS.get(old_status)
        new_col = _COUNTER_COLS.get(status)
        if old_col and new_col and old_col != new_col:
            # Both column names come from _COUNTER_COLS (all hardcoded),
            # so f-string interpolation is safe here.
            assert old_col in _ALLOWED_BATCH_COLS  # defensive check
            assert new_col in _ALLOWED_BATCH_COLS  # defensive check
            self._db.execute(
                f"UPDATE batches SET {old_col} = MAX(0, {old_col} - 1), "  # noqa: S608
                f"{new_col} = {new_col} + 1 WHERE id = ?",
                (batch_id,),
            )
        self._db.commit()

        updated = self.get_page(page_id)
        assert updated is not None
        return updated

    def bulk_update_status(
        self,
        page_ids: list[int],
        status: str,
        reviewer_notes: str = "",
        reviewed_by: str = "",
    ) -> list[dict[str, Any]]:
        """Apply the same status to a list of pages."""
        return [
            self.update_page_status(pid, status, reviewer_notes, reviewed_by)
            for pid in page_ids
        ]

    def delete_page(self, page_id: int) -> None:
        """
        Permanently remove a page and update the owning batch counter.

        Raises :class:`ValueError` if the page does not exist.
        """
        page = self.get_page(page_id)
        if page is None:
            raise ValueError(f"Page {page_id} not found")
        batch_id = page["batch_id"]
        self._db.execute(
            "DELETE FROM content_pages WHERE id = ?", (page_id,)
        )
        self._db.execute(
            "UPDATE batches SET total_pages = MAX(0, total_pages - 1) WHERE id = ?",
            (batch_id,),
        )
        self._db.commit()

    def apply_branding_to_pages(
        self,
        page_ids: list[int],
        brand_color: str | None = None,
        logo_url: str | None = None,
        cta_text: str | None = None,
        cta_link: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Push per-page styling overrides to a list of pages.

        Fields that are ``None`` are left unchanged.
        """
        results: list[dict[str, Any]] = []
        for pid in page_ids:
            fields: list[str] = ["last_modified_at = ?"]
            params: list[Any] = [_now_iso()]

            if brand_color is not None:
                fields.append("brand_color_override = ?")
                params.append(brand_color)
            if logo_url is not None:
                fields.append("custom_logo_url = ?")
                params.append(logo_url)
            if cta_text is not None:
                fields.append("cta_text_override = ?")
                params.append(cta_text)
            if cta_link is not None:
                fields.append("cta_link_override = ?")
                params.append(cta_link)

            params.append(pid)
            self._db.execute(
                f"UPDATE content_pages SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
                tuple(params),
            )
        self._db.commit()

        for pid in page_ids:
            page = self.get_page(pid)
            if page:
                results.append(page)
        return results

    def switch_template(self, page_id: int, template_name: str) -> dict[str, Any]:
        """Switch the rendering template for a page."""
        tmpl = self._db.fetchone(
            "SELECT id FROM templates WHERE name = ?", (template_name,)
        )
        if tmpl is None:
            raise ValueError(f"Template '{template_name}' not found")
        self._db.execute(
            "UPDATE content_pages SET template_id = ?, last_modified_at = ? WHERE id = ?",
            (tmpl["id"], _now_iso(), page_id),
        )
        self._db.commit()
        page = self.get_page(page_id)
        assert page is not None
        return page

    # ------------------------------------------------------------------
    # Quality scores
    # ------------------------------------------------------------------

    def update_quality_scores(
        self,
        page_id: int,
        scores: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Persist quality scores for a page.

        *scores* should contain keys: ``authority``, ``semantic``,
        ``structure``, ``engagement``, ``uniqueness``.  The ``overall``
        key is computed as the mean if not supplied.
        """
        metric_keys = ["authority", "semantic", "structure", "engagement", "uniqueness"]
        if "overall" not in scores:
            vals = [scores.get(k, 0) for k in metric_keys if isinstance(scores.get(k), (int, float))]
            scores["overall"] = round(sum(vals) / len(vals), 1) if vals else 0.0

        self._db.execute(
            "UPDATE content_pages SET quality_scores = ?, last_modified_at = ? WHERE id = ?",
            (json.dumps(scores), _now_iso(), page_id),
        )
        self._db.commit()
        page = self.get_page(page_id)
        assert page is not None
        return page

    # ------------------------------------------------------------------
    # Hub-and-spoke internal link validation
    # ------------------------------------------------------------------

    def set_hub_spoke_relationship(
        self,
        spoke_page_id: int,
        hub_page_id: int,
    ) -> dict[str, Any]:
        """Mark a page as a spoke of a hub page."""
        self._db.execute(
            "UPDATE content_pages SET hub_page_id = ?, last_modified_at = ? WHERE id = ?",
            (hub_page_id, _now_iso(), spoke_page_id),
        )
        self._db.commit()
        page = self.get_page(spoke_page_id)
        assert page is not None
        return page

    def add_internal_link(
        self,
        from_page_id: int,
        to_page_id: int,
        anchor_text: str,
        status: str = "linked",
    ) -> None:
        """
        Add or update a single internal link record on a page.

        *status* should be ``'linked'``, ``'weak'``, or ``'missing'``.
        """
        page = self.get_page(from_page_id)
        if page is None:
            raise ValueError(f"Page {from_page_id} not found")
        links_data = page.get("internal_links") or {"links": []}
        links = links_data.get("links", [])

        # Update existing or append
        for link in links:
            if link.get("to_page_id") == to_page_id:
                link["anchor_text"] = anchor_text
                link["status"] = status
                break
        else:
            links.append(
                {"to_page_id": to_page_id, "anchor_text": anchor_text, "status": status}
            )

        links_data["links"] = links
        self._db.execute(
            "UPDATE content_pages SET internal_links = ?, last_modified_at = ? WHERE id = ?",
            (json.dumps(links_data), _now_iso(), from_page_id),
        )
        self._db.commit()

    def validate_hub_spoke_links(self, batch_id: int) -> dict[str, Any]:
        """
        Validate the hub-and-spoke link structure for a batch.

        Returns a report with:
        - ``hub_pages``: list of hub page summaries
        - ``spoke_pages``: list of spoke summaries with link status
        - ``issues``: list of actionable problems (missing/weak links)
        - ``silo_violations``: spokes that link outside their cluster
        """
        pages = self.get_batch_pages(batch_id)

        # Build lookup
        page_map: dict[int, dict[str, Any]] = {p["id"]: p for p in pages}

        # Identify hubs (hub_page_id is NULL) and spokes
        hub_pages = [p for p in pages if p.get("hub_page_id") is None]
        spoke_pages = [p for p in pages if p.get("hub_page_id") is not None]

        issues: list[dict[str, Any]] = []
        silo_violations: list[dict[str, Any]] = []
        link_statuses: list[dict[str, Any]] = []

        for spoke in spoke_pages:
            hub_id = spoke["hub_page_id"]
            hub = page_map.get(hub_id)
            spoke_links = (spoke.get("internal_links") or {}).get("links", [])
            spoke_link_targets = {lk["to_page_id"] for lk in spoke_links}

            # Check spoke → hub link
            if hub_id not in spoke_link_targets:
                issues.append(
                    {
                        "type": "missing_spoke_to_hub",
                        "severity": "red",
                        "spoke_id": spoke["id"],
                        "spoke_title": spoke["title"],
                        "hub_id": hub_id,
                        "hub_title": hub["title"] if hub else f"Page {hub_id}",
                        "message": f"'{spoke['title']}' → Hub: Missing (SILO broken!)",
                    }
                )
            else:
                anchor = next(
                    (lk["anchor_text"] for lk in spoke_links if lk["to_page_id"] == hub_id),
                    "",
                )
                link_statuses.append(
                    {
                        "from_title": spoke["title"],
                        "to_title": hub["title"] if hub else f"Page {hub_id}",
                        "direction": "spoke → hub",
                        "anchor": anchor,
                        "status": "linked",
                    }
                )

            # Check hub → spoke link
            if hub:
                hub_links = (hub.get("internal_links") or {}).get("links", [])
                hub_link_targets = {lk["to_page_id"] for lk in hub_links}
                if spoke["id"] not in hub_link_targets:
                    issues.append(
                        {
                            "type": "missing_hub_to_spoke",
                            "severity": "yellow",
                            "hub_id": hub_id,
                            "hub_title": hub["title"],
                            "spoke_id": spoke["id"],
                            "spoke_title": spoke["title"],
                            "message": f"Hub → '{spoke['title']}': Not linked",
                        }
                    )
                else:
                    anchor = next(
                        (lk["anchor_text"] for lk in hub_links if lk["to_page_id"] == spoke["id"]),
                        "",
                    )
                    link_statuses.append(
                        {
                            "from_title": hub["title"],
                            "to_title": spoke["title"],
                            "direction": "hub → spoke",
                            "anchor": anchor,
                            "status": "linked",
                        }
                    )

            # SILO violation: spoke links to a page in a different hub cluster
            if hub:
                sibling_hub_ids = {p["id"] for p in spoke_pages if p.get("hub_page_id") == hub_id}
                sibling_hub_ids.add(hub_id)
                for lk in spoke_links:
                    target_id = lk["to_page_id"]
                    if target_id not in sibling_hub_ids and target_id in page_map:
                        target = page_map[target_id]
                        target_hub = target.get("hub_page_id")
                        if target_hub is not None and target_hub != hub_id:
                            silo_violations.append(
                                {
                                    "spoke_id": spoke["id"],
                                    "spoke_title": spoke["title"],
                                    "target_id": target_id,
                                    "target_title": target["title"],
                                    "message": f"'{spoke['title']}' crosses silo boundary to '{target['title']}'",
                                }
                            )

        return {
            "batch_id": batch_id,
            "hub_pages": [
                {"id": h["id"], "title": h["title"], "spoke_count": sum(1 for s in spoke_pages if s.get("hub_page_id") == h["id"])}
                for h in hub_pages
            ],
            "spoke_pages": [
                {"id": s["id"], "title": s["title"], "hub_id": s.get("hub_page_id")}
                for s in spoke_pages
            ],
            "link_statuses": link_statuses,
            "issues": issues,
            "silo_violations": silo_violations,
            "is_healthy": len(issues) == 0 and len(silo_violations) == 0,
        }

    # ------------------------------------------------------------------
    # Pre-flight checks and deployment
    # ------------------------------------------------------------------

    def run_preflight_checks(self, page_ids: list[int]) -> dict[str, Any]:
        """
        Run deployment pre-flight checks on a list of pages.

        Returns a dict with ``passed`` (bool), ``checks`` (list of per-check
        results), and ``blocking_issues`` (list of strings).
        """
        pages = [self.get_page(pid) for pid in page_ids]
        pages_found = [p for p in pages if p is not None]

        checks: list[dict[str, Any]] = []
        blocking: list[str] = []

        # 1 — All pages have H1
        missing_h1 = [p["title"] for p in pages_found if not (p.get("h1_content") or "").strip()]
        checks.append(
            {
                "name": "All pages have H1",
                "passed": len(missing_h1) == 0,
                "detail": f"Missing H1: {missing_h1}" if missing_h1 else "✅ All pages have H1",
            }
        )
        if missing_h1:
            blocking.append(f"{len(missing_h1)} page(s) missing H1")

        # 2 — All pages have meta description
        missing_meta = [p["title"] for p in pages_found if not (p.get("meta_description") or "").strip()]
        checks.append(
            {
                "name": "All pages have meta description",
                "passed": len(missing_meta) == 0,
                "detail": f"Missing meta: {missing_meta}" if missing_meta else "✅ All pages have meta description",
            }
        )
        if missing_meta:
            blocking.append(f"{len(missing_meta)} page(s) missing meta description")

        # 3 — Quality score > threshold
        low_quality = [
            p["title"]
            for p in pages_found
            if (p.get("quality_scores") or {}).get("overall", 0) < MIN_QUALITY_SCORE_FOR_DEPLOY
            and (p.get("quality_scores") or {}).get("overall", 0) > 0
        ]
        checks.append(
            {
                "name": f"All pages quality score > {MIN_QUALITY_SCORE_FOR_DEPLOY}",
                "passed": len(low_quality) == 0,
                "detail": f"Low quality: {low_quality}" if low_quality else f"✅ All pages above {MIN_QUALITY_SCORE_FOR_DEPLOY}",
            }
        )
        if low_quality:
            blocking.append(f"{len(low_quality)} page(s) below quality threshold")

        # 4 — All pages are 'approved'
        not_approved = [
            p["title"]
            for p in pages_found
            if p.get("review_status") != "approved"
        ]
        checks.append(
            {
                "name": "All pages approved",
                "passed": len(not_approved) == 0,
                "detail": f"Not approved: {not_approved}" if not_approved else "✅ All pages approved",
            }
        )
        if not_approved:
            blocking.append(f"{len(not_approved)} page(s) not yet approved")

        return {
            "passed": len(blocking) == 0,
            "checks": checks,
            "blocking_issues": blocking,
            "page_count": len(pages_found),
        }

    def deploy_pages(self, page_ids: list[int], deployed_by: str = "") -> dict[str, Any]:
        """
        Mark pages as deployed and return a ZIP bundle (HTML + CSV).

        The ZIP bytes are returned under the ``"zip_bytes"`` key so the
        caller can offer them as a download.  The ``"deployed_pages"`` key
        contains the updated page records.
        """
        deployed: list[dict[str, Any]] = []

        zip_buf = io.BytesIO()
        csv_rows: list[dict[str, str]] = []

        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for pid in page_ids:
                page = self.get_page(pid)
                if page is None:
                    continue

                # Fetch template HTML
                tmpl_html = ""
                if page.get("template_id"):
                    tmpl_row = self._db.fetchone(
                        "SELECT template_html FROM templates WHERE id = ?",
                        (page["template_id"],),
                    )
                    if tmpl_row:
                        tmpl_html = tmpl_row["template_html"] or ""

                html = _render_page_html(page, tmpl_html)
                slug = page.get("slug") or f"page-{pid}"
                zf.writestr(f"{slug}.html", html)

                # Mark as deployed
                self.update_page_status(pid, "deployed", reviewed_by=deployed_by)
                updated = self.get_page(pid)
                assert updated is not None
                deployed.append(updated)

                scores = updated.get("quality_scores") or {}
                csv_rows.append(
                    {
                        "id": str(pid),
                        "slug": slug,
                        "title": updated.get("title", ""),
                        "h1": updated.get("h1_content", ""),
                        "meta_title": updated.get("meta_title", ""),
                        "meta_description": updated.get("meta_description", ""),
                        "quality_overall": str(scores.get("overall", "")),
                        "review_status": "deployed",
                        "deployed_at": updated.get("deployed_at", ""),
                    }
                )

            # Write metadata CSV
            if csv_rows:
                csv_buf = io.StringIO()
                writer = csv.DictWriter(csv_buf, fieldnames=list(csv_rows[0].keys()))
                writer.writeheader()
                writer.writerows(csv_rows)
                zf.writestr("metadata.csv", csv_buf.getvalue())

        return {
            "deployed_pages": deployed,
            "zip_bytes": zip_buf.getvalue(),
            "page_count": len(deployed),
        }

    # ------------------------------------------------------------------
    # Revision history
    # ------------------------------------------------------------------

    def get_page_revisions(self, page_id: int) -> list[dict[str, Any]]:
        return self._db.fetchall(
            "SELECT * FROM page_revisions WHERE page_id = ? ORDER BY revision_number DESC",
            (page_id,),
        )

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def list_templates(self) -> list[dict[str, Any]]:
        return self._db.fetchall("SELECT * FROM templates ORDER BY name")

    def get_template(self, template_name: str) -> dict[str, Any] | None:
        return self._db.fetchone(
            "SELECT * FROM templates WHERE name = ?", (template_name,)
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _enrich_page(self, page: dict[str, Any]) -> dict[str, Any]:
        """
        Deserialise JSON fields and attach the template display name.
        """
        page = dict(page)

        # Deserialise JSON blobs
        for json_field in ("quality_scores", "internal_links"):
            raw = page.get(json_field)
            if isinstance(raw, str) and raw:
                try:
                    page[json_field] = json.loads(raw)
                except json.JSONDecodeError:
                    page[json_field] = {}
            elif not raw:
                page[json_field] = {}

        # Compute overall quality score if missing
        qs = page.get("quality_scores") or {}
        if qs and "overall" not in qs:
            metric_keys = ["authority", "semantic", "structure", "engagement", "uniqueness"]
            vals = [qs[k] for k in metric_keys if isinstance(qs.get(k), (int, float))]
            qs["overall"] = round(sum(vals) / len(vals), 1) if vals else 0.0
            page["quality_scores"] = qs

        # Attach template display name
        if page.get("template_id"):
            tmpl = self._db.fetchone(
                "SELECT name, display_name FROM templates WHERE id = ?",
                (page["template_id"],),
            )
            page["template_name"] = tmpl["name"] if tmpl else ""
            page["template_display_name"] = tmpl["display_name"] if tmpl else ""
        else:
            page["template_name"] = ""
            page["template_display_name"] = ""

        return page
