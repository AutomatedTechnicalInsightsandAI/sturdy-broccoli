"""Tests for the agency system prompt module."""
from __future__ import annotations

import pytest

from src.agency_system_prompt import (
    LEAD_CONTENT_ARCHITECT_SYSTEM_PROMPT,
    BATCH_GENERATION_SYSTEM_PROMPT,
    get_system_prompt,
)


class TestGetSystemPrompt:
    def test_default_returns_full_prompt(self) -> None:
        prompt = get_system_prompt()
        assert prompt == LEAD_CONTENT_ARCHITECT_SYSTEM_PROMPT

    def test_full_mode_explicit(self) -> None:
        assert get_system_prompt("full") == LEAD_CONTENT_ARCHITECT_SYSTEM_PROMPT

    def test_batch_mode_returns_condensed_prompt(self) -> None:
        prompt = get_system_prompt("batch")
        assert prompt == BATCH_GENERATION_SYSTEM_PROMPT

    def test_full_prompt_contains_quality_standards(self) -> None:
        prompt = get_system_prompt()
        assert "Quality Standards" in prompt
        assert "Information Gain" in prompt
        assert "SILO Structure" in prompt

    def test_full_prompt_mentions_json_output(self) -> None:
        prompt = get_system_prompt()
        assert "content_markdown" in prompt
        assert "schema_json_ld" in prompt

    def test_batch_prompt_mentions_keyword_density(self) -> None:
        prompt = get_system_prompt("batch")
        assert "1.2-1.5%" in prompt

    def test_both_prompts_non_empty(self) -> None:
        assert len(get_system_prompt("full")) > 100
        assert len(get_system_prompt("batch")) > 50
