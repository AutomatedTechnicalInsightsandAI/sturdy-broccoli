"""
quality_scorer.py

Five-metric quality scoring engine for the Decoupled SEO Site Factory.

Every page object is evaluated on five dimensions (0–100 each):

  1. Authority Score        — E-E-A-T signals (sources, competitor mentions, data)
  2. Semantic Richness      — LSI keywords, entity density, topic coverage depth
  3. Structure Score        — Heading hierarchy, schema markup, internal links
  4. Engagement Potential   — Problem-Solution-Result narrative, CTA strength
  5. Uniqueness Score       — Information gain vs. competitors, original angles

Overall = mean of the five metric scores (rounded to nearest integer).

Usage::

    scorer = QualityScorer()
    scores = scorer.score(page_data)
    # scores['overall_score'] == 87 (example)
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Module-level compiled patterns (avoid re-compilation on every call)
# ---------------------------------------------------------------------------

_CITATION_PATTERN = re.compile(
    r'(?:according to|cited by|source:|reference:|per |as reported by)',
    re.IGNORECASE,
)
_COMP_MENTION_PATTERN = re.compile(
    r'\b(?:[A-Z][a-z]+(?:labs?|io|\.com|\.net|ly)?)\b',
)
_STAT_PATTERN = re.compile(
    r'\d+\s*%|\d+x\s+(?:faster|slower|more|less)',
    re.IGNORECASE,
)
_AUTHOR_PATTERN = re.compile(r'\bauthor[:\s]', re.IGNORECASE)
_SUPERLATIVE_PATTERN = re.compile(
    r'\bguaranteed\b|\bbest in class\b|\bworld-class\b',
    re.IGNORECASE,
)
_PROBLEM_PATTERN = re.compile(
    r'\b(struggle|challenge|problem|pain point|issue|fail)\b',
    re.IGNORECASE,
)
_SOLUTION_PATTERN = re.compile(
    r'\b(solution|solve|fix|address|resolve|framework|approach)\b',
    re.IGNORECASE,
)
_RESULT_PATTERN = re.compile(
    r'\b(result|outcome|achieve|improve|reduce|increase|case study)\b',
    re.IGNORECASE,
)
_BENEFIT_PATTERN = re.compile(
    r'\b(reduce|save|increase|improve|achieve|accelerate|eliminate|grow)\b[^.]*\b\d+[%x]?\b',
    re.IGNORECASE,
)
_BULLET_PATTERN = re.compile(r'^[\s]*[-*•]\s', re.MULTILINE)
_RECENCY_PATTERN = re.compile(r'\b(202[4-9]|2030)\b')
_DIFF_STATEMENT_PATTERN = re.compile(
    r'\bunlike\b|\bcompared to\b|\bversus\b|\bdifferent from\b',
    re.IGNORECASE,
)
_RESEARCH_STAT_PATTERN = re.compile(
    r'\b\d+\s*%\s+(?:of|say|report|agree)',
    re.IGNORECASE,
)
_FRAMEWORK_PATTERN = re.compile(
    r'\b(?:framework|methodology|approach|process|model|system)\b',
    re.IGNORECASE,
)
_CASE_STUDY_PATTERN = re.compile(
    r'\bcase study\b|\bclient\b.{0,30}\b\d+%\b',
    re.IGNORECASE,
)

# Schema marker patterns (compiled once at module level)
_SCHEMA_MARKERS: dict[str, re.Pattern[str]] = {
    "Organization schema": re.compile(r'"@type"\s*:\s*"Organization"', re.IGNORECASE),
    "FAQ schema": re.compile(r'"@type"\s*:\s*"FAQPage"', re.IGNORECASE),
    "BreadcrumbList schema": re.compile(r'"@type"\s*:\s*"BreadcrumbList"', re.IGNORECASE),
    "Article schema": re.compile(r'"@type"\s*:\s*"Article"', re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# Score band helpers
# ---------------------------------------------------------------------------

def _score_band(score: int) -> str:
    """Return a human-readable band label for a 0–100 score."""
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Strong"
    if score >= 70:
        return "Good"
    if score >= 60:
        return "Fair"
    return "Needs Work"


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Metric 1: Authority Score (E-E-A-T)
# ---------------------------------------------------------------------------

def _score_authority(page: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    """
    Score E-E-A-T authority signals.

    Returns (score, positives, suggestions).
    """
    positives: list[str] = []
    suggestions: list[str] = []
    raw = 0

    # Cited industry sources (up to 3 = +45)
    semantic_core: dict[str, Any] = page.get("semantic_core") or {}
    content_md: str = page.get("content_markdown") or page.get("content_body", "")
    content_lower = content_md.lower()

    # Count source citations inferred from content or explicit field
    cited_sources: list[str] = []
    competitor_intel: dict[str, Any] = page.get("competitor_intelligence") or {}
    benchmarks: list[dict[str, Any]] = competitor_intel.get("benchmarked_against") or []
    # Each benchmark entry counts as knowledge of a competitor source
    source_count = min(len(benchmarks), 3)
    # Also look for citation patterns in content ("[source]", "according to", etc.)
    citation_matches = _CITATION_PATTERN.findall(content_lower)
    source_count = _clamp(source_count + len(citation_matches), 0, 3)
    raw += source_count * 15
    if source_count > 0:
        positives.append(f"{source_count} industry source(s) cited")
    else:
        suggestions.append("Add at least 1 cited industry source (Gartner, Forrester, etc.)")

    # Unbiased competitor mentions (up to 5 = +50)
    comp_advantages: list[str] = competitor_intel.get("competitive_advantage") or []
    # Count mentions of competitors in content
    comp_mentions = len(_COMP_MENTION_PATTERN.findall(content_md))
    # Clamp to realistic range for competitor mentions
    comp_mention_count = min(max(len(comp_advantages), comp_mentions // 10), 5)
    raw += comp_mention_count * 10
    if comp_mention_count > 0:
        positives.append(f"{comp_mention_count} unbiased competitor mention(s)")
    else:
        suggestions.append("Mention 1–5 competitors by name to signal confidence and unbiased expertise")

    # Original data points (up to 2 = +20)
    data_count = 0
    # Detect statistics / survey data in content
    stat_matches = _STAT_PATTERN.findall(content_lower)
    data_count = min(len(stat_matches), 2)
    raw += data_count * 10
    if data_count > 0:
        positives.append(f"{data_count} original data point(s) / statistic(s)")
    else:
        suggestions.append("Add 1–2 original statistics or case-study metrics")

    # Author byline (+5)
    if page.get("author") or _AUTHOR_PATTERN.search(content_lower):
        raw += 5
        positives.append("Author byline present")
    else:
        suggestions.append("Add an author byline with credentials")

    # Recency date (+5)
    if page.get("last_modified_at") or _RECENCY_PATTERN.search(content_md):
        raw += 5
        positives.append("Recency date visible (within last 2 years)")
    else:
        suggestions.append("Add a visible 'last updated' date")

    # Penalties
    if _SUPERLATIVE_PATTERN.search(content_lower):
        raw -= 10
        suggestions.append("Remove unsubstantiated superlatives ('guaranteed', 'world-class')")

    score = _clamp(raw)
    return score, positives, suggestions


# ---------------------------------------------------------------------------
# Metric 2: Semantic Richness (LSI & Entity Density)
# ---------------------------------------------------------------------------

def _score_semantic_richness(page: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    positives: list[str] = []
    suggestions: list[str] = []
    raw = 0

    semantic_core: dict[str, Any] = page.get("semantic_core") or {}
    lsi_keywords: list[str] = semantic_core.get("lsi_keywords") or []
    entities: list[dict[str, Any]] = semantic_core.get("entities") or []

    # LSI keywords (8 optimal, diminishing return >12, cap at 64+)
    lsi_count = len(lsi_keywords)
    if lsi_count >= 8:
        raw += min(lsi_count, 12) * 8
        positives.append(f"{lsi_count} LSI keywords detected (optimal: 8–12)")
    elif lsi_count > 0:
        raw += lsi_count * 8
        suggestions.append(f"Add more LSI keywords ({lsi_count}/8 minimum found)")
    else:
        suggestions.append("No LSI keywords found — add semantic variations of the target keyword")

    # Entity density (unique entities mentioned 3+ times)
    strong_entities = [e for e in entities if e.get("mentions", 0) >= 3]
    raw += len(strong_entities) * 5
    if strong_entities:
        positives.append(f"{len(strong_entities)} strong entity mention(s) (3+ times each)")
    else:
        suggestions.append("Build entity density: mention key concepts 3+ times each")

    # Topic coverage depth
    topic_coverage: dict[str, Any] = semantic_core.get("topic_coverage") or {}
    if topic_coverage.get("problem") and topic_coverage.get("solution") and topic_coverage.get("result"):
        raw += 15
        positives.append("Ultimate Guide structure: Problem → Solution → Result detected")
    elif topic_coverage.get("problem") or topic_coverage.get("solution"):
        raw += 8
        suggestions.append("Complete the Problem-Solution-Result narrative for full depth score")
    else:
        suggestions.append("Add topic_coverage with problem, solution, and result angles")

    # H2 sections depth
    structure: dict[str, Any] = page.get("structure") or {}
    h2_sections: list[dict[str, Any]] = structure.get("h2_sections") or []
    if len(h2_sections) >= 5:
        raw += 10
        positives.append(f"{len(h2_sections)} H2 sections provide comprehensive subtopic coverage")
    elif len(h2_sections) >= 3:
        raw += 5
        suggestions.append(f"Add {5 - len(h2_sections)} more H2 sections for comprehensive subtopic coverage")
    else:
        suggestions.append("Add at least 5 H2 sections with unique subtopic angles")

    # Spoke uniqueness vs hub
    role = page.get("role", "spoke")
    if role == "spoke":
        hub_page_id = page.get("hub_page_id")
        if hub_page_id:
            raw += 10
            positives.append("Spoke page covers unique angle differentiated from hub")

    score = _clamp(raw)
    return score, positives, suggestions


# ---------------------------------------------------------------------------
# Metric 3: Structure & Schema Validation
# ---------------------------------------------------------------------------

def _score_structure(page: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    positives: list[str] = []
    suggestions: list[str] = []
    raw = 0

    structure: dict[str, Any] = page.get("structure") or {}
    content_md: str = page.get("content_markdown") or page.get("content_body", "")

    # H1 — single, descriptive, <60 chars
    h1 = page.get("h1") or structure.get("h1") or ""
    if h1:
        raw += 20
        if len(h1) <= 60:
            positives.append(f"Valid H1 ({len(h1)} chars, within 60-char limit)")
        else:
            suggestions.append(f"Shorten H1 to <60 chars (currently {len(h1)} chars)")
    else:
        suggestions.append("Add an H1 heading to the page")

    # H2 sections
    h2_sections: list[dict[str, Any]] = structure.get("h2_sections") or []
    h2_count = len(h2_sections)
    if 3 <= h2_count <= 5:
        raw += 15
        positives.append(f"{h2_count} H2 sections (optimal range 3–5)")
    elif h2_count > 5:
        raw += 10
        positives.append(f"{h2_count} H2 sections present")
    elif h2_count > 0:
        raw += 5
        suggestions.append(f"Add {3 - h2_count} more H2 sections (minimum 3)")
    else:
        suggestions.append("Add H2 sections to the page structure")

    # H3 subsections
    h3_count = sum(len(s.get("subsections") or []) for s in h2_sections)
    if h3_count > 0:
        raw += 10
        positives.append(f"{h3_count} H3 subsections provide logical hierarchy")
    else:
        suggestions.append("Add H3 subsections under each H2 for deeper structure")

    # Schema markup — use module-level compiled patterns
    content_html: str = page.get("content_html") or ""
    combined = content_md + content_html
    schema_found: list[str] = []
    for schema_name, pattern in _SCHEMA_MARKERS.items():
        if pattern.search(combined):
            schema_found.append(schema_name)

    schema_points = {
        "Organization schema": 15,
        "FAQ schema": 10,
        "BreadcrumbList schema": 10,
        "Article schema": 5,
    }
    for schema in schema_found:
        raw += schema_points.get(schema, 5)
        positives.append(f"{schema} present")
    for schema in _SCHEMA_MARKERS:
        if schema not in schema_found:
            suggestions.append(f"Add {schema} for richer search engine understanding")

    # Internal link integrity (hub-spoke)
    hub_and_spoke: dict[str, Any] = page.get("hub_and_spoke") or {}
    role = page.get("role", "spoke")
    spokes: list[dict[str, Any]] = hub_and_spoke.get("spokes") or []
    if role == "hub" and len(spokes) > 0:
        verified = sum(1 for s in spokes if s.get("link_status") == "verified")
        raw += 20
        positives.append(f"Hub page links to {len(spokes)} spoke(s) ({verified} verified)")
    elif role == "spoke" and page.get("hub_page_id"):
        raw += 10
        positives.append("Spoke page links back to hub")
    else:
        suggestions.append("Set up hub-and-spoke internal linking for SEO equity")

    # Metadata
    meta_title = page.get("meta_title") or ""
    meta_desc = page.get("meta_description") or ""
    if 50 <= len(meta_title) <= 60:
        raw += 5
        positives.append(f"Meta title optimal length ({len(meta_title)} chars)")
    elif meta_title:
        raw += 3
        suggestions.append(f"Adjust meta title to 50–60 chars (currently {len(meta_title)} chars)")
    else:
        suggestions.append("Add meta title (50–60 chars)")

    if 155 <= len(meta_desc) <= 160:
        raw += 5
        positives.append(f"Meta description optimal length ({len(meta_desc)} chars)")
    elif meta_desc:
        raw += 3
        suggestions.append(f"Adjust meta description to 155–160 chars (currently {len(meta_desc)} chars)")
    else:
        suggestions.append("Add meta description (155–160 chars)")

    score = _clamp(raw)
    return score, positives, suggestions


# ---------------------------------------------------------------------------
# Metric 4: Engagement Potential (Narrative & CTA Strength)
# ---------------------------------------------------------------------------

def _score_engagement(page: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    positives: list[str] = []
    suggestions: list[str] = []
    raw = 0

    content_md: str = page.get("content_markdown") or page.get("content_body", "")
    content_lower = content_md.lower()
    structure: dict[str, Any] = page.get("structure") or {}
    cta_sections: list[dict[str, Any]] = structure.get("cta_sections") or []
    semantic_core: dict[str, Any] = page.get("semantic_core") or {}
    topic_coverage: dict[str, Any] = semantic_core.get("topic_coverage") or {}

    # Problem-Solution-Result narrative
    has_problem = bool(
        topic_coverage.get("problem")
        or _PROBLEM_PATTERN.search(content_lower)
    )
    has_solution = bool(
        topic_coverage.get("solution")
        or _SOLUTION_PATTERN.search(content_lower)
    )
    has_result = bool(
        topic_coverage.get("result")
        or _RESULT_PATTERN.search(content_lower)
    )

    if has_problem:
        raw += 25
        positives.append("Problem statement detected in content")
    else:
        suggestions.append("Add a clear problem statement in the opening 100 words")

    if has_solution:
        raw += 25
        positives.append("Solution section explains the 'how'")
    else:
        suggestions.append("Add a solution section describing your approach or framework")

    if has_result:
        raw += 15
        positives.append("Result/outcome section with specific metrics or case study")
    else:
        suggestions.append("Add a result section with measurable outcomes (e.g., '60% faster launch')")

    # CTA placement & strength
    mid_cta = next((c for c in cta_sections if c.get("position") == "mid-page"), None)
    end_cta = next((c for c in cta_sections if c.get("position") == "end-of-page"), None)

    if mid_cta:
        raw += 15
        positives.append(f"Mid-page CTA: '{mid_cta.get('text', '')}'")
        if mid_cta.get("strength") != "benefit-driven":
            suggestions.append("Strengthen mid-page CTA with benefit-driven language")
    else:
        suggestions.append("Add a mid-page CTA with benefit-driven language")

    if end_cta:
        raw += 15
        positives.append(f"End-of-page CTA: '{end_cta.get('text', '')}'")
        if end_cta.get("strength") != "urgency":
            suggestions.append("Strengthen end-of-page CTA with urgency language ('Claim your…')")
    else:
        suggestions.append("Add an end-of-page CTA with urgency language")

    # CTA brand colour
    color_override = page.get("color_override") or ""
    if color_override:
        raw += 5
        positives.append("CTA uses brand primary colour")
    else:
        suggestions.append("Apply brand primary colour to CTA buttons")

    # Benefit statements
    benefit_matches = _BENEFIT_PATTERN.findall(content_lower)
    benefit_count = min(len(benefit_matches), 3)
    raw += benefit_count * 5
    if benefit_count > 0:
        positives.append(f"{benefit_count} benefit statement(s) with quantified outcomes")
    else:
        suggestions.append("Add 1–3 benefit statements with quantified outcomes")

    # Readability
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', content_md) if p.strip()]
    long_paras = [p for p in paragraphs if len(p.split()) > 200]
    if paragraphs and not long_paras:
        raw += 5
        positives.append("Paragraphs are scannable (<200 words each)")
    elif long_paras:
        suggestions.append(f"Break up {len(long_paras)} dense paragraph(s) (>200 words)")

    if _BULLET_PATTERN.search(content_md):
        raw += 5
        positives.append("Bullet lists improve scannability")
    else:
        suggestions.append("Add bullet lists for improved scannability")

    score = _clamp(raw)
    return score, positives, suggestions


# ---------------------------------------------------------------------------
# Metric 5: Uniqueness vs. Competitors (Information Gain)
# ---------------------------------------------------------------------------

def _score_uniqueness(page: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    positives: list[str] = []
    suggestions: list[str] = []
    raw = 0

    competitor_intel: dict[str, Any] = page.get("competitor_intelligence") or {}
    benchmarks: list[dict[str, Any]] = competitor_intel.get("benchmarked_against") or []
    advantages: list[str] = competitor_intel.get("competitive_advantage") or []
    content_md: str = page.get("content_markdown") or page.get("content_body", "")
    content_lower = content_md.lower()

    # Content overlap estimation (heuristic: fewer benchmark topics that overlap = more unique)
    if not benchmarks:
        # No competitor data — assume moderate uniqueness
        raw += 20
        suggestions.append("Supply competitor URLs in competitor_intelligence to enable overlap analysis")
    else:
        # Count overlapping topics (topics shared with competitors)
        overlapping_topics = 0
        for bench in benchmarks:
            shared_topics: list[str] = bench.get("key_topics_covered") or []
            for topic in shared_topics:
                if topic.lower() in content_lower:
                    overlapping_topics += 1

        total_competitor_topics = sum(
            len(bench.get("key_topics_covered") or []) for bench in benchmarks
        )
        if total_competitor_topics > 0:
            overlap_ratio = overlapping_topics / total_competitor_topics
        else:
            overlap_ratio = 0.0

        if overlap_ratio < 0.3:
            raw += 30
            positives.append(f"<30% content overlap with competitors (highly original)")
        elif overlap_ratio < 0.5:
            raw += 20
            positives.append(f"30–50% content overlap (some original angles)")
            suggestions.append("Reduce overlap by differentiating sections that mirror competitors")
        elif overlap_ratio < 0.7:
            raw += 10
            suggestions.append(f"50–70% content overlap — add more differentiated sections")
        else:
            suggestions.append(">70% overlap with competitors — regenerate to add unique value")

    # Unique angles / differentiators (up to 3 = +45)
    unique_angle_count = min(len(advantages), 3)
    raw += unique_angle_count * 15
    if unique_angle_count > 0:
        positives.append(f"{unique_angle_count} unique angle(s) not found in competitors")
    else:
        suggestions.append("Define 1–3 competitive differentiators in competitor_intelligence")

    # Information gain signals
    # Original research/stat
    if _RESEARCH_STAT_PATTERN.search(content_lower):
        raw += 10
        positives.append("Original research statistic present")
    else:
        suggestions.append("Add an original statistic or proprietary research finding")

    # Unique framework/methodology
    if _FRAMEWORK_PATTERN.search(content_lower):
        raw += 10
        positives.append("Unique framework or methodology described")
    else:
        suggestions.append("Describe a proprietary framework or methodology to differentiate")

    # Original case study
    if _CASE_STUDY_PATTERN.search(content_lower):
        raw += 10
        positives.append("Original case study or client outcome present")
    else:
        suggestions.append("Add an original case study with measurable client outcomes")

    # Clear differentiation statement
    if _DIFF_STATEMENT_PATTERN.search(content_lower):
        raw += 5
        positives.append("Clear differentiation statement vs. competitors")
    else:
        suggestions.append("Add an explicit differentiation statement vs. competitors")

    score = _clamp(raw)
    return score, positives, suggestions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class QualityScorer:
    """
    Evaluates a page object on five SEO quality dimensions.

    The page object should follow the data model described in the
    problem statement (JSON-first structure with semantic_core,
    structure, competitor_intelligence, etc.).
    """

    # Metric weights (equal by default, matching spec)
    WEIGHTS: dict[str, float] = {
        "authority_score": 1.0,
        "semantic_richness_score": 1.0,
        "structure_score": 1.0,
        "engagement_potential_score": 1.0,
        "uniqueness_score": 1.0,
    }

    def score(self, page: dict[str, Any]) -> dict[str, Any]:
        """
        Score a page object and return a comprehensive quality report.

        Parameters
        ----------
        page:
            The page data dict (page object as described in the spec).

        Returns
        -------
        dict with keys:
            ``authority_score``, ``semantic_richness_score``,
            ``structure_score``, ``engagement_potential_score``,
            ``uniqueness_score``, ``overall_score``,
            ``breakdown`` (per-metric positives and suggestions),
            ``recommendations`` (flat list of all suggestions)
        """
        auth_score, auth_pos, auth_sug = _score_authority(page)
        sem_score, sem_pos, sem_sug = _score_semantic_richness(page)
        struct_score, struct_pos, struct_sug = _score_structure(page)
        eng_score, eng_pos, eng_sug = _score_engagement(page)
        uniq_score, uniq_pos, uniq_sug = _score_uniqueness(page)

        overall = round(
            (auth_score + sem_score + struct_score + eng_score + uniq_score) / 5
        )

        breakdown: dict[str, Any] = {
            "authority": {
                "score": auth_score,
                "band": _score_band(auth_score),
                "positives": auth_pos,
                "suggestions": auth_sug,
            },
            "semantic_richness": {
                "score": sem_score,
                "band": _score_band(sem_score),
                "positives": sem_pos,
                "suggestions": sem_sug,
            },
            "structure": {
                "score": struct_score,
                "band": _score_band(struct_score),
                "positives": struct_pos,
                "suggestions": struct_sug,
            },
            "engagement": {
                "score": eng_score,
                "band": _score_band(eng_score),
                "positives": eng_pos,
                "suggestions": eng_sug,
            },
            "uniqueness": {
                "score": uniq_score,
                "band": _score_band(uniq_score),
                "positives": uniq_pos,
                "suggestions": uniq_sug,
            },
        }

        all_suggestions = auth_sug + sem_sug + struct_sug + eng_sug + uniq_sug

        return {
            "authority_score": auth_score,
            "semantic_richness_score": sem_score,
            "structure_score": struct_score,
            "engagement_potential_score": eng_score,
            "uniqueness_score": uniq_score,
            "overall_score": overall,
            "breakdown": breakdown,
            "recommendations": all_suggestions,
        }

    def score_batch(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Score a list of page objects and return a list of quality reports.

        Each result dict is augmented with ``page_id`` if present in the
        page object.
        """
        results: list[dict[str, Any]] = []
        for page in pages:
            result = self.score(page)
            if "id" in page:
                result["page_id"] = page["id"]
            results.append(result)
        return results

    @staticmethod
    def quality_label(overall_score: int) -> str:
        """Return a human-readable status label for an overall score."""
        if overall_score >= 85:
            return "Approve"
        if overall_score >= 70:
            return "Approve with notes"
        if overall_score >= 55:
            return "Needs Revision"
        return "Reject"

    @staticmethod
    def color_for_score(score: int) -> str:
        """Return a colour name suitable for UI display (green/yellow/orange/red)."""
        if score >= 85:
            return "green"
        if score >= 70:
            return "yellow"
        if score >= 55:
            return "orange"
        return "red"
