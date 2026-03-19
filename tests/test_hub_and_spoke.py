"""Tests for the hub-and-spoke additions to PromptBuilder and BatchProcessor."""
from __future__ import annotations

import pytest

from src.prompt_builder import PromptBuilder
from src.batch_processor import HubAndSpokeProcessor, HubAndSpokeResult
from tests.conftest import MockLLMClient, SAMPLE_PAGE_DATA


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

HUB_PAGE_DATA = {
    **SAMPLE_PAGE_DATA,
    "service_name": "PostgreSQL Performance Optimisation",
    "page_type": "landing_page",
    "h2_sections": [
        "Why Query Optimisation Matters",
        "Our PostgreSQL Tuning Process",
        "Case Studies",
    ],
    "trust_factors": [
        "15 years PostgreSQL experience",
        "200+ databases tuned",
    ],
    "related_services": ["Database Monitoring", "Query Caching"],
}

SPOKE_TOPICS = [
    "PostgreSQL EXPLAIN ANALYZE: A Practical Guide",
    "Autovacuum Tuning for High-Write Tables",
    "Connection Pooling with PgBouncer",
]


# ---------------------------------------------------------------------------
# PromptBuilder hub-and-spoke methods
# ---------------------------------------------------------------------------


class TestBuildHubPrompt:
    def test_returns_non_empty_string(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_hub_prompt(HUB_PAGE_DATA)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_primary_keyword(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_hub_prompt(HUB_PAGE_DATA)
        assert HUB_PAGE_DATA["primary_keyword"] in prompt

    def test_contains_service_name(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_hub_prompt(HUB_PAGE_DATA)
        assert "PostgreSQL Performance Optimisation" in prompt

    def test_raises_on_missing_required_field(self) -> None:
        builder = PromptBuilder()
        incomplete = dict(HUB_PAGE_DATA)
        del incomplete["primary_keyword"]
        with pytest.raises(ValueError, match="missing required fields"):
            builder.build_hub_prompt(incomplete)

    def test_h2_sections_included_in_prompt(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_hub_prompt(HUB_PAGE_DATA)
        assert "Why Query Optimisation Matters" in prompt


class TestBuildSpokePrompts:
    def test_returns_list_of_dicts(self) -> None:
        builder = PromptBuilder()
        results = builder.build_spoke_prompts(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)

    def test_count_matches_spoke_topics(self) -> None:
        builder = PromptBuilder()
        results = builder.build_spoke_prompts(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert len(results) == len(SPOKE_TOPICS)

    def test_each_result_has_required_keys(self) -> None:
        builder = PromptBuilder()
        results = builder.build_spoke_prompts(HUB_PAGE_DATA, SPOKE_TOPICS)
        for r in results:
            assert "topic" in r
            assert "spoke_number" in r
            assert "hub_keyword" in r
            assert "prompt" in r

    def test_spoke_numbers_are_sequential(self) -> None:
        builder = PromptBuilder()
        results = builder.build_spoke_prompts(HUB_PAGE_DATA, SPOKE_TOPICS)
        numbers = [r["spoke_number"] for r in results]
        assert numbers == list(range(1, len(SPOKE_TOPICS) + 1))

    def test_hub_keyword_in_each_spoke_prompt(self) -> None:
        builder = PromptBuilder()
        results = builder.build_spoke_prompts(HUB_PAGE_DATA, SPOKE_TOPICS)
        for r in results:
            assert HUB_PAGE_DATA["primary_keyword"] in r["prompt"]

    def test_empty_spoke_topics_returns_empty_list(self) -> None:
        builder = PromptBuilder()
        results = builder.build_spoke_prompts(HUB_PAGE_DATA, [])
        assert results == []


class TestBuildThoughtLeadershipPrompt:
    def test_returns_non_empty_string(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_thought_leadership_prompt(HUB_PAGE_DATA)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_default_title_includes_topic(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_thought_leadership_prompt(HUB_PAGE_DATA)
        assert "Ultimate Guide" in prompt

    def test_custom_title_used_when_provided(self) -> None:
        builder = PromptBuilder()
        custom_title = "The Definitive PostgreSQL Performance Handbook"
        prompt = builder.build_thought_leadership_prompt(HUB_PAGE_DATA, guide_title=custom_title)
        assert custom_title in prompt

    def test_word_count_target_mentioned(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_thought_leadership_prompt(HUB_PAGE_DATA)
        assert "5,000" in prompt or "7,000" in prompt

    def test_raises_on_missing_required_field(self) -> None:
        builder = PromptBuilder()
        incomplete = dict(HUB_PAGE_DATA)
        del incomplete["topic"]
        with pytest.raises(ValueError, match="missing required fields"):
            builder.build_thought_leadership_prompt(incomplete)


# ---------------------------------------------------------------------------
# HubAndSpokeProcessor
# ---------------------------------------------------------------------------


class TestHubAndSpokeProcessorInit:
    def test_creates_with_mock_client(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        assert processor is not None

    def test_include_thought_leadership_default_true(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        assert processor._include_tl is True

    def test_include_thought_leadership_can_be_disabled(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client, include_thought_leadership=False)
        assert processor._include_tl is False


class TestGenerateCluster:
    def test_returns_hub_and_spoke_result(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert isinstance(result, HubAndSpokeResult)

    def test_hub_is_generated(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert result.hub is not None

    def test_spoke_count_matches_topics(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert len(result.spokes) == len(SPOKE_TOPICS)

    def test_thought_leadership_generated_by_default(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert result.thought_leadership is not None

    def test_thought_leadership_skipped_when_disabled(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client, include_thought_leadership=False)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert result.thought_leadership is None

    def test_internal_linking_strategy_populated(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert len(result.internal_linking_strategy) == len(SPOKE_TOPICS)

    def test_content_outlines_populated(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert len(result.content_outlines) == len(SPOKE_TOPICS)

    def test_summary_contains_expected_keys(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert "hub_quality_score" in result.summary
        assert "spoke_count" in result.summary
        assert "total_word_count" in result.summary

    def test_total_word_count_is_positive(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        assert result.total_word_count() > 0

    def test_all_results_returns_list(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, SPOKE_TOPICS)
        all_results = result.all_results()
        assert isinstance(all_results, list)
        # hub + spokes + thought_leadership
        assert len(all_results) == 1 + len(SPOKE_TOPICS) + 1

    def test_empty_spoke_topics_produces_zero_spokes(self) -> None:
        client = MockLLMClient()
        processor = HubAndSpokeProcessor(client)
        result = processor.generate_cluster(HUB_PAGE_DATA, [])
        assert result.spokes == []
        assert result.internal_linking_strategy == []
