"""Tests for ContentGenerator."""
from __future__ import annotations

import json

import pytest

from src.content_generator import ContentGenerator, GenerationResult, LLMClient
from tests.conftest import MockLLMClient


class TestLLMClientProtocol:
    def test_mock_satisfies_protocol(self) -> None:
        client = MockLLMClient()
        assert isinstance(client, LLMClient)

    def test_invalid_client_raises_on_construction(self) -> None:
        with pytest.raises(TypeError, match="LLMClient protocol"):
            ContentGenerator(object())  # type: ignore[arg-type]


class TestGenerationResult:
    def test_quality_score_defaults_to_zero(self) -> None:
        result = GenerationResult(page_data={})
        assert result.quality_score == 0

    def test_human_review_defaults_to_true(self) -> None:
        result = GenerationResult(page_data={})
        assert result.human_review_required is True

    def test_word_count_from_final_content(self) -> None:
        result = GenerationResult(page_data={}, final_content="one two three four five")
        assert result.word_count == 5

    def test_word_count_from_quality_report(self) -> None:
        result = GenerationResult(
            page_data={},
            final_content="one two three",
            quality_report={"word_count": 999},
        )
        assert result.word_count == 999


class TestContentGenerator:
    def test_generate_returns_generation_result(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert isinstance(result, GenerationResult)

    def test_outline_is_parsed_as_dict(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert isinstance(result.outline, dict)
        assert "sections" in result.outline

    def test_research_is_parsed_as_dict(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert isinstance(result.research, dict)

    def test_final_content_is_non_empty_string(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert isinstance(result.final_content, str)
        assert len(result.final_content) > 50

    def test_quality_report_contains_score(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert "quality_score" in result.quality_report
        assert isinstance(result.quality_report["quality_score"], int)

    def test_static_validation_runs(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert "word_count" in result.static_validation
        assert "violations" in result.static_validation

    def test_high_quality_score_means_no_review(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        # MockLLMClient returns quality_score=88, human_review_required=false
        assert result.quality_score == 88
        assert result.human_review_required is False

    def test_page_data_preserved_in_result(
        self, mock_llm_client: MockLLMClient, sample_page_data: dict
    ) -> None:
        gen = ContentGenerator(mock_llm_client)
        result = gen.generate(sample_page_data)
        assert result.page_data["topic"] == sample_page_data["topic"]


class TestParseJsonResponse:
    def test_parses_fenced_json(self) -> None:
        response = '```json\n{"key": "value"}\n```'
        result = ContentGenerator._parse_json_response(response, "test")
        assert result == {"key": "value"}

    def test_parses_bare_json(self) -> None:
        response = 'Here is the result:\n{"key": "value"}\nDone.'
        result = ContentGenerator._parse_json_response(response, "test")
        assert result == {"key": "value"}

    def test_falls_back_to_raw_on_invalid_json(self) -> None:
        response = "This is not JSON at all."
        result = ContentGenerator._parse_json_response(response, "test")
        assert result == {"raw": response}


class TestParsePolishResponse:
    def test_splits_json_and_article(self) -> None:
        article = "## Section\n\nSome content here."
        response = f'```json\n{{"quality_score": 90}}\n```\n\n{article}'
        report, content = ContentGenerator._parse_polish_response(response)
        assert report["quality_score"] == 90
        assert article in content

    def test_falls_back_when_no_json(self) -> None:
        response = "Just article text, no JSON."
        report, content = ContentGenerator._parse_polish_response(response)
        assert report == {}
        assert content == response
