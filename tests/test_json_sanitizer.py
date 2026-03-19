"""Tests for the JSON sanitizer module."""
from __future__ import annotations

import json

import pytest

from src.json_sanitizer import (
    clean_ai_json,
    sanitize_field,
    sanitize_content_fields,
)


class TestCleanAiJson:
    def test_parses_valid_json(self) -> None:
        raw = '{"title": "Hello", "h1": "World"}'
        result = clean_ai_json(raw)
        assert result == {"title": "Hello", "h1": "World"}

    def test_strips_code_fence(self) -> None:
        raw = '```json\n{"title": "Test"}\n```'
        result = clean_ai_json(raw)
        assert result is not None
        assert result["title"] == "Test"

    def test_strips_code_fence_no_language(self) -> None:
        raw = "```\n{\"key\": \"value\"}\n```"
        result = clean_ai_json(raw)
        assert result is not None
        assert result["key"] == "value"

    def test_handles_trailing_comma(self) -> None:
        raw = '{"title": "Hello", "h1": "World",}'
        result = clean_ai_json(raw)
        assert result is not None
        assert result["title"] == "Hello"

    def test_handles_literal_newline_in_string(self) -> None:
        # Literal newline inside a string value (not escape sequence)
        raw = '{"content": "line one\nline two"}'
        result = clean_ai_json(raw)
        assert result is not None
        assert "line one" in result["content"]

    def test_handles_literal_tab_in_string(self) -> None:
        raw = '{"content": "col1\tcol2"}'
        result = clean_ai_json(raw)
        assert result is not None
        assert "col1" in result["content"]

    def test_strips_bom(self) -> None:
        raw = "\ufeff{\"title\": \"BOM test\"}"
        result = clean_ai_json(raw)
        assert result is not None
        assert result["title"] == "BOM test"

    def test_extracts_json_from_prose_prefix(self) -> None:
        raw = 'Here is your JSON output:\n{"title": "Result"}\nThat is all.'
        result = clean_ai_json(raw)
        assert result is not None
        assert result["title"] == "Result"

    def test_returns_none_for_empty_string(self) -> None:
        assert clean_ai_json("") is None

    def test_returns_none_for_unparseable_input(self) -> None:
        assert clean_ai_json("this is not json at all!") is None

    def test_handles_control_characters(self) -> None:
        # \x01 is a control character that should be stripped
        raw = '{"title": "Hello\x01World"}'
        result = clean_ai_json(raw)
        assert result is not None
        assert "\x01" not in result["title"]

    def test_nested_json_object(self) -> None:
        raw = '{"title": "Test", "schema": {"@type": "Article"}}'
        result = clean_ai_json(raw)
        assert result is not None
        assert result["schema"]["@type"] == "Article"


class TestSanitizeField:
    def test_removes_control_characters(self) -> None:
        val = "hello\x00\x01\x1fworld"
        cleaned = sanitize_field(val)
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        assert "\x1f" not in cleaned
        assert "hello" in cleaned
        assert "world" in cleaned

    def test_preserves_normal_text(self) -> None:
        val = "Hello World! 123 αβγ"
        assert sanitize_field(val) == val

    def test_preserves_newlines_and_tabs(self) -> None:
        val = "line1\nline2\ttabbed"
        cleaned = sanitize_field(val)
        assert "\n" in cleaned
        assert "\t" in cleaned


class TestSanitizeContentFields:
    def test_sanitizes_all_string_values(self) -> None:
        data = {
            "title": "Hello\x00World",
            "body": "Clean text",
            "count": 42,
        }
        cleaned = sanitize_content_fields(data)
        assert "\x00" not in cleaned["title"]
        assert cleaned["body"] == "Clean text"
        assert cleaned["count"] == 42

    def test_handles_nested_dict(self) -> None:
        data = {"outer": {"inner": "text\x01here"}}
        cleaned = sanitize_content_fields(data)
        assert "\x01" not in cleaned["outer"]["inner"]

    def test_handles_list_values(self) -> None:
        data = {"items": ["clean", "bad\x02item"]}
        cleaned = sanitize_content_fields(data)
        assert "\x02" not in cleaned["items"][1]
