"""
tests/test_database.py

Unit tests for src/database.py — SQLite persistence layer.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.database import Database


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.db")


# ---------------------------------------------------------------------------
# Batch tests
# ---------------------------------------------------------------------------


def test_create_and_get_batch(db: Database) -> None:
    batch_id = db.create_batch("Test Batch", description="A test batch", created_by="pytest")
    assert isinstance(batch_id, int)
    batch = db.get_batch(batch_id)
    assert batch is not None
    assert batch["name"] == "Test Batch"
    assert batch["description"] == "A test batch"
    assert batch["created_by"] == "pytest"


def test_list_batches(db: Database) -> None:
    db.create_batch("Batch A")
    db.create_batch("Batch B")
    batches = db.list_batches()
    assert len(batches) == 2
    names = {b["name"] for b in batches}
    assert names == {"Batch A", "Batch B"}


def test_update_batch_counts(db: Database) -> None:
    batch_id = db.create_batch("Count Batch")
    db.create_page({"batch_id": batch_id, "title": "P1", "slug": "p1", "topic": "T", "primary_keyword": "kw"})
    db.create_page({"batch_id": batch_id, "title": "P2", "slug": "p2", "topic": "T", "primary_keyword": "kw"})
    db.update_batch_counts(batch_id)
    batch = db.get_batch(batch_id)
    assert batch["total_pages"] == 2
    assert batch["pages_pending"] == 2


# ---------------------------------------------------------------------------
# Page tests
# ---------------------------------------------------------------------------


def test_create_and_get_page(db: Database) -> None:
    batch_id = db.create_batch("Page Batch")
    page_id = db.create_page(
        {
            "batch_id": batch_id,
            "title": "My Landing Page",
            "slug": "my-landing-page",
            "topic": "SEO",
            "primary_keyword": "seo agency",
            "h1_content": "The Best SEO Agency",
            "meta_title": "Best SEO Agency | YourBrand",
            "meta_description": "We help you rank.",
            "content_markdown": "## Hello\nWorld",
            "quality_scores": {"overall": 75},
        }
    )
    assert isinstance(page_id, int)
    page = db.get_page(page_id)
    assert page is not None
    assert page["title"] == "My Landing Page"
    assert page["status"] == "pending_review"
    assert page["quality_scores"]["overall"] == 75


def test_update_page_status(db: Database) -> None:
    batch_id = db.create_batch("Status Batch")
    page_id = db.create_page({"batch_id": batch_id, "title": "P", "slug": "p", "topic": "T", "primary_keyword": "kw"})
    db.set_page_status(page_id, "approved")
    page = db.get_page(page_id)
    assert page["status"] == "approved"


def test_bulk_set_status(db: Database) -> None:
    batch_id = db.create_batch("Bulk Batch")
    ids = []
    for i in range(3):
        ids.append(
            db.create_page({"batch_id": batch_id, "title": f"P{i}", "slug": f"p{i}", "topic": "T", "primary_keyword": "kw"})
        )
    db.bulk_set_status(ids, "reviewed")
    pages = db.list_pages(batch_id=batch_id)
    assert all(p["status"] == "reviewed" for p in pages)


def test_list_pages_filter_by_status(db: Database) -> None:
    batch_id = db.create_batch("Filter Batch")
    db.create_page({"batch_id": batch_id, "title": "A", "slug": "a", "topic": "T", "primary_keyword": "kw", "status": "pending_review"})
    db.create_page({"batch_id": batch_id, "title": "B", "slug": "b", "topic": "T", "primary_keyword": "kw", "status": "approved"})
    pending = db.list_pages(batch_id=batch_id, status="pending_review")
    approved = db.list_pages(batch_id=batch_id, status="approved")
    assert len(pending) == 1
    assert len(approved) == 1


def test_bulk_update_preview_state(db: Database) -> None:
    batch_id = db.create_batch("Preview Batch")
    ids = [
        db.create_page({"batch_id": batch_id, "title": "X", "slug": "x", "topic": "T", "primary_keyword": "kw"}),
        db.create_page({"batch_id": batch_id, "title": "Y", "slug": "y", "topic": "T", "primary_keyword": "kw"}),
    ]
    db.bulk_update_preview_state(ids, {"color_override": "green", "cta_link": "https://example.com"})
    for pid in ids:
        page = db.get_page(pid)
        state = page["preview_state"]
        assert state["color_override"] == "green"
        assert state["cta_link"] == "https://example.com"


def test_bulk_set_template(db: Database) -> None:
    batch_id = db.create_batch("Template Batch")
    ids = [
        db.create_page({"batch_id": batch_id, "title": "A", "slug": "a2", "topic": "T", "primary_keyword": "kw"}),
        db.create_page({"batch_id": batch_id, "title": "B", "slug": "b2", "topic": "T", "primary_keyword": "kw"}),
    ]
    db.bulk_set_template(ids, "enterprise")
    for pid in ids:
        page = db.get_page(pid)
        assert page["assigned_template"] == "enterprise"


def test_deploy_approved_pages(db: Database) -> None:
    batch_id = db.create_batch("Deploy Batch")
    pid1 = db.create_page({"batch_id": batch_id, "title": "P1", "slug": "p1d", "topic": "T", "primary_keyword": "kw"})
    pid2 = db.create_page({"batch_id": batch_id, "title": "P2", "slug": "p2d", "topic": "T", "primary_keyword": "kw"})
    db.set_page_status(pid1, "approved")
    db.set_page_status(pid2, "reviewed")  # not approved — should not deploy

    deployed = db.deploy_approved_pages(batch_id)
    assert len(deployed) == 1
    assert deployed[0]["slug"] == "p1d"
    page1 = db.get_page(pid1)
    assert page1["status"] == "deployed"
    page2 = db.get_page(pid2)
    assert page2["status"] == "reviewed"


def test_delete_page(db: Database) -> None:
    batch_id = db.create_batch("Del Batch")
    pid = db.create_page({"batch_id": batch_id, "title": "ToDelete", "slug": "to-delete", "topic": "T", "primary_keyword": "kw"})
    db.delete_page(pid)
    assert db.get_page(pid) is None


def test_slug_unique_constraint(db: Database) -> None:
    batch_id = db.create_batch("Slug Batch")
    db.create_page({"batch_id": batch_id, "title": "X", "slug": "unique-slug", "topic": "T", "primary_keyword": "kw"})
    with pytest.raises(Exception):
        db.create_page({"batch_id": batch_id, "title": "Y", "slug": "unique-slug", "topic": "T", "primary_keyword": "kw"})
