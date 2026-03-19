"""
competitor_analyzer.py

Provides competitor analysis utilities for enterprise SEO content strategy.

The ``CompetitorAnalyzer`` does NOT make live HTTP requests — it operates on
competitor data supplied by the caller (URLs, extracted content snippets, and
optional keyword lists).  When an LLM client is provided it can generate
richer analysis; otherwise it falls back to rule-based heuristics.

Typical workflow
----------------
1. Collect competitor data manually or via a scraping tool.
2. Pass the data to ``CompetitorAnalyzer.analyze()``.
3. Use the returned ``CompetitorReport`` to inform hub content and spoke topics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CompetitorProfile:
    """Parsed profile of a single competitor."""

    name: str
    url: str = ""
    page_title: str = ""
    h1: str = ""
    h2_headings: list[str] = field(default_factory=list)
    content_themes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    word_count: int = 0
    has_case_studies: bool = False
    has_testimonials: bool = False
    has_pricing: bool = False
    trust_signals: list[str] = field(default_factory=list)
    raw_content: str = ""


@dataclass
class CompetitorReport:
    """Aggregated analysis of all competitors for a given service/topic."""

    service_topic: str
    competitors: list[CompetitorProfile] = field(default_factory=list)
    common_themes: list[str] = field(default_factory=list)
    common_keywords: list[str] = field(default_factory=list)
    content_gaps: list[str] = field(default_factory=list)
    unique_positioning: list[str] = field(default_factory=list)
    differentiation_opportunities: list[str] = field(default_factory=list)
    recommended_spoke_topics: list[str] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class CompetitorAnalyzer:
    """
    Analyses competitor page data and produces differentiation recommendations.

    Parameters
    ----------
    llm_client:
        Optional LLM client implementing a ``complete(prompt)`` method.
        When supplied, richer narrative analysis is generated.  When omitted,
        rule-based heuristics are used.
    """

    # Common content themes to detect in competitor content
    _THEME_SIGNALS: dict[str, list[str]] = {
        "case studies": ["case study", "case studies", "success story", "client story"],
        "pricing transparency": ["pricing", "packages", "from £", "from $", "per month"],
        "process explanation": ["our process", "how we work", "step 1", "step 2", "methodology"],
        "team/credentials": ["our team", "certified", "accredited", "award", "years experience"],
        "data/results": ["increase", "growth", "%", "ROI", "results", "metrics"],
        "thought leadership": ["guide", "whitepaper", "research", "report", "study"],
        "guarantees": ["guarantee", "money-back", "risk-free", "no contract"],
    }

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def build_profile(self, competitor_data: dict[str, Any]) -> CompetitorProfile:
        """
        Build a ``CompetitorProfile`` from a dictionary of raw competitor data.

        Expected keys in *competitor_data*:
        - ``name`` (str, required)
        - ``url`` (str, optional)
        - ``page_title`` (str, optional)
        - ``h1`` (str, optional)
        - ``h2_headings`` (list[str], optional)
        - ``content`` (str, optional) — raw page text or excerpt
        - ``keywords`` (list[str], optional)

        Parameters
        ----------
        competitor_data:
            Dictionary describing one competitor.

        Returns
        -------
        CompetitorProfile
        """
        name = competitor_data.get("name", "Unknown")
        raw_content = competitor_data.get("content", "")

        profile = CompetitorProfile(
            name=name,
            url=competitor_data.get("url", ""),
            page_title=competitor_data.get("page_title", ""),
            h1=competitor_data.get("h1", ""),
            h2_headings=list(competitor_data.get("h2_headings", [])),
            keywords=list(competitor_data.get("keywords", [])),
            word_count=len(raw_content.split()) if raw_content else 0,
            raw_content=raw_content,
        )

        # Detect content themes from raw content
        profile.content_themes = self._detect_themes(raw_content)

        # Detect trust signals
        profile.trust_signals = self._detect_trust_signals(raw_content)

        # Feature flags
        content_lower = raw_content.lower()
        profile.has_case_studies = any(
            kw in content_lower for kw in ["case study", "case studies", "success story"]
        )
        profile.has_testimonials = any(
            kw in content_lower for kw in ["testimonial", "review", "said", "quote"]
        )
        profile.has_pricing = any(
            kw in content_lower for kw in ["pricing", "packages", "per month", "price"]
        )

        return profile

    def analyze(
        self,
        service_topic: str,
        competitors: list[dict[str, Any]],
        our_strengths: list[str] | None = None,
    ) -> CompetitorReport:
        """
        Analyse a list of competitor data dictionaries and return a
        ``CompetitorReport``.

        Parameters
        ----------
        service_topic:
            The service or topic being compared (e.g. ``'Local SEO'``).
        competitors:
            List of competitor data dicts as expected by ``build_profile()``.
        our_strengths:
            Optional list of your brand's known strengths for comparison.

        Returns
        -------
        CompetitorReport
        """
        profiles = [self.build_profile(c) for c in competitors]

        report = CompetitorReport(service_topic=service_topic, competitors=profiles)

        report.common_themes = self._identify_common_themes(profiles)
        report.common_keywords = self._identify_common_keywords(profiles)
        report.content_gaps = self._identify_content_gaps(profiles)
        report.differentiation_opportunities = self._build_differentiation_opportunities(
            profiles, our_strengths or []
        )
        report.unique_positioning = self._build_unique_positioning(
            service_topic, profiles, our_strengths or []
        )
        report.recommended_spoke_topics = self._recommend_spoke_topics(
            service_topic, report.content_gaps, report.differentiation_opportunities
        )

        if self._llm:
            report.summary = self._generate_llm_summary(report)
        else:
            report.summary = self._generate_rule_summary(report)

        return report

    def extract_keywords_from_headings(
        self, headings: list[str]
    ) -> list[str]:
        """
        Extract meaningful keyword phrases from a list of heading strings
        by stripping stop words and returning 2-4 word phrases.

        Parameters
        ----------
        headings:
            List of H1/H2/H3 strings from a competitor page.

        Returns
        -------
        list[str]
            De-duplicated list of keyword phrases.
        """
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "our", "your",
            "we", "you", "it", "its", "that", "this", "these", "those", "how",
            "why", "what", "when", "where", "who", "which",
        }
        keywords: list[str] = []
        seen: set[str] = set()

        for heading in headings:
            words = re.sub(r"[^a-zA-Z0-9\s]", "", heading.lower()).split()
            filtered = [w for w in words if w not in stop_words and len(w) > 2]
            for n in (3, 2):
                for i in range(len(filtered) - n + 1):
                    phrase = " ".join(filtered[i : i + n])
                    if phrase not in seen:
                        seen.add(phrase)
                        keywords.append(phrase)

        return keywords[:20]  # cap at 20 phrases

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _detect_themes(self, content: str) -> list[str]:
        content_lower = content.lower()
        detected: list[str] = []
        for theme, signals in self._THEME_SIGNALS.items():
            if any(s.lower() in content_lower for s in signals):
                detected.append(theme)
        return detected

    def _detect_trust_signals(self, content: str) -> list[str]:
        patterns = [
            r"\d+\s*(?:years?|yr)\s+experience",
            r"\d+\+?\s*clients?",
            r"\d+\+?\s*(?:projects?|campaigns?)",
            r"award[- ]winning",
            r"certified",
            r"accredited",
            r"google partner",
            r"clutch|g2|trustpilot",
            r"#1|top\s+\d+",
        ]
        signals: list[str] = []
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                signals.append(match.group(0).strip())
        return signals

    def _identify_common_themes(
        self, profiles: list[CompetitorProfile]
    ) -> list[str]:
        if not profiles:
            return []
        theme_counts: dict[str, int] = {}
        for p in profiles:
            for theme in p.content_themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
        # Themes present in more than half of competitors
        threshold = max(1, len(profiles) // 2)
        return [t for t, c in theme_counts.items() if c >= threshold]

    def _identify_common_keywords(
        self, profiles: list[CompetitorProfile]
    ) -> list[str]:
        if not profiles:
            return []
        keyword_counts: dict[str, int] = {}
        for p in profiles:
            for kw in p.keywords:
                kw_lower = kw.lower().strip()
                keyword_counts[kw_lower] = keyword_counts.get(kw_lower, 0) + 1
        threshold = max(1, len(profiles) // 2)
        return [kw for kw, c in keyword_counts.items() if c >= threshold]

    def _identify_content_gaps(
        self, profiles: list[CompetitorProfile]
    ) -> list[str]:
        """Identify content areas that few or no competitors cover."""
        all_themes = set(self._THEME_SIGNALS.keys())
        covered: set[str] = set()
        for p in profiles:
            covered.update(p.content_themes)
        gaps = list(all_themes - covered)
        # Additional structural gaps
        if not any(p.has_pricing for p in profiles):
            gaps.append("transparent pricing information")
        if not any(p.has_case_studies for p in profiles):
            gaps.append("detailed case studies with metrics")
        return gaps

    def _build_differentiation_opportunities(
        self,
        profiles: list[CompetitorProfile],
        our_strengths: list[str],
    ) -> list[str]:
        gaps = self._identify_content_gaps(profiles)
        opps: list[str] = []

        for gap in gaps:
            opps.append(f"Create content covering: {gap}")

        if our_strengths:
            common = self._identify_common_themes(profiles)
            for strength in our_strengths:
                if not any(strength.lower() in t.lower() for t in common):
                    opps.append(
                        f"Highlight differentiator: {strength} (not covered by competitors)"
                    )

        return opps

    def _build_unique_positioning(
        self,
        service_topic: str,
        profiles: list[CompetitorProfile],
        our_strengths: list[str],
    ) -> list[str]:
        positioning: list[str] = [
            f"Position as the data-first {service_topic} provider with transparent metrics",
            f"Emphasise measurable outcomes over vague promises for {service_topic}",
            "Offer unbiased competitor mentions to demonstrate industry authority",
            "Lead with client-specific ROI data rather than generic statistics",
        ]
        if our_strengths:
            for strength in our_strengths[:2]:
                positioning.append(f"Lead with: {strength}")
        return positioning

    def _recommend_spoke_topics(
        self,
        service_topic: str,
        content_gaps: list[str],
        differentiation_opportunities: list[str],
    ) -> list[str]:
        topics: list[str] = [
            f"Ultimate Guide to {service_topic}: Strategy, Tactics, and ROI",
            f"How to Choose the Right {service_topic} Agency: An Unbiased Framework",
            f"{service_topic} vs. In-House: Total Cost of Ownership Analysis",
            f"How We Measure {service_topic} ROI: Our Reporting Framework",
            f"Common {service_topic} Mistakes and How to Avoid Them",
        ]
        for gap in content_gaps[:3]:
            topics.append(f"{service_topic}: {gap.title()} — A Complete Guide")
        return topics[:8]

    def _generate_rule_summary(self, report: CompetitorReport) -> str:
        n = len(report.competitors)
        themes = ", ".join(report.common_themes[:3]) if report.common_themes else "none identified"
        gaps = len(report.content_gaps)
        opps = len(report.differentiation_opportunities)
        return (
            f"Analysed {n} competitor(s) for '{report.service_topic}'. "
            f"Common themes across competitors: {themes}. "
            f"Identified {gaps} content gap(s) and {opps} differentiation "
            f"opportunit{'y' if opps == 1 else 'ies'}. "
            f"Recommended {len(report.recommended_spoke_topics)} spoke topics."
        )

    def _generate_llm_summary(self, report: CompetitorReport) -> str:
        competitor_names = ", ".join(c.name for c in report.competitors)
        gaps_text = "\n".join(f"- {g}" for g in report.content_gaps)
        opps_text = "\n".join(f"- {o}" for o in report.differentiation_opportunities)

        prompt = (
            f"You are an enterprise SEO strategist. Summarise the following "
            f"competitor analysis for the service topic: '{report.service_topic}'.\n\n"
            f"Competitors analysed: {competitor_names}\n\n"
            f"Common themes: {', '.join(report.common_themes)}\n\n"
            f"Content gaps:\n{gaps_text}\n\n"
            f"Differentiation opportunities:\n{opps_text}\n\n"
            f"Write a 3-paragraph strategic summary. Be specific and actionable. "
            f"Mention competitors by name where relevant to show industry awareness."
        )
        try:
            return self._llm.complete(prompt)
        except Exception:  # noqa: BLE001
            return self._generate_rule_summary(report)
