"""
seo_optimizer.py

Validates and scores generated content against SEO quality requirements:

  - Search intent alignment
  - Long-tail keyword presence
  - Semantic triplet density (Subject-Predicate-Object sentence ratio)
  - EEAT signal detection
  - Topic depth adequacy

This module performs static text analysis only — no LLM calls required.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# Common auxiliary/linking verbs that indicate weak SPO structure
_WEAK_PREDICATES = re.compile(
    r"\b(is|are|was|were|be|been|being|has|have|had|"
    r"does|do|did|seems?|appears?|feels?|looks?|sounds?|"
    r"involves?|includes?|contains?|consists?)\b",
    re.IGNORECASE,
)

# Simple heuristic: sentence contains a named entity-like subject (capitalised
# or a concrete noun) followed by a strong action verb
_STRONG_PREDICATE = re.compile(
    r"\b(generates?|produces?|reduces?|increases?|decreases?|"
    r"calculates?|converts?|transforms?|prevents?|causes?|"
    r"enables?|disables?|triggers?|processes?|stores?|retrieves?|"
    r"sends?|receives?|reads?|writes?|creates?|deletes?|updates?|"
    r"computes?|measures?|validates?|enforces?|returns?|yields?|"
    r"allocates?|releases?|exposes?|defines?|implements?|extends?|"
    r"overrides?|replaces?|requires?|depends?|uses?|applies?|"
    r"accepts?|rejects?|maps?|filters?|sorts?|groups?|merges?|splits?)\b",
    re.IGNORECASE,
)


class SEOOptimizer:
    """
    Analyses a piece of generated content for SEO quality signals.

    Parameters
    ----------
    seo_config_path:
        Optional path override for ``seo_config.json``.
    """

    def __init__(
        self,
        seo_config_path: Path | None = None,
    ) -> None:
        config_path = seo_config_path or (_CONFIG_DIR / "seo_config.json")
        with config_path.open(encoding="utf-8") as fh:
            self._seo = json.load(fh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        content: str,
        page_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run all SEO checks on *content* and return a structured report.

        Parameters
        ----------
        content:
            The final article text (plain text or Markdown).
        page_data:
            The page-specific variables used to generate this content.

        Returns
        -------
        dict
            Keys: ``seo_score`` (0–100), ``keyword_present`` (bool),
            ``intent_match`` (bool), ``semantic_triplet_ratio`` (float),
            ``eeat_signals_found`` (list), ``depth_adequate`` (bool),
            ``recommendations`` (list[str]).
        """
        content_lower = content.lower()
        sentences = self._split_sentences(content)
        word_count = len(content.split())

        keyword_present = self._check_keyword_presence(
            content_lower, page_data
        )
        intent_match = self._check_intent_match(
            content, page_data.get("search_intent_type", "")
        )
        spo_ratio = self._compute_spo_ratio(sentences)
        eeat_signals = self._detect_eeat_signals(content, page_data)
        depth_adequate = self._check_depth_adequacy(
            word_count, page_data.get("depth_level", "medium")
        )

        recommendations = self._build_recommendations(
            keyword_present=keyword_present,
            intent_match=intent_match,
            spo_ratio=spo_ratio,
            eeat_signals=eeat_signals,
            depth_adequate=depth_adequate,
            page_data=page_data,
        )

        seo_score = self._compute_score(
            keyword_present=keyword_present,
            intent_match=intent_match,
            spo_ratio=spo_ratio,
            eeat_signals=eeat_signals,
            depth_adequate=depth_adequate,
        )

        return {
            "seo_score": seo_score,
            "keyword_present": keyword_present,
            "intent_match": intent_match,
            "semantic_triplet_ratio": round(spo_ratio, 3),
            "eeat_signals_found": eeat_signals,
            "depth_adequate": depth_adequate,
            "word_count": word_count,
            "recommendations": recommendations,
        }

    def build_long_tail_query(self, pattern_index: int, **kwargs: str) -> str:
        """
        Render a long-tail query pattern from the SEO config.

        Parameters
        ----------
        pattern_index:
            Index into ``long_tail_query_patterns.patterns``.
        **kwargs:
            Variable substitutions for the pattern placeholders.

        Returns
        -------
        str
            The rendered long-tail query string.
        """
        patterns = self._seo["long_tail_query_patterns"]["patterns"]
        if pattern_index >= len(patterns):
            raise IndexError(
                f"pattern_index {pattern_index} out of range "
                f"(only {len(patterns)} patterns available)"
            )
        pattern = patterns[pattern_index]
        for key, value in kwargs.items():
            pattern = pattern.replace("{" + key + "}", value)
        return pattern

    # ------------------------------------------------------------------
    # Private analysis methods
    # ------------------------------------------------------------------

    def _check_keyword_presence(
        self,
        content_lower: str,
        page_data: dict[str, Any],
    ) -> bool:
        """Return True if the primary keyword appears in the content."""
        primary = page_data.get("primary_keyword", "").lower()
        if not primary:
            return False
        return primary in content_lower

    def _check_intent_match(
        self,
        content: str,
        intent_type: str,
    ) -> bool:
        """
        Check whether the content contains structural signals matching the
        declared search intent type.
        """
        intent_config = self._seo.get("search_intent_types", {}).get(intent_type)
        if not intent_config:
            return True  # Unknown intent type: skip check

        requirements = intent_config.get("content_requirements", {})
        content_lower = content.lower()

        checks = {
            "must_define_subject": lambda: bool(
                re.search(r"\b(is|are|refers to|means|defined as)\b", content_lower)
            ),
            "must_include_mechanism": lambda: bool(
                re.search(r"\b(works by|operates by|functions by|how it|mechanism)\b", content_lower)
            ),
            "must_include_examples": lambda: bool(
                re.search(r"\b(for example|for instance|such as|e\.g\.|specifically)\b", content_lower)
            ),
            "must_include_comparison": lambda: bool(
                re.search(r"\b(compared to|vs\.?|versus|unlike|whereas|while)\b", content_lower)
            ),
            "must_include_verdict": lambda: bool(
                re.search(r"\b(recommend|choose|pick|best option|winner)\b", content_lower)
            ),
            "must_include_proof": lambda: bool(
                re.search(r"\b(\d+%|\d+ percent|case study|result|outcome)\b", content_lower)
            ),
        }

        failed = 0
        for req_key, req_value in requirements.items():
            if req_value and req_key in checks:
                if not checks[req_key]():
                    failed += 1

        # Allow one check to fail before flagging intent mismatch
        return failed <= 1

    def _compute_spo_ratio(self, sentences: list[str]) -> float:
        """
        Estimate the ratio of sentences with strong Subject-Predicate-Object
        structure vs. total sentences.

        Uses heuristics rather than a full dependency parser:
        - Presence of a strong action verb (not a linking verb)
        - Sentence length between 6 and 40 words (excludes headings, fragments)
        """
        if not sentences:
            return 0.0

        analysable = [
            s for s in sentences
            if 6 <= len(s.split()) <= 40
        ]
        if not analysable:
            return 0.0

        strong = sum(
            1
            for s in analysable
            if _STRONG_PREDICATE.search(s) and not self._is_weak_only(s)
        )
        return strong / len(analysable)

    @staticmethod
    def _is_weak_only(sentence: str) -> bool:
        """Return True if the sentence contains only weak predicates."""
        words = sentence.lower().split()
        for i, word in enumerate(words):
            if _STRONG_PREDICATE.match(word):
                return False
        return bool(_WEAK_PREDICATES.search(sentence))

    def _detect_eeat_signals(
        self,
        content: str,
        page_data: dict[str, Any],
    ) -> list[str]:
        """Detect which EEAT signal categories are present in the content."""
        signals_found: list[str] = []
        content_lower = content.lower()
        eeat = self._seo.get("eeat_signals", {})

        # Experience: first-person language or measurement references
        if re.search(r"\b(i |we |our |found that|measured|tested|observed)\b", content_lower):
            signals_found.append("experience")

        # Expertise: primary technical term used and defined
        primary_term = page_data.get("primary_technical_term", "").lower()
        if primary_term and primary_term in content_lower:
            if re.search(r"\b(defined as|means|refers to|is a|are a)\b", content_lower):
                signals_found.append("expertise")

        # Authoritativeness: named authority source referenced
        authority = page_data.get("authority_source", "").lower()
        if authority and authority in content_lower:
            signals_found.append("authoritativeness")

        # Trustworthiness: limitation or condition acknowledgement
        if re.search(
            r"\b(does not apply|not applicable|limitation|caveat|"
            r"exception|only when|provided that|assuming)\b",
            content_lower,
        ):
            signals_found.append("trustworthiness")

        return signals_found

    def _check_depth_adequacy(self, word_count: int, depth_level: str) -> bool:
        """Return True if the word count meets the minimum for the depth level."""
        depth_config = self._seo.get("topic_depth_requirements", {}).get(
            depth_level, {}
        )
        min_words = depth_config.get("word_count", 300)
        return word_count >= min_words

    def _build_recommendations(
        self,
        *,
        keyword_present: bool,
        intent_match: bool,
        spo_ratio: float,
        eeat_signals: list[str],
        depth_adequate: bool,
        page_data: dict[str, Any],
    ) -> list[str]:
        recs: list[str] = []

        if not keyword_present:
            kw = page_data.get("primary_keyword", "")
            recs.append(
                f"Primary keyword '{kw}' not detected. "
                "Include it naturally in the first 100 words and at least one H2 heading."
            )

        if not intent_match:
            intent = page_data.get("search_intent_type", "unknown")
            recs.append(
                f"Content does not clearly match '{intent}' search intent. "
                "Review required structural signals for this intent type."
            )

        if spo_ratio < 0.60:
            recs.append(
                f"Semantic triplet density is {spo_ratio:.0%} (target ≥60%). "
                "Rewrite passive-voice and linking-verb sentences to use active, "
                "specific predicates."
            )

        missing_eeat = {"experience", "expertise", "authoritativeness", "trustworthiness"} - set(eeat_signals)
        for signal in sorted(missing_eeat):
            recs.append(f"EEAT signal missing: '{signal}'. See seo_config.json for remediation.")

        if not depth_adequate:
            depth = page_data.get("depth_level", "medium")
            required = self._seo.get("topic_depth_requirements", {}).get(depth, {}).get("word_count", 300)
            recs.append(
                f"Content depth is insufficient for '{depth}' depth level "
                f"(requires ≥{required} words)."
            )

        return recs

    @staticmethod
    def _compute_score(
        *,
        keyword_present: bool,
        intent_match: bool,
        spo_ratio: float,
        eeat_signals: list[str],
        depth_adequate: bool,
    ) -> int:
        score = 100
        if not keyword_present:
            score -= 20
        if not intent_match:
            score -= 15
        spo_penalty = max(0, int((0.60 - spo_ratio) * 100))
        score -= min(spo_penalty, 20)
        missing_eeat_count = 4 - len(eeat_signals)
        score -= missing_eeat_count * 8
        if not depth_adequate:
            score -= 15
        return max(0, score)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split *text* into sentences on terminal punctuation."""
        # Strip Markdown headers before analysis
        clean = re.sub(r"^#{1,6}\s.*$", "", text, flags=re.MULTILINE)
        parts = re.split(r"(?<=[.!?])\s+", clean.strip())
        return [p.strip() for p in parts if p.strip()]
