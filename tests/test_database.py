"""Tests for src/database.py — SQLite persistence layer."""
from __future__ import annotations

import json

import pytest

from src.database import Database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db() -> Database:
    """Return an in-memory Database instance for each test."""
    return Database(":memory:")


SAMPLE_PAGE: dict = {
    "title": "NFT Consultant Services - CrowdCreate",
    "slug": "nft-consultant-services",
    "h1": "Expert NFT Strategy Consulting for Fortune 500 Companies",
    "meta_title": "NFT Consultant Services | CrowdCreate",
    "meta_description": "CrowdCreate specializes in NFT consulting for enterprise clients. Proven results in blockchain strategy.",
    "target_keyword": "nft consulting services",
    "secondary_keywords": ["nft strategy", "blockchain consultant", "web3 advisory"],
    "word_count": 2847,
    "semantic_core": {
        "entities": [
            {"text": "NFT", "entity_type": "TECHNOLOGY", "mentions": 23},
        ],
        "lsi_keywords": ["digital assets", "smart contracts", "tokenomics"],
        "topic_coverage": {
            "problem": "Enterprise companies struggle with NFT integration",
            "solution": "CrowdCreate's data-driven approach",
            "result": "60% faster launch",
        },
    },
    "structure": {
        "h1": "Expert NFT Strategy Consulting for Fortune 500 Companies",
        "h2_sections": [
            {"text": "Why Enterprise NFT Strategies Fail", "subsections": ["Mistake 1"]},
        ],
        "cta_sections": [
            {"position": "mid-page", "text": "Get a Free Audit", "strength": "benefit-driven"},
        ],
    },
    "competitor_intelligence": {
        "benchmarked_against": [
            {"url": "https://example.com", "key_topics_covered": ["regulatory compliance"]},
        ],
        "competitive_advantage": ["Speed-to-Launch: 90 days vs 6 months"],
    },
    "role": "hub",
    "content_markdown": "# Expert NFT Strategy\n\nThis page covers NFT consulting.",
    "content_html": "<h1>Expert NFT Strategy</h1>",
    "quality_scores": {
        "authority_score": 92,
        "semantic_richness_score": 87,
        "structure_score": 95,
        "engagement_potential_score": 84,
        "uniqueness_score": 78,
        "overall_score": 87,
    },
    "review_status": "draft",
    "reviewer_notes": "High authority.",
}


# ---------------------------------------------------------------------------
# Batch CRUD
# ---------------------------------------------------------------------------

class TestBatchCRUD:
    def test_create_batch_returns_integer_id(self, db: Database) -> None:
        batch_id = db.create_batch("Test Batch")
        assert isinstance(batch_id, int)
        assert batch_id > 0

    def test_get_batch_returns_dict(self, db: Database) -> None:
        batch_id = db.create_batch("Client A", description="March run")
        batch = db.get_batch(batch_id)
        assert batch is not None
        assert batch["name"] == "Client A"
        assert batch["description"] == "March run"

    def test_get_batch_nonexistent_returns_none(self, db: Database) -> None:
        assert db.get_batch(9999) is None

    def test_list_batches_returns_all(self, db: Database) -> None:
        db.create_batch("Batch 1")
        db.create_batch("Batch 2")
        batches = db.list_batches()
        assert len(batches) >= 2
        names = [b["name"] for b in batches]
        assert "Batch 1" in names
        assert "Batch 2" in names

    def test_update_batch_styles(self, db: Database) -> None:
        batch_id = db.create_batch("Style Test")
        db.update_batch_styles(
            batch_id,
            primary_color="#FF0000",
            global_cta_text="Book Now",
        )
        batch = db.get_batch(batch_id)
        assert batch["batch_primary_color"] == "#FF0000"
        assert batch["batch_global_cta_text"] == "Book Now"

    def test_update_batch_styles_no_op_when_no_kwargs(self, db: Database) -> None:
        batch_id = db.create_batch("No-op")
        db.update_batch_styles(batch_id)  # Should not raise
        batch = db.get_batch(batch_id)
        assert batch is not None


# ---------------------------------------------------------------------------
# Template operations
# ---------------------------------------------------------------------------

class TestTemplates:
    def test_list_templates_returns_seeded_templates(self, db: Database) -> None:
        templates = db.list_templates()
        assert len(templates) >= 5
        names = [t["name"] for t in templates]
        assert "professional_service" in names
        assert "thought_leadership" in names

    def test_get_template_by_id(self, db: Database) -> None:
        templates = db.list_templates()
        t = db.get_template(templates[0]["id"])
        assert t is not None
        assert "name" in t

    def test_get_template_by_name(self, db: Database) -> None:
        t = db.get_template_by_name("professional_service")
        assert t is not None
        assert t["display_name"] == "Professional Service"

    def test_get_template_by_name_nonexistent(self, db: Database) -> None:
        assert db.get_template_by_name("nonexistent_template") is None

    def test_template_color_config_is_dict(self, db: Database) -> None:
        t = db.get_template_by_name("professional_service")
        assert isinstance(t["color_config"], dict)
        assert "primary" in t["color_config"]

    def test_template_cta_positions_is_list(self, db: Database) -> None:
        t = db.get_template_by_name("professional_service")
        assert isinstance(t["cta_positions"], list)


# ---------------------------------------------------------------------------
# Page CRUD
# ---------------------------------------------------------------------------

class TestPageCRUD:
    def test_create_page_returns_integer_id(self, db: Database) -> None:
        batch_id = db.create_batch("Pages Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        assert isinstance(page_id, int)
        assert page_id > 0

    def test_get_page_returns_dict(self, db: Database) -> None:
        batch_id = db.create_batch("Pages Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        page = db.get_page(page_id)
        assert page is not None
        assert page["title"] == SAMPLE_PAGE["title"]
        assert page["h1"] == SAMPLE_PAGE["h1"]

    def test_json_fields_deserialised(self, db: Database) -> None:
        batch_id = db.create_batch("JSON Fields Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        page = db.get_page(page_id)
        assert isinstance(page["secondary_keywords"], list)
        assert isinstance(page["semantic_core"], dict)
        assert isinstance(page["structure"], dict)
        assert isinstance(page["quality_scores"], dict)
        assert page["quality_scores"]["overall_score"] == 87

    def test_get_page_nonexistent_returns_none(self, db: Database) -> None:
        assert db.get_page(9999) is None

    def test_list_pages_returns_pages_for_batch(self, db: Database) -> None:
        batch_id = db.create_batch("List Batch")
        db.create_page(batch_id, {**SAMPLE_PAGE, "title": "Page A"})
        db.create_page(batch_id, {**SAMPLE_PAGE, "title": "Page B", "slug": "page-b"})
        pages = db.list_pages(batch_id)
        assert len(pages) == 2

    def test_list_pages_with_status_filter(self, db: Database) -> None:
        batch_id = db.create_batch("Filter Batch")
        db.create_page(batch_id, {**SAMPLE_PAGE, "review_status": "draft"})
        db.create_page(batch_id, {**SAMPLE_PAGE, "review_status": "approved", "slug": "approved-1"})
        drafts = db.list_pages(batch_id, status_filter="draft")
        approved = db.list_pages(batch_id, status_filter="approved")
        assert len(drafts) == 1
        assert len(approved) == 1

    def test_list_pages_different_batches_isolated(self, db: Database) -> None:
        b1 = db.create_batch("Batch One")
        b2 = db.create_batch("Batch Two")
        db.create_page(b1, SAMPLE_PAGE)
        pages_b2 = db.list_pages(b2)
        assert len(pages_b2) == 0

    def test_update_page_modifies_fields(self, db: Database) -> None:
        batch_id = db.create_batch("Update Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.update_page(page_id, {"title": "Updated Title", "word_count": 3000})
        page = db.get_page(page_id)
        assert page["title"] == "Updated Title"
        assert page["word_count"] == 3000

    def test_update_page_json_field(self, db: Database) -> None:
        batch_id = db.create_batch("JSON Update Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        new_scores = {"authority_score": 95, "overall_score": 90}
        db.update_page(page_id, {"quality_scores": new_scores})
        page = db.get_page(page_id)
        assert page["quality_scores"]["authority_score"] == 95

    def test_delete_page(self, db: Database) -> None:
        batch_id = db.create_batch("Delete Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.delete_page(page_id)
        assert db.get_page(page_id) is None


# ---------------------------------------------------------------------------
# Review workflow
# ---------------------------------------------------------------------------

class TestReviewWorkflow:
    def test_update_page_status_to_approved(self, db: Database) -> None:
        batch_id = db.create_batch("Review Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.update_page_status(page_id, "approved", reviewer_notes="Looks great")
        page = db.get_page(page_id)
        assert page["review_status"] == "approved"
        assert page["reviewer_notes"] == "Looks great"

    def test_update_page_status_cycles(self, db: Database) -> None:
        batch_id = db.create_batch("Status Cycle Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        for status in ("reviewed", "needs_revision", "approved", "deployed"):
            db.update_page_status(page_id, status)
            page = db.get_page(page_id)
            assert page["review_status"] == status

    def test_batch_counts_refreshed_on_status_change(self, db: Database) -> None:
        batch_id = db.create_batch("Count Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.update_page_status(page_id, "approved")
        batch = db.get_batch(batch_id)
        assert batch["pages_approved"] == 1
        assert batch["pages_draft"] == 0


# ---------------------------------------------------------------------------
# Quality scores
# ---------------------------------------------------------------------------

class TestQualityScores:
    def test_update_page_quality_scores(self, db: Database) -> None:
        batch_id = db.create_batch("Quality Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        new_scores = {
            "authority_score": 90,
            "semantic_richness_score": 80,
            "structure_score": 95,
            "engagement_potential_score": 85,
            "uniqueness_score": 75,
            "overall_score": 85,
        }
        db.update_page_quality_scores(page_id, new_scores)
        page = db.get_page(page_id)
        assert page["quality_scores"]["authority_score"] == 90
        assert page["quality_scores"]["overall_score"] == 85

    def test_audit_trail_appended(self, db: Database) -> None:
        batch_id = db.create_batch("Audit Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        entry = {"metric_name": "authority_score", "score": 90, "reason": "Added citation"}
        db.update_page_quality_scores(page_id, {"authority_score": 90}, audit_entry=entry)
        page = db.get_page(page_id)
        trail = page["quality_audit_trail"]
        assert isinstance(trail, list)
        assert len(trail) == 1
        assert trail[0]["metric_name"] == "authority_score"


# ---------------------------------------------------------------------------
# Batch style application
# ---------------------------------------------------------------------------

class TestBatchStyleApplication:
    def test_apply_batch_styles_updates_all_pages(self, db: Database) -> None:
        batch_id = db.create_batch("Style Batch")
        db.create_page(batch_id, {**SAMPLE_PAGE, "slug": "p1"})
        db.create_page(batch_id, {**SAMPLE_PAGE, "slug": "p2"})
        count = db.apply_batch_styles_to_pages(
            batch_id, color_override="#FF0000", cta_text_override="Book Now"
        )
        assert count == 2
        for page in db.list_pages(batch_id):
            assert page["color_override"] == "#FF0000"
            assert page["cta_text_override"] == "Book Now"

    def test_apply_batch_styles_returns_zero_on_no_updates(self, db: Database) -> None:
        batch_id = db.create_batch("No-op Style Batch")
        count = db.apply_batch_styles_to_pages(batch_id)
        assert count == 0


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------

class TestRevisions:
    def test_record_revision_returns_id(self, db: Database) -> None:
        batch_id = db.create_batch("Rev Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        rev_id = db.record_revision(
            page_id,
            quality_scores_before={"overall_score": 75},
            quality_scores_after={"overall_score": 85},
            change_type="regenerate_section",
            change_reason="Added original data",
        )
        assert isinstance(rev_id, int)

    def test_list_revisions_sequential_numbers(self, db: Database) -> None:
        batch_id = db.create_batch("Rev Seq Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.record_revision(page_id, {}, {"overall_score": 80})
        db.record_revision(page_id, {"overall_score": 80}, {"overall_score": 90})
        revisions = db.list_revisions(page_id)
        assert len(revisions) == 2
        assert revisions[0]["revision_number"] == 1
        assert revisions[1]["revision_number"] == 2

    def test_revision_json_fields_deserialised(self, db: Database) -> None:
        batch_id = db.create_batch("Rev JSON Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        before = {"overall_score": 70, "authority_score": 65}
        after = {"overall_score": 85, "authority_score": 90}
        db.record_revision(page_id, before, after)
        revisions = db.list_revisions(page_id)
        assert isinstance(revisions[0]["quality_scores_before"], dict)
        assert revisions[0]["quality_scores_after"]["overall_score"] == 85


# ---------------------------------------------------------------------------
# Pre-flight checks & deployment
# ---------------------------------------------------------------------------

class TestDeployment:
    def test_preflight_fails_with_no_approved_pages(self, db: Database) -> None:
        batch_id = db.create_batch("Empty Deploy Batch")
        result = db.get_deploy_preflight(batch_id)
        assert result["passed"] is False
        assert result["total_approved"] == 0

    def test_preflight_fails_missing_meta(self, db: Database) -> None:
        batch_id = db.create_batch("Missing Meta Batch")
        page_no_meta = {**SAMPLE_PAGE, "meta_title": "", "meta_description": ""}
        page_id = db.create_page(batch_id, page_no_meta)
        db.update_page_status(page_id, "approved")
        result = db.get_deploy_preflight(batch_id)
        assert result["passed"] is False
        assert any("meta tags" in f for f in result["failures"])

    def test_preflight_passes_all_checks(self, db: Database) -> None:
        batch_id = db.create_batch("Deploy OK Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.update_page_status(page_id, "approved")
        result = db.get_deploy_preflight(batch_id)
        # Should pass meta check (SAMPLE_PAGE has meta_title and meta_description)
        assert result["checks"]["meta_tags_present"] is True
        assert result["total_approved"] == 1

    def test_deploy_batch_marks_pages_deployed(self, db: Database) -> None:
        batch_id = db.create_batch("Deploy Batch")
        page_id = db.create_page(batch_id, SAMPLE_PAGE)
        db.update_page_status(page_id, "approved")
        count = db.deploy_batch(batch_id)
        assert count == 1
        page = db.get_page(page_id)
        assert page["review_status"] == "deployed"
        assert page["deployed_at"] is not None

    def test_deploy_batch_only_deploys_approved_pages(self, db: Database) -> None:
        batch_id = db.create_batch("Partial Deploy Batch")
        p1 = db.create_page(batch_id, {**SAMPLE_PAGE, "slug": "approved-page"})
        p2 = db.create_page(batch_id, {**SAMPLE_PAGE, "slug": "draft-page"})
        db.update_page_status(p1, "approved")
        count = db.deploy_batch(batch_id)
        assert count == 1
        assert db.get_page(p2)["review_status"] == "draft"
