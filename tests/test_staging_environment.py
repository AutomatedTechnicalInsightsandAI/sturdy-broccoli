"""Tests for the StagingEnvironment client review workflow."""
from __future__ import annotations

import pytest

from src.database import Database
from src.staging_environment import StagingEnvironment
from src.staging_review import StagingReviewManager


@pytest.fixture
def db() -> Database:
    d = Database(":memory:")
    d.init_schema()
    return d


@pytest.fixture
def env(db: Database) -> StagingEnvironment:
    return StagingEnvironment(db)


@pytest.fixture
def review_manager(db: Database) -> StagingReviewManager:
    return StagingReviewManager(db)


def _make_batch_with_pages(
    review_manager: StagingReviewManager,
    n_pages: int = 3,
) -> int:
    """Helper: create a batch with *n_pages* draft pages."""
    batch_id = review_manager.create_batch(
        name="Test Batch", description="For testing", created_by="pytest"
    )["id"]
    for i in range(n_pages):
        review_manager.add_page(
            batch_id=batch_id,
            title=f"Page {i + 1}",
            content_markdown=f"Content for page {i + 1}.",
        )
    return batch_id


class TestGetBatchGallery:
    def test_returns_batch_and_pages(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 3)
        gallery = env.get_batch_gallery(batch_id)
        assert gallery["batch"] is not None
        assert len(gallery["pages"]) == 3

    def test_status_filter_works(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 3)
        # approve one page
        pages = review_manager.get_batch_pages(batch_id)
        review_manager.update_page_status(pages[0]["id"], "approved")
        gallery = env.get_batch_gallery(batch_id, status_filter="approved")
        assert len(gallery["pages"]) == 1
    def test_nonexistent_batch_returns_none(self, env: StagingEnvironment) -> None:
        gallery = env.get_batch_gallery(99999)
        assert gallery["batch"] is None
        assert gallery["pages"] == []


class TestBulkApproveReject:
    def test_bulk_approve_updates_status(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 3)
        pages = review_manager.get_batch_pages(batch_id)
        page_ids = [p["id"] for p in pages]
        count = env.bulk_approve(page_ids, reviewer="manager")
        assert count == 3
        updated = review_manager.get_batch_pages(batch_id, status_filter="approved")
        assert len(updated) == 3

    def test_bulk_reject_updates_status(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 2)
        pages = review_manager.get_batch_pages(batch_id)
        page_ids = [p["id"] for p in pages]
        count = env.bulk_reject(page_ids)
        assert count == 2
        updated = review_manager.get_batch_pages(batch_id, status_filter="rejected")
        assert len(updated) == 2


class TestAddPageComment:
    def test_add_comment_preserves_status(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 1)
        pages = review_manager.get_batch_pages(batch_id)
        page_id = pages[0]["id"]
        original_status = pages[0]["review_status"]

        env.add_page_comment(page_id, "Please fix the H1.", reviewer="client@example.com")

        updated = review_manager.get_page(page_id)
        assert updated["review_status"] == original_status
        assert updated["reviewer_notes"] == "Please fix the H1."


class TestAddBatchComment:
    def test_add_batch_comment(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        from src.agency_dashboard import AgencyDashboard
        db = Database(":memory:")
        db.init_schema()
        local_review = StagingReviewManager(db)
        local_env = StagingEnvironment(db)
        dashboard = AgencyDashboard(db)

        staging_batch_id = dashboard.create_staging_batch("Test", "Client A")
        rid = local_env.add_batch_comment(staging_batch_id, "Approved!", "approved")
        assert isinstance(rid, int)
        comments = local_env.list_batch_comments(staging_batch_id)
        assert len(comments) == 1
        assert comments[0]["client_comment"] == "Approved!"


class TestDeployReadiness:
    def test_not_ready_when_pages_not_approved(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 3)
        readiness = env.get_deploy_readiness(batch_id)
        assert readiness["ready"] is False
        assert readiness["approved_count"] == 0
        assert readiness["total_count"] == 3

    def test_ready_when_all_approved(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 2)
        pages = review_manager.get_batch_pages(batch_id)
        for page in pages:
            review_manager.update_page_status(page["id"], "approved")
        readiness = env.get_deploy_readiness(batch_id)
        assert readiness["ready"] is True
        assert readiness["approved_count"] == 2


class TestRevisionHistory:
    def test_get_revision_history_returns_list(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 1)
        pages = review_manager.get_batch_pages(batch_id)
        page_id = pages[0]["id"]
        history = env.get_page_revision_history(page_id)
        assert isinstance(history, list)

    def test_compare_revisions_empty_returns_empty_strings(
        self, env: StagingEnvironment, review_manager: StagingReviewManager
    ) -> None:
        batch_id = _make_batch_with_pages(review_manager, 1)
        pages = review_manager.get_batch_pages(batch_id)
        page_id = pages[0]["id"]
        # No revisions recorded yet
        comparison = env.compare_revisions(page_id)
        assert comparison["page_id"] == page_id
        assert isinstance(comparison["before"], str)
        assert isinstance(comparison["after"], str)
