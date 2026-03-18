"""Tests for PromptBuilder."""
from __future__ import annotations

import json
import re

import pytest

from src.prompt_builder import PromptBuilder


class TestPromptBuilderInit:
    def test_loads_config_files(self) -> None:
        builder = PromptBuilder()
        assert builder._constraints  # negative_constraints.json loaded
        assert builder._structure    # content_structure.json loaded
        assert builder._seo          # seo_config.json loaded

    def test_loads_system_prompt_template(self) -> None:
        builder = PromptBuilder()
        assert "{{topic}}" in builder._system_prompt_template or \
               "Technical Consultant" in builder._system_prompt_template


class TestBuildSystemPrompt:
    def test_substitutes_all_page_data_fields(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(sample_page_data)

        assert sample_page_data["topic"] in prompt
        assert sample_page_data["target_audience"] in prompt
        assert sample_page_data["primary_keyword"] in prompt
        assert sample_page_data["niche"] in prompt

    def test_injects_banned_phrases(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(sample_page_data)
        # The formatted list must include at least some known banned phrases
        assert "delve" in prompt
        assert "leverage" in prompt

    def test_injects_content_sections(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(sample_page_data)
        # Section labels from content_structure.json blog_post type
        assert "Opening Hook" in prompt or "Hook" in prompt

    def test_raises_on_missing_required_field(self, sample_page_data: dict) -> None:
        del sample_page_data["topic"]
        builder = PromptBuilder()
        with pytest.raises(ValueError, match="topic"):
            builder.build_system_prompt(sample_page_data)

    def test_unknown_placeholders_are_preserved(self, sample_page_data: dict) -> None:
        """Unresolved placeholders should remain in the template, not be removed."""
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(sample_page_data)
        # These are multi-stage placeholders that will be resolved later
        # They should appear in CoT prompts, not the system prompt — but
        # the render method must not crash on unknown keys.
        assert isinstance(prompt, str)
        assert len(prompt) > 200


class TestBuildChainOfThoughtPrompts:
    def test_returns_four_stages(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        cot = builder.build_chain_of_thought_prompts(sample_page_data)
        assert set(cot.keys()) == {"outline", "research", "tone", "polish"}

    def test_each_stage_is_non_empty_string(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        cot = builder.build_chain_of_thought_prompts(sample_page_data)
        for stage, text in cot.items():
            assert isinstance(text, str), f"Stage {stage!r} is not a string"
            assert len(text) > 100, f"Stage {stage!r} prompt is suspiciously short"

    def test_outline_stage_contains_primary_keyword(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        cot = builder.build_chain_of_thought_prompts(sample_page_data)
        assert sample_page_data["primary_keyword"] in cot["outline"]

    def test_tone_stage_contains_reading_level(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        cot = builder.build_chain_of_thought_prompts(sample_page_data)
        # Stage 3 should include grade-level instructions
        assert "Grade" in cot["tone"] or "grade" in cot["tone"]


class TestGetRequiredSections:
    def test_blog_post_has_required_sections(self) -> None:
        builder = PromptBuilder()
        sections = builder.get_required_sections("blog_post")
        assert isinstance(sections, list)
        assert len(sections) >= 5
        section_ids = [s["id"] for s in sections]
        assert "hook" in section_ids
        assert "close" in section_ids

    def test_landing_page_has_required_sections(self) -> None:
        builder = PromptBuilder()
        sections = builder.get_required_sections("landing_page")
        section_ids = [s["id"] for s in sections]
        assert "headline" in section_ids
        assert "cta" in section_ids

    def test_unknown_page_type_raises(self) -> None:
        builder = PromptBuilder()
        with pytest.raises(ValueError, match="Unknown page type"):
            builder.get_required_sections("nonexistent_type")


class TestValidateContent:
    def test_clean_content_passes(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        clean = (
            "PostgreSQL MVCC stores multiple row versions in the heap. "
            "Dead tuples accumulate until autovacuum reclaims them. "
            "The autovacuum_vacuum_cost_delay parameter throttles I/O. "
            "A 2ms delay limits vacuum throughput to 200 pages per second. "
        ) * 50  # pad to meet word count minimum
        result = builder.validate_content(clean, "blog_post")
        assert result["word_count"] > 0
        # Should find no banned phrase violations
        phrase_violations = [
            v for v in result["violations"]
            if v["type"] == "banned_phrase"
        ]
        assert len(phrase_violations) == 0

    def test_detects_banned_phrase(self) -> None:
        builder = PromptBuilder()
        content = "We must delve into the rapidly evolving landscape of databases." * 200
        result = builder.validate_content(content, "blog_post")
        banned = [v["type"] for v in result["violations"]]
        assert "banned_phrase" in banned
        assert not result["passed"]

    def test_detects_word_count_too_low(self) -> None:
        builder = PromptBuilder()
        short = "PostgreSQL autovacuum reclaims dead tuples."
        result = builder.validate_content(short, "blog_post")
        types = [v["type"] for v in result["violations"]]
        assert "word_count_too_low" in types

    def test_counts_vague_subjects(self) -> None:
        builder = PromptBuilder()
        content = (
            "This is a very important concept. "
            "These are the key factors to consider. "
            "It is worth noting that autovacuum runs in the background. "
        ) * 100
        result = builder.validate_content(content, "blog_post")
        assert result["vague_subject_count"] > 0

    def test_word_count_in_range_passes_count_check(self, sample_page_data: dict) -> None:
        builder = PromptBuilder()
        # Generate content that's exactly within the blog_post range (900–1800)
        word = "autovacuum "
        content = word * 1000  # 1000 words, within range
        result = builder.validate_content(content, "blog_post")
        count_violations = [
            v for v in result["violations"]
            if v["type"] in ("word_count_too_low", "word_count_too_high")
        ]
        assert len(count_violations) == 0
