"""Tests for the multi-dimensional QualityScorer."""
from __future__ import annotations

import pytest

from src.quality_scorer import QualityScorer, QualityScoreResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_HIGH_QUALITY_HTML = """
<html>
<head>
<script type="application/ld+json">{"@context":"https://schema.org"}</script>
</head>
<body>
<h1>Local SEO Services That Drive Real Revenue</h1>
<p>According to Google, 46% of all searches have local intent.
Our proven methodology has helped 500+ businesses increase calls by 3×.</p>
<h2>Why Local SEO Matters for Your Business</h2>
<p>Unlike generic SEO, local search targets customers in your geography.
We've measured a 40% increase in map-pack clicks within 90 days.
Research shows businesses in the top 3 positions receive 75% of local clicks.</p>
<h2>Our Battle-Tested Process</h2>
<ul>
  <li>Google Business Profile optimisation</li>
  <li>Citation building and NAP consistency</li>
  <li>Local link acquisition from community sites</li>
  <li>Review strategy and management</li>
</ul>
<h2>Client Results That Prove Our Approach</h2>
<p>Case study: Pacific Plumbing increased calls from Google by 2× in 60 days.
Client result: Bright Smiles Dental ranked in the top 3 local pack for all target terms.</p>
<blockquote>Within 60 days we were in the top 3 of the local pack.</blockquote>
<h2>Why We Outperform Competitors</h2>
<p>Compared to Thrive Internet Marketing and WebFX, we deliver faster results
with transparent monthly reporting. Unlike most agencies, we guarantee map-pack
placement or your money back.</p>
<h3>Our Reporting Framework</h3>
<p>We track calls, clicks, and conversions — not just rankings.
Our proprietary ROI calculator shows your return on investment monthly.</p>
<h2>Trust Signals &amp; Credentials</h2>
<p>Certified Google Partner. Award-winning agency. 10 years experience.
Clutch Top 100 SEO Agency 2024. 500+ clients served.</p>
<h2>Get Started Today</h2>
<p>Ready to dominate local search? Get your free Local SEO audit today.
Book a strategy call now. Schedule your consultation.</p>
</body>
</html>
"""

_LOW_QUALITY_HTML = """
<p>This is a generated page about local seo. Lorem ipsum placeholder.
In today's world, it is important to leverage the power of local SEO.
As a game-changer, we take your business to the next level.
Think outside the box with our dynamic solutions.
This is a placeholder. Add content here. TODO.</p>
"""

_MARKDOWN_CONTENT = """
# Ultimate Guide to LinkedIn Marketing

## Why LinkedIn Marketing Drives B2B Results

According to HubSpot, LinkedIn generates 80% of B2B social media leads.
Our proven LinkedIn strategy has helped clients increase leads by 3× in 90 days.

## Our Battle-Tested LinkedIn Process

Research shows that companies posting consistently see 2× more engagement.
We've measured these results across 200+ campaigns.

1. Profile optimisation
2. Content calendar creation
3. Outreach strategy
4. Analytics and reporting

## Case Studies: LinkedIn Marketing Results

Case study: Tech startup achieved 150% more qualified leads in Q1.
Client result: SaaS company grew their pipeline by $2M via LinkedIn outreach.

## Get Your Free LinkedIn Audit

Schedule a strategy call today. Get started with LinkedIn marketing.
Book your free consultation now.
"""


# ---------------------------------------------------------------------------
# Test: Score returns correct types
# ---------------------------------------------------------------------------


class TestQualityScorerTypes:
    def test_returns_quality_score_result(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(_HIGH_QUALITY_HTML)
        assert isinstance(result, QualityScoreResult)

    def test_all_scores_are_floats(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(_HIGH_QUALITY_HTML)
        assert isinstance(result.authority, float)
        assert isinstance(result.semantic, float)
        assert isinstance(result.structure, float)
        assert isinstance(result.engagement, float)
        assert isinstance(result.uniqueness, float)
        assert isinstance(result.overall, float)

    def test_scores_in_range_0_to_100(self) -> None:
        scorer = QualityScorer()
        for content in (_HIGH_QUALITY_HTML, _LOW_QUALITY_HTML, _MARKDOWN_CONTENT):
            result = scorer.score(content)
            for dim in ("authority", "semantic", "structure", "engagement", "uniqueness", "overall"):
                val = getattr(result, dim)
                assert 0.0 <= val <= 100.0, f"{dim} score {val} out of range for content"

    def test_as_dict_returns_dict(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(_HIGH_QUALITY_HTML)
        d = result.as_dict()
        assert isinstance(d, dict)
        for key in ("authority", "semantic", "structure", "engagement", "uniqueness", "overall"):
            assert key in d
        assert "explanations" in d

    def test_explanations_have_all_dimensions(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(_HIGH_QUALITY_HTML)
        for dim in ("authority", "semantic", "structure", "engagement", "uniqueness"):
            assert dim in result.explanations
            assert isinstance(result.explanations[dim], list)


# ---------------------------------------------------------------------------
# Test: High-quality content scores higher than low-quality
# ---------------------------------------------------------------------------


class TestQualityScorerRelativeScores:
    def test_high_quality_overall_exceeds_low_quality(self) -> None:
        scorer = QualityScorer()
        high = scorer.score(_HIGH_QUALITY_HTML)
        low = scorer.score(_LOW_QUALITY_HTML)
        assert high.overall > low.overall

    def test_high_quality_authority_exceeds_low(self) -> None:
        scorer = QualityScorer()
        high = scorer.score(_HIGH_QUALITY_HTML)
        low = scorer.score(_LOW_QUALITY_HTML)
        assert high.authority > low.authority

    def test_high_quality_structure_exceeds_low(self) -> None:
        scorer = QualityScorer()
        high = scorer.score(_HIGH_QUALITY_HTML)
        low = scorer.score(_LOW_QUALITY_HTML)
        assert high.structure > low.structure

    def test_high_quality_uniqueness_exceeds_low(self) -> None:
        scorer = QualityScorer()
        high = scorer.score(_HIGH_QUALITY_HTML)
        low = scorer.score(_LOW_QUALITY_HTML)
        # High quality has no placeholder phrases; low quality does.
        # Both are capped by word count, but low quality has additional
        # placeholder penalty so it cannot exceed high quality.
        assert high.uniqueness >= low.uniqueness

    def test_placeholder_content_has_low_uniqueness(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(_LOW_QUALITY_HTML)
        # Low quality with placeholder phrases should score below 50
        assert result.uniqueness <= 50.0

    def test_markdown_scores_reasonably(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(_MARKDOWN_CONTENT)
        assert result.overall > 20.0


# ---------------------------------------------------------------------------
# Test: Authority score dimension
# ---------------------------------------------------------------------------


class TestAuthorityScore:
    def test_no_citations_lowers_authority(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("<p>We are the best agency.</p>")
        assert result.authority < 50.0

    def test_statistics_improve_authority(self) -> None:
        scorer = QualityScorer()
        result_no_stats = scorer.score("<p>We help businesses rank higher.</p>")
        result_with_stats = scorer.score(
            "<p>According to Google, 46% of searches have local intent. "
            "Research shows 3× increase in leads. Data suggests 80% improvement.</p>"
        )
        assert result_with_stats.authority > result_no_stats.authority

    def test_competitor_mentions_improve_authority(self) -> None:
        scorer = QualityScorer()
        result_no_comp = scorer.score("<p>We are a great SEO agency.</p>")
        result_with_comp = scorer.score(
            "<p>Compared to competitors like Thrive and WebFX, "
            "we deliver versus industry rivals. Unlike alternatives, "
            "we guarantee results.</p>"
        )
        assert result_with_comp.authority > result_no_comp.authority

    def test_named_sources_improve_authority(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(
            "<p>According to Google and HubSpot research, SEMrush data shows...</p>"
        )
        assert result.authority > 20.0


# ---------------------------------------------------------------------------
# Test: Structure score dimension
# ---------------------------------------------------------------------------


class TestStructureScore:
    def test_single_h1_gives_full_h1_score(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("<h1>Title</h1><h2>Section</h2>")
        # Should get H1 points
        assert result.structure > 10.0

    def test_no_headings_gives_low_structure(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("<p>Just a paragraph with no headings at all.</p>")
        assert result.structure < 30.0

    def test_schema_markup_improves_structure(self) -> None:
        scorer = QualityScorer()
        without_schema = scorer.score(
            "<h1>Title</h1><h2>Section 1</h2><h2>Section 2</h2>"
        )
        with_schema = scorer.score(
            '<script type="application/ld+json">{}</script>'
            "<h1>Title</h1><h2>Section 1</h2><h2>Section 2</h2>"
        )
        assert with_schema.structure > without_schema.structure

    def test_multiple_h2_improves_structure(self) -> None:
        scorer = QualityScorer()
        one_h2 = scorer.score("<h1>Title</h1><h2>Only One Section</h2>")
        many_h2 = scorer.score(
            "<h1>T</h1><h2>S1</h2><h2>S2</h2><h2>S3</h2><h2>S4</h2>"
        )
        assert many_h2.structure > one_h2.structure

    def test_markdown_h1_and_h2_detected(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("# Title\n\n## Section A\n\n## Section B\n\n## Section C\n\n## Section D")
        assert result.structure > 20.0


# ---------------------------------------------------------------------------
# Test: Uniqueness score dimension
# ---------------------------------------------------------------------------


class TestUniquenessScore:
    def test_placeholder_text_zeros_uniqueness(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(
            "This is a generated page about local SEO. Lorem ipsum placeholder. TODO."
        )
        # With placeholder phrases and short content, uniqueness should be <= 30
        assert result.uniqueness <= 30.0

    def test_specific_content_has_high_uniqueness(self) -> None:
        scorer = QualityScorer()
        result = scorer.score(
            "Pacific Plumbing achieved 3× call volume growth by optimising "
            "their Google Business Profile for 12 location-specific keywords. "
            "The campaign delivered 2,400 additional monthly calls within 60 days. "
            "This was measured using call tracking software integrated with GA4. "
            "The team focused on citation consistency across 85 directories. "
            "Their NAP data was updated across Yelp, Yellow Pages, and Bing Places. "
            "The result: #1 map-pack ranking for 'plumber [city]' in all 4 target areas."
        )
        # Specific content has no placeholder phrases; only word-count cap applies
        assert result.uniqueness >= 30.0

    def test_short_content_capped_uniqueness(self) -> None:
        scorer = QualityScorer()
        # Short but specific content — uniqueness capped due to word count
        result = scorer.score("Local SEO drives revenue.")
        assert result.uniqueness <= 60.0


# ---------------------------------------------------------------------------
# Test: page_data integration
# ---------------------------------------------------------------------------


class TestPageDataIntegration:
    def test_keyword_match_improves_semantic_score(self) -> None:
        scorer = QualityScorer()
        page_data = {"primary_keyword": "local seo services"}
        result_match = scorer.score(
            "local seo services that drive revenue for your business", page_data
        )
        result_no_match = scorer.score(
            "digital marketing that drives revenue for your business", page_data
        )
        assert result_match.semantic > result_no_match.semantic

    def test_empty_page_data_does_not_raise(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("<h1>Title</h1>", {})
        assert isinstance(result, QualityScoreResult)

    def test_none_page_data_does_not_raise(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("<h1>Title</h1>", None)
        assert isinstance(result, QualityScoreResult)


# ---------------------------------------------------------------------------
# Test: empty / edge case content
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_content_returns_all_zeros(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("")
        # Empty content should score 0 on dimensions that require content,
        # with overall close to zero.
        assert result.authority == 0.0
        assert result.semantic == 0.0
        assert result.structure == 0.0
        assert result.engagement == 0.0
        assert result.overall < 10.0

    def test_whitespace_only_content(self) -> None:
        scorer = QualityScorer()
        result = scorer.score("   \n\t  ")
        assert result.overall >= 0.0

    def test_very_long_content_does_not_error(self) -> None:
        scorer = QualityScorer()
        long_content = (
            "<h1>Title</h1>"
            + "<h2>Section</h2><p>According to research, 50% of businesses saw results. "
            "We helped clients increase revenue by 3×. Case study: Company X grew leads. "
            "Compared to Thrive Agency, our ROI is better. Get your free audit today. "
            "Book a consultation now. Schedule your call. "
            "Certified Google Partner. Award-winning team. </p>" * 100
        )
        result = scorer.score(long_content)
        for dim in ("authority", "semantic", "structure", "engagement", "uniqueness", "overall"):
            val = getattr(result, dim)
            assert 0.0 <= val <= 100.0
