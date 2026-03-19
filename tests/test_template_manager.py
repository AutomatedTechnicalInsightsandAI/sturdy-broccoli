"""Tests for TemplateManager."""
from __future__ import annotations

import pytest

from src.template_manager import TemplateManager


class TestTemplateManagerInit:
    def test_creates_instance(self) -> None:
        tm = TemplateManager()
        assert tm is not None

    def test_list_service_types_returns_sorted_list(self) -> None:
        tm = TemplateManager()
        types = tm.list_service_types()
        assert isinstance(types, list)
        assert types == sorted(types)

    def test_list_service_types_includes_all_expected(self) -> None:
        tm = TemplateManager()
        types = tm.list_service_types()
        expected = {
            "local_seo",
            "capital_raise_advisory",
            "investor_marketing_agency",
            "digital_pr",
            "linkedin_marketing",
            "ecommerce_marketing",
            "geo_ai_seo",
        }
        assert expected.issubset(set(types))


class TestGetTemplate:
    def test_get_known_template_returns_dict(self) -> None:
        tm = TemplateManager()
        tmpl = tm.get_template("local_seo")
        assert isinstance(tmpl, dict)

    def test_template_contains_required_keys(self) -> None:
        tm = TemplateManager()
        for service_type in tm.list_service_types():
            tmpl = tm.get_template(service_type)
            for key in ("h1", "h2_sections", "trust_factors", "testimonials",
                        "service_description", "cta", "related_services",
                        "primary_keyword", "secondary_keywords"):
                assert key in tmpl, f"Missing key '{key}' in template '{service_type}'"

    def test_unknown_service_type_raises_value_error(self) -> None:
        tm = TemplateManager()
        with pytest.raises(ValueError, match="Unknown service type"):
            tm.get_template("does_not_exist")

    def test_returns_copy_not_reference(self) -> None:
        tm = TemplateManager()
        tmpl1 = tm.get_template("local_seo")
        tmpl2 = tm.get_template("local_seo")
        tmpl1["h1"] = "MUTATED"
        assert tmpl2["h1"] != "MUTATED"


class TestRenderPageData:
    def test_returns_dict_with_required_prompt_builder_fields(self) -> None:
        from src.prompt_builder import PromptBuilder
        tm = TemplateManager()
        for service_type in tm.list_service_types():
            page_data = tm.render_page_data(service_type)
            required = PromptBuilder._REQUIRED_PAGE_FIELDS
            missing = required - set(page_data.keys())
            assert not missing, (
                f"render_page_data('{service_type}') missing fields: {missing}"
            )

    def test_overrides_are_applied(self) -> None:
        tm = TemplateManager()
        page_data = tm.render_page_data(
            "local_seo", overrides={"primary_keyword": "local SEO London"}
        )
        assert page_data["primary_keyword"] == "local SEO London"

    def test_page_type_is_landing_page(self) -> None:
        tm = TemplateManager()
        for service_type in tm.list_service_types():
            page_data = tm.render_page_data(service_type)
            assert page_data["page_type"] == "landing_page"

    def test_template_metadata_included_in_page_data(self) -> None:
        tm = TemplateManager()
        page_data = tm.render_page_data("local_seo")
        assert "h1" in page_data
        assert "trust_factors" in page_data
        assert "testimonials" in page_data
        assert "related_services" in page_data


class TestRenderHtmlStructure:
    def test_returns_non_empty_string(self) -> None:
        tm = TemplateManager()
        html = tm.render_html_structure("digital_pr")
        assert isinstance(html, str)
        assert len(html) > 100

    def test_contains_h1_tag(self) -> None:
        tm = TemplateManager()
        html = tm.render_html_structure("digital_pr")
        assert "<h1>" in html

    def test_contains_h2_tags(self) -> None:
        tm = TemplateManager()
        html = tm.render_html_structure("digital_pr")
        assert "<h2>" in html

    def test_contains_trust_factors_section(self) -> None:
        tm = TemplateManager()
        html = tm.render_html_structure("local_seo")
        assert "trust" in html.lower()

    def test_contains_testimonials_section(self) -> None:
        tm = TemplateManager()
        html = tm.render_html_structure("local_seo")
        assert "<blockquote>" in html

    def test_contains_cta(self) -> None:
        tm = TemplateManager()
        html = tm.render_html_structure("linkedin_marketing")
        assert "cta" in html.lower()
