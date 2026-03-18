"""Tests for MultiFormatGenerator."""
from __future__ import annotations

import pytest

from src.multi_format_generator import FormatOutput, MultiFormatBundle, MultiFormatGenerator

_SOURCE = {
    "topic": "GEO and AI SEO for Enterprise Brands",
    "service_name": "GEO/AI SEO",
    "primary_keyword": "GEO AI SEO agency",
    "key_points": [
        "Generative AI influences 15-30% of queries",
        "Entity-based optimisation is foundational",
        "Brands cited in AI answers see higher CTR",
    ],
    "trust_factors": [
        "Pioneer GEO/AI SEO agency since 2023",
        "Clients cited in ChatGPT and Gemini responses",
    ],
    "testimonials": [
        {
            "quote": "Our brand now appears in AI answers for 20 target queries.",
            "author": "VP Marketing",
        }
    ],
    "cta": "Audit Your AI Search Visibility",
}


class TestSupportedFormats:
    def test_returns_list(self) -> None:
        fmts = MultiFormatGenerator.supported_formats()
        assert isinstance(fmts, list)

    def test_contains_all_expected_formats(self) -> None:
        fmts = MultiFormatGenerator.supported_formats()
        expected = {"html", "markdown", "linkedin", "youtube", "reddit", "twitter", "email"}
        assert expected.issubset(set(fmts))


class TestGenerateSingle:
    def test_returns_format_output(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "linkedin")
        assert isinstance(output, FormatOutput)

    def test_output_format_name_is_correct(self) -> None:
        gen = MultiFormatGenerator()
        for fmt in MultiFormatGenerator.supported_formats():
            output = gen.generate_single(_SOURCE, fmt)
            assert output.format_name == fmt

    def test_content_is_non_empty_string(self) -> None:
        gen = MultiFormatGenerator()
        for fmt in MultiFormatGenerator.supported_formats():
            output = gen.generate_single(_SOURCE, fmt)
            assert isinstance(output.content, str)
            assert len(output.content) > 10

    def test_unknown_format_raises_value_error(self) -> None:
        gen = MultiFormatGenerator()
        with pytest.raises(ValueError, match="Unsupported format"):
            gen.generate_single(_SOURCE, "fax_machine")

    def test_platform_notes_is_string(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "linkedin")
        assert isinstance(output.platform_notes, str)


class TestGenerateAll:
    def test_returns_multi_format_bundle(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE)
        assert isinstance(bundle, MultiFormatBundle)

    def test_bundle_has_all_formats_by_default(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE)
        expected = set(MultiFormatGenerator.supported_formats())
        assert expected == set(bundle.format_names())

    def test_bundle_with_subset_of_formats(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE, formats=["linkedin", "twitter"])
        assert set(bundle.format_names()) == {"linkedin", "twitter"}

    def test_source_topic_is_set_in_bundle(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE)
        assert bundle.source_topic == _SOURCE["topic"]

    def test_source_keyword_is_set_in_bundle(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE)
        assert bundle.source_keyword == _SOURCE["primary_keyword"]

    def test_unknown_format_in_subset_raises_value_error(self) -> None:
        gen = MultiFormatGenerator()
        with pytest.raises(ValueError, match="Unsupported format"):
            gen.generate_all(_SOURCE, formats=["linkedin", "carrier_pigeon"])

    def test_bundle_get_returns_correct_output(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE, formats=["email"])
        output = bundle.get("email")
        assert output is not None
        assert output.format_name == "email"

    def test_bundle_get_returns_none_for_missing_format(self) -> None:
        gen = MultiFormatGenerator()
        bundle = gen.generate_all(_SOURCE, formats=["email"])
        assert bundle.get("html") is None


class TestSpecificFormats:
    def test_html_contains_h1(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "html")
        assert "<h1>" in output.content

    def test_markdown_starts_with_heading(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "markdown")
        assert output.content.startswith("#")

    def test_linkedin_contains_hashtags(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "linkedin")
        assert "#" in output.content

    def test_twitter_contains_numbered_tweets(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "twitter")
        # Should contain thread-style numbering like "1/" or "1."
        assert "1/" in output.content or "1." in output.content

    def test_youtube_contains_section_headers(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "youtube")
        assert "HOOK" in output.content.upper() or "##" in output.content

    def test_reddit_contains_subreddit(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "reddit")
        assert "r/" in output.content

    def test_email_contains_subject_line(self) -> None:
        gen = MultiFormatGenerator()
        output = gen.generate_single(_SOURCE, "email")
        assert "SUBJECT" in output.content.upper()

    def test_minimal_source_does_not_crash(self) -> None:
        gen = MultiFormatGenerator()
        minimal = {"topic": "SEO Services", "primary_keyword": "SEO"}
        for fmt in MultiFormatGenerator.supported_formats():
            output = gen.generate_single(minimal, fmt)
            assert isinstance(output.content, str)
