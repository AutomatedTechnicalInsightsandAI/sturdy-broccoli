"""Tests for the ContentEditor module."""
from __future__ import annotations

import pytest

from src.content_editor import ContentEditor, _keyword_density, _seo_preview, _unified_diff
from src.database import Database


@pytest.fixture
def db() -> Database:
    return Database(":memory:")


@pytest.fixture
def editor(db: Database) -> ContentEditor:
    return ContentEditor(db)


@pytest.fixture
def page_id(db: Database) -> int:
    return db.create_page(
        "blog",
        "SEO Best Practices",
        "seo best practices",
    )


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------


class TestKeywordDensity:
    def test_basic_density(self) -> None:
        text = "seo is great for seo and seo is easy"
        # 9 words, seo appears 3 times: 3/9 * 100 = 33.33%
        assert _keyword_density(text, "seo") == pytest.approx(33.33, rel=0.01)

    def test_multi_word_keyword(self) -> None:
        text = "local seo is great and local seo helps"
        density = _keyword_density(text, "local seo")
        assert density > 0

    def test_empty_text_returns_zero(self) -> None:
        assert _keyword_density("", "seo") == 0.0

    def test_empty_keyword_returns_zero(self) -> None:
        assert _keyword_density("some text here", "") == 0.0

    def test_case_insensitive(self) -> None:
        text = "SEO is great and seo is easy"
        d = _keyword_density(text, "seo")
        assert d > 0


class TestSeoPreview:
    def test_short_title_passes(self) -> None:
        preview = _seo_preview("Short Title", "https://example.com", "Good description under 160 chars")
        assert preview["title_ok"] is True
        assert preview["desc_ok"] is True

    def test_long_title_truncated(self) -> None:
        title = "A" * 70
        preview = _seo_preview(title, "https://example.com", "ok desc")
        assert preview["title_ok"] is False
        assert preview["display_title"].endswith("…")

    def test_long_desc_truncated(self) -> None:
        desc = "D" * 200
        preview = _seo_preview("Title", "https://example.com", desc)
        assert preview["desc_ok"] is False
        assert preview["display_description"].endswith("…")

    def test_returns_all_keys(self) -> None:
        preview = _seo_preview("Title", "https://example.com", "Desc")
        for key in ("display_title", "display_url", "display_description",
                    "title_length", "desc_length", "title_ok", "desc_ok"):
            assert key in preview


class TestUnifiedDiff:
    def test_identical_texts_empty_diff(self) -> None:
        diff = _unified_diff("hello world", "hello world")
        assert diff == ""

    def test_different_texts_has_diff(self) -> None:
        diff = _unified_diff("hello world", "hello earth")
        assert "-" in diff or "+" in diff


# ---------------------------------------------------------------------------
# ContentEditor integration tests
# ---------------------------------------------------------------------------


class TestSaveEdit:
    def test_save_edit_returns_result(self, editor: ContentEditor, page_id: int) -> None:
        result = editor.save_edit(page_id, "# Hello\n\nThis is content about seo best practices.")
        assert result["version"] == 1
        assert isinstance(result["version_id"], int)
        assert isinstance(result["quality_scores"], dict)
        assert result["word_count"] > 0
        assert "saved" in result["message"].lower()

    def test_increments_version(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "First version content with enough words.")
        result = editor.save_edit(page_id, "Second version content with updated words.")
        assert result["version"] == 2

    def test_version_notes_persisted(self, editor: ContentEditor, page_id: int, db: Database) -> None:
        editor.save_edit(page_id, "Content here with notes.", version_notes="Fixed typos")
        versions = db.list_versions(page_id)
        assert versions[0]["version_notes"] == "Fixed typos"

    def test_edited_by_persisted(self, editor: ContentEditor, page_id: int, db: Database) -> None:
        editor.save_edit(page_id, "Content with editor.", edited_by="Alice")
        versions = db.list_versions(page_id)
        assert versions[0]["edited_by"] == "Alice"

    def test_invalid_page_raises(self, editor: ContentEditor) -> None:
        with pytest.raises(ValueError, match="not found"):
            editor.save_edit(9999, "Some content")


class TestGetVersion:
    def test_get_specific_version(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "Version one content.")
        editor.save_edit(page_id, "Version two content.")
        v1 = editor.get_version(page_id, 1)
        assert v1 is not None
        assert v1["version"] == 1
        assert "Version one" in v1["content_markdown"]

    def test_nonexistent_version_returns_none(self, editor: ContentEditor, page_id: int) -> None:
        assert editor.get_version(page_id, 99) is None


class TestListVersions:
    def test_returns_all_versions_ascending(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "First")
        editor.save_edit(page_id, "Second")
        editor.save_edit(page_id, "Third")
        versions = editor.list_versions(page_id)
        assert len(versions) == 3
        assert [v["version"] for v in versions] == [1, 2, 3]

    def test_empty_for_page_with_no_versions(self, editor: ContentEditor, page_id: int) -> None:
        assert editor.list_versions(page_id) == []


class TestGetLatestVersion:
    def test_returns_last(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "Old content")
        editor.save_edit(page_id, "New content")
        latest = editor.get_latest_version(page_id)
        assert latest is not None
        assert latest["version"] == 2

    def test_none_when_no_versions(self, editor: ContentEditor, page_id: int) -> None:
        assert editor.get_latest_version(page_id) is None


class TestScoreContent:
    def test_returns_dict_with_overall(self, editor: ContentEditor) -> None:
        result = editor.score_content("This is some content about SEO best practices.")
        assert isinstance(result, dict)
        assert "overall" in result

    def test_with_page_data(self, editor: ContentEditor) -> None:
        result = editor.score_content(
            "Content about seo.",
            {"primary_keyword": "seo", "topic": "SEO"},
        )
        assert isinstance(result, dict)


class TestBuildSeoPreview:
    def test_returns_preview_dict(self, editor: ContentEditor) -> None:
        preview = editor.build_seo_preview(
            "My Page Title",
            "This is the meta description for the page.",
            "https://example.com/my-page",
        )
        assert preview["display_title"] == "My Page Title"
        assert preview["title_ok"] is True


class TestCompareVersions:
    def test_compare_returns_diff(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "# Hello\n\nOriginal content here.")
        editor.save_edit(page_id, "# Hello\n\nUpdated content here.")
        result = editor.compare_versions(page_id, 1, 2)
        assert result["version_a"] == 1
        assert result["version_b"] == 2
        assert isinstance(result["diff"], str)
        assert result["word_count_delta"] != 0 or result["diff"] != ""

    def test_compare_invalid_version_raises(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "Content")
        with pytest.raises(ValueError):
            editor.compare_versions(page_id, 1, 99)

    def test_word_count_delta(self, editor: ContentEditor, page_id: int) -> None:
        editor.save_edit(page_id, "one two three")
        editor.save_edit(page_id, "one two three four five")
        result = editor.compare_versions(page_id, 1, 2)
        assert result["word_count_delta"] == 2


class TestKeywordDensityMethod:
    def test_method_delegates_to_helper(self, editor: ContentEditor) -> None:
        density = editor.keyword_density("seo is great for seo users", "seo")
        assert density > 0
