"""Tests for HTML5PageBuilder."""
from __future__ import annotations

import json

import pytest

from src.html5_page_builder import HTML5PageBuilder


@pytest.fixture
def builder() -> HTML5PageBuilder:
    return HTML5PageBuilder()


@pytest.fixture
def base_config() -> dict:
    return {
        "layout": "hero_features",
        "business_name": "Acme SEO Agency",
        "service": "Local SEO Services",
        "primary_keyword": "local seo agency london",
        "target_audience": "Small businesses in London",
        "tone": "Professional",
        "color_scheme": "corporate_blue",
        "cta_text": "Get a Free Audit",
        "cta_url": "https://example.com/contact",
        "canonical_url": "https://example.com/local-seo",
        "sections": ["hero", "features", "benefits", "social_proof", "faq", "cta"],
    }


# ---------------------------------------------------------------------------
# LAYOUTS registry
# ---------------------------------------------------------------------------


class TestLayoutsRegistry:
    def test_six_layouts_defined(self, builder: HTML5PageBuilder) -> None:
        assert len(builder.LAYOUTS) == 6

    def test_all_expected_layouts_present(self, builder: HTML5PageBuilder) -> None:
        expected = {
            "hero_features",
            "service_hub",
            "blog_article",
            "case_study",
            "lead_gen",
            "resource_guide",
        }
        assert expected == set(builder.LAYOUTS.keys())

    def test_each_layout_has_required_keys(self, builder: HTML5PageBuilder) -> None:
        for name, layout in builder.LAYOUTS.items():
            for key in ("label", "description", "icon", "best_for"):
                assert key in layout, f"Layout '{name}' missing key '{key}'"

    def test_best_for_is_non_empty_list(self, builder: HTML5PageBuilder) -> None:
        for name, layout in builder.LAYOUTS.items():
            assert isinstance(layout["best_for"], list), f"Layout '{name}' 'best_for' not a list"
            assert layout["best_for"], f"Layout '{name}' 'best_for' is empty"


# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------


class TestColourPalettes:
    def test_five_palettes_defined(self, builder: HTML5PageBuilder) -> None:
        assert len(builder._PALETTES) >= 5

    def test_each_palette_has_required_keys(self, builder: HTML5PageBuilder) -> None:
        required = {"primary", "primary_light", "accent", "bg", "bg_dark", "text", "text_muted", "white", "border", "success"}
        for name, palette in builder._PALETTES.items():
            missing = required - set(palette.keys())
            assert not missing, f"Palette '{name}' missing keys: {missing}"


# ---------------------------------------------------------------------------
# generate_page — error handling
# ---------------------------------------------------------------------------


class TestGeneratePageErrors:
    def test_missing_layout_defaults_to_hero_features(self, builder: HTML5PageBuilder) -> None:
        config = {"business_name": "Acme", "service": "SEO"}
        html = builder.generate_page(config)
        assert "<!DOCTYPE html>" in html

    def test_unknown_layout_raises_value_error(self, builder: HTML5PageBuilder) -> None:
        with pytest.raises(ValueError, match="Unknown layout"):
            builder.generate_page({"layout": "does_not_exist"})

    def test_unknown_color_scheme_falls_back_gracefully(self, builder: HTML5PageBuilder) -> None:
        config = {"layout": "hero_features", "color_scheme": "nonexistent_scheme"}
        html = builder.generate_page(config)
        assert "<!DOCTYPE html>" in html


# ---------------------------------------------------------------------------
# generate_page — all layouts produce valid HTML5 structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layout", [
    "hero_features",
    "service_hub",
    "blog_article",
    "case_study",
    "lead_gen",
    "resource_guide",
])
class TestAllLayoutsGenerate:
    def test_returns_string(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        result = builder.generate_page(config)
        assert isinstance(result, str)

    def test_has_doctype(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "<!DOCTYPE html>" in html

    def test_has_html_root(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert '<html lang="en">' in html

    def test_has_head_and_body(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "<head>" in html or "</head>" in html
        assert "<body>" in html

    def test_not_empty(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert len(html) > 5000

    def test_has_schema_markup(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "application/ld+json" in html

    def test_has_open_graph_tags(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "og:title" in html

    def test_has_canonical_link(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert 'rel="canonical"' in html

    def test_contains_business_name(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "Acme SEO Agency" in html

    def test_no_cdn_dependencies(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        """Generated pages must not depend on external CDNs."""
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "cdn.tailwindcss.com" not in html
        assert "cdnjs.cloudflare.com" not in html
        assert "jsdelivr.net" not in html

    def test_has_internal_link_placeholder(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "{{hub_url}}" in html

    def test_has_header_element(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "<header" in html

    def test_has_footer_element(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "<footer" in html

    def test_has_h1_tag(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "<h1" in html

    def test_cta_url_in_output(self, builder: HTML5PageBuilder, base_config: dict, layout: str) -> None:
        config = {**base_config, "layout": layout}
        html = builder.generate_page(config)
        assert "https://example.com/contact" in html


# ---------------------------------------------------------------------------
# Meta tags
# ---------------------------------------------------------------------------


class TestBuildMetaTags:
    def test_title_in_meta(self, builder: HTML5PageBuilder, base_config: dict) -> None:
        palette = builder._PALETTES["corporate_blue"]
        result = builder._build_meta_tags(base_config, palette)
        assert "Local SEO Services" in result

    def test_canonical_url_in_meta(self, builder: HTML5PageBuilder, base_config: dict) -> None:
        palette = builder._PALETTES["corporate_blue"]
        result = builder._build_meta_tags(base_config, palette)
        assert 'rel="canonical"' in result
        assert "https://example.com/local-seo" in result

    def test_twitter_card_present(self, builder: HTML5PageBuilder, base_config: dict) -> None:
        palette = builder._PALETTES["corporate_blue"]
        result = builder._build_meta_tags(base_config, palette)
        assert "twitter:card" in result

    def test_custom_meta_description_used(self, builder: HTML5PageBuilder) -> None:
        palette = builder._PALETTES["corporate_blue"]
        config = {
            "layout": "hero_features",
            "business_name": "Test Co",
            "service": "SEO",
            "meta_description": "My custom SEO description.",
        }
        result = builder._build_meta_tags(config, palette)
        assert "My custom SEO description." in result


# ---------------------------------------------------------------------------
# Schema markup
# ---------------------------------------------------------------------------


class TestBuildSchemaMarkup:
    def test_returns_script_tag(self, builder: HTML5PageBuilder, base_config: dict) -> None:
        result = builder._build_schema_markup(base_config)
        assert "<script" in result
        assert "application/ld+json" in result

    def test_schema_context_is_schema_org(self, builder: HTML5PageBuilder, base_config: dict) -> None:
        result = builder._build_schema_markup(base_config)
        raw_json = result.replace('<script type="application/ld+json">', "").replace("</script>", "").strip()
        data = json.loads(raw_json)
        assert data["@context"] == "https://schema.org"

    def test_service_layout_produces_service_schema(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "Local SEO",
            "primary_keyword": "local seo",
        }
        result = builder._build_schema_markup(config)
        data = json.loads(result.replace("<script type=\"application/ld+json\">", "").replace("</script>", "").strip())
        assert data["@type"] == "Service"

    def test_blog_layout_produces_article_schema(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "blog_article",
            "business_name": "Acme",
            "service": "Local SEO",
            "primary_keyword": "local seo",
        }
        result = builder._build_schema_markup(config)
        data = json.loads(result.replace("<script type=\"application/ld+json\">", "").replace("</script>", "").strip())
        assert data["@type"] == "Article"

    def test_case_study_layout_produces_article_schema(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "case_study",
            "business_name": "Acme",
            "service": "SEO",
            "primary_keyword": "seo",
        }
        result = builder._build_schema_markup(config)
        data = json.loads(result.replace("<script type=\"application/ld+json\">", "").replace("</script>", "").strip())
        assert data["@type"] == "Article"

    def test_valid_json_ld(self, builder: HTML5PageBuilder, base_config: dict) -> None:
        for layout in builder.LAYOUTS:
            config = {**base_config, "layout": layout}
            result = builder._build_schema_markup(config)
            raw_json = result.replace("<script type=\"application/ld+json\">", "").replace("</script>", "").strip()
            data = json.loads(raw_json)
            assert "@context" in data
            assert "@type" in data


# ---------------------------------------------------------------------------
# Section inclusion
# ---------------------------------------------------------------------------


class TestSectionInclusion:
    def test_hero_section_included_when_selected(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "SEO",
            "sections": ["hero"],
        }
        html = builder.generate_page(config)
        assert 'class="hero"' in html

    def test_faq_section_included_when_selected(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "SEO",
            "sections": ["faq"],
        }
        html = builder.generate_page(config)
        assert "faq" in html.lower()

    def test_empty_sections_list_produces_valid_document(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "SEO",
            "sections": [],
        }
        html = builder.generate_page(config)
        assert "<!DOCTYPE html>" in html

    def test_social_proof_section_includes_testimonials(self, builder: HTML5PageBuilder) -> None:
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "SEO",
            "sections": ["social_proof"],
        }
        html = builder.generate_page(config)
        assert "testimonial" in html.lower()


# ---------------------------------------------------------------------------
# Tone variations
# ---------------------------------------------------------------------------


class TestToneVariations:
    @pytest.mark.parametrize("tone", ["Professional", "Conversational", "Technical", "Authority"])
    def test_all_tones_produce_output(self, builder: HTML5PageBuilder, tone: str) -> None:
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "SEO",
            "tone": tone,
        }
        html = builder.generate_page(config)
        assert len(html) > 1000


# ---------------------------------------------------------------------------
# HTML special-character escaping
# ---------------------------------------------------------------------------


class TestHtmlEscaping:
    def test_xss_in_business_name_is_escaped(self, builder: HTML5PageBuilder) -> None:
        """Angle brackets in business_name must be HTML-escaped in output."""
        config = {
            "layout": "hero_features",
            "business_name": "<script>alert('xss')</script>",
            "service": "SEO",
        }
        html = builder.generate_page(config)
        # The raw unescaped <script> must not appear outside of JSON-LD
        # JSON-LD is protected by the </script> → <\/script> escaping
        assert "&lt;script&gt;" in html

    def test_xss_in_service_is_escaped(self, builder: HTML5PageBuilder) -> None:
        """Angle brackets in service name must be HTML-escaped in page sections."""
        config = {
            "layout": "hero_features",
            "business_name": "Acme",
            "service": "<b>Bold</b> & <i>Italic</i>",
            "sections": ["hero", "features"],
        }
        html = builder.generate_page(config)
        # Raw HTML injection must be escaped in section content
        assert "&lt;b&gt;" in html

    def test_script_close_tag_not_injectable_in_schema(self, builder: HTML5PageBuilder) -> None:
        """</script> must not appear unescaped in JSON-LD to prevent tag injection."""
        config = {
            "layout": "hero_features",
            "business_name": "Test</script><script>alert(1)//",
            "service": "SEO",
        }
        schema = builder._build_schema_markup(config)
        # The literal </script> sequence must be escaped as <\/script>
        assert "</script>" not in schema.replace('<script type="application/ld+json">', "").replace("</script>", "", 1)
