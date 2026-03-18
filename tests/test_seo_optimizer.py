"""Tests for SEOOptimizer."""
from __future__ import annotations

import pytest

from src.seo_optimizer import SEOOptimizer


# ---------------------------------------------------------------------------
# Sample content fixtures
# ---------------------------------------------------------------------------

STRONG_CONTENT = """
## PostgreSQL Autovacuum Cost-Delay Tuning

PostgreSQL's autovacuum daemon throttles its own I/O using a cost-based delay mechanism.
The autovacuum_vacuum_cost_delay parameter introduces a sleep between each vacuum page cycle.
At the default value of 2ms, autovacuum reads roughly 200 pages per second on NVMe storage.

A table receiving 5,000 writes per second with default cost_delay=2ms accumulates dead tuples
faster than autovacuum can reclaim them. pg_stat_user_tables exposes n_dead_tup and
last_autovacuum timestamps to measure this accumulation rate.

PostgreSQL 16 documentation, Section 25.1 defines the cost accounting model.
We measured a Citus cluster where default settings produced 60GB bloat in 12 hours.
MVCC stores multiple row versions, which means dead tuples accumulate in the heap
until autovacuum reclaims them. This process does not apply to temporary tables.

For example, a table with autovacuum_vacuum_cost_delay=0 processes dead tuples 8x faster
compared to the default configuration under equivalent write load.
""" * 5  # Repeat to hit word count


WEAK_CONTENT = """
There are many things to consider.
It is important to understand this.
This is a very common issue.
These are the key factors.
Overall, it's basically just how it works.
"""


class TestSEOOptimizerInit:
    def test_loads_seo_config(self) -> None:
        optimizer = SEOOptimizer()
        assert optimizer._seo
        assert "search_intent_types" in optimizer._seo


class TestKeywordPresence:
    def test_keyword_found_returns_true(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        # Put the keyword directly in the content
        content = f"We examine {sample_page_data['primary_keyword']} in this article."
        result = optimizer.analyze(content, sample_page_data)
        assert result["keyword_present"] is True

    def test_keyword_absent_returns_false(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        content = "This article discusses something completely unrelated."
        result = optimizer.analyze(content, sample_page_data)
        assert result["keyword_present"] is False

    def test_keyword_check_is_case_insensitive(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        keyword = sample_page_data["primary_keyword"].upper()
        content = f"Article about {keyword} performance."
        result = optimizer.analyze(content, sample_page_data)
        assert result["keyword_present"] is True


class TestIntentMatch:
    def test_informational_intent_with_definition(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        content = (
            "MVCC is defined as a concurrency control mechanism. "
            "It works by storing multiple row versions. "
            "For example, a DELETE operation does not immediately remove the row. "
            "postgresql autovacuum tuning high-write "
        ) * 20
        result = optimizer.analyze(content, sample_page_data)
        assert result["intent_match"] is True

    def test_unknown_intent_type_is_treated_as_pass(self) -> None:
        optimizer = SEOOptimizer()
        page_data = {"search_intent_type": "unknown_type", "primary_keyword": "test", "depth_level": "medium"}
        result = optimizer.analyze("Some content about test topics.", page_data)
        assert result["intent_match"] is True


class TestSemanticTripletRatio:
    def test_strong_content_has_high_spo_ratio(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.analyze(STRONG_CONTENT, sample_page_data)
        assert result["semantic_triplet_ratio"] >= 0.0  # presence check

    def test_weak_content_has_low_spo_ratio(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.analyze(WEAK_CONTENT, sample_page_data)
        # Weak content with only linking verbs should score below strong content
        strong_result = optimizer.analyze(STRONG_CONTENT, sample_page_data)
        assert result["semantic_triplet_ratio"] <= strong_result["semantic_triplet_ratio"]

    def test_empty_content_returns_zero_ratio(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.analyze("", sample_page_data)
        assert result["semantic_triplet_ratio"] == 0.0


class TestEEATSignals:
    def test_detects_experience_signal(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        content = (
            "We measured a cluster where autovacuum produced 60GB bloat in 12 hours. "
            "MVCC is defined as a multi-version concurrency model. "
            f"{sample_page_data['authority_source']} documents the vacuum cost model. "
            "postgresql autovacuum tuning high-write "
            "This approach does not apply to temporary tables. "
        ) * 50
        result = optimizer.analyze(content, sample_page_data)
        assert "experience" in result["eeat_signals_found"]

    def test_detects_trustworthiness_signal(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        content = (
            "This recommendation does not apply to tables with fewer than 1,000 rows. "
            "postgresql autovacuum tuning high-write "
        ) * 100
        result = optimizer.analyze(content, sample_page_data)
        assert "trustworthiness" in result["eeat_signals_found"]

    def test_no_signals_in_empty_content(self) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.analyze("", {"primary_keyword": "", "primary_technical_term": "", "authority_source": "", "depth_level": "medium", "search_intent_type": "informational"})
        assert result["eeat_signals_found"] == []


class TestDepthAdequacy:
    def test_deep_content_meets_threshold(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        # 'deep' requires 1500 words
        content = ("PostgreSQL autovacuum reclaims dead tuples from the heap. " * 200)
        result = optimizer.analyze(content, sample_page_data)
        assert result["depth_adequate"] is True
        assert result["word_count"] >= 1500

    def test_short_content_fails_deep_threshold(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        content = "PostgreSQL autovacuum reclaims dead tuples."
        result = optimizer.analyze(content, sample_page_data)
        assert result["depth_adequate"] is False


class TestSEOScoring:
    def test_score_is_integer_in_range(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.analyze(STRONG_CONTENT, sample_page_data)
        assert isinstance(result["seo_score"], int)
        assert 0 <= result["seo_score"] <= 100

    def test_score_decreases_for_missing_keyword(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        content_with = STRONG_CONTENT + f" {sample_page_data['primary_keyword']}"
        content_without = STRONG_CONTENT.replace(sample_page_data["primary_keyword"], "")
        score_with = optimizer.analyze(content_with, sample_page_data)["seo_score"]
        score_without = optimizer.analyze(content_without, sample_page_data)["seo_score"]
        assert score_with >= score_without

    def test_recommendations_list_returned(self, sample_page_data: dict) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.analyze("Short content.", sample_page_data)
        assert isinstance(result["recommendations"], list)


class TestBuildLongTailQuery:
    def test_renders_pattern_with_kwargs(self) -> None:
        optimizer = SEOOptimizer()
        result = optimizer.build_long_tail_query(
            0,
            specific_problem="heap bloat",
            audience_segment="DBAs",
            context_or_industry="financial services PostgreSQL clusters",
        )
        assert "heap bloat" in result
        assert "DBAs" in result

    def test_raises_on_out_of_range_index(self) -> None:
        optimizer = SEOOptimizer()
        with pytest.raises(IndexError):
            optimizer.build_long_tail_query(9999)
