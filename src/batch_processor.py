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
