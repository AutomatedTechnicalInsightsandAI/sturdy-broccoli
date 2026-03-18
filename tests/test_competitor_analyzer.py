"""Tests for CompetitorAnalyzer."""
from __future__ import annotations

import pytest

from src.competitor_analyzer import CompetitorAnalyzer, CompetitorProfile, CompetitorReport


_COMPETITOR_A = {
    "name": "Agency Alpha",
    "url": "https://agencyalpha.example.com",
    "page_title": "Digital PR Agency — Agency Alpha",
    "h1": "Digital PR That Drives SEO Authority",
    "h2_headings": [
        "Our Digital PR Process",
        "Why Choose Agency Alpha?",
        "Case Studies",
        "Measuring ROI",
    ],
    "keywords": ["digital PR agency", "link building", "earned media"],
    "content": (
        "Agency Alpha is an award-winning digital PR agency with 10 years experience. "
        "We create campaigns that earn links from top-tier publications. "
        "Our team of 50+ specialists delivers case studies showing 100+ links per campaign. "
        "We are Google Partner certified. Clients include Fortune 500 companies."
    ),
}

_COMPETITOR_B = {
    "name": "Brand Beta",
    "url": "https://brandbeta.example.com",
    "page_title": "Link Building Agency — Brand Beta",
    "h1": "Creative PR Campaigns for SEO",
    "h2_headings": [
        "What Is Digital PR?",
        "Our Approach",
        "Results",
    ],
    "keywords": ["digital PR", "link building agency", "earned media SEO"],
    "content": (
        "Brand Beta delivers creative PR campaigns. "
        "We have worked with 200+ clients. "
        "Results include coverage in BBC and Guardian. "
        "No long-term contracts required."
    ),
}


class TestBuildProfile:
    def test_returns_competitor_profile(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert isinstance(profile, CompetitorProfile)

    def test_name_is_set(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert profile.name == "Agency Alpha"

    def test_keywords_are_populated(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert len(profile.keywords) > 0

    def test_word_count_is_calculated(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert profile.word_count > 0

    def test_content_themes_are_detected(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert isinstance(profile.content_themes, list)

    def test_trust_signals_detected_for_rich_content(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert isinstance(profile.trust_signals, list)

    def test_has_case_studies_detected(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile(_COMPETITOR_A)
        assert profile.has_case_studies is True

    def test_has_case_studies_false_for_minimal_content(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile({"name": "Minimal", "content": "We do PR."})
        assert profile.has_case_studies is False

    def test_missing_content_gives_zero_word_count(self) -> None:
        analyzer = CompetitorAnalyzer()
        profile = analyzer.build_profile({"name": "NoContent"})
        assert profile.word_count == 0


class TestAnalyze:
    def test_returns_competitor_report(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A, _COMPETITOR_B])
        assert isinstance(report, CompetitorReport)

    def test_service_topic_is_set(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A])
        assert report.service_topic == "Digital PR"

    def test_competitor_count_matches_input(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A, _COMPETITOR_B])
        assert len(report.competitors) == 2

    def test_common_themes_is_list(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A, _COMPETITOR_B])
        assert isinstance(report.common_themes, list)

    def test_content_gaps_is_list(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A, _COMPETITOR_B])
        assert isinstance(report.content_gaps, list)

    def test_differentiation_opportunities_populated(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze(
            "Digital PR",
            [_COMPETITOR_A],
            our_strengths=["Data journalism approach"],
        )
        assert len(report.differentiation_opportunities) > 0

    def test_recommended_spoke_topics_populated(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A])
        assert len(report.recommended_spoke_topics) >= 3

    def test_summary_is_non_empty_string(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A])
        assert isinstance(report.summary, str)
        assert len(report.summary) > 10

    def test_empty_competitors_list_returns_report(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [])
        assert isinstance(report, CompetitorReport)
        assert report.competitors == []

    def test_unique_positioning_is_non_empty(self) -> None:
        analyzer = CompetitorAnalyzer()
        report = analyzer.analyze("Digital PR", [_COMPETITOR_A])
        assert len(report.unique_positioning) > 0


class TestExtractKeywordsFromHeadings:
    def test_returns_list_of_strings(self) -> None:
        analyzer = CompetitorAnalyzer()
        headings = ["Why Digital PR Matters for SEO", "Our Approach to Link Building"]
        result = analyzer.extract_keywords_from_headings(headings)
        assert isinstance(result, list)
        assert all(isinstance(k, str) for k in result)

    def test_stop_words_removed(self) -> None:
        analyzer = CompetitorAnalyzer()
        headings = ["The Best Digital PR Agency in the World"]
        result = analyzer.extract_keywords_from_headings(headings)
        # Stop words like 'the', 'in' should not appear as standalone terms
        flat = " ".join(result)
        assert " the " not in flat.lower()

    def test_returns_at_most_twenty_phrases(self) -> None:
        analyzer = CompetitorAnalyzer()
        headings = [f"Heading Number {i} about marketing strategy" for i in range(50)]
        result = analyzer.extract_keywords_from_headings(headings)
        assert len(result) <= 20

    def test_empty_headings_returns_empty_list(self) -> None:
        analyzer = CompetitorAnalyzer()
        result = analyzer.extract_keywords_from_headings([])
        assert result == []
