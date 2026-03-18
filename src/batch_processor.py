"""
batch_processor.py

Processes a list of page data dictionaries through the full generation
pipeline, enforcing variation across the batch to prevent duplication.

Variation enforcement:
  - Tracks n-gram fingerprints of generated content
  - Flags pages that share too many phrases with previously generated pages
  - Rotates variation axes (opening data point, counter-intuitive claim, etc.)
    to ensure each page draws from a distinct angle

The ``BatchProcessor`` does not run LLM calls itself — it delegates to
``ContentGenerator`` and accumulates results.
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .content_generator import ContentGenerator, GenerationResult, LLMClient
from .prompt_builder import PromptBuilder
from .seo_optimizer import SEOOptimizer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hub-and-spoke data structures
# ---------------------------------------------------------------------------


@dataclass
class HubAndSpokeResult:
    """Container for a complete hub-and-spoke content cluster."""

    hub: GenerationResult | None = None
    spokes: list[GenerationResult] = field(default_factory=list)
    thought_leadership: GenerationResult | None = None
    internal_linking_strategy: list[dict[str, Any]] = field(default_factory=list)
    content_outlines: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def total_word_count(self) -> int:
        total = 0
        if self.hub:
            total += self.hub.word_count
        for spoke in self.spokes:
            total += spoke.word_count
        if self.thought_leadership:
            total += self.thought_leadership.word_count
        return total

    def all_results(self) -> list[GenerationResult]:
        results: list[GenerationResult] = []
        if self.hub:
            results.append(self.hub)
        results.extend(self.spokes)
        if self.thought_leadership:
            results.append(self.thought_leadership)
        return results


@dataclass
class BatchResult:
    """Aggregated results for a full batch run."""

    results: list[GenerationResult] = field(default_factory=list)
    duplication_flags: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def pages_requiring_review(self) -> list[GenerationResult]:
        return [r for r in self.results if r.human_review_required]

    def average_quality_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.quality_score for r in self.results) / len(self.results)

    def average_seo_score(self) -> float:
        scores = [
            r.static_validation.get("seo_score", 0)
            for r in self.results
            if "seo_score" in r.static_validation
        ]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)


class BatchProcessor:
    """
    Runs the content generation pipeline across a list of pages.

    Parameters
    ----------
    llm_client:
        Backend LLM client implementing the ``LLMClient`` protocol.
    max_shared_phrase_length:
        Maximum number of consecutive words that may appear verbatim across
        more than ``duplication_threshold`` fraction of the batch.
        Defaults to 6 (from ``content_structure.json`` global rules).
    duplication_threshold:
        Fraction of the batch (0.0–1.0) above which a shared phrase triggers
        a duplication flag.  Defaults to 0.10.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_shared_phrase_length: int = 6,
        duplication_threshold: float = 0.10,
    ) -> None:
        self._generator = ContentGenerator(llm_client)
        self._optimizer = SEOOptimizer()
        self._max_phrase_len = max_shared_phrase_length
        self._dup_threshold = duplication_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_batch(
        self,
        pages: list[dict[str, Any]],
    ) -> BatchResult:
        """
        Generate content for every page in *pages* and return a ``BatchResult``.

        Parameters
        ----------
        pages:
            List of page data dictionaries.  Each must contain the fields
            required by ``PromptBuilder``.

        Returns
        -------
        BatchResult
        """
        batch = BatchResult()
        phrase_index: dict[str, list[int]] = defaultdict(list)  # phrase → page indices

        for idx, page_data in enumerate(pages):
            logger.info(
                "Batch processing page %d/%d: %s",
                idx + 1,
                len(pages),
                page_data.get("topic", "<unknown>"),
            )

            try:
                result = self._generator.generate(page_data)
            except Exception:  # noqa: BLE001
                logger.exception("Page %d generation failed", idx)
                continue

            # Attach SEO analysis to the static_validation block
            seo_report = self._optimizer.analyze(result.final_content, page_data)
            result.static_validation.update(seo_report)

            batch.results.append(result)

            # Index n-gram fingerprints for duplication detection
            if result.final_content:
                self._index_phrases(result.final_content, idx, phrase_index)

        # Detect cross-page phrase duplication
        batch.duplication_flags = self._detect_duplication(
            phrase_index, total_pages=len(batch.results)
        )

        batch.summary = self._build_summary(batch)
        return batch

    def enforce_variation(
        self,
        pages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Validate that the provided page data list has sufficient variation
        across its ``variation_axes`` fields.

        Raises ``ValueError`` if any two pages share identical values for
        ALL variation axes simultaneously (i.e. are functionally identical).

        Returns the input list unchanged if all pages are sufficiently varied.

        Parameters
        ----------
        pages:
            List of page data dictionaries to validate.
        """
        builder = PromptBuilder()
        seen_fingerprints: set[str] = set()

        for idx, page in enumerate(pages):
            page_type = page.get("page_type", "blog_post")
            try:
                structure = builder.get_page_type_structure(page_type)
            except ValueError:
                continue

            variation_axes = structure.get("variation_axes", [])
            if not variation_axes:
                continue

            # Fingerprint = hash of the variation-axis values for this page
            axis_values = tuple(
                str(page.get(axis, "")).strip().lower()
                for axis in variation_axes
            )
            fingerprint = hashlib.sha256(  # noqa: S324
                "|".join(axis_values).encode()
            ).hexdigest()

            if fingerprint in seen_fingerprints:
                raise ValueError(
                    f"Page at index {idx} (topic: '{page.get('topic')}') "
                    f"is a near-duplicate of a previous page — all variation "
                    f"axes have identical values: {dict(zip(variation_axes, axis_values))}"
                )
            seen_fingerprints.add(fingerprint)

        return pages

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _index_phrases(
        self,
        content: str,
        page_index: int,
        phrase_index: dict[str, list[int]],
    ) -> None:
        """Extract word n-grams from *content* and record their page index."""
        words = re.sub(r"[^\w\s]", "", content.lower()).split()
        n = self._max_phrase_len
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i: i + n])
            phrase_index[phrase].append(page_index)

    def _detect_duplication(
        self,
        phrase_index: dict[str, list[int]],
        total_pages: int,
    ) -> list[dict[str, Any]]:
        """
        Return a list of duplication flag records for phrases that appear in
        more than ``_dup_threshold`` of the batch.
        """
        if total_pages == 0:
            return []

        flags: list[dict[str, Any]] = []
        threshold_count = max(2, int(total_pages * self._dup_threshold))

        seen_pairs: set[frozenset[int]] = set()
        for phrase, indices in phrase_index.items():
            unique_pages = list(set(indices))
            if len(unique_pages) >= threshold_count:
                pair_key = frozenset(unique_pages[:2])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                flags.append(
                    {
                        "phrase": phrase,
                        "appears_on_pages": unique_pages,
                        "occurrence_count": len(unique_pages),
                        "threshold": threshold_count,
                    }
                )

        return flags

    @staticmethod
    def _build_summary(batch: BatchResult) -> dict[str, Any]:
        total = len(batch.results)
        review_count = len(batch.pages_requiring_review())
        scores = [r.quality_score for r in batch.results]

        return {
            "total_pages": total,
            "pages_requiring_review": review_count,
            "average_quality_score": round(
                sum(scores) / total if total else 0, 1
            ),
            "min_quality_score": min(scores) if scores else 0,
            "max_quality_score": max(scores) if scores else 0,
            "duplication_flag_count": len(batch.duplication_flags),
        }


# ---------------------------------------------------------------------------
# Hub-and-spoke processor
# ---------------------------------------------------------------------------


class HubAndSpokeProcessor:
    """
    Generates a complete hub-and-spoke content cluster for a single service.

    The cluster consists of:
    - One hub (service landing page)
    - 3–5 spoke blog posts that link back to the hub
    - An optional long-form thought leadership guide
    - An internal linking strategy document
    - Content outlines for each spoke

    Parameters
    ----------
    llm_client:
        Backend LLM client implementing the ``LLMClient`` protocol.
    include_thought_leadership:
        Whether to generate a long-form 'Ultimate Guide' as part of the cluster.
        Defaults to ``True``.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        include_thought_leadership: bool = True,
    ) -> None:
        self._generator = ContentGenerator(llm_client)
        self._optimizer = SEOOptimizer()
        self._builder = PromptBuilder()
        self._include_tl = include_thought_leadership

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def generate_cluster(
        self,
        hub_page_data: dict[str, Any],
        spoke_topics: list[str],
        guide_title: str | None = None,
    ) -> HubAndSpokeResult:
        """
        Generate a complete hub-and-spoke content cluster.

        Parameters
        ----------
        hub_page_data:
            Page data dictionary for the hub page.  Must contain all fields
            required by ``PromptBuilder``.
        spoke_topics:
            List of 3–5 spoke article topics.  Each topic becomes a blog post
            that internally links to the hub.
        guide_title:
            Optional title for the thought leadership guide.  Defaults to
            ``'Ultimate Guide to {hub topic}'``.

        Returns
        -------
        HubAndSpokeResult
        """
        cluster = HubAndSpokeResult()

        # 1. Generate hub page
        logger.info("Generating hub page: %s", hub_page_data.get("topic"))
        try:
            cluster.hub = self._generator.generate(hub_page_data)
            seo_report = self._optimizer.analyze(cluster.hub.final_content, hub_page_data)
            cluster.hub.static_validation.update(seo_report)
        except Exception:  # noqa: BLE001
            logger.exception("Hub page generation failed")

        # 2. Generate spoke pages
        spoke_prompt_dicts = self._builder.build_spoke_prompts(hub_page_data, spoke_topics)
        for spoke_info in spoke_prompt_dicts:
            logger.info("Generating spoke: %s", spoke_info["topic"])
            spoke_data = self._build_spoke_page_data(hub_page_data, spoke_info)
            try:
                spoke_result = self._generator.generate(spoke_data)
                seo_report = self._optimizer.analyze(spoke_result.final_content, spoke_data)
                spoke_result.static_validation.update(seo_report)
                cluster.spokes.append(spoke_result)
            except Exception:  # noqa: BLE001
                logger.exception("Spoke '%s' generation failed", spoke_info["topic"])

            # Store content outline for the spoke
            cluster.content_outlines.append(
                {
                    "topic": spoke_info["topic"],
                    "spoke_number": spoke_info["spoke_number"],
                    "hub_keyword": spoke_info["hub_keyword"],
                    "prompt_preview": spoke_info["prompt"][:200] + "...",
                }
            )

        # 3. Generate thought leadership guide (optional)
        if self._include_tl:
            logger.info("Generating thought leadership guide")
            try:
                tl_prompt = self._builder.build_thought_leadership_prompt(
                    hub_page_data, guide_title=guide_title
                )
                tl_data = dict(hub_page_data)
                tl_data["page_type"] = "blog_post"  # use blog_post for validation
                tl_result = self._generator.generate(tl_data)
                cluster.thought_leadership = tl_result
            except Exception:  # noqa: BLE001
                logger.exception("Thought leadership guide generation failed")

        # 4. Build internal linking strategy
        cluster.internal_linking_strategy = self._build_linking_strategy(
            hub_page_data, spoke_topics
        )

        # 5. Build summary
        cluster.summary = self._build_cluster_summary(cluster, hub_page_data)

        return cluster

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_spoke_page_data(
        hub_data: dict[str, Any],
        spoke_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a full page data dict for a spoke from hub data + spoke info."""
        spoke_data = dict(hub_data)
        spoke_data["topic"] = spoke_info["topic"]
        spoke_data["page_type"] = "blog_post"
        # Adjust depth for spoke posts (intermediate unless hub is deep)
        if hub_data.get("depth_level") != "deep":
            spoke_data["depth_level"] = "intermediate"
        return spoke_data

    @staticmethod
    def _build_linking_strategy(
        hub_data: dict[str, Any],
        spoke_topics: list[str],
    ) -> list[dict[str, Any]]:
        """Generate an internal linking strategy document."""
        hub_keyword = hub_data.get("primary_keyword", hub_data.get("topic", ""))
        strategy: list[dict[str, Any]] = []

        for i, topic in enumerate(spoke_topics, 1):
            strategy.append(
                {
                    "spoke_number": i,
                    "spoke_topic": topic,
                    "links_to_hub": [
                        {
                            "anchor_text": hub_keyword,
                            "context": f"Contextual mention in introduction of '{topic}'",
                        },
                        {
                            "anchor_text": f"learn more about {hub_keyword}",
                            "context": f"CTA section of '{topic}'",
                        },
                    ],
                    "hub_links_to_spoke": {
                        "anchor_text": topic[:50],
                        "context": f"Related content section of hub page",
                    },
                }
            )

        return strategy

    @staticmethod
    def _build_cluster_summary(
        cluster: HubAndSpokeResult,
        hub_data: dict[str, Any],
    ) -> dict[str, Any]:
        hub_score = cluster.hub.quality_score if cluster.hub else 0
        spoke_scores = [s.quality_score for s in cluster.spokes]
        tl_score = cluster.thought_leadership.quality_score if cluster.thought_leadership else None

        return {
            "service_topic": hub_data.get("topic", ""),
            "primary_keyword": hub_data.get("primary_keyword", ""),
            "hub_quality_score": hub_score,
            "spoke_count": len(cluster.spokes),
            "spoke_quality_scores": spoke_scores,
            "average_spoke_quality": (
                round(sum(spoke_scores) / len(spoke_scores), 1)
                if spoke_scores
                else 0
            ),
            "thought_leadership_quality_score": tl_score,
            "total_word_count": cluster.total_word_count(),
            "internal_links_planned": len(cluster.internal_linking_strategy) * 2,
        }
