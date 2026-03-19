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

    def build_hub_prompt(self, page_data: dict[str, Any]) -> str:
        """
        Return a prompt for generating a hub (service landing page) in a
        hub-and-spoke content model.

        The hub prompt instructs the LLM to produce a comprehensive service
        page that acts as the central authority document.  Spoke content
        links back to this page.

        Parameters
        ----------
        page_data:
            Dictionary of page-specific variables.  Must contain all fields
            from ``_REQUIRED_PAGE_FIELDS`` plus optional ``service_name``,
            ``h2_sections``, ``trust_factors``, and ``related_services``.

        Returns
        -------
        str
            The assembled hub prompt text.
        """
        self._validate_page_data(page_data)
        substitutions = self._build_substitutions(page_data)

        service_name = page_data.get("service_name", page_data.get("topic", "the service"))
        h2_sections = page_data.get("h2_sections", [])
        trust_factors = page_data.get("trust_factors", [])
        related_services = page_data.get("related_services", [])

        sections_text = (
            "\n".join(f"- {s}" for s in h2_sections)
            if h2_sections
            else "- Service overview\n- Process\n- Results\n- Testimonials\n- CTA"
        )
        trust_text = (
            "\n".join(f"- {t}" for t in trust_factors)
            if trust_factors
            else "- Certifications\n- Client results\n- Years of experience"
        )
        related_text = (
            "\n".join(f"- {s}" for s in related_services)
            if related_services
            else "- Related service 1\n- Related service 2"
        )

        hub_prompt = (
            f"You are an expert SEO content writer creating a hub (service landing page) "
            f"for '{service_name}'.\n\n"
            f"PRIMARY KEYWORD: {page_data.get('primary_keyword', '')}\n"
            f"TARGET AUDIENCE: {page_data.get('target_audience', '')}\n\n"
            f"H2 SECTIONS TO INCLUDE:\n{sections_text}\n\n"
            f"TRUST FACTORS TO INCORPORATE:\n{trust_text}\n\n"
            f"RELATED SERVICES (for internal linking):\n{related_text}\n\n"
            f"REQUIREMENTS:\n"
            f"- Write a comprehensive {page_data.get('page_type', 'landing_page')} "
            f"  (1,500–2,500 words)\n"
            f"- Include an H1, multiple H2 sections, a trust factors section, "
            f"  client testimonials, a clear CTA, and related services links\n"
            f"- Naturally incorporate the primary keyword and secondary keywords: "
            f"  {page_data.get('secondary_keywords', '')}\n"
            f"- Use {page_data.get('depth_level', 'intermediate')}-depth coverage\n"
            f"- Support claims with: {page_data.get('data_point', '')}\n\n"
            f"Write the full page content now:"
        )
        return self._render_template(hub_prompt, substitutions)

    def build_spoke_prompts(
        self,
        hub_page_data: dict[str, Any],
        spoke_topics: list[str],
    ) -> list[dict[str, Any]]:
        """
        Return a list of prompt dicts for generating spoke blog posts that
        link back to a hub page.

        Each spoke prompt dict contains:
        - ``topic`` — the spoke topic
        - ``prompt`` — the assembled LLM prompt string
        - ``hub_keyword`` — the hub's primary keyword for internal linking

        Parameters
        ----------
        hub_page_data:
            Page data dict for the hub page (same format as ``build_hub_prompt``).
        spoke_topics:
            List of spoke article topic strings (3–5 recommended).

        Returns
        -------
        list[dict[str, Any]]
        """
        self._validate_page_data(hub_page_data)
        hub_keyword = hub_page_data.get("primary_keyword", "")
        hub_url_placeholder = (
            f"[link to: {hub_page_data.get('topic', 'the main service page')}]"
        )
        service_name = hub_page_data.get("service_name", hub_page_data.get("topic", ""))

        results: list[dict[str, Any]] = []
        for i, spoke_topic in enumerate(spoke_topics, 1):
            prompt = (
                f"You are an expert SEO content writer creating a spoke blog post "
                f"that supports the hub page about '{service_name}'.\n\n"
                f"SPOKE TOPIC: {spoke_topic}\n"
                f"HUB PAGE KEYWORD: {hub_keyword}\n"
                f"TARGET AUDIENCE: {hub_page_data.get('target_audience', '')}\n\n"
                f"REQUIREMENTS:\n"
                f"- Write a focused blog post (1,000–1,500 words) on: {spoke_topic}\n"
                f"- Include 2–3 natural internal links back to the hub page "
                f"  using anchor text variations of '{hub_keyword}'\n"
                f"  Reference the hub page as: {hub_url_placeholder}\n"
                f"- Use a unique angle not covered in the hub page\n"
                f"- Depth level: {hub_page_data.get('depth_level', 'intermediate')}\n"
                f"- Reference this data point where relevant: "
                f"  {hub_page_data.get('data_point', '')}\n"
                f"- Secondary keywords to include: "
                f"  {hub_page_data.get('secondary_keywords', '')}\n\n"
                f"Write the full spoke blog post now:"
            )
            results.append(
                {
                    "topic": spoke_topic,
                    "spoke_number": i,
                    "hub_keyword": hub_keyword,
                    "prompt": prompt,
                }
            )

        return results

    def build_thought_leadership_prompt(
        self,
        page_data: dict[str, Any],
        guide_title: str | None = None,
    ) -> str:
        """
        Return a prompt for generating a long-form thought leadership guide
        (15–20 pages / 5,000–7,000 words) in the 'Ultimate Guide to X' format.

        Parameters
        ----------
        page_data:
            Standard page data dictionary.
        guide_title:
            Optional override for the guide title.  Defaults to
            ``'Ultimate Guide to {topic}'``.

        Returns
        -------
        str
        """
        self._validate_page_data(page_data)
        substitutions = self._build_substitutions(page_data)
        topic = page_data.get("topic", "")
        title = guide_title or f"Ultimate Guide to {topic}"
        keyword = page_data.get("primary_keyword", "")

        prompt = (
            f"You are an expert content strategist writing a comprehensive thought "
            f"leadership guide.\n\n"
            f"GUIDE TITLE: {title}\n"
            f"PRIMARY KEYWORD: {keyword}\n"
            f"AUDIENCE: {page_data.get('target_audience', '')}\n\n"
            f"GUIDE REQUIREMENTS:\n"
            f"- Length: 5,000–7,000 words (15–20 pages equivalent)\n"
            f"- Structure: Executive summary, 6–8 chapters, conclusion, glossary\n"
            f"- Each chapter: 600–900 words with H2 heading, body, and key takeaway\n"
            f"- Unique perspective: {page_data.get('unique_perspective', '')}\n"
            f"- Anchor data point: {page_data.get('data_point', '')}\n"
            f"- Authority source: {page_data.get('authority_source', '')}\n"
            f"- Technical term to define and use correctly: "
            f"  {page_data.get('primary_technical_term', '')}\n"
            f"- Depth level: {page_data.get('depth_level', 'deep')}\n\n"
            f"TONE & STYLE:\n"
            f"- Write for: {page_data.get('target_audience', '')}\n"
            f"- Avoid generic statements — every claim must be substantiated\n"
            f"- Include original frameworks, named models, or proprietary methodologies\n"
            f"- Add a 'Further Reading' section at the end\n\n"
            f"Write the complete guide now:"
        )
        return self._render_template(prompt, substitutions)

    def _load_prompt(self, relative_path: str) -> str:
        path = _PROMPTS_DIR / relative_path
        return path.read_text(encoding="utf-8")
