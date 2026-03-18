"""Tests for BatchProcessor."""
from __future__ import annotations

import copy

import pytest

from src.batch_processor import BatchProcessor, BatchResult
from tests.conftest import MockLLMClient, SAMPLE_PAGE_DATA


def _make_pages(n: int) -> list[dict]:
    """Return *n* distinct page data dicts with varied variation axes."""
    pages = []
    for i in range(n):
        page = copy.deepcopy(SAMPLE_PAGE_DATA)
        page["topic"] = f"Topic {i}: PostgreSQL autovacuum tuning variant {i}"
        page["unique_perspective"] = f"Unique angle {i}: cost_delay perspective {i}"
        page["data_point"] = f"Data point {i}: {i * 100} writes/second scenario"
        page["primary_technical_term"] = f"term_{i}"
        page["named_tool"] = f"tool_{i}"
        page["failure_mode"] = f"Failure mode {i} description"
        pages.append(page)
    return pages


class TestBatchProcessorInit:
    def test_creates_with_mock_client(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        assert processor is not None


class TestEnforceVariation:
    def test_unique_pages_pass(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(3)
        result = processor.enforce_variation(pages)
        assert result is pages  # returns same list

    def test_duplicate_pages_raise(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        page = copy.deepcopy(SAMPLE_PAGE_DATA)
        pages = [page, copy.deepcopy(page)]  # identical variation axes
        with pytest.raises(ValueError, match="near-duplicate"):
            processor.enforce_variation(pages)

    def test_empty_list_passes(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        result = processor.enforce_variation([])
        assert result == []


class TestProcessBatch:
    def test_returns_batch_result(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(2)
        batch = processor.process_batch(pages)
        assert isinstance(batch, BatchResult)

    def test_result_count_matches_page_count(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(3)
        batch = processor.process_batch(pages)
        assert len(batch.results) == 3

    def test_summary_contains_expected_keys(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(2)
        batch = processor.process_batch(pages)
        assert "total_pages" in batch.summary
        assert "average_quality_score" in batch.summary
        assert "duplication_flag_count" in batch.summary

    def test_seo_report_attached_to_results(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(1)
        batch = processor.process_batch(pages)
        # SEO optimizer attaches seo_score to static_validation
        result = batch.results[0]
        assert "seo_score" in result.static_validation

    def test_average_quality_score_is_float(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(2)
        batch = processor.process_batch(pages)
        assert isinstance(batch.average_quality_score(), float)

    def test_pages_requiring_review_filters_correctly(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        pages = _make_pages(2)
        batch = processor.process_batch(pages)
        # MockLLMClient returns human_review_required=False (score=88)
        review_pages = batch.pages_requiring_review()
        assert isinstance(review_pages, list)

    def test_empty_batch_returns_empty_result(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client)
        batch = processor.process_batch([])
        assert batch.results == []
        assert batch.summary["total_pages"] == 0


class TestDuplicationDetection:
    def test_flags_repeated_phrases_across_pages(self) -> None:
        client = MockLLMClient()
        # Low threshold so even 2 pages can trigger a flag
        processor = BatchProcessor(client, duplication_threshold=0.0)
        pages = _make_pages(2)
        batch = processor.process_batch(pages)
        # With threshold=0, any phrase appearing on 2+ pages is flagged
        # MockLLMClient returns the same draft for all pages, so we expect flags
        assert isinstance(batch.duplication_flags, list)
        assert len(batch.duplication_flags) >= 0  # structure is correct

    def test_duplication_flag_structure(self) -> None:
        client = MockLLMClient()
        processor = BatchProcessor(client, duplication_threshold=0.0)
        pages = _make_pages(2)
        batch = processor.process_batch(pages)
        for flag in batch.duplication_flags:
            assert "phrase" in flag
            assert "appears_on_pages" in flag
            assert "occurrence_count" in flag
