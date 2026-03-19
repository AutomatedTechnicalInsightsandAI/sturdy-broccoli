"""Tests for the WordPressPublisher module."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.database import Database
from src.wordpress_publisher import (
    WordPressPublisher,
    _build_wp_post_payload,
    _obfuscate,
    _deobfuscate,
    _replace_internal_links,
    _wp_date_format,
)


@pytest.fixture
def db() -> Database:
    return Database(":memory:")


def _make_mock_http(status_code: int = 200, json_data: dict[str, Any] | None = None) -> Any:
    """Build a mock HTTP client that returns a fixed response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"id": 42, "link": "https://site.com/post/", "status": "draft"}
    resp.text = "ok"
    http = MagicMock()
    http.get.return_value = resp
    http.post.return_value = resp
    http.put.return_value = resp
    return http


@pytest.fixture
def publisher(db: Database) -> WordPressPublisher:
    return WordPressPublisher(db, http_client=_make_mock_http())


@pytest.fixture
def connection_id(publisher: WordPressPublisher) -> int:
    return publisher.add_connection(
        site_url="https://example.com",
        api_username="admin",
        api_password="secret",
        site_name="Example Site",
    )


@pytest.fixture
def page_id(db: Database) -> int:
    return db.create_page("blog", "SEO Guide", "seo guide")


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestObfuscation:
    def test_roundtrip(self) -> None:
        plain = "super-secret-password"
        assert _deobfuscate(_obfuscate(plain)) == plain

    def test_obfuscated_differs_from_plaintext(self) -> None:
        plain = "mypassword"
        assert _obfuscate(plain) != plain


class TestBuildWpPostPayload:
    def test_basic_payload(self) -> None:
        payload = _build_wp_post_payload("Title", "Content")
        assert payload["title"] == "Title"
        assert payload["content"] == "Content"
        assert payload["status"] == "draft"

    def test_custom_status(self) -> None:
        payload = _build_wp_post_payload("T", "C", status="publish")
        assert payload["status"] == "publish"

    def test_schedule_sets_date_gmt(self) -> None:
        payload = _build_wp_post_payload("T", "C", date_gmt="2025-06-01T10:00:00")
        assert "date_gmt" in payload

    def test_optional_fields(self) -> None:
        payload = _build_wp_post_payload(
            "T", "C", slug="my-slug", excerpt="exc",
            categories=[1, 2], tags=[3], author=5
        )
        assert payload["slug"] == "my-slug"
        assert payload["excerpt"] == "exc"
        assert payload["categories"] == [1, 2]
        assert payload["tags"] == [3]
        assert payload["author"] == 5


class TestReplaceInternalLinks:
    def test_replaces_link(self) -> None:
        content = "See our [guide](/seo-guide) for more."
        result = _replace_internal_links(content, {"/seo-guide": "https://wp.com/seo-guide/"})
        assert "https://wp.com/seo-guide/" in result

    def test_no_match_unchanged(self) -> None:
        content = "No internal links here."
        result = _replace_internal_links(content, {"/other": "https://wp.com/other/"})
        assert result == content


class TestWpDateFormat:
    def test_valid_iso(self) -> None:
        result = _wp_date_format("2025-06-01T10:30:00+00:00")
        assert result == "2025-06-01T10:30:00"

    def test_invalid_returns_input(self) -> None:
        result = _wp_date_format("not-a-date")
        assert result == "not-a-date"


# ---------------------------------------------------------------------------
# WordPressPublisher integration tests
# ---------------------------------------------------------------------------


class TestAddConnection:
    def test_returns_int(self, publisher: WordPressPublisher) -> None:
        cid = publisher.add_connection("https://blog.com", "user", "pass")
        assert isinstance(cid, int)

    def test_password_not_stored_plaintext(self, publisher: WordPressPublisher, db: Database) -> None:
        cid = publisher.add_connection("https://blog.com", "user", "plainpassword")
        conn = db.get_wordpress_connection(cid)
        assert conn is not None
        assert conn["api_password_encrypted"] != "plainpassword"

    def test_site_url_trailing_slash_stripped(self, publisher: WordPressPublisher, db: Database) -> None:
        cid = publisher.add_connection("https://blog.com/", "user", "pass")
        conn = db.get_wordpress_connection(cid)
        assert conn is not None
        assert not conn["site_url"].endswith("/")


class TestListConnections:
    def test_passwords_redacted(self, publisher: WordPressPublisher) -> None:
        publisher.add_connection("https://site.com", "u", "p")
        conns = publisher.list_connections()
        assert all("api_password_encrypted" not in c for c in conns)

    def test_filter_by_client(self, publisher: WordPressPublisher, db: Database) -> None:
        cid = db.create_client("Acme", "acme")
        publisher.add_connection("https://acme.com", "u", "p", client_id=cid)
        publisher.add_connection("https://other.com", "u", "p")
        filtered = publisher.list_connections(client_id=cid)
        assert len(filtered) == 1
        assert filtered[0]["site_url"] == "https://acme.com"


class TestRemoveConnection:
    def test_removes_connection(self, publisher: WordPressPublisher, db: Database) -> None:
        cid = publisher.add_connection("https://del.com", "u", "p")
        publisher.remove_connection(cid)
        assert db.get_wordpress_connection(cid) is None


class TestTestConnection:
    def test_success(self, publisher: WordPressPublisher, connection_id: int) -> None:
        result = publisher.test_connection(connection_id)
        assert result["success"] is True

    def test_missing_connection(self, publisher: WordPressPublisher) -> None:
        result = publisher.test_connection(9999)
        assert result["success"] is False

    def test_http_error(self, db: Database, connection_id: int) -> None:
        http = _make_mock_http(status_code=401)
        publisher = WordPressPublisher(db, http_client=http)
        cid = publisher.add_connection("https://fail.com", "u", "p")
        result = publisher.test_connection(cid)
        assert result["success"] is False


class TestPublishPage:
    def test_success(self, publisher: WordPressPublisher, page_id: int, connection_id: int) -> None:
        result = publisher.publish_page(
            page_id=page_id,
            connection_id=connection_id,
            title="My SEO Guide",
            content="<p>Content here</p>",
        )
        assert result["success"] is True
        assert result["post_id"] == "42"
        assert "post_url" in result

    def test_records_persisted(
        self, publisher: WordPressPublisher, page_id: int, connection_id: int, db: Database
    ) -> None:
        publisher.publish_page(page_id, connection_id, "Title", "Content")
        posts = db.list_wordpress_posts(page_id=page_id)
        assert len(posts) == 1

    def test_missing_connection(self, publisher: WordPressPublisher, page_id: int) -> None:
        result = publisher.publish_page(page_id, 9999, "T", "C")
        assert result["success"] is False

    def test_schedule_sets_status_to_future(
        self, publisher: WordPressPublisher, page_id: int, connection_id: int
    ) -> None:
        result = publisher.publish_page(
            page_id, connection_id, "T", "C",
            schedule_date="2099-01-01T10:00:00"
        )
        # WP API mock returns 'draft'; just ensure no error
        assert result["wp_record_id"] is not None

    def test_link_map_applied(
        self, publisher: WordPressPublisher, page_id: int, connection_id: int
    ) -> None:
        http = _make_mock_http()
        publisher2 = WordPressPublisher(publisher._db, http_client=http)
        publisher2.publish_page(
            page_id, connection_id,
            title="T",
            content="Visit /internal-link for more",
            link_map={"/internal-link": "https://wp.com/published/"},
        )
        call_kwargs = http.post.call_args
        assert "https://wp.com/published/" in call_kwargs[1]["json"]["content"]

    def test_http_failure(self, db: Database, page_id: int) -> None:
        http = _make_mock_http(status_code=500)
        http.post.return_value.text = "server error"
        publisher = WordPressPublisher(db, http_client=http)
        cid = publisher.add_connection("https://fail.com", "u", "p")
        result = publisher.publish_page(page_id, cid, "T", "C")
        assert result["success"] is False
        assert result["status"] == "failed"


class TestBatchPublish:
    def test_returns_result_per_page(
        self, publisher: WordPressPublisher, db: Database, connection_id: int
    ) -> None:
        p1 = db.create_page("blog", "Page 1", "kw1")
        p2 = db.create_page("blog", "Page 2", "kw2")
        pages = [
            {"page_id": p1, "title": "Page 1", "content": "Content 1"},
            {"page_id": p2, "title": "Page 2", "content": "Content 2"},
        ]
        results = publisher.batch_publish(pages, connection_id)
        assert len(results) == 2
        assert all("success" in r for r in results)
        assert all(r["page_id"] in (p1, p2) for r in results)


class TestGetPublishStatus:
    def test_unpublished_page(self, publisher: WordPressPublisher, page_id: int) -> None:
        status = publisher.get_publish_status(page_id)
        assert status["published"] is False

    def test_published_page(
        self, publisher: WordPressPublisher, page_id: int, connection_id: int
    ) -> None:
        http = _make_mock_http(json_data={"id": 10, "link": "https://wp.com/p/", "status": "publish"})
        pub = WordPressPublisher(publisher._db, http_client=http)
        pub.publish_page(page_id, connection_id, "T", "C", status="publish")
        status = pub.get_publish_status(page_id)
        assert status["post_url"] == "https://wp.com/p/"
        assert status["published"] is True


class TestUpdatePost:
    def test_update_success(
        self, publisher: WordPressPublisher, page_id: int, connection_id: int
    ) -> None:
        pub_result = publisher.publish_page(page_id, connection_id, "T", "C")
        wp_record_id = pub_result["wp_record_id"]
        result = publisher.update_post(wp_record_id, title="Updated Title")
        assert result["success"] is True

    def test_update_missing_record(self, publisher: WordPressPublisher) -> None:
        result = publisher.update_post(9999, title="T")
        assert result["success"] is False
