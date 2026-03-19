"""
quality_scorer.py

Multi-dimensional content quality scoring that goes beyond basic SEO metrics.

Five dimensions are measured:

1. **Authority Score**      — Competitor mentions, data citations, statistics,
                              named sources, and case study references.
2. **Semantic Richness**    — Entity density, topic-specific terminology,
                              LSI keyword coverage, and vocabulary diversity.
3. **Structure Score**      — HTML heading hierarchy, schema markup presence,
                              CTA placement, and proper section organisation.
4. **Engagement Potential** — Benefit-driven language, CTA clarity, numbered
                              lists, rhetorical questions, and power words.
5. **Uniqueness Score**     — Absence of generic filler phrases, generic
                              sentence starters, and placeholder boilerplate.

Each dimension returns a float 0–100.  The ``overall`` score is a weighted
average.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Weights for the overall score
# ---------------------------------------------------------------------------

_WEIGHTS: dict[str, float] = {
    "authority": 0.25,
    "semantic": 0.20,
    "structure": 0.25,
    "engagement": 0.15,
    "uniqueness": 0.15,
}

# ---------------------------------------------------------------------------
# Signals used by each dimension
# ---------------------------------------------------------------------------

# Authority signals — broken into named sub-patterns for readability
_CITATION_DATA_WORDS = (
    r"according to|study shows?|research (shows?|finds?|found|indicates?)|"
    r"data (shows?|suggests?)|survey|report by|published in|source:"
)
_CITATION_PATTERNS = re.compile(
    rf"\b(\d{{1,3}}%|\d+\s*percent|{_CITATION_DATA_WORDS})\b",
    re.IGNORECASE,
)
_NAMED_SOURCE_PATTERN = re.compile(
    r"\b(google|gartner|forrester|mckinsey|harvard|mit|stanford|statista|"
    r"hubspot|semrush|ahrefs|moz|search engine journal|search engine land|"
    r"neil patel|rand fishkin|backlinko)\b",
    re.IGNORECASE,
)
_COMPETITOR_MENTION_PATTERN = re.compile(
    r"\b(competitor|alternative|compare|vs\.?|versus|unlike|similar to|"
    r"industry leader|market leader|top agenc|rival)\b",
    re.IGNORECASE,
)
_CASE_STUDY_PATTERN = re.compile(
    r"\b(case study|success story|client result|how we helped|before and after|"
    r"increased by|grew by|reduced by|achieved|delivered|resulted in)\b",
    re.IGNORECASE,
)

# Semantic richness signals
_GENERIC_FILLER = re.compile(
    r"\b(in today's (world|digital|landscape)|it is (important|crucial|vital|"
    r"essential) to|in (conclusion|summary|today)|leverag(e|ing) (the power of|"
    r"our|your)|in the (fast-paced|ever-changing|dynamic)|game.changer|"
    r"take.*to the next level|think outside the box|move the needle)\b",
    re.IGNORECASE,
)
_TECHNICAL_TERM_DENSITY_PATTERN = re.compile(
    r"\b([A-Z][a-z]*(?:[A-Z][a-z]*)+|[A-Z]{2,})\b"  # CamelCase or ACRONYM
)

# Structure signals
_H1_PATTERN = re.compile(r"<h1[^>]*>.*?</h1>", re.IGNORECASE | re.DOTALL)
_H2_PATTERN = re.compile(r"<h2[^>]*>.*?</h2>", re.IGNORECASE | re.DOTALL)
_H3_PATTERN = re.compile(r"<h3[^>]*>.*?</h3>", re.IGNORECASE | re.DOTALL)
_SCHEMA_PATTERN = re.compile(
    r'(application/ld\+json|itemtype|itemscope|schema\.org)', re.IGNORECASE
)
_CTA_PATTERN = re.compile(
    r"\b(get (started|a (free|quote)|your|in touch)|contact us|schedule (a|your)|"
    r"book (a|your|now)|request (a|your|demo)|download|sign up|learn more|"
    r"start (your|a|now)|try (it|for free)|get (the|your) (guide|ebook|report))\b",
    re.IGNORECASE,
)
_TRUST_SECTION_PATTERN = re.compile(
    r"(trust|testimonial|review|client|award|certif|accredit|partner|result)",
    re.IGNORECASE,
)
# Markdown heading fallbacks
_MD_H1 = re.compile(r"^#\s+.+", re.MULTILINE)
_MD_H2 = re.compile(r"^##\s+.+", re.MULTILINE)
_MD_H3 = re.compile(r"^###\s+.+", re.MULTILINE)

# Engagement signals
_POWER_WORDS = re.compile(
    r"\b(proven|guaranteed|exclusive|instant|free|save|easy|simple|fast|quick|"
    r"powerful|transform|boost|double|triple|skyrocket|unlock|discover|secret|"
    r"ultimate|complete|comprehensive|essential|critical|important|must|need to|"
    r"you (can|will|should|must)|your (business|company|brand|team|clients?))\b",
    re.IGNORECASE,
)
_BENEFIT_LANGUAGE = re.compile(
    r"\b(result(s|ing in)?|outcome|achiev|deliver|increas|grow|improve|reduc|"
    r"sav(e|ing)|generat|earn|gain|benefit|value|return|ROI|profit|revenue|"
    r"rank(ing)?|traffic|lead|conversion)\b",
    re.IGNORECASE,
)
_LIST_PATTERN = re.compile(r"(<li>|^\s*[\*\-•]\s+|\d+\.\s+)", re.MULTILINE)
_QUESTION_PATTERN = re.compile(r"\?")

# Uniqueness / anti-generic signals
_PLACEHOLDER_PHRASES = re.compile(
    r"(this is a generated page about|lorem ipsum|placeholder|todo|tbd|"
    r"insert.*here|add.*content|coming soon|under construction|"
    r"generic (content|template)|example (page|content|text))",
    re.IGNORECASE,
)
_BANNED_OPENERS = re.compile(
    r"^(in (today|this|our|the)|it is|there (is|are)|as (a|an|the)|"
    r"when it comes to|the fact (is|that)|needless to say)",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class QualityScoreResult:
    """Holds scores and per-dimension explanations."""

    authority: float = 0.0
    semantic: float = 0.0
    structure: float = 0.0
    engagement: float = 0.0
    uniqueness: float = 0.0
    overall: float = 0.0
    explanations: dict[str, list[str]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "authority": round(self.authority, 1),
            "semantic": round(self.semantic, 1),
            "structure": round(self.structure, 1),
            "engagement": round(self.engagement, 1),
            "uniqueness": round(self.uniqueness, 1),
            "overall": round(self.overall, 1),
            "explanations": self.explanations,
        }


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


class QualityScorer:
    """
    Computes multi-dimensional quality scores for generated content.

    All scoring is static text analysis — no LLM calls required.

    Usage::

        scorer = QualityScorer()
        result = scorer.score(html_content, page_data)
        print(result.overall)   # e.g. 74.3
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        content: str,
        page_data: dict[str, Any] | None = None,
    ) -> QualityScoreResult:
        """
        Score *content* across all five quality dimensions.

        Parameters
        ----------
        content:
            The generated content string (HTML or Markdown).
        page_data:
            Optional page-level metadata used to improve scoring accuracy
            (e.g. primary keyword for semantic checks).

        Returns
        -------
        QualityScoreResult
        """
        page_data = page_data or {}
        result = QualityScoreResult()

        result.authority, result.explanations["authority"] = self._score_authority(
            content, page_data
        )
        result.semantic, result.explanations["semantic"] = self._score_semantic(
            content, page_data
        )
        result.structure, result.explanations["structure"] = self._score_structure(
            content
        )
        result.engagement, result.explanations["engagement"] = self._score_engagement(
            content
        )
        result.uniqueness, result.explanations["uniqueness"] = self._score_uniqueness(
            content
        )

        result.overall = (
            result.authority * _WEIGHTS["authority"]
            + result.semantic * _WEIGHTS["semantic"]
            + result.structure * _WEIGHTS["structure"]
            + result.engagement * _WEIGHTS["engagement"]
            + result.uniqueness * _WEIGHTS["uniqueness"]
        )

        return result

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_authority(
        content: str, page_data: dict[str, Any]
    ) -> tuple[float, list[str]]:
        """Score content authority signals (0–100)."""
        notes: list[str] = []
        score = 0.0

        # Data citations (up to 30 pts)
        citation_matches = len(_CITATION_PATTERNS.findall(content))
        citation_score = min(30.0, citation_matches * 6.0)
        score += citation_score
        if citation_matches >= 3:
            notes.append(f"Strong: {citation_matches} citation/data signals found.")
        elif citation_matches > 0:
            notes.append(f"Moderate: {citation_matches} citation signal(s). Add more statistics.")
        else:
            notes.append("Missing: No data citations or statistics found. Add concrete numbers.")

        # Named authority sources (up to 20 pts)
        named_sources = len(set(_NAMED_SOURCE_PATTERN.findall(content.lower())))
        authority_score = min(20.0, named_sources * 10.0)
        score += authority_score
        if named_sources > 0:
            notes.append(f"Good: {named_sources} named authority source(s) referenced.")
        else:
            notes.append("Consider citing recognised authority sources (Google, Gartner, etc.).")

        # Competitor mentions (up to 20 pts)
        competitor_hits = len(_COMPETITOR_MENTION_PATTERN.findall(content))
        comp_score = min(20.0, competitor_hits * 5.0)
        score += comp_score
        if competitor_hits >= 2:
            notes.append("Good: Competitor context or comparisons present.")
        else:
            notes.append("Consider adding unbiased competitor mentions for authority.")

        # Case studies / results (up to 30 pts)
        case_hits = len(_CASE_STUDY_PATTERN.findall(content))
        case_score = min(30.0, case_hits * 5.0)
        score += case_score
        if case_hits >= 3:
            notes.append("Strong: Client results and outcome language detected.")
        elif case_hits > 0:
            notes.append("Add more measurable client results to boost authority.")
        else:
            notes.append("Missing: No case study or results language found.")

        return min(100.0, score), notes

    @staticmethod
    def _score_semantic(
        content: str, page_data: dict[str, Any]
    ) -> tuple[float, list[str]]:
        """Score semantic richness (0–100)."""
        notes: list[str] = []
        score = 0.0
        words = content.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0, ["Content is empty."]

        # Generic filler penalty (up to -20 pts base)
        filler_count = len(_GENERIC_FILLER.findall(content))
        filler_penalty = min(20.0, filler_count * 4.0)
        base = 50.0 - filler_penalty
        score = max(0.0, base)
        if filler_count > 3:
            notes.append(f"Warning: {filler_count} generic filler phrases detected. Rewrite them.")
        elif filler_count > 0:
            notes.append(f"{filler_count} filler phrase(s). Consider replacing with specific claims.")
        else:
            notes.append("Good: No generic filler phrases detected.")

        # Technical term density (up to 20 pts)
        tech_terms = len(set(_TECHNICAL_TERM_DENSITY_PATTERN.findall(content)))
        tech_score = min(20.0, tech_terms * 2.0)
        score += tech_score
        if tech_terms >= 5:
            notes.append(f"Good: {tech_terms} technical terms/acronyms detected.")
        else:
            notes.append("Add more domain-specific terminology and acronyms.")

        # Vocabulary diversity (type-token ratio) — up to 20 pts
        unique_words = len(set(w.lower() for w in words if len(w) > 3))
        ttr = unique_words / word_count if word_count else 0
        ttr_score = min(20.0, ttr * 40.0)
        score += ttr_score

        # Primary keyword present (10 pts)
        primary_kw = page_data.get("primary_keyword", "")
        if primary_kw and primary_kw.lower() in content.lower():
            score += 10.0
            notes.append("Primary keyword present in content.")
        elif primary_kw:
            notes.append(f"Primary keyword '{primary_kw}' not found in content.")

        return min(100.0, score), notes

    @staticmethod
    def _score_structure(content: str) -> tuple[float, list[str]]:
        """Score semantic HTML structure (0–100)."""
        notes: list[str] = []
        score = 0.0

        # Detect whether content is HTML or Markdown
        is_html = bool(re.search(r"<[a-zA-Z][^>]*>", content))

        if is_html:
            h1_count = len(_H1_PATTERN.findall(content))
            h2_count = len(_H2_PATTERN.findall(content))
            h3_count = len(_H3_PATTERN.findall(content))
        else:
            h1_count = len(_MD_H1.findall(content))
            h2_count = len(_MD_H2.findall(content))
            h3_count = len(_MD_H3.findall(content))

        # H1 (20 pts)
        if h1_count == 1:
            score += 20.0
            notes.append("Correct: Exactly one H1 found.")
        elif h1_count > 1:
            score += 10.0
            notes.append(f"Warning: {h1_count} H1 tags found. Use exactly one H1 per page.")
        else:
            notes.append("Missing: No H1 found. Add a single H1 heading.")

        # H2 sections (25 pts)
        if h2_count >= 4:
            score += 25.0
            notes.append(f"Good: {h2_count} H2 sections found (target ≥4).")
        elif h2_count >= 2:
            score += 15.0
            notes.append(f"Moderate: {h2_count} H2 sections. Add more to improve structure.")
        elif h2_count == 1:
            score += 5.0
            notes.append("Only 1 H2 found. Expand the section structure.")
        else:
            notes.append("Missing: No H2 headings. Structure the content with subheadings.")

        # H3 sub-sections (10 pts)
        if h3_count >= 2:
            score += 10.0
            notes.append("Good: H3 sub-sections present.")
        else:
            notes.append("Consider adding H3 sub-sections for deeper structure.")

        # Schema markup (20 pts)
        if _SCHEMA_PATTERN.search(content):
            score += 20.0
            notes.append("Schema markup detected.")
        else:
            notes.append("Missing: No schema markup detected. Add JSON-LD or microdata.")

        # CTA presence (15 pts)
        cta_count = len(_CTA_PATTERN.findall(content))
        if cta_count >= 2:
            score += 15.0
            notes.append(f"Good: {cta_count} CTA phrase(s) found.")
        elif cta_count == 1:
            score += 8.0
            notes.append("One CTA found. Add 2–3 strategically placed CTAs.")
        else:
            notes.append("Missing: No clear CTAs detected.")

        # Trust section (10 pts)
        trust_hits = len(_TRUST_SECTION_PATTERN.findall(content))
        if trust_hits >= 3:
            score += 10.0
            notes.append("Trust signals present (testimonials, awards, etc.).")
        else:
            notes.append("Add trust/credibility signals: testimonials, awards, certifications.")

        return min(100.0, score), notes

    @staticmethod
    def _score_engagement(content: str) -> tuple[float, list[str]]:
        """Score engagement potential (0–100)."""
        notes: list[str] = []
        score = 0.0

        # Power words (up to 30 pts)
        power_count = len(_POWER_WORDS.findall(content))
        power_score = min(30.0, power_count * 2.0)
        score += power_score
        if power_count >= 10:
            notes.append("Strong: Plenty of power/persuasion words detected.")
        elif power_count >= 5:
            notes.append("Moderate: Some power words found. Add more benefit-driven language.")
        else:
            notes.append("Few power words found. Use more action-oriented, benefit-focused language.")

        # Benefit-driven language (up to 30 pts)
        benefit_count = len(_BENEFIT_LANGUAGE.findall(content))
        benefit_score = min(30.0, benefit_count * 3.0)
        score += benefit_score
        if benefit_count >= 5:
            notes.append("Good: Benefit and outcome language detected.")
        else:
            notes.append("Add more outcome-focused language (results, growth, ROI).")

        # Lists (up to 20 pts) — scannable content
        list_count = len(_LIST_PATTERN.findall(content))
        list_score = min(20.0, list_count * 2.0)
        score += list_score
        if list_count >= 5:
            notes.append("Good: Lists improve scannability.")
        else:
            notes.append("Add bullet or numbered lists to improve scannability.")

        # Rhetorical questions (up to 20 pts) — keep readers engaged
        question_count = len(_QUESTION_PATTERN.findall(content))
        q_score = min(20.0, question_count * 4.0)
        score += q_score
        if question_count >= 3:
            notes.append("Good: Questions create engagement and curiosity.")
        else:
            notes.append("Use questions to keep readers engaged and curious.")

        return min(100.0, score), notes

    @staticmethod
    def _score_uniqueness(content: str) -> tuple[float, list[str]]:
        """Score content uniqueness vs. generic/placeholder content (0–100)."""
        notes: list[str] = []
        score = 100.0  # Start at 100 and deduct

        # Placeholder phrases
        placeholder_count = len(_PLACEHOLDER_PHRASES.findall(content))
        placeholder_penalty = min(60.0, placeholder_count * 20.0)
        score -= placeholder_penalty
        if placeholder_count > 0:
            notes.append(
                f"Critical: {placeholder_count} placeholder/generic phrase(s) detected. "
                "Replace with specific, original content immediately."
            )
        else:
            notes.append("No placeholder phrases detected.")

        # Generic sentence openers
        opener_count = len(_BANNED_OPENERS.findall(content))
        opener_penalty = min(30.0, opener_count * 3.0)
        score -= opener_penalty
        if opener_count >= 5:
            notes.append(
                f"{opener_count} generic sentence openers detected. "
                "Vary sentence structure for uniqueness."
            )
        elif opener_count > 0:
            notes.append(f"{opener_count} weak sentence starter(s). Diversify.")
        else:
            notes.append("Sentence starters are varied — good for uniqueness.")

        # Very short content is likely generic
        word_count = len(content.split())
        if word_count < 300:
            score = min(score, 30.0)
            notes.append("Content is very short (<300 words). Expand for uniqueness and depth.")
        elif word_count < 800:
            score = min(score, 60.0)
            notes.append("Content length is below recommended (800+ words for uniqueness signal).")

        return max(0.0, score), notes
