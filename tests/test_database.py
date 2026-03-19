"""Tests for the Database persistence layer."""
from __future__ import annotations

import pytest

from src.database import Database


@pytest.fixture
def db() -> Database:
    """Return a fresh in-memory database for each test."""
    return Database(":memory:")


# ---------------------------------------------------------------------------
# Schema / initialisation
# ---------------------------------------------------------------------------


class TestDatabaseInit:
    def test_creates_instance(self, db: Database) -> None:
        assert db is not None

    def test_schema_initialised_no_error(self) -> None:
        db = Database(":memory:")
        # Re-running init should be idempotent
        db._init_schema()

    def test_in_memory_flag(self) -> None:
        db = Database(":memory:")
        assert db._db_path == ":memory:"


# ---------------------------------------------------------------------------
# Client management
# ---------------------------------------------------------------------------


class TestClients:
    def test_create_client_returns_int(self, db: Database) -> None:
        cid = db.create_client("Acme Corp", "acme-corp")
        assert isinstance(cid, int)
        assert cid >= 1

    def test_get_client_returns_dict(self, db: Database) -> None:
        cid = db.create_client("Acme Corp", "acme-corp", "https://acme.com")
        client = db.get_client(cid)
        assert client is not None
        assert client["name"] == "Acme Corp"
        assert client["slug"] == "acme-corp"
        assert client["website"] == "https://acme.com"

    def test_get_nonexistent_client_returns_none(self, db: Database) -> None:
        assert db.get_client(9999) is None

    def test_list_clients_empty(self, db: Database) -> None:
        assert db.list_clients() == []

    def test_list_clients_multiple(self, db: Database) -> None:
        db.create_client("Beta Ltd", "beta-ltd")
        db.create_client("Alpha Inc", "alpha-inc")
        clients = db.list_clients()
        assert len(clients) == 2
        # Should be sorted by name
        assert clients[0]["name"] == "Alpha Inc"
        assert clients[1]["name"] == "Beta Ltd"

    def test_duplicate_slug_raises(self, db: Database) -> None:
        db.create_client("First", "same-slug")
        with pytest.raises(Exception):
            db.create_client("Second", "same-slug")


# ---------------------------------------------------------------------------
# Page management
# ---------------------------------------------------------------------------


class TestPages:
    def test_create_page_returns_int(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Local SEO for Plumbers", "local seo plumber")
        assert isinstance(pid, int)
        assert pid >= 1

    def test_get_page_returns_dict(self, db: Database) -> None:
        pid = db.create_page(
            "local_seo",
            "Local SEO for Dentists",
            "local seo dentist",
            page_type="landing_page",
        )
        page = db.get_page(pid)
        assert page is not None
        assert page["service_type"] == "local_seo"
        assert page["topic"] == "Local SEO for Dentists"
        assert page["primary_keyword"] == "local seo dentist"
        assert page["status"] == "draft"
        assert page["page_type"] == "landing_page"
        assert isinstance(page["metadata"], dict)

    def test_get_nonexistent_page_returns_none(self, db: Database) -> None:
        assert db.get_page(9999) is None

    def test_create_page_with_client(self, db: Database) -> None:
        cid = db.create_client("Test Client", "test-client")
        pid = db.create_page("digital_pr", "Digital PR", client_id=cid)
        page = db.get_page(pid)
        assert page is not None
        assert page["client_id"] == cid

    def test_create_page_with_metadata(self, db: Database) -> None:
        meta = {"target_region": "UK", "competitor_urls": ["https://example.com"]}
        pid = db.create_page("geo_ai_seo", "GEO SEO", metadata=meta)
        page = db.get_page(pid)
        assert page is not None
        assert page["metadata"]["target_region"] == "UK"
        assert "competitor_urls" in page["metadata"]

    def test_list_pages_empty(self, db: Database) -> None:
        assert db.list_pages() == []

    def test_list_pages_returns_all(self, db: Database) -> None:
        db.create_page("local_seo", "Page A", "kw-a")
        db.create_page("digital_pr", "Page B", "kw-b")
        pages = db.list_pages()
        assert len(pages) == 2

    def test_list_pages_filter_by_status(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Draft Page", "kw")
        db.update_page_status(pid, "published")
        db.create_page("local_seo", "Draft Page 2", "kw2")
        published = db.list_pages(status="published")
        drafts = db.list_pages(status="draft")
        assert len(published) == 1
        assert len(drafts) == 1

    def test_list_pages_filter_by_service_type(self, db: Database) -> None:
        db.create_page("local_seo", "Local SEO Page", "kw")
        db.create_page("digital_pr", "Digital PR Page", "kw")
        local_seo_pages = db.list_pages(service_type="local_seo")
        assert len(local_seo_pages) == 1
        assert local_seo_pages[0]["service_type"] == "local_seo"

    def test_list_pages_filter_by_client(self, db: Database) -> None:
        cid = db.create_client("Client A", "client-a")
        db.create_page("local_seo", "Client A Page", client_id=cid)
        db.create_page("local_seo", "No Client Page")
        client_pages = db.list_pages(client_id=cid)
        assert len(client_pages) == 1

    def test_update_page_status(self, db: Database) -> None:
        pid = db.create_page("local_seo", "My Page", "kw")
        db.update_page_status(pid, "published")
        page = db.get_page(pid)
        assert page is not None
        assert page["status"] == "published"

    def test_update_page_status_invalid_raises(self, db: Database) -> None:
        pid = db.create_page("local_seo", "My Page", "kw")
        with pytest.raises(Exception):
            db.update_page_status(pid, "invalid_status")

    def test_update_page_metadata_merges(self, db: Database) -> None:
        pid = db.create_page("local_seo", "My Page", metadata={"key1": "val1"})
        db.update_page_metadata(pid, {"key2": "val2"})
        page = db.get_page(pid)
        assert page is not None
        assert page["metadata"]["key1"] == "val1"
        assert page["metadata"]["key2"] == "val2"

    def test_update_metadata_nonexistent_page_raises(self, db: Database) -> None:
        with pytest.raises(ValueError, match="not found"):
            db.update_page_metadata(9999, {"key": "val"})

    def test_delete_page(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page to Delete", "kw")
        db.delete_page(pid)
        assert db.get_page(pid) is None

    def test_delete_page_cascades_versions(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page with Version", "kw")
        db.save_content_version(pid, content_markdown="Some content here")
        db.delete_page(pid)
        # Versions should also be gone
        assert db.list_versions(pid) == []


# ---------------------------------------------------------------------------
# Content versions
# ---------------------------------------------------------------------------


class TestContentVersions:
    def test_save_version_returns_int(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        vid = db.save_content_version(pid, content_markdown="Hello world content here")
        assert isinstance(vid, int)
        assert vid >= 1

    def test_auto_increments_version_number(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        db.save_content_version(pid, content_markdown="Version 1")
        db.save_content_version(pid, content_markdown="Version 2")
        versions = db.list_versions(pid)
        assert len(versions) == 2
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2

    def test_get_latest_version(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        db.save_content_version(pid, content_markdown="First content text")
        db.save_content_version(pid, content_markdown="Updated content text here")
        latest = db.get_latest_version(pid)
        assert latest is not None
        assert latest["version"] == 2
        assert "Updated" in latest["content_markdown"]

    def test_get_latest_version_none_if_no_versions(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        assert db.get_latest_version(pid) is None

    def test_word_count_computed_from_markdown(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        text = "This is a ten word markdown content string for test"
        db.save_content_version(pid, content_markdown=text)
        version = db.get_latest_version(pid)
        assert version is not None
        assert version["word_count"] == 10

    def test_quality_report_stored_and_retrieved(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        report = {"quality_score": 85, "violations": []}
        db.save_content_version(pid, content_markdown="Content", quality_report=report)
        version = db.get_latest_version(pid)
        assert version is not None
        assert version["quality_report"]["quality_score"] == 85

    def test_html_and_markdown_both_stored(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        db.save_content_version(
            pid,
            content_html="<h1>Title</h1>",
            content_markdown="# Title",
        )
        version = db.get_latest_version(pid)
        assert version is not None
        assert "<h1>" in version["content_html"]
        assert "# Title" in version["content_markdown"]


# ---------------------------------------------------------------------------
# Competitor cache
# ---------------------------------------------------------------------------


class TestCompetitorCache:
    def test_cache_and_retrieve(self, db: Database) -> None:
        analysis = {"competitors": ["Thrive", "WebFX"], "gaps": ["pricing"]}
        db.cache_competitor_analysis("Local SEO", analysis)
        result = db.get_competitor_analysis("Local SEO")
        assert result is not None
        assert result["competitors"] == ["Thrive", "WebFX"]

    def test_expired_cache_returns_none(self, db: Database) -> None:
        analysis = {"data": "old"}
        db.cache_competitor_analysis("Old Topic", analysis, ttl_hours=0)
        # With ttl_hours=0, expires_at == created_at, so it's immediately expired
        result = db.get_competitor_analysis("Old Topic")
        assert result is None

    def test_missing_topic_returns_none(self, db: Database) -> None:
        assert db.get_competitor_analysis("Nonexistent Topic") is None

    def test_returns_most_recent_valid_entry(self, db: Database) -> None:
        db.cache_competitor_analysis("SEO", {"v": 1})
        db.cache_competitor_analysis("SEO", {"v": 2})
        result = db.get_competitor_analysis("SEO")
        assert result is not None
        assert result["v"] == 2


# ---------------------------------------------------------------------------
# Quality scores
# ---------------------------------------------------------------------------


class TestQualityScores:
    def test_save_and_retrieve(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        scores = {
            "authority": 70.0,
            "semantic": 65.0,
            "structure": 80.0,
            "engagement": 55.0,
            "uniqueness": 90.0,
            "overall": 73.0,
        }
        db.save_quality_scores(pid, scores)
        retrieved = db.get_latest_quality_scores(pid)
        assert retrieved is not None
        assert retrieved["authority"] == 70.0
        assert retrieved["overall"] == 73.0

    def test_get_latest_scores_no_records_returns_none(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        assert db.get_latest_quality_scores(pid) is None

    def test_most_recent_scores_returned(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        db.save_quality_scores(pid, {"overall": 50.0})
        db.save_quality_scores(pid, {"overall": 75.0})
        scores = db.get_latest_quality_scores(pid)
        assert scores is not None
        assert scores["overall"] == 75.0


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


class TestDashboardStats:
    def test_empty_db_returns_zeros(self, db: Database) -> None:
        stats = db.get_dashboard_stats()
        assert stats["total_pages"] == 0
        assert stats["published_pages"] == 0
        assert stats["draft_pages"] == 0
        assert stats["total_words"] == 0
        assert stats["avg_quality_score"] == 0.0

    def test_counts_pages_correctly(self, db: Database) -> None:
        pid1 = db.create_page("local_seo", "Page 1", "kw1")
        pid2 = db.create_page("local_seo", "Page 2", "kw2")
        db.update_page_status(pid1, "published")
        stats = db.get_dashboard_stats()
        assert stats["total_pages"] == 2
        assert stats["published_pages"] == 1
        assert stats["draft_pages"] == 1

    def test_total_words_sums_latest_versions(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        db.save_content_version(pid, content_markdown="one two three four five")
        stats = db.get_dashboard_stats()
        assert stats["total_words"] == 5

    def test_client_scoped_stats(self, db: Database) -> None:
        cid = db.create_client("Agency A", "agency-a")
        db.create_page("local_seo", "Client Page", client_id=cid)
        db.create_page("digital_pr", "Other Page")  # no client
        client_stats = db.get_dashboard_stats(client_id=cid)
        all_stats = db.get_dashboard_stats()
        assert client_stats["total_pages"] == 1
        assert all_stats["total_pages"] == 2

    def test_avg_quality_score(self, db: Database) -> None:
        pid = db.create_page("local_seo", "Page", "kw")
        db.save_quality_scores(pid, {"overall": 80.0})
        stats = db.get_dashboard_stats()
        assert stats["avg_quality_score"] == 80.0
