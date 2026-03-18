"""
content_generator.py

Orchestrates the four-stage Chain-of-Thought content generation pipeline:

  Stage 1 — Outline Generation
  Stage 2 — Research Extraction and Claim Substantiation
  Stage 3 — Tone Application and Prose Generation
  Stage 4 — Final Polish and Quality Gate

Each stage sends a prompt to the configured LLM client and parses the
structured response before passing it to the next stage.

The generator requires an LLM client that implements the ``LLMClient``
protocol (see below).  By default it expects an OpenAI-compatible
``chat/completions`` interface, but any client conforming to the protocol
can be injected.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMClient(Protocol):
    """
    Minimal interface required by ``ContentGenerator``.

    Any object implementing ``complete(prompt, system_prompt)`` that returns
    a string can be used as the LLM backend.
    """

    def complete(self, prompt: str, *, system_prompt: str = "") -> str:
        """
        Send *prompt* to the LLM and return the text response.

        Parameters
        ----------
        prompt:
            The user-turn message.
        system_prompt:
            Optional system-turn message.  Some providers attach this as a
            separate message; others prepend it to the user message.
        """
        ...  # pragma: no cover


@dataclass
class GenerationResult:
    """Container for a completed content generation run."""

    page_data: dict[str, Any]
    outline: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)
    draft: str = ""
    final_content: str = ""
    quality_report: dict[str, Any] = field(default_factory=dict)
    static_validation: dict[str, Any] = field(default_factory=dict)

    @property
    def quality_score(self) -> int:
        return self.quality_report.get("quality_score", 0)

    @property
    def human_review_required(self) -> bool:
        return self.quality_report.get("human_review_required", True)

    @property
    def word_count(self) -> int:
        return self.quality_report.get("word_count", len(self.final_content.split()))


class ContentGenerator:
    """
    Runs the four-stage CoT pipeline for a single content page.

    Parameters
    ----------
    llm_client:
        An object implementing the ``LLMClient`` protocol.
    builder:
        Optional ``PromptBuilder`` instance.  Created automatically if omitted.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        builder: PromptBuilder | None = None,
    ) -> None:
        if not isinstance(llm_client, LLMClient):
            raise TypeError(
                "llm_client must implement the LLMClient protocol "
                "(requires a `complete(prompt, *, system_prompt)` method)"
            )
        self._client = llm_client
        self._builder = builder or PromptBuilder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, page_data: dict[str, Any]) -> GenerationResult:
        """
        Execute the full four-stage pipeline for *page_data*.

        Parameters
        ----------
        page_data:
            Page-specific variables dictionary.  See
            ``PromptBuilder._REQUIRED_PAGE_FIELDS`` for required keys.

        Returns
        -------
        GenerationResult
            Populated result object with each stage's output and a final
            quality report.
        """
        result = GenerationResult(page_data=page_data)
        prompts = self._builder.build_chain_of_thought_prompts(page_data)
        system_prompt = self._builder.build_system_prompt(page_data)

        # Stage 1: Outline
        logger.info("Stage 1/4 — Outline generation for: %s", page_data["topic"])
        outline_response = self._client.complete(
            prompts["outline"], system_prompt=system_prompt
        )
        result.outline = self._parse_json_response(outline_response, stage="outline")

        # Stage 2: Research Extraction
        logger.info("Stage 2/4 — Research extraction for: %s", page_data["topic"])
        research_prompt = self._inject_stage_output(
            prompts["research"],
            {"outline_json": json.dumps(result.outline, indent=2)},
        )
        research_response = self._client.complete(
            research_prompt, system_prompt=system_prompt
        )
        result.research = self._parse_json_response(
            research_response, stage="research"
        )

        # Stage 3: Tone Application
        logger.info("Stage 3/4 — Prose generation for: %s", page_data["topic"])
        tone_prompt = self._inject_stage_output(
            prompts["tone"],
            {"research_json": json.dumps(result.research, indent=2)},
        )
        result.draft = self._client.complete(
            tone_prompt, system_prompt=system_prompt
        )

        # Stage 4: Final Polish
        logger.info("Stage 4/4 — Final polish for: %s", page_data["topic"])
        polish_prompt = self._inject_stage_output(
            prompts["polish"],
            {
                "draft_content": result.draft,
                "counter_intuitive_claim": result.outline.get(
                    "counter_intuitive_claim", page_data.get("unique_perspective", "")
                ),
            },
        )
        polish_response = self._client.complete(
            polish_prompt, system_prompt=system_prompt
        )
        result.quality_report, result.final_content = self._parse_polish_response(
            polish_response
        )

        # Static validation (does not require LLM)
        result.static_validation = self._builder.validate_content(
            result.final_content, page_data.get("page_type", "blog_post")
        )

        logger.info(
            "Generation complete — quality score: %d, human review: %s",
            result.quality_score,
            result.human_review_required,
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_stage_output(
        prompt_template: str, values: dict[str, str]
    ) -> str:
        """Replace stage-output placeholders in a prompt template."""
        for key, value in values.items():
            prompt_template = prompt_template.replace("{{" + key + "}}", value)
        return prompt_template

    @staticmethod
    def _parse_json_response(response: str, stage: str) -> dict[str, Any]:
        """
        Extract the first JSON object from an LLM response.

        Falls back to wrapping the raw text in ``{'raw': response}`` when no
        valid JSON block is found, so the pipeline can continue.
        """
        # Try to find a fenced JSON block first
        fenced = re.search(r"```json\s*([\s\S]+?)\s*```", response, re.IGNORECASE)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass

        # Try bare JSON object
        bare = re.search(r"\{[\s\S]+\}", response)
        if bare:
            try:
                return json.loads(bare.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("Stage '%s': could not parse JSON from response", stage)
        return {"raw": response}

    @staticmethod
    def _parse_polish_response(
        response: str,
    ) -> tuple[dict[str, Any], str]:
        """
        Split the Stage 4 response into a quality report (JSON) and the
        corrected article (Markdown text after the JSON block).

        Returns
        -------
        tuple[dict, str]
            ``(quality_report, article_markdown)``
        """
        fenced = re.search(r"```json\s*([\s\S]+?)\s*```", response, re.IGNORECASE)
        quality_report: dict[str, Any] = {}
        if fenced:
            try:
                quality_report = json.loads(fenced.group(1))
                # Article is everything after the closing fence
                article = response[fenced.end():].strip()
                return quality_report, article
            except json.JSONDecodeError:
                pass

        # Fall back: treat entire response as article
        return quality_report, response
