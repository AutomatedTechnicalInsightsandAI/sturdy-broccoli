"""
tests/test_staging_manager.py

Unit tests for src/staging_manager.py — SEO Site Factory staging layer.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.staging_manager import StagingManager, _slugify


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mgr(tmp_path: Path) -> StagingManager:
    return StagingManager(db_path=tmp_path / "staging_test.db")


def _sample_pages(n: int = 3) -> list[dict]:
    pages = []
    for i in range(n):
        pages.append(
            {
                "title": f"Landing Page {i+1}",
                "topic": f"Topic {i+1}",
                "primary_keyword": "seo agency",
                "h1_content": f"H1 for page {i+1}",
                "meta_title": f"Meta Title {i+1}",
                "meta_description": f"Meta description for page {i+1}.",
                "content_markdown": f"## Section\nContent for page {i+1}.",
            }
        )
    return pages


# ---------------------------------------------------------------------------
# Slugify helper
# ---------------------------------------------------------------------------


def test_slugify_basic() -> None:
    assert _slugify("Hello World") == "hello-world"


def test_slugify_special_chars() -> None:
    assert _slugify("NFT Consultant: Guide!") == "nft-consultant-guide"


# ---------------------------------------------------------------------------
# Batch creation
# ---------------------------------------------------------------------------


def test_create_batch_returns_id(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("My Batch", _sample_pages(3))
    assert isinstance(batch_id, int)
    assert batch_id > 0


def test_batch_pages_are_pending(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Pending Batch", _sample_pages(5))
    pages = mgr.list_pages(batch_id=batch_id)
    assert len(pages) == 5
    assert all(p["status"] == "pending_review" for p in pages)


def test_batch_counts_updated(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Count Batch", _sample_pages(4))
    batch = mgr.get_batch(batch_id)
    assert batch["total_pages"] == 4
    assert batch["pages_pending"] == 4


def test_slugs_are_unique(mgr: StagingManager) -> None:
    # Two pages with the same title should get different slugs
    pages = [{"title": "Same Title", "topic": "T", "primary_keyword": "kw"} for _ in range(3)]
    batch_id = mgr.create_batch_from_pages("Dup Slugs", pages)
    result = mgr.list_pages(batch_id=batch_id)
    slugs = [p["slug"] for p in result]
    assert len(set(slugs)) == 3


# ---------------------------------------------------------------------------
# Stub page generation
# ---------------------------------------------------------------------------


def test_generate_stub_pages(mgr: StagingManager) -> None:
    stubs = mgr.generate_stub_pages("Local SEO", "local seo agency", count=10)
    assert len(stubs) == 10
    for stub in stubs:
        assert "title" in stub
        assert "content_markdown" in stub
        assert len(stub["content_markdown"]) > 50


# ---------------------------------------------------------------------------
# Preview rendering
# ---------------------------------------------------------------------------


def test_render_page_preview_returns_html(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Preview Batch", _sample_pages(1))
    pages = mgr.list_pages(batch_id=batch_id)
    page_id = pages[0]["id"]
    html = mgr.render_page_preview(page_id)
    assert "<html" in html.lower()
    assert "H1 for page 1" in html


def test_render_with_template_override(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Tpl Batch", _sample_pages(1))
    page_id = mgr.list_pages(batch_id=batch_id)[0]["id"]
    for tpl in ("modern_saas", "professional_service", "content_guide", "ecommerce", "enterprise"):
        html = mgr.render_page_preview(page_id, template_override=tpl)
        assert "<html" in html.lower()


def test_render_unknown_page_raises(mgr: StagingManager) -> None:
    with pytest.raises(ValueError, match="not found"):
        mgr.render_page_preview(9999)


# ---------------------------------------------------------------------------
# Markdown update
# ---------------------------------------------------------------------------


def test_update_page_markdown(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("MD Batch", _sample_pages(1))
    page_id = mgr.list_pages(batch_id=batch_id)[0]["id"]
    new_md = "## Updated\nThis is updated content with many words " * 20
    mgr.update_page_markdown(page_id, new_md)
    page = mgr.get_page(page_id)
    assert page["content_markdown"] == new_md
    assert page["word_count"] > 50
    assert "<h2" in page["content_html"].lower()


# ---------------------------------------------------------------------------
# Batch style application
# ---------------------------------------------------------------------------


def test_apply_batch_style(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Style Batch", _sample_pages(3))
    pages = mgr.list_pages(batch_id=batch_id)
    ids = [p["id"] for p in pages]
    count = mgr.apply_batch_style(ids, brand_color="red", cta_link="https://example.com/cta")
    assert count == 3
    for pid in ids:
        page = mgr.get_page(pid)
        state = page["preview_state"]
        assert state["color_override"] == "red"
        assert state["cta_link"] == "https://example.com/cta"


def test_apply_batch_style_template(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Tpl Style Batch", _sample_pages(2))
    pages = mgr.list_pages(batch_id=batch_id)
    ids = [p["id"] for p in pages]
    mgr.apply_batch_style(ids, template="enterprise")
    for pid in ids:
        page = mgr.get_page(pid)
        assert page["assigned_template"] == "enterprise"


def test_apply_batch_style_empty_ids(mgr: StagingManager) -> None:
    count = mgr.apply_batch_style([], brand_color="green")
    assert count == 0


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_approve_pages(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("Approve Batch", _sample_pages(3))
    pages = mgr.list_pages(batch_id=batch_id)
    ids = [p["id"] for p in pages[:2]]
    mgr.approve_pages(ids)
    for pid in ids:
        page = mgr.get_page(pid)
        assert page["status"] == "approved"
    # third page still pending
    third = mgr.get_page(pages[2]["id"])
    assert third["status"] == "pending_review"


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------


def test_deploy_batch(mgr: StagingManager) -> None:
    pages_data = _sample_pages(3)
    batch_id = mgr.create_batch_from_pages("Deploy Batch", pages_data)
    pages = mgr.list_pages(batch_id=batch_id)
    # Approve first two
    mgr.approve_pages([pages[0]["id"], pages[1]["id"]])
    manifest = mgr.deploy_batch(batch_id)
    assert manifest["deployed_count"] == 2
    assert len(manifest["pages"]) == 2
    assert "deployed_at" in manifest
    # Verify each deployed page has a URL
    for p in manifest["pages"]:
        assert p["url"].startswith("/pages/")
    batch = mgr.get_batch(batch_id)
    assert batch["pages_deployed"] == 2


def test_deploy_batch_no_approved(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("No Deploy Batch", _sample_pages(2))
    manifest = mgr.deploy_batch(batch_id)
    assert manifest["deployed_count"] == 0


def test_generate_deployment_csv(mgr: StagingManager) -> None:
    batch_id = mgr.create_batch_from_pages("CSV Batch", _sample_pages(2))
    pages = mgr.list_pages(batch_id=batch_id)
    mgr.approve_pages([p["id"] for p in pages])
    manifest = mgr.deploy_batch(batch_id)
    csv = mgr.generate_deployment_csv(manifest)
    lines = csv.strip().splitlines()
    assert lines[0].startswith("title,slug,url")
    assert len(lines) == 3  # header + 2 pages


# ---------------------------------------------------------------------------
# Template listing
# ---------------------------------------------------------------------------


def test_list_templates(mgr: StagingManager) -> None:
    templates = mgr.list_templates()
    assert "modern_saas" in templates
    assert "enterprise" in templates
    assert len(templates) == 5
