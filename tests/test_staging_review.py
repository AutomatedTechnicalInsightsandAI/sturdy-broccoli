"""Tests for Database schema and StagingReviewManager."""
from __future__ import annotations

import io
import pytest

from src.database import Database
from src.staging_review import StagingReviewManager, VALID_STATUSES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Database:
    """In-memory SQLite database with schema initialised."""
    d = Database(":memory:")
    d.init_schema()
    return d


@pytest.fixture
def mgr(db: Database) -> StagingReviewManager:
    return StagingReviewManager(db)


@pytest.fixture
def batch(mgr: StagingReviewManager) -> dict:
    return mgr.create_batch("Test Batch", description="Unit-test batch", created_by="tester")


@pytest.fixture
def page(mgr: StagingReviewManager, batch: dict) -> dict:
    return mgr.add_page(
        batch_id=batch["id"],
        title="NFT Consulting Services",
        h1_content="Expert NFT Strategy for Fortune 500 Companies",
        meta_title="NFT Consulting | CrowdCreate",
        meta_description="We help Fortune 500 companies navigate the NFT landscape.",
        content_markdown="## What We Do\nWe provide strategic NFT consulting.",
        template_name="modern_saas",
        quality_scores={"authority": 92, "semantic": 87, "structure": 95, "engagement": 84, "uniqueness": 78},
        competitor_benchmark="consensys.net",
    )


# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------


class TestDatabaseSchema:
    def test_init_schema_idempotent(self, db: Database) -> None:
        """Calling init_schema twice should not raise."""
        db.init_schema()  # second call — must be idempotent

    def test_templates_seeded(self, db: Database) -> None:
        templates = db.fetchall("SELECT name FROM templates ORDER BY name")
        names = {r["name"] for r in templates}
        expected = {"modern_saas", "professional_service", "content_guide", "ecommerce", "enterprise"}
        assert expected == names

    def test_fetchone_missing_returns_none(self, db: Database) -> None:
        result = db.fetchone("SELECT * FROM batches WHERE id = ?", (9999,))
        assert result is None


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


class TestBatchOperations:
    def test_create_batch(self, mgr: StagingReviewManager) -> None:
        b = mgr.create_batch("My Batch", description="desc", created_by="alice")
        assert b["id"] is not None
        assert b["name"] == "My Batch"
        assert b["description"] == "desc"
        assert b["created_by"] == "alice"
        assert b["total_pages"] == 0

    def test_list_batches(self, mgr: StagingReviewManager) -> None:
        mgr.create_batch("Batch A")
        mgr.create_batch("Batch B")
        batches = mgr.list_batches()
        assert len(batches) >= 2

    def test_update_batch_branding(self, mgr: StagingReviewManager, batch: dict) -> None:
        updated = mgr.update_batch_branding(
            batch["id"],
            primary_color="#2563EB",
            font_family="Poppins",
            global_cta_text="Get Started Today",
            global_cta_link="https://example.com/contact",
        )
        assert updated["batch_primary_color"] == "#2563EB"
        assert updated["batch_font_family"] == "Poppins"
        assert updated["batch_global_cta_text"] == "Get Started Today"

    def test_update_batch_branding_partial(self, mgr: StagingReviewManager, batch: dict) -> None:
        """Passing only one field should not overwrite others."""
        mgr.update_batch_branding(batch["id"], primary_color="#FF0000")
        updated = mgr.update_batch_branding(batch["id"], font_family="Inter")
        assert updated["batch_primary_color"] == "#FF0000"
        assert updated["batch_font_family"] == "Inter"

    def test_update_batch_branding_no_args(self, mgr: StagingReviewManager, batch: dict) -> None:
        """Calling with no field args should return the current record unchanged."""
        original = mgr.get_batch(batch["id"])
        result = mgr.update_batch_branding(batch["id"])
        assert result["id"] == original["id"]


# ---------------------------------------------------------------------------
# Page CRUD
# ---------------------------------------------------------------------------


class TestPageCRUD:
    def test_add_page_returns_record(self, page: dict) -> None:
        assert page["id"] is not None
        assert page["title"] == "NFT Consulting Services"
        assert page["review_status"] == "draft"

    def test_add_page_increments_batch_counter(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        mgr.add_page(batch["id"], title="Page One")
        mgr.add_page(batch["id"], title="Page Two")
        b = mgr.get_batch(batch["id"])
        assert b["total_pages"] == 2
        assert b["pages_draft"] == 2

    def test_add_page_default_template(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(batch["id"], title="No Template Page")
        assert p["template_name"] == "modern_saas"

    def test_add_page_quality_scores_enriched(self, page: dict) -> None:
        scores = page["quality_scores"]
        assert isinstance(scores, dict)
        assert scores["authority"] == 92
        assert "overall" in scores

    def test_get_page_unknown_returns_none(
        self, mgr: StagingReviewManager
    ) -> None:
        assert mgr.get_page(99999) is None

    def test_get_batch_pages_returns_list(
        self, mgr: StagingReviewManager, batch: dict, page: dict
    ) -> None:
        pages = mgr.get_batch_pages(batch["id"])
        assert len(pages) == 1
        assert pages[0]["id"] == page["id"]

    def test_get_batch_pages_status_filter(
        self, mgr: StagingReviewManager, batch: dict, page: dict
    ) -> None:
        pages_draft = mgr.get_batch_pages(batch["id"], status_filter="draft")
        assert len(pages_draft) == 1

        pages_approved = mgr.get_batch_pages(batch["id"], status_filter="approved")
        assert len(pages_approved) == 0

    def test_get_batch_pages_min_quality_filter(
        self, mgr: StagingReviewManager, batch: dict, page: dict
    ) -> None:
        pages = mgr.get_batch_pages(batch["id"], min_quality=87.0)
        assert all(p["quality_scores"].get("overall", 0) >= 87.0 for p in pages)

    def test_delete_page_removes_page(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(batch["id"], title="Page to Delete")
        mgr.delete_page(p["id"])
        assert mgr.get_page(p["id"]) is None

    def test_delete_page_updates_batch_counter(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(batch["id"], title="Counted Page")
        b_before = mgr.get_batch(batch["id"])
        assert b_before["total_pages"] == 1
        mgr.delete_page(p["id"])
        b_after = mgr.get_batch(batch["id"])
        assert b_after["total_pages"] == 0

    def test_delete_page_unknown_raises(
        self, mgr: StagingReviewManager
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            mgr.delete_page(99999)


# ---------------------------------------------------------------------------
# Content editing
# ---------------------------------------------------------------------------


class TestContentEditing:
    def test_update_page_content(
        self, mgr: StagingReviewManager, page: dict
    ) -> None:
        updated = mgr.update_page_content(
            page["id"],
            h1_content="New H1 Headline",
            meta_description="Updated meta.",
            changed_by="editor",
            change_reason="User edit",
        )
        assert updated["h1_content"] == "New H1 Headline"
        assert updated["meta_description"] == "Updated meta."

    def test_update_content_saves_revision(
        self, mgr: StagingReviewManager, page: dict, db: Database
    ) -> None:
        mgr.update_page_content(page["id"], content_markdown="# New Content")
        revisions = mgr.get_page_revisions(page["id"])
        assert len(revisions) == 1
        assert "New Content" in revisions[0]["content_markdown"]

    def test_update_content_unknown_page_raises(
        self, mgr: StagingReviewManager
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            mgr.update_page_content(99999, h1_content="test")

    def test_switch_template(self, mgr: StagingReviewManager, page: dict) -> None:
        updated = mgr.switch_template(page["id"], "enterprise")
        assert updated["template_name"] == "enterprise"
        assert updated["template_display_name"] == "Enterprise"

    def test_switch_template_unknown_raises(
        self, mgr: StagingReviewManager, page: dict
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            mgr.switch_template(page["id"], "nonexistent_template")


# ---------------------------------------------------------------------------
# Review status lifecycle
# ---------------------------------------------------------------------------


class TestReviewStatus:
    @pytest.mark.parametrize("status", list(VALID_STATUSES))
    def test_valid_status_transitions(
        self, mgr: StagingReviewManager, page: dict, status: str
    ) -> None:
        updated = mgr.update_page_status(page["id"], status, reviewed_by="reviewer")
        assert updated["review_status"] == status

    def test_invalid_status_raises(
        self, mgr: StagingReviewManager, page: dict
    ) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            mgr.update_page_status(page["id"], "published")

    def test_status_updates_batch_counters(
        self, mgr: StagingReviewManager, batch: dict, page: dict
    ) -> None:
        mgr.update_page_status(page["id"], "approved")
        b = mgr.get_batch(batch["id"])
        assert b["pages_approved"] == 1
        assert b["pages_draft"] == 0

    def test_update_page_status_unknown_page_raises(
        self, mgr: StagingReviewManager
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            mgr.update_page_status(99999, "approved")

    def test_bulk_update_status(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p1 = mgr.add_page(batch["id"], title="Page 1")
        p2 = mgr.add_page(batch["id"], title="Page 2")
        results = mgr.bulk_update_status([p1["id"], p2["id"]], "approved")
        assert all(r["review_status"] == "approved" for r in results)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Branding overrides
# ---------------------------------------------------------------------------


class TestBrandingOverrides:
    def test_apply_branding_to_pages(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p1 = mgr.add_page(batch["id"], title="Brand Page 1")
        p2 = mgr.add_page(batch["id"], title="Brand Page 2")
        results = mgr.apply_branding_to_pages(
            [p1["id"], p2["id"]],
            brand_color="#FF6600",
            cta_text="Book a Call",
            cta_link="https://calendly.com/test",
        )
        assert len(results) == 2
        for r in results:
            assert r["brand_color_override"] == "#FF6600"
            assert r["cta_text_override"] == "Book a Call"
            assert r["cta_link_override"] == "https://calendly.com/test"

    def test_apply_branding_partial(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(batch["id"], title="Partial Brand Page")
        mgr.apply_branding_to_pages([p["id"]], brand_color="#AABBCC")
        results = mgr.apply_branding_to_pages([p["id"]], cta_text="New CTA")
        assert results[0]["brand_color_override"] == "#AABBCC"
        assert results[0]["cta_text_override"] == "New CTA"


# ---------------------------------------------------------------------------
# Quality scores
# ---------------------------------------------------------------------------


class TestQualityScores:
    def test_update_quality_scores_computes_overall(
        self, mgr: StagingReviewManager, page: dict
    ) -> None:
        scores = {"authority": 80, "semantic": 90, "structure": 70, "engagement": 85, "uniqueness": 75}
        updated = mgr.update_quality_scores(page["id"], scores)
        qs = updated["quality_scores"]
        assert "overall" in qs
        assert qs["overall"] == round((80 + 90 + 70 + 85 + 75) / 5, 1)

    def test_update_quality_scores_custom_overall(
        self, mgr: StagingReviewManager, page: dict
    ) -> None:
        scores = {"authority": 80, "overall": 99.0}
        updated = mgr.update_quality_scores(page["id"], scores)
        assert updated["quality_scores"]["overall"] == 99.0


# ---------------------------------------------------------------------------
# Hub-and-spoke validation
# ---------------------------------------------------------------------------


class TestHubSpokeValidation:
    def _setup_cluster(self, mgr: StagingReviewManager, batch: dict) -> tuple[dict, list[dict]]:
        """Create a hub + 2 spoke pages."""
        hub = mgr.add_page(batch["id"], title="NFT Consulting Hub")
        s1 = mgr.add_page(batch["id"], title="Ultimate Guide to NFT")
        s2 = mgr.add_page(batch["id"], title="How to Find an NFT Consultant")
        mgr.set_hub_spoke_relationship(s1["id"], hub["id"])
        mgr.set_hub_spoke_relationship(s2["id"], hub["id"])
        return hub, [s1, s2]

    def test_healthy_cluster(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        hub, spokes = self._setup_cluster(mgr, batch)
        # Wire up all required links
        mgr.add_internal_link(spokes[0]["id"], hub["id"], "NFT consulting")
        mgr.add_internal_link(spokes[1]["id"], hub["id"], "NFT consultant guide")
        mgr.add_internal_link(hub["id"], spokes[0]["id"], "ultimate guide")
        mgr.add_internal_link(hub["id"], spokes[1]["id"], "find consultant")
        report = mgr.validate_hub_spoke_links(batch["id"])
        assert report["is_healthy"] is True
        assert len(report["issues"]) == 0

    def test_missing_spoke_to_hub_link(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        hub, spokes = self._setup_cluster(mgr, batch)
        # Only wire s1 → hub; leave s2 → hub missing
        mgr.add_internal_link(spokes[0]["id"], hub["id"], "NFT consulting")
        mgr.add_internal_link(hub["id"], spokes[0]["id"], "guide")
        mgr.add_internal_link(hub["id"], spokes[1]["id"], "find")
        report = mgr.validate_hub_spoke_links(batch["id"])
        assert report["is_healthy"] is False
        missing = [i for i in report["issues"] if i["type"] == "missing_spoke_to_hub"]
        assert len(missing) == 1
        assert missing[0]["spoke_id"] == spokes[1]["id"]

    def test_empty_batch_no_issues(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        report = mgr.validate_hub_spoke_links(batch["id"])
        assert report["is_healthy"] is True
        assert report["issues"] == []

    def test_set_hub_spoke_relationship(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        hub = mgr.add_page(batch["id"], title="Hub Page")
        spoke = mgr.add_page(batch["id"], title="Spoke Page")
        updated = mgr.set_hub_spoke_relationship(spoke["id"], hub["id"])
        assert updated["hub_page_id"] == hub["id"]

    def test_add_internal_link_updates_existing(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        hub = mgr.add_page(batch["id"], title="Hub")
        spoke = mgr.add_page(batch["id"], title="Spoke")
        mgr.add_internal_link(spoke["id"], hub["id"], "original anchor")
        mgr.add_internal_link(spoke["id"], hub["id"], "updated anchor")
        page = mgr.get_page(spoke["id"])
        links = page["internal_links"]["links"]
        assert len(links) == 1
        assert links[0]["anchor_text"] == "updated anchor"


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------


class TestPreflightChecks:
    def test_all_pass(self, mgr: StagingReviewManager, batch: dict) -> None:
        p = mgr.add_page(
            batch["id"],
            title="Good Page",
            h1_content="My H1",
            meta_description="A proper meta description.",
            quality_scores={"overall": 90},
        )
        mgr.update_page_status(p["id"], "approved")
        result = mgr.run_preflight_checks([p["id"]])
        assert result["passed"] is True
        assert result["blocking_issues"] == []

    def test_missing_h1_blocks_deploy(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(
            batch["id"],
            title="No H1 Page",
            h1_content="",
            meta_description="desc",
            quality_scores={"overall": 90},
        )
        mgr.update_page_status(p["id"], "approved")
        result = mgr.run_preflight_checks([p["id"]])
        assert result["passed"] is False
        assert any("H1" in issue for issue in result["blocking_issues"])

    def test_low_quality_blocks_deploy(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(
            batch["id"],
            title="Low Quality Page",
            h1_content="Has H1",
            meta_description="desc",
            quality_scores={"overall": 50},
        )
        mgr.update_page_status(p["id"], "approved")
        result = mgr.run_preflight_checks([p["id"]])
        assert result["passed"] is False
        assert any("quality" in issue.lower() for issue in result["blocking_issues"])

    def test_not_approved_blocks_deploy(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(
            batch["id"],
            title="Draft Page",
            h1_content="Has H1",
            meta_description="desc",
            quality_scores={"overall": 90},
        )
        # Left as draft
        result = mgr.run_preflight_checks([p["id"]])
        assert result["passed"] is False
        assert any("approved" in issue.lower() for issue in result["blocking_issues"])

    def test_empty_page_list(self, mgr: StagingReviewManager) -> None:
        result = mgr.run_preflight_checks([])
        assert result["passed"] is True
        assert result["page_count"] == 0


# ---------------------------------------------------------------------------
# Deployment / export
# ---------------------------------------------------------------------------


class TestDeployment:
    def test_deploy_pages_returns_zip(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(
            batch["id"],
            title="Deploy Page",
            h1_content="Deploy H1",
            meta_description="deploy meta",
            content_markdown="## Section\nContent here.",
            quality_scores={"overall": 90},
        )
        mgr.update_page_status(p["id"], "approved")
        result = mgr.deploy_pages([p["id"]], deployed_by="publisher")
        assert result["page_count"] == 1
        assert isinstance(result["zip_bytes"], bytes)
        assert len(result["zip_bytes"]) > 0

    def test_deploy_pages_marks_deployed(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        p = mgr.add_page(batch["id"], title="To Deploy", h1_content="H1")
        mgr.update_page_status(p["id"], "approved")
        result = mgr.deploy_pages([p["id"]])
        assert result["deployed_pages"][0]["review_status"] == "deployed"

    def test_deploy_zip_contains_html_and_csv(
        self, mgr: StagingReviewManager, batch: dict
    ) -> None:
        import zipfile as zf

        p = mgr.add_page(batch["id"], title="Zip Page", h1_content="H1")
        mgr.update_page_status(p["id"], "approved")
        result = mgr.deploy_pages([p["id"]])
        with zf.ZipFile(io.BytesIO(result["zip_bytes"])) as z:
            names = z.namelist()
        assert any(n.endswith(".html") for n in names)
        assert "metadata.csv" in names


# ---------------------------------------------------------------------------
# Template listing
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_list_templates(self, mgr: StagingReviewManager) -> None:
        templates = mgr.list_templates()
        assert len(templates) == 5

    def test_get_template_by_name(self, mgr: StagingReviewManager) -> None:
        t = mgr.get_template("modern_saas")
        assert t is not None
        assert t["display_name"] == "Modern SaaS"

    def test_get_unknown_template_returns_none(
        self, mgr: StagingReviewManager
    ) -> None:
        assert mgr.get_template("nonexistent") is None
