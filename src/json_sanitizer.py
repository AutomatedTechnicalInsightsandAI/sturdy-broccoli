"""
json_sanitizer.py

Agency-grade JSON cleaner for AI-generated output.

AI models frequently return JSON with hidden control characters, unescaped
quotes, stray newlines inside string values, or other formatting issues that
break ``json.loads``.  This module provides a robust sanitiser that forces
AI output into database-safe, parse-safe JSON.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex helpers (compiled once for performance)
# ---------------------------------------------------------------------------

# Control characters U+0000–U+001F, excluding permitted whitespace (\t \n \r)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# JSON code-fence wrapper that some models produce
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# Trailing commas before closing brace/bracket (invalid JSON)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def clean_ai_json(raw_string: str) -> dict[str, Any] | None:
    """
    Parse and sanitise a raw AI-generated JSON string.

    Handles:
    - Markdown code fences (```json ... ```)
    - Control characters that break SQLite / ``json.loads``
    - Unescaped tab / newline characters inside string values
    - Trailing commas (``{"key": "value",}``)
    - Nested HTML in content fields (preserved as-is, just escaped properly)
    - BOM characters at the start of the string

    Parameters
    ----------
    raw_string:
        The raw text returned by an LLM.

    Returns
    -------
    dict or None
        Parsed dictionary on success, or ``None`` on failure (error is logged).
    """
    if not raw_string or not raw_string.strip():
        logger.warning("json_sanitizer: received empty string")
        return None

    cleaned = raw_string

    # 1. Strip BOM
    cleaned = cleaned.lstrip("\ufeff")

    # 2. Extract JSON from code fences if present
    fence_match = _CODE_FENCE_RE.search(cleaned)
    if fence_match:
        cleaned = fence_match.group(1)

    # 3. Find the outermost JSON object or array
    start = cleaned.find("{")
    if start == -1:
        start = cleaned.find("[")
    if start != -1:
        cleaned = cleaned[start:]
        # Trim anything after the closing brace/bracket
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if end != -1:
            cleaned = cleaned[: end + 1]

    # 4. Remove control characters (keep \t, \n, \r — handled below)
    cleaned = _CTRL_RE.sub("", cleaned)

    # 5. Attempt fast parse first — may succeed for well-formed output
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 6. Fix trailing commas
    cleaned = _TRAILING_COMMA_RE.sub(r"\1", cleaned)

    # 7. Second parse attempt after trailing-comma fix
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 8. Aggressive repair: replace literal tabs and newlines inside strings
    #    with their JSON escape sequences.  We walk char by char to stay
    #    inside string boundaries only.
    cleaned = _repair_string_whitespace(cleaned)

    try:
        result = json.loads(cleaned)
        return result
    except json.JSONDecodeError as exc:
        logger.error(
            "json_sanitizer: failed to parse AI JSON after all repair attempts. "
            "Error: %s | First 200 chars: %.200s",
            exc,
            raw_string,
        )
        return None


def sanitize_field(value: str) -> str:
    """
    Sanitise a single string field for safe storage in SQLite.

    Strips control characters while preserving printable ASCII, extended
    Unicode, and standard whitespace (spaces, newlines, tabs).

    Parameters
    ----------
    value:
        Raw string value (e.g. from a parsed JSON field).

    Returns
    -------
    str
        Sanitised string.
    """
    return _CTRL_RE.sub("", value)


def sanitize_content_fields(page_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Walk a page dictionary and sanitise all string values.

    Recursively handles nested dicts and lists.  Non-string values are
    returned unchanged.

    Parameters
    ----------
    page_dict:
        Dictionary of page fields, typically parsed from AI output.

    Returns
    -------
    dict
        New dictionary with all string values sanitised.
    """
    return _sanitize_recursive(page_dict)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _sanitize_recursive(obj: Any) -> Any:
    if isinstance(obj, str):
        return sanitize_field(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_recursive(item) for item in obj]
    return obj


def _repair_string_whitespace(text: str) -> str:
    """
    Replace literal newlines and tabs inside JSON string values with ``\\n``
    and ``\\t`` escape sequences.

    This is a character-level scanner that only modifies content inside
    double-quoted strings, leaving structural JSON characters untouched.
    """
    result: list[str] = []
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == "\\":
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if in_string:
            if char == "\n":
                result.append("\\n")
            elif char == "\r":
                result.append("\\r")
            elif char == "\t":
                result.append("\\t")
            else:
                result.append(char)
        else:
            result.append(char)

    return "".join(result)
