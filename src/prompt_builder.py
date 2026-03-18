"""
prompt_builder.py

Assembles LLM prompts by combining Markdown prompt templates with
page-specific variable data and injected constraint rules.

The builder enforces:
- Variable-driven specificity (each page gets unique data-point anchors)
- Negative constraint injection (banned phrases formatted for prompt inclusion)
- Content structure validation (required sections present and within word targets)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Root paths resolved relative to this file's location
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _REPO_ROOT / "prompts"
_CONFIG_DIR = _REPO_ROOT / "config"


class PromptBuilder:
    """
    Assembles a complete, variable-substituted prompt for a single content page.

    Usage::

        builder = PromptBuilder()
        prompt = builder.build_system_prompt(page_data)
    """

    _REQUIRED_PAGE_FIELDS = {
        "topic",
        "target_audience",
        "search_intent_type",
        "primary_keyword",
        "niche",
        "niche_terminology",
        "unique_perspective",
        "data_point",
        "named_tool",
        "failure_mode",
        "depth_level",
        "experience_signal",
        "primary_technical_term",
        "authority_source",
        "secondary_keywords",
        "page_type",
    }

    def __init__(self) -> None:
        self._constraints = self._load_json("negative_constraints.json")
        self._structure = self._load_json("content_structure.json")
        self._seo = self._load_json("seo_config.json")
        self._system_prompt_template = self._load_prompt("system_prompt.md")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_system_prompt(self, page_data: dict[str, Any]) -> str:
        """
        Return the fully assembled system prompt for one content page.

        Parameters
        ----------
        page_data:
            Dictionary of page-specific variables.  Must contain every key
            listed in ``_REQUIRED_PAGE_FIELDS``.

        Returns
        -------
        str
            The rendered prompt text, ready to send to an LLM.
        """
        self._validate_page_data(page_data)
        substitutions = self._build_substitutions(page_data)
        return self._render_template(self._system_prompt_template, substitutions)

    def build_chain_of_thought_prompts(
        self, page_data: dict[str, Any]
    ) -> dict[str, str]:
        """
        Return all four chain-of-thought stage prompts for one content page.

        Parameters
        ----------
        page_data:
            Dictionary of page-specific variables.

        Returns
        -------
        dict[str, str]
            Keys are stage names ('outline', 'research', 'tone', 'polish');
            values are the rendered prompt texts.
        """
        self._validate_page_data(page_data)
        substitutions = self._build_substitutions(page_data)

        stages = {
            "outline": "chain_of_thought/01_outline.md",
            "research": "chain_of_thought/02_research_extraction.md",
            "tone": "chain_of_thought/03_tone_application.md",
            "polish": "chain_of_thought/04_final_polish.md",
        }

        return {
            stage_name: self._render_template(
                self._load_prompt(template_path), substitutions
            )
            for stage_name, template_path in stages.items()
        }

    def get_required_sections(self, page_type: str) -> list[dict[str, Any]]:
        """
        Return the required sections definition for a given page type.

        Parameters
        ----------
        page_type:
            One of the page types defined in ``content_structure.json``
            (e.g. ``'blog_post'``, ``'landing_page'``).
        """
        page_types = self._structure.get("page_types", {})
        if page_type not in page_types:
            raise ValueError(
                f"Unknown page type '{page_type}'. "
                f"Available types: {list(page_types.keys())}"
            )
        return page_types[page_type]["required_sections"]

    def get_page_type_structure(self, page_type: str) -> dict[str, Any]:
        """
        Return the full structure definition for a given page type.

        Includes ``required_sections``, ``total_word_range``, and
        ``variation_axes`` as defined in ``content_structure.json``.

        Parameters
        ----------
        page_type:
            One of the page types defined in ``content_structure.json``
            (e.g. ``'blog_post'``, ``'landing_page'``).

        Raises
        ------
        ValueError
            If *page_type* is not found in the configuration.
        """
        page_types = self._structure.get("page_types", {})
        if page_type not in page_types:
            raise ValueError(
                f"Unknown page type '{page_type}'. "
                f"Available types: {list(page_types.keys())}"
            )
        return page_types[page_type]

    def validate_content(self, content: str, page_type: str) -> dict[str, Any]:
        """
        Run static validation checks on generated content without calling an LLM.

        Checks performed:
        - Banned phrase presence
        - Vague sentence-subject detection
        - Approximate word count vs. target range

        Parameters
        ----------
        content:
            The generated article text.
        page_type:
            Page type key used to look up word-count targets.

        Returns
        -------
        dict
            ``{'passed': bool, 'violations': list, 'word_count': int,
               'vague_subject_count': int}``
        """
        violations = []
        word_count = len(content.split())

        # Check banned phrases (case-insensitive)
        for phrase in self._constraints.get("blacklisted_phrases", []):
            if phrase.lower() in content.lower():
                violations.append(
                    {"type": "banned_phrase", "text": phrase}
                )

        # Check banned regex patterns
        for pattern in self._constraints.get("blacklisted_patterns", []):
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                violations.append(
                    {"type": "banned_pattern", "pattern": pattern}
                )

        # Check vague sentence starters
        vague_subject_count = 0
        vague_starters = self._constraints.get("blacklisted_sentence_starters", [])
        sentences = re.split(r"(?<=[.!?])\s+", content)
        for sentence in sentences:
            for starter in vague_starters:
                if re.match(rf"^{re.escape(starter)}\b", sentence, re.IGNORECASE):
                    vague_subject_count += 1
                    break

        # Check word count range
        page_types = self._structure.get("page_types", {})
        word_range = (
            page_types.get(page_type, {}).get("total_word_range")
            if page_type in page_types
            else None
        )
        if word_range:
            min_words, max_words = word_range
            if word_count < min_words:
                violations.append(
                    {
                        "type": "word_count_too_low",
                        "word_count": word_count,
                        "minimum": min_words,
                    }
                )
            elif word_count > max_words:
                violations.append(
                    {
                        "type": "word_count_too_high",
                        "word_count": word_count,
                        "maximum": max_words,
                    }
                )

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "word_count": word_count,
            "vague_subject_count": vague_subject_count,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_page_data(self, page_data: dict[str, Any]) -> None:
        missing = self._REQUIRED_PAGE_FIELDS - set(page_data.keys())
        if missing:
            raise ValueError(
                f"page_data is missing required fields: {sorted(missing)}"
            )

    def _build_substitutions(self, page_data: dict[str, Any]) -> dict[str, str]:
        """Produce the full substitution dictionary for template rendering."""
        substitutions: dict[str, str] = dict(page_data)

        # Format banned phrases as a bulleted list for prompt injection
        phrases = self._constraints.get("blacklisted_phrases", [])
        substitutions["banned_phrases_formatted"] = "\n".join(
            f"- {p}" for p in phrases
        )

        # Format banned sentence starters
        starters = self._constraints.get("blacklisted_sentence_starters", [])
        substitutions["banned_sentence_starters_formatted"] = "\n".join(
            f"- {s}" for s in starters
        )

        # Reading level targets from constraints
        substitutions["min_reading_grade"] = str(
            self._constraints.get("min_reading_grade", 8)
        )
        substitutions["max_reading_grade"] = str(
            self._constraints.get("max_reading_grade", 14)
        )

        # Content sections list derived from page_type
        page_type = page_data.get("page_type", "blog_post")
        sections = self.get_required_sections(page_type)
        substitutions["content_sections"] = "\n".join(
            f"{i + 1}. **{s['label']}** — {s['description']}"
            for i, s in enumerate(sections)
        )

        return substitutions

    def _render_template(
        self, template: str, substitutions: dict[str, str]
    ) -> str:
        """
        Replace ``{{variable}}`` placeholders in *template* with values from
        *substitutions*.  Unknown placeholders are left unchanged so that
        multi-stage prompts that carry unresolved placeholders (e.g.
        ``{{outline_json}}``) are still returned in a usable form.
        """
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            return substitutions.get(key, match.group(0))

        return re.sub(r"\{\{([^}]+)\}\}", replacer, template)

    def _load_json(self, filename: str) -> dict[str, Any]:
        path = _CONFIG_DIR / filename
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def _load_prompt(self, relative_path: str) -> str:
        path = _PROMPTS_DIR / relative_path
        return path.read_text(encoding="utf-8")
