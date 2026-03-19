"""Tests for src/quality_scorer.py — Five-metric quality scoring engine."""
from __future__ import annotations

import pytest

from src.quality_scorer import QualityScorer, _score_band, _clamp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scorer() -> QualityScorer:
    return QualityScorer()


# Minimal page with all semantic data populated
RICH_PAGE: dict = {
    "title": "NFT Consultant Services - CrowdCreate",
    "h1": "Expert NFT Strategy Consulting for Fortune 500 Companies",
    "meta_title": "NFT Consultant Services | CrowdCreate",  # 44 chars — short
    "meta_description": (
        "CrowdCreate specializes in NFT consulting for enterprise clients. "
        "Proven results in blockchain strategy and Web3 adoption."
    ),  # ~128 chars
    "target_keyword": "nft consulting services",
    "secondary_keywords": ["nft strategy", "blockchain consultant", "web3 advisory"],
    "word_count": 2847,
    "role": "hub",
    "hub_page_id": None,
    "color_override": "#2563EB",
    "semantic_core": {
        "entities": [
            {"text": "NFT", "entity_type": "TECHNOLOGY", "mentions": 23},
            {"text": "blockchain", "entity_type": "TECHNOLOGY", "mentions": 18},
            {"text": "enterprise adoption", "entity_type": "CONCEPT", "mentions": 7},
            {"text": "Ethereum", "entity_type": "TECHNOLOGY", "mentions": 5},
            {"text": "CrowdCreate", "entity_type": "ORG", "mentions": 9},
        ],
        "lsi_keywords": [
            "digital assets", "smart contracts", "tokenomics", "Web3",
            "decentralized", "DeFi", "enterprise", "blockchain adoption",
            "regulatory compliance", "token strategy",
        ],
        "topic_coverage": {
            "problem": "Enterprise companies struggle with NFT integration strategy",
            "solution": "CrowdCreate's 3-phase data-driven approach to blockchain adoption",
            "result": "Case study: Client reduced time-to-launch by 60%",
        },
    },
    "structure": {
        "h1": "Expert NFT Strategy Consulting for Fortune 500 Companies",
        "h2_sections": [
            {"text": "Why Enterprise NFT Strategies Fail", "subsections": ["Mistake 1", "Mistake 2"]},
            {"text": "Our NFT Consulting Framework", "subsections": ["Phase 1", "Phase 2", "Phase 3"]},
            {"text": "Case Studies", "subsections": ["Fashion Brand", "Financial Services"]},
            {"text": "Pricing & Timeline", "subsections": []},
            {"text": "FAQ", "subsections": []},
        ],
        "cta_sections": [
            {"position": "mid-page", "text": "Get a Free NFT Strategy Audit", "strength": "benefit-driven"},
            {"position": "end-of-page", "text": "Claim Your Consultation", "strength": "urgency"},
        ],
    },
    "competitor_intelligence": {
        "benchmarked_against": [
            {
                "url": "https://consensys.net/nft-services",
                "key_topics_covered": ["regulatory compliance", "technical architecture", "use cases"],
            }
        ],
        "competitive_advantage": [
            "Speed-to-Launch: 90 days vs. 6-month industry standard",
            "Fortune 500 case studies (competitors focus on startups)",
            "Regulatory compliance framework 2026",
        ],
    },
    "hub_and_spoke": {
        "role": "HUB",
        "spokes": [
            {"spoke_id": 43, "title": "Ultimate Guide", "anchor_text": "in-depth guide", "link_status": "verified"},
            {"spoke_id": 44, "title": "How to Choose", "anchor_text": "comprehensive guide", "link_status": "verified"},
        ],
    },
    "content_markdown": (
        "# Expert NFT Strategy Consulting\n\n"
        "Enterprise companies struggle with NFT integration strategy and face challenges.\n\n"
        "Our solution is a framework to solve this problem and address the issue.\n\n"
        "According to Gartner, 67% of Fortune 500 companies see NFTs as critical by 2026.\n\n"
        "Results: We helped a client achieve a 60% improvement in time-to-launch.\n\n"
        "Unlike Consensys, we focus on enterprise-specific blockchain strategy versus generic consulting.\n\n"
        "Our methodology involves a 3-phase approach:\n\n"
        "- Phase 1: Strategic Assessment\n"
        "- Phase 2: Blockchain Architecture Design\n"
        "- Phase 3: Launch & Scale\n\n"
        "Case study: Client reduced launch time by 60% compared to industry standard of 6 months.\n\n"
        "Save 6 months with our proven reduce risk framework that increases ROI by 40%.\n"
    ),
    "content_html": "<h1>Expert NFT Strategy</h1>",
    "last_modified_at": "2026-03-19T14:32:00Z",
}

# Minimal page — most fields missing or empty
MINIMAL_PAGE: dict = {
    "title": "Minimal Page",
    "h1": "",
    "meta_title": "",
    "meta_description": "",
    "target_keyword": "test keyword",
    "word_count": 100,
    "role": "spoke",
    "content_markdown": "",
    "content_html": "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_score_band_excellent(self) -> None:
        assert _score_band(95) == "Excellent"
        assert _score_band(90) == "Excellent"

    def test_score_band_strong(self) -> None:
        assert _score_band(85) == "Strong"
        assert _score_band(80) == "Strong"

    def test_score_band_good(self) -> None:
        assert _score_band(75) == "Good"
        assert _score_band(70) == "Good"

    def test_score_band_fair(self) -> None:
        assert _score_band(65) == "Fair"
        assert _score_band(60) == "Fair"

    def test_score_band_needs_work(self) -> None:
        assert _score_band(50) == "Needs Work"
        assert _score_band(0) == "Needs Work"

    def test_clamp_within_range(self) -> None:
        assert _clamp(50) == 50

    def test_clamp_above_max(self) -> None:
        assert _clamp(150) == 100

    def test_clamp_below_min(self) -> None:
        assert _clamp(-10) == 0


# ---------------------------------------------------------------------------
# QualityScorer.score()
# ---------------------------------------------------------------------------

class TestScoreOutputStructure:
    def test_returns_dict(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        assert isinstance(result, dict)

    def test_has_all_metric_keys(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        for key in (
            "authority_score",
            "semantic_richness_score",
            "structure_score",
            "engagement_potential_score",
            "uniqueness_score",
            "overall_score",
        ):
            assert key in result, f"Missing key: {key}"

    def test_all_scores_in_range(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        for key in (
            "authority_score", "semantic_richness_score", "structure_score",
            "engagement_potential_score", "uniqueness_score", "overall_score",
        ):
            score = result[key]
            assert 0 <= score <= 100, f"{key}={score} out of range"

    def test_overall_is_mean_of_five(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        five = [
            result["authority_score"],
            result["semantic_richness_score"],
            result["structure_score"],
            result["engagement_potential_score"],
            result["uniqueness_score"],
        ]
        expected = round(sum(five) / 5)
        assert result["overall_score"] == expected

    def test_has_breakdown_key(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        assert "breakdown" in result
        for metric in ("authority", "semantic_richness", "structure", "engagement", "uniqueness"):
            assert metric in result["breakdown"]

    def test_breakdown_has_positives_and_suggestions(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        for metric in result["breakdown"].values():
            assert "positives" in metric
            assert "suggestions" in metric
            assert isinstance(metric["positives"], list)
            assert isinstance(metric["suggestions"], list)

    def test_has_recommendations_list(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_breakdown_band_is_string(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        for metric in result["breakdown"].values():
            assert isinstance(metric["band"], str)


# ---------------------------------------------------------------------------
# Rich page scores higher than minimal page
# ---------------------------------------------------------------------------

class TestScoringRelative:
    def test_rich_page_authority_higher_than_minimal(self, scorer: QualityScorer) -> None:
        rich = scorer.score(RICH_PAGE)["authority_score"]
        minimal = scorer.score(MINIMAL_PAGE)["authority_score"]
        assert rich > minimal

    def test_rich_page_semantic_higher_than_minimal(self, scorer: QualityScorer) -> None:
        rich = scorer.score(RICH_PAGE)["semantic_richness_score"]
        minimal = scorer.score(MINIMAL_PAGE)["semantic_richness_score"]
        assert rich > minimal

    def test_rich_page_structure_higher_than_minimal(self, scorer: QualityScorer) -> None:
        rich = scorer.score(RICH_PAGE)["structure_score"]
        minimal = scorer.score(MINIMAL_PAGE)["structure_score"]
        assert rich > minimal

    def test_rich_page_engagement_higher_than_minimal(self, scorer: QualityScorer) -> None:
        rich = scorer.score(RICH_PAGE)["engagement_potential_score"]
        minimal = scorer.score(MINIMAL_PAGE)["engagement_potential_score"]
        assert rich > minimal

    def test_rich_page_overall_above_60(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        assert result["overall_score"] >= 60

    def test_minimal_page_overall_below_rich(self, scorer: QualityScorer) -> None:
        rich = scorer.score(RICH_PAGE)["overall_score"]
        minimal = scorer.score(MINIMAL_PAGE)["overall_score"]
        assert rich > minimal


# ---------------------------------------------------------------------------
# score_batch()
# ---------------------------------------------------------------------------

class TestScoreBatch:
    def test_score_batch_returns_list(self, scorer: QualityScorer) -> None:
        results = scorer.score_batch([RICH_PAGE, MINIMAL_PAGE])
        assert isinstance(results, list)
        assert len(results) == 2

    def test_score_batch_includes_page_id(self, scorer: QualityScorer) -> None:
        pages = [{**RICH_PAGE, "id": 42}, {**MINIMAL_PAGE, "id": 99}]
        results = scorer.score_batch(pages)
        assert results[0]["page_id"] == 42
        assert results[1]["page_id"] == 99

    def test_score_batch_no_page_id_still_returns_scores(self, scorer: QualityScorer) -> None:
        results = scorer.score_batch([RICH_PAGE])
        assert "overall_score" in results[0]
        assert "page_id" not in results[0]

    def test_score_batch_empty_list(self, scorer: QualityScorer) -> None:
        results = scorer.score_batch([])
        assert results == []


# ---------------------------------------------------------------------------
# quality_label() and color_for_score()
# ---------------------------------------------------------------------------

class TestLabelsAndColors:
    def test_quality_label_approve(self, scorer: QualityScorer) -> None:
        assert scorer.quality_label(90) == "Approve"
        assert scorer.quality_label(85) == "Approve"

    def test_quality_label_approve_with_notes(self, scorer: QualityScorer) -> None:
        assert scorer.quality_label(80) == "Approve with notes"
        assert scorer.quality_label(70) == "Approve with notes"

    def test_quality_label_needs_revision(self, scorer: QualityScorer) -> None:
        assert scorer.quality_label(60) == "Needs Revision"
        assert scorer.quality_label(55) == "Needs Revision"

    def test_quality_label_reject(self, scorer: QualityScorer) -> None:
        assert scorer.quality_label(40) == "Reject"
        assert scorer.quality_label(0) == "Reject"

    def test_color_for_score_green(self, scorer: QualityScorer) -> None:
        assert scorer.color_for_score(90) == "green"
        assert scorer.color_for_score(85) == "green"

    def test_color_for_score_yellow(self, scorer: QualityScorer) -> None:
        assert scorer.color_for_score(75) == "yellow"
        assert scorer.color_for_score(70) == "yellow"

    def test_color_for_score_orange(self, scorer: QualityScorer) -> None:
        assert scorer.color_for_score(60) == "orange"
        assert scorer.color_for_score(55) == "orange"

    def test_color_for_score_red(self, scorer: QualityScorer) -> None:
        assert scorer.color_for_score(40) == "red"
        assert scorer.color_for_score(0) == "red"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_dict_does_not_raise(self, scorer: QualityScorer) -> None:
        result = scorer.score({})
        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 100

    def test_none_values_do_not_raise(self, scorer: QualityScorer) -> None:
        page = {
            "semantic_core": None,
            "structure": None,
            "competitor_intelligence": None,
            "hub_and_spoke": None,
            "content_markdown": None,
        }
        result = scorer.score(page)
        assert "overall_score" in result

    def test_suggestions_provided_for_minimal_page(self, scorer: QualityScorer) -> None:
        result = scorer.score(MINIMAL_PAGE)
        assert len(result["recommendations"]) > 0

    def test_positives_provided_for_rich_page(self, scorer: QualityScorer) -> None:
        result = scorer.score(RICH_PAGE)
        total_positives = sum(
            len(m["positives"]) for m in result["breakdown"].values()
        )
        assert total_positives > 0
