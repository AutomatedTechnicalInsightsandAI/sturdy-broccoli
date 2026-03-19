"""Tests for the BatchValidator (hub-and-spoke structure validation)."""
from __future__ import annotations

import pytest

from src.batch_validator import BatchValidator, BatchValidationResult, ValidationIssue


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

HUB_PAGE = {
    "slug": "postgresql-optimisation",
    "title": "PostgreSQL Performance Optimisation",
    "h1_content": "PostgreSQL Performance Optimisation Services",
    "primary_keyword": "postgresql optimisation",
    "content_markdown": (
        "Professional database services can dramatically improve the speed and "
        "reliability of your application. Our postgresql optimisation service helps "
        "companies reduce query execution times by up to 90%.\n\n"
        "## What We Cover\n"
        "We analyse indexes, vacuum settings, connection limits, and query plans. "
        "Every recommendation is tailored to your workload and infrastructure.\n\n"
        "## Related Topics\n"
        "- [EXPLAIN ANALYZE Guide](/explain-analyze-guide)\n"
        "- [Autovacuum Tuning](/autovacuum-tuning)\n"
        "- [Connection Pooling PgBouncer](/connection-pooling-pgbouncer)\n"
        "Learn more about the benefits of systematic database tuning in our guides.\n"
        "Contact our team for a free assessment of your database environment.\n"
    ),
    "internal_links": [
        "explain-analyze-guide",
        "autovacuum-tuning",
        "connection-pooling-pgbouncer",
    ],
    "schema_json_ld": {"@context": "https://schema.org", "@type": "Service"},
    "is_hub": True,
}

SPOKE_1 = {
    "slug": "explain-analyze-guide",
    "title": "PostgreSQL EXPLAIN ANALYZE: A Practical Guide",
    "primary_keyword": "postgresql optimisation",
    "content_markdown": (
        "Use EXPLAIN ANALYZE to understand how the query planner works. "
        "Reading the output helps engineers spot sequential scans, "
        "inefficient joins, and missing indexes. This process is a key part of "
        "postgresql optimisation methodology that high-performance teams rely on. "
        "With the right tooling you can quickly identify bottlenecks and "
        "implement fixes that reduce query latency by significant margins. "
        "For a broader overview see our [postgresql optimisation]"
        "(/postgresql-optimisation) guide.\n"
    ),
    "internal_links": ["postgresql-optimisation"],
    "schema_json_ld": {"@context": "https://schema.org", "@type": "Article"},
    "hub_page_id": 1,
}

SPOKE_2 = {
    "slug": "autovacuum-tuning",
    "title": "Autovacuum Tuning for High-Write Tables",
    "primary_keyword": "postgresql optimisation",
    "content_markdown": (
        "Autovacuum prevents table bloat caused by dead tuples accumulating "
        "over time in high-write workloads. Correct settings depend on the "
        "write volume, dead tuple ratio, and available maintenance resources. "
        "Poorly tuned autovacuum leads to slow queries and index fragmentation, "
        "which is why it is central to any postgresql optimisation strategy. "
        "Combine autovacuum tuning with our other recommendations for best results. "
        "See the full [postgresql optimisation](/postgresql-optimisation) overview.\n"
    ),
    "internal_links": ["postgresql-optimisation"],
    "schema_json_ld": {"@context": "https://schema.org", "@type": "Article"},
    "hub_page_id": 1,
}

SPOKE_3 = {
    "slug": "connection-pooling-pgbouncer",
    "title": "Connection Pooling with PgBouncer",
    "primary_keyword": "postgresql optimisation",
    "content_markdown": (
        "PgBouncer manages a pool of server connections and reuses them "
        "across many client requests, dramatically reducing the overhead of "
        "establishing new connections under high concurrency. "
        "This technique is complementary to postgresql optimisation at the "
        "query and schema level. Combined, they allow your application to "
        "scale without exhausting database resources. "
        "Return to our [postgresql optimisation](/postgresql-optimisation) hub "
        "for the full picture of tuning strategies.\n"
    ),
    "internal_links": ["postgresql-optimisation"],
    "schema_json_ld": {"@context": "https://schema.org", "@type": "Article"},
    "hub_page_id": 1,
}

VALID_BATCH = [HUB_PAGE, SPOKE_1, SPOKE_2, SPOKE_3]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBatchValidatorValid:
    def test_valid_batch_passes(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        assert result.valid is True

    def test_result_has_correct_hub(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        assert result.hub_slug == "postgresql-optimisation"

    def test_result_counts_spokes(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        assert result.spoke_count == 3

    def test_schema_valid_when_all_pages_have_schema(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        assert result.schema_valid is True

    def test_no_orphaned_pages(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        assert result.orphaned_pages == []


class TestBatchValidatorErrors:
    def test_empty_pages_returns_error(self) -> None:
        validator = BatchValidator()
        result = validator.validate([])
        assert result.valid is False
        assert result.has_errors()

    def test_too_few_spokes_is_error(self) -> None:
        batch = [HUB_PAGE, SPOKE_1, SPOKE_2]  # only 2 spokes, min is 3
        validator = BatchValidator()
        result = validator.validate(batch, hub_slug="postgresql-optimisation")
        assert result.has_errors()

    def test_missing_hub_to_spoke_link_is_error(self) -> None:
        hub_no_links = {**HUB_PAGE, "internal_links": [], "content_markdown": "no links here"}
        batch = [hub_no_links, SPOKE_1, SPOKE_2, SPOKE_3]
        validator = BatchValidator()
        result = validator.validate(batch, hub_slug="postgresql-optimisation")
        assert result.has_errors()
        error_msgs = [i.message for i in result.issues if i.severity == "error"]
        assert any("does not link to spoke" in m for m in error_msgs)

    def test_missing_backlink_is_error(self) -> None:
        spoke_no_backlink = {**SPOKE_1, "internal_links": [], "content_markdown": "no links"}
        batch = [HUB_PAGE, spoke_no_backlink, SPOKE_2, SPOKE_3]
        validator = BatchValidator()
        result = validator.validate(batch, hub_slug="postgresql-optimisation")
        assert result.has_errors()
        error_msgs = [i.message for i in result.issues if i.severity == "error"]
        assert any("does not link back to hub" in m for m in error_msgs)

    def test_invalid_hub_slug_returns_error(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="nonexistent-slug")
        assert result.valid is False
        assert result.has_errors()


class TestBatchValidatorReport:
    def test_report_contains_valid_status(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        report = result.to_report()
        assert "Hub-and-Spoke Structure" in report

    def test_report_shows_issue_count(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        report = result.to_report()
        assert "Issues Found:" in report

    def test_report_shows_spoke_count(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        report = result.to_report()
        assert "3 sub-pages" in report

    def test_to_dict_is_serialisable(self) -> None:
        import json
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH, hub_slug="postgresql-optimisation")
        d = result.to_dict()
        # Should not raise
        json.dumps(d)
        assert "valid" in d
        assert "spoke_count" in d


class TestSchemaValidation:
    def test_missing_schema_is_warning(self) -> None:
        spoke_no_schema = {**SPOKE_1, "schema_json_ld": None}
        batch = [HUB_PAGE, spoke_no_schema, SPOKE_2, SPOKE_3]
        validator = BatchValidator()
        result = validator.validate(batch, hub_slug="postgresql-optimisation")
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert any("schema" in w.message.lower() for w in warnings)

    def test_schema_as_json_string(self) -> None:
        import json
        spoke_str_schema = {
            **SPOKE_1,
            "schema_json_ld": json.dumps({"@context": "https://schema.org", "@type": "Article"}),
        }
        batch = [HUB_PAGE, spoke_str_schema, SPOKE_2, SPOKE_3]
        validator = BatchValidator()
        result = validator.validate(batch, hub_slug="postgresql-optimisation")
        # String schema should be treated as valid
        schema_warnings = [
            i for i in result.issues
            if i.severity == "warning" and i.page_slug == "explain-analyze-guide"
            and "schema" in i.message.lower()
        ]
        assert schema_warnings == []


class TestAutoHubDetection:
    def test_auto_detect_hub_from_is_hub_flag(self) -> None:
        validator = BatchValidator()
        result = validator.validate(VALID_BATCH)  # no hub_slug provided
        # Should detect HUB_PAGE because it has is_hub=True
        assert result.hub_slug == "postgresql-optimisation"
