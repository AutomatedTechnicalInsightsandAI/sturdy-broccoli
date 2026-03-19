"""
staging_environment.py

Client-facing staging environment for reviewing, approving, and deploying
batches of generated landing pages.

This module wraps the lower-level staging_review and agency_dashboard layers
to provide a clean, high-level API for the client approval workflow:

1. **Gallery view** — list all pages in a batch with preview metadata
2. **Bulk approve/reject** — change status on multiple pages at once
3. **Comment system** — record client feedback per page or per batch
4. **Before/after comparison** — retrieve page revision history
5. **Version history** — track changes to a page's content over time
6. **One-click deploy** — delegate to GCPPersistentDeployer when approved
"""
from __future__ import annotations

import logging
from typing import Any

from .agency_dashboard import AgencyDashboard
from .database import Database
from .staging_review import StagingReviewManager

logger = logging.getLogger(__name__)


class StagingEnvironment:
    """
    High-level facade for the client staging and approval workflow.

    Parameters
    ----------
    db:
        Initialised :class:`~src.database.Database` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._review_manager = StagingReviewManager(db)
        self._dashboard = AgencyDashboard(db)

    # ------------------------------------------------------------------
    # Gallery view
    # ------------------------------------------------------------------

    def get_batch_gallery(
        self,
        batch_id: int,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Return a gallery-friendly representation of all pages in a batch.

        Parameters
        ----------
        batch_id:
            The batch to retrieve.
        status_filter:
            Optional status to filter pages (e.g. ``'approved'``).

        Returns
        -------
        dict
            ``batch`` metadata and ``pages`` list with preview info.
        """
        batch = self._review_manager.get_batch(batch_id)
        if batch is None:
            return {"batch": None, "pages": []}

        pages = self._review_manager.get_batch_pages(
            batch_id=batch_id, status_filter=status_filter
        )

        # Trim content for gallery (keep preview short)
        gallery_pages = []
        for page in pages:
            gallery_pages.append(
                {
                    "id": page.get("id"),
                    "title": page.get("title"),
                    "slug": page.get("slug"),
                    "status": page.get("review_status"),
                    "primary_keyword": page.get("primary_keyword"),
                    "word_count": page.get("word_count", 0),
                    "quality_scores": page.get("quality_scores") or {},
                    "meta_description": page.get("meta_description", ""),
                    "assigned_template": page.get("assigned_template", ""),
                    "updated_at": page.get("updated_at"),
                }
            )

        return {"batch": batch, "pages": gallery_pages}

    # ------------------------------------------------------------------
    # Bulk approve / reject
    # ------------------------------------------------------------------

    def bulk_approve(self, page_ids: list[int], reviewer: str = "") -> int:
        """
        Approve multiple pages at once.

        Parameters
        ----------
        page_ids:
            List of page ids to approve.
        reviewer:
            Identifier of the person approving the pages.

        Returns
        -------
        int
            Number of pages successfully updated.
        """
        return self._bulk_set_status(page_ids, "approved", reviewer)

    def bulk_reject(self, page_ids: list[int], reviewer: str = "") -> int:
        """
        Reject multiple pages at once.

        Parameters
        ----------
        page_ids:
            List of page ids to reject.
        reviewer:
            Identifier of the person rejecting the pages.

        Returns
        -------
        int
            Number of pages successfully updated.
        """
        return self._bulk_set_status(page_ids, "rejected", reviewer)

    def _bulk_set_status(
        self, page_ids: list[int], status: str, reviewer: str
    ) -> int:
        count = 0
        for page_id in page_ids:
            try:
                self._review_manager.update_page_status(
                    page_id=page_id,
                    status=status,
                    reviewed_by=reviewer,
                )
                count += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to set page %s status to '%s': %s", page_id, status, exc
                )
        return count

    # ------------------------------------------------------------------
    # Comment system
    # ------------------------------------------------------------------

    def add_page_comment(
        self,
        page_id: int,
        comment: str,
        reviewer: str = "",
    ) -> None:
        """
        Add a reviewer comment to a specific page without changing its status.

        Parameters
        ----------
        page_id:
            Page to annotate.
        comment:
            The reviewer's feedback text.
        reviewer:
            Identifier of the reviewer.
        """
        page = self._review_manager.get_page(page_id)
        if page is None:
            raise ValueError(f"Page {page_id} not found")
        current_status = page.get("review_status", "draft")
        self._review_manager.update_page_status(
            page_id=page_id,
            status=current_status,
            reviewer_notes=comment,
            reviewed_by=reviewer,
        )

    def add_batch_comment(
        self,
        batch_id: int,
        comment: str,
        status: str = "pending",
    ) -> int:
        """
        Add a client-level comment to an entire staging batch.

        Parameters
        ----------
        batch_id:
            Staging batch to annotate.
        comment:
            Client feedback text.
        status:
            Review status: ``'pending'``, ``'approved'``, or ``'rejected'``.

        Returns
        -------
        int
            New review record id.
        """
        return self._dashboard.add_client_review(
            batch_id=batch_id,
            client_comment=comment,
            status=status,
        )

    def list_batch_comments(self, batch_id: int) -> list[dict[str, Any]]:
        """Return all client comments for a staging batch."""
        return self._dashboard.list_reviews(batch_id)

    # ------------------------------------------------------------------
    # Version history / before-after comparison
    # ------------------------------------------------------------------

    def get_page_revision_history(self, page_id: int) -> list[dict[str, Any]]:
        """
        Return the full revision history for a page.

        Parameters
        ----------
        page_id:
            Page whose history to retrieve.

        Returns
        -------
        list of dict
            Revisions in reverse chronological order, each containing
            ``revision_number``, ``content_markdown``, ``changed_by``,
            ``change_reason``, and ``created_at``.
        """
        return self._review_manager.get_page_revisions(page_id)

    def compare_revisions(
        self,
        page_id: int,
        revision_a: int | None = None,
        revision_b: int | None = None,
    ) -> dict[str, Any]:
        """
        Return a before/after comparison of two page revisions.

        Parameters
        ----------
        page_id:
            Target page.
        revision_a:
            Earlier revision number.  Defaults to the oldest revision.
        revision_b:
            Later revision number.  Defaults to the newest revision.

        Returns
        -------
        dict
            ``{"before": str, "after": str, "page_id": int, "diff_lines": int}``
        """
        revisions = self.get_page_revision_history(page_id)
        if not revisions:
            return {"before": "", "after": "", "page_id": page_id, "diff_lines": 0}

        # Revisions are newest-first; reverse for indexing
        ordered = list(reversed(revisions))

        before_rev = (
            next((r for r in ordered if r["revision_number"] == revision_a), ordered[0])
            if revision_a is not None
            else ordered[0]
        )
        after_rev = (
            next((r for r in ordered if r["revision_number"] == revision_b), ordered[-1])
            if revision_b is not None
            else ordered[-1]
        )

        before_text = before_rev.get("content_markdown", "")
        after_text = after_rev.get("content_markdown", "")
        diff_lines = abs(
            len(after_text.splitlines()) - len(before_text.splitlines())
        )

        return {
            "before": before_text,
            "after": after_text,
            "page_id": page_id,
            "revision_before": before_rev.get("revision_number"),
            "revision_after": after_rev.get("revision_number"),
            "diff_lines": diff_lines,
        }

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def get_deploy_readiness(self, batch_id: int) -> dict[str, Any]:
        """
        Check whether a batch is ready to deploy.

        Returns
        -------
        dict
            ``{"ready": bool, "approved_count": int, "total_count": int,
               "blocked_pages": list}``
        """
        pages = self._review_manager.get_batch_pages(batch_id=batch_id)
        approved = [p for p in pages if p.get("review_status") == "approved"]
        blocked = [
            {"id": p.get("id"), "title": p.get("title"), "status": p.get("review_status")}
            for p in pages
            if p.get("review_status") not in {"approved", "deployed"}
        ]
        return {
            "ready": len(approved) == len(pages) and len(pages) > 0,
            "approved_count": len(approved),
            "total_count": len(pages),
            "blocked_pages": blocked,
        }
