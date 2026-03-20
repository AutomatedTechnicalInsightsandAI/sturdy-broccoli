"""
template_manager.py

Manages landing page templates for enterprise SEO services.  Each template
defines the full page structure: H1/H2 hierarchy, trust factors, testimonials,
service description, CTAs, and related service links.

Supported service types
-----------------------
- local_seo
- capital_raise_advisory
- investor_marketing_agency
- digital_pr
- linkedin_marketing
- ecommerce_marketing
- geo_ai_seo
"""
from __future__ import annotations

from typing import Any

from src.premium_page_builder import PremiumPageBuilder


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, dict[str, Any]] = {
    "local_seo": {
        "service_name": "Local SEO",
        "h1": "Local SEO Services That Put Your Business on the Map",
        "h2_sections": [
            "Why Local Search Visibility Drives Revenue",
            "Our Local SEO Process",
            "Google Business Profile Optimisation",
            "Citation Building & NAP Consistency",
            "Local Link Acquisition",
            "Measuring Local SEO Success",
        ],
        "trust_factors": [
            "Google Partner certified",
            "Ranked #1 local SEO agency by Clutch (2024)",
            "500+ local businesses ranked in map pack",
            "Average 3× increase in Google Maps calls within 90 days",
        ],
        "testimonials": [
            {
                "quote": "Within 60 days we were in the top 3 of the local pack for every core service term.",
                "author": "Sarah M., Owner — Bright Smiles Dental",
            },
            {
                "quote": "Our phone calls from Google doubled in the first quarter after the campaign launched.",
                "author": "James T., MD — Pacific Plumbing",
            },
        ],
        "service_description": (
            "Local SEO bridges the gap between online search and offline revenue. "
            "We combine Google Business Profile optimisation, hyper-local content, "
            "citation audits, and targeted link acquisition to place your brand at "
            "the top of map-pack and organic results in your target geography."
        ),
        "cta": {
            "primary": "Get Your Free Local SEO Audit",
            "secondary": "View Local SEO Case Studies",
        },
        "related_services": [
            "Digital PR",
            "GEO/AI SEO",
            "E-commerce Marketing",
        ],
        "primary_keyword": "local SEO services",
        "secondary_keywords": [
            "local search optimisation",
            "Google Business Profile management",
            "map pack ranking",
            "local citation building",
        ],
    },
    "capital_raise_advisory": {
        "service_name": "Capital Raise Advisory",
        "h1": "Capital Raise Advisory: Strategic Investor Outreach That Closes Rounds",
        "h2_sections": [
            "Why Content-Driven Capital Raises Outperform Cold Outreach",
            "Our Capital Raise Content Strategy",
            "Investor Deck Narrative Development",
            "Thought Leadership Content for Credibility",
            "Digital Distribution to Qualified Investors",
            "Tracking and Reporting Investor Engagement",
        ],
        "trust_factors": [
            "$2B+ in capital raises supported",
            "Portfolio includes 40+ funded startups",
            "Average 6× increase in investor enquiries after campaign launch",
            "Relationships with 500+ family offices and VC funds",
        ],
        "testimonials": [
            {
                "quote": "Our Series A oversubscribed by 30% — the content strategy built inbound momentum we had never experienced before.",
                "author": "Daniel R., CEO — FinTech Ventures",
            },
            {
                "quote": "The thought leadership articles established credibility before we even spoke to lead investors.",
                "author": "Priya K., CFO — GreenBridge Capital",
            },
        ],
        "service_description": (
            "Sophisticated investors are inundated with decks. Our capital raise "
            "advisory service positions your company through strategic content — "
            "founder thought leadership, industry data narratives, and targeted "
            "distribution — so investors arrive pre-sold on your thesis."
        ),
        "cta": {
            "primary": "Book a Capital Raise Strategy Session",
            "secondary": "Download Our Investor Marketing Playbook",
        },
        "related_services": [
            "Investor Marketing Agency",
            "Digital PR",
            "LinkedIn Marketing",
        ],
        "primary_keyword": "capital raise advisory",
        "secondary_keywords": [
            "investor content marketing",
            "startup fundraising strategy",
            "VC outreach content",
            "investor relations content",
        ],
    },
    "investor_marketing_agency": {
        "service_name": "Investor Marketing Agency",
        "h1": "Investor Marketing Agency: Content That Attracts the Right Capital",
        "h2_sections": [
            "The Investor Marketing Gap Most Startups Miss",
            "Our Investor Marketing Framework",
            "Building an Investor-Grade Content Engine",
            "Multi-Channel Investor Distribution",
            "Measuring Investor Engagement ROI",
            "Investor Marketing for Every Stage",
        ],
        "trust_factors": [
            "Specialised in Series A–C investor marketing",
            "Content served to 200K+ qualified investors monthly",
            "Featured in Bloomberg, TechCrunch, and Forbes",
            "Dedicated investor relations content team",
        ],
        "testimonials": [
            {
                "quote": "They understood the investor mindset in a way no generalist agency ever could.",
                "author": "Marcus L., Founder — EduTech Scale",
            },
        ],
        "service_description": (
            "Investor marketing is not traditional B2B marketing. It requires a "
            "distinct content voice, precise distribution channels, and measurable "
            "engagement signals. Our agency brings all three together to build "
            "sustainable inbound investor pipelines."
        ),
        "cta": {
            "primary": "Start Building Your Investor Pipeline",
            "secondary": "See Our Investor Marketing Results",
        },
        "related_services": [
            "Capital Raise Advisory",
            "Digital PR",
            "LinkedIn Marketing",
        ],
        "primary_keyword": "investor marketing agency",
        "secondary_keywords": [
            "startup investor marketing",
            "investor relations content",
            "fundraising content strategy",
            "investor outreach agency",
        ],
    },
    "digital_pr": {
        "service_name": "Digital PR",
        "h1": "Digital PR Services: Earned Media at Scale for SEO and Brand Authority",
        "h2_sections": [
            "Why Digital PR Beats Traditional Link Building",
            "Our Digital PR Process",
            "Data-Driven PR Campaigns That Earn Coverage",
            "Journalist Relationships and Media Placement",
            "Measuring Digital PR ROI: Links, Brand Mentions, and Traffic",
            "Digital PR for Your Industry",
        ],
        "trust_factors": [
            "10,000+ links earned in the last 12 months",
            "Coverage in BBC, Guardian, Forbes, and 200+ trade outlets",
            "Average DR 65+ for earned placements",
            "98% client retention rate",
        ],
        "testimonials": [
            {
                "quote": "A single campaign earned us 400 links and a 60-point domain rating increase.",
                "author": "Claire W., Head of SEO — RetailTech Co.",
            },
        ],
        "service_description": (
            "Digital PR combines the authority of earned media with the measurable "
            "impact of SEO link building. Our campaigns create newsworthy data stories, "
            "expert commentary, and reactive PR moments that generate coverage in "
            "top-tier publications and pass genuine authority to your domain."
        ),
        "cta": {
            "primary": "Get a Free Digital PR Campaign Concept",
            "secondary": "View Our Digital PR Case Studies",
        },
        "related_services": [
            "Local SEO",
            "GEO/AI SEO",
            "LinkedIn Marketing",
        ],
        "primary_keyword": "digital PR agency",
        "secondary_keywords": [
            "earned media SEO",
            "link building through PR",
            "media relations digital marketing",
            "data-driven PR campaigns",
        ],
    },
    "linkedin_marketing": {
        "service_name": "LinkedIn Marketing",
        "h1": "LinkedIn Marketing Agency: B2B Lead Generation Through Strategic Content",
        "h2_sections": [
            "Why LinkedIn Outperforms Other B2B Channels for Lead Quality",
            "Our LinkedIn Marketing Strategy",
            "Executive Thought Leadership on LinkedIn",
            "LinkedIn Content Calendar and Distribution",
            "LinkedIn Paid Amplification",
            "Measuring LinkedIn Marketing ROI",
        ],
        "trust_factors": [
            "Managed $10M+ in LinkedIn ad spend",
            "Average 4× improvement in LinkedIn engagement rate",
            "Clients include Fortune 500 and scale-up brands",
            "LinkedIn Marketing Solutions certified partners",
        ],
        "testimonials": [
            {
                "quote": "Our CEO's LinkedIn went from 2,000 followers to 28,000 in eight months — inbound leads tripled.",
                "author": "Rachel B., CMO — B2B SaaS Platform",
            },
        ],
        "service_description": (
            "LinkedIn is the highest-intent B2B platform on the planet. Our LinkedIn "
            "marketing service combines executive ghostwriting, strategic content "
            "calendars, targeted paid amplification, and conversion optimisation to "
            "turn your company and leadership presence into a consistent lead engine."
        ),
        "cta": {
            "primary": "Get Your LinkedIn Marketing Assessment",
            "secondary": "Download Our LinkedIn Content Playbook",
        },
        "related_services": [
            "Digital PR",
            "Investor Marketing Agency",
            "Capital Raise Advisory",
        ],
        "primary_keyword": "LinkedIn marketing agency",
        "secondary_keywords": [
            "LinkedIn lead generation",
            "B2B LinkedIn strategy",
            "executive LinkedIn ghostwriting",
            "LinkedIn content marketing",
        ],
    },
    "ecommerce_marketing": {
        "service_name": "E-commerce Marketing",
        "h1": "E-commerce Marketing Agency: Revenue-Focused SEO and Content Strategy",
        "h2_sections": [
            "The E-commerce Content Gap That Costs You Revenue",
            "Our E-commerce SEO Framework",
            "Category Page Optimisation at Scale",
            "Product Content That Converts and Ranks",
            "E-commerce Link Building and Digital PR",
            "Measuring E-commerce Marketing ROI",
        ],
        "trust_factors": [
            "£500M+ in client e-commerce revenue influenced",
            "Average 150% organic traffic increase within 12 months",
            "Shopify, WooCommerce, and Magento specialists",
            "Google Shopping and organic synergy approach",
        ],
        "testimonials": [
            {
                "quote": "Organic revenue grew 180% year-over-year. The category content strategy was the turning point.",
                "author": "Tom H., E-commerce Director — Home & Garden Retailer",
            },
        ],
        "service_description": (
            "E-commerce brands leave significant revenue on the table without a "
            "structured SEO and content strategy. We combine category architecture, "
            "product content optimisation, and data-led digital PR to drive "
            "sustainable organic traffic that converts at scale."
        ),
        "cta": {
            "primary": "Get Your Free E-commerce SEO Audit",
            "secondary": "See Our E-commerce Case Studies",
        },
        "related_services": [
            "Local SEO",
            "Digital PR",
            "GEO/AI SEO",
        ],
        "primary_keyword": "ecommerce marketing agency",
        "secondary_keywords": [
            "e-commerce SEO agency",
            "online store content strategy",
            "product page SEO",
            "category page optimisation",
        ],
    },
    "geo_ai_seo": {
        "service_name": "GEO/AI SEO",
        "h1": "GEO & AI SEO: Optimise for Generative Search and LLM Visibility",
        "h2_sections": [
            "How Generative AI Is Reshaping Search Visibility",
            "What GEO (Generative Engine Optimisation) Means for Your Brand",
            "Optimising Content for AI Overviews and LLM Answers",
            "Entity Building and Knowledge Graph Authority",
            "Monitoring AI Search Visibility",
            "GEO Strategy for Your Industry",
        ],
        "trust_factors": [
            "Pioneer GEO/AI SEO agency since 2023",
            "Clients cited in ChatGPT, Gemini, and Claude responses",
            "Entity-first optimisation methodology",
            "Transparent AI mention tracking dashboard",
        ],
        "testimonials": [
            {
                "quote": "Our brand now appears in AI-generated answers for our top 20 target queries. It's a new channel we didn't have before.",
                "author": "Lena C., VP Marketing — Enterprise SaaS",
            },
        ],
        "service_description": (
            "Generative AI tools like ChatGPT, Gemini, and Perplexity are becoming "
            "primary discovery channels. GEO/AI SEO ensures your brand, products, "
            "and expertise are cited and recommended in AI-generated responses — "
            "building a channel that sits above traditional search results."
        ),
        "cta": {
            "primary": "Audit Your AI Search Visibility",
            "secondary": "Read Our GEO Research Report",
        },
        "related_services": [
            "Digital PR",
            "Local SEO",
            "E-commerce Marketing",
        ],
        "primary_keyword": "GEO AI SEO agency",
        "secondary_keywords": [
            "generative engine optimisation",
            "AI SEO strategy",
            "LLM visibility optimisation",
            "AI Overview optimisation",
        ],
    },
}


class TemplateManager:
    """
    Provides access to service landing page templates and renders them into
    structured page data dictionaries compatible with ``PromptBuilder``.

    Usage::

        tm = TemplateManager()
        template = tm.get_template("local_seo")
        page_data = tm.render_page_data(
            service_type="local_seo",
            overrides={"primary_keyword": "local SEO London"},
        )
    """

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def list_service_types(self) -> list[str]:
        """Return a sorted list of all available service type keys."""
        return sorted(_TEMPLATES.keys())

    def get_template(self, service_type: str) -> dict[str, Any]:
        """
        Return the raw template dictionary for *service_type*.

        Raises
        ------
        ValueError
            If *service_type* is not recognised.
        """
        if service_type not in _TEMPLATES:
            raise ValueError(
                f"Unknown service type '{service_type}'. "
                f"Available types: {self.list_service_types()}"
            )
        return dict(_TEMPLATES[service_type])

    def render_page_data(
        self,
        service_type: str,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Render a ``PromptBuilder``-compatible page data dictionary from a
        service template, optionally merging caller-supplied *overrides*.

        The returned dictionary contains the standard ``PromptBuilder``
        required fields pre-populated from the template plus all template
        metadata (trust factors, testimonials, CTAs, related services).

        Parameters
        ----------
        service_type:
            Key identifying the service template (e.g. ``'local_seo'``).
        overrides:
            Optional mapping of field names to replacement values.  Any key
            from the returned dict can be overridden.

        Returns
        -------
        dict[str, Any]
        """
        tmpl = self.get_template(service_type)

        page_data: dict[str, Any] = {
            # PromptBuilder required fields
            "topic": f"{tmpl['service_name']} Services",
            "target_audience": "business owners and marketing decision-makers",
            "search_intent_type": "commercial",
            "primary_keyword": tmpl["primary_keyword"],
            "secondary_keywords": ", ".join(tmpl["secondary_keywords"]),
            "niche": "digital marketing agency",
            "niche_terminology": (
                "SERP, domain rating, organic traffic, conversion rate, "
                "click-through rate, impressions, search intent"
            ),
            "unique_perspective": tmpl["service_description"],
            "data_point": tmpl["trust_factors"][0] if tmpl["trust_factors"] else "",
            "named_tool": "Google Search Console",
            "failure_mode": "Relying on a single channel without a content-first strategy",
            "depth_level": "intermediate",
            "experience_signal": (
                f"Demonstrated through {tmpl['trust_factors'][0].lower()}"
                if tmpl["trust_factors"]
                else ""
            ),
            "primary_technical_term": tmpl["primary_keyword"].split()[0].upper(),
            "authority_source": "Google Search Central documentation",
            "page_type": "landing_page",
            # Template-specific metadata
            "h1": tmpl["h1"],
            "h2_sections": tmpl["h2_sections"],
            "trust_factors": tmpl["trust_factors"],
            "testimonials": tmpl["testimonials"],
            "service_description": tmpl["service_description"],
            "cta_primary": tmpl["cta"]["primary"],
            "cta_secondary": tmpl["cta"]["secondary"],
            "related_services": tmpl["related_services"],
        }

        if overrides:
            page_data.update(overrides)

        return page_data

    def render_html_structure(self, service_type: str) -> str:
        """
        Return an HTML skeleton string for the given service landing page.

        The skeleton uses semantic HTML5 elements and includes placeholder
        comments for dynamic content insertion.

        Parameters
        ----------
        service_type:
            Key identifying the service template.

        Returns
        -------
        str
            HTML string (not a full document — intended as a content block).
        """
        tmpl = self.get_template(service_type)
        lines: list[str] = []

        lines.append(f'<h1>{tmpl["h1"]}</h1>')
        lines.append("")
        lines.append("<section class=\"service-description\">")
        lines.append(f'  <p>{tmpl["service_description"]}</p>')
        lines.append("</section>")
        lines.append("")
        lines.append("<section class=\"trust-factors\">")
        lines.append("  <h2>Why Choose Us</h2>")
        lines.append("  <ul>")
        for factor in tmpl["trust_factors"]:
            lines.append(f"    <li>{factor}</li>")
        lines.append("  </ul>")
        lines.append("</section>")
        lines.append("")

        for h2 in tmpl["h2_sections"]:
            lines.append(f"<section>")
            lines.append(f"  <h2>{h2}</h2>")
            lines.append("  <!-- Content block -->")
            lines.append("</section>")
            lines.append("")

        lines.append("<section class=\"testimonials\">")
        lines.append("  <h2>Client Testimonials</h2>")
        for t in tmpl["testimonials"]:
            lines.append("  <blockquote>")
            lines.append(f'    <p>"{t["quote"]}"</p>')
            lines.append(f'    <cite>— {t["author"]}</cite>')
            lines.append("  </blockquote>")
        lines.append("</section>")
        lines.append("")
        lines.append("<section class=\"cta\">")
        lines.append(f'  <a href="#contact" class="btn-primary">{tmpl["cta"]["primary"]}</a>')
        lines.append(f'  <a href="#case-studies" class="btn-secondary">{tmpl["cta"]["secondary"]}</a>')
        lines.append("</section>")
        lines.append("")
        lines.append("<section class=\"related-services\">")
        lines.append("  <h2>Related Services</h2>")
        lines.append("  <ul>")
        for svc in tmpl["related_services"]:
            lines.append(f"    <li>{svc}</li>")
        lines.append("  </ul>")
        lines.append("</section>")

        return "\n".join(lines)

    def render_premium_page(self, service_type: str) -> str:
        """
        Render a complete, production-quality HTML5 page for the given
        service type using :class:`PremiumPageBuilder`.

        The template data for *service_type* is mapped to a
        ``PremiumPageBuilder``-compatible config dict and passed to
        :meth:`PremiumPageBuilder.build`.

        Parameters
        ----------
        service_type:
            Key identifying the service template (e.g. ``'digital_pr'``).

        Returns
        -------
        str
            A fully self-contained HTML5 document string.
        """
        tmpl = self.get_template(service_type)

        testimonials_items = []
        for t in tmpl["testimonials"]:
            raw = t["author"]
            # Expected format: "Name, Role — Company" or "Name — Company" or just "Name"
            if "—" in raw:
                before_dash, company = raw.split("—", 1)
                company = company.strip()
            else:
                before_dash = raw
                company = ""
            if "," in before_dash:
                author_name, role = before_dash.split(",", 1)
                author_name = author_name.strip()
                role = role.strip()
            else:
                author_name = before_dash.strip()
                role = ""
            testimonials_items.append({
                "quote": t["quote"],
                "author": author_name,
                "role": role,
                "company": company,
            })

        config: dict[str, Any] = {
            "brand": {
                "name": tmpl["service_name"],
                "tagline": tmpl["service_description"][:80] + "…",
                "primary": "#1e3a5f",
                "accent": "#3b82f6",
                "dark": "#0f172a",
                "light": "#f8fafc",
            },
            "meta": {
                "title": tmpl["h1"],
                "description": tmpl["service_description"],
            },
            "nav_links": [
                {"text": "Services", "url": "#services"},
                {"text": "Results",  "url": "#stats"},
                {"text": "Pricing",  "url": "#pricing"},
            ],
            "hero": {
                "badge": tmpl["trust_factors"][0] if tmpl["trust_factors"] else "",
                "heading": tmpl["h1"],
                "subheading": tmpl["service_description"],
                "video_url": "",
                "poster_url": "",
            },
            "cta": {
                "primary_text": tmpl["cta"]["primary"],
                "secondary_text": tmpl["cta"]["secondary"],
                "url": "#contact",
                "banner_heading": f"Ready to grow with {tmpl['service_name']}?",
                "banner_subheading": tmpl["service_description"],
            },
            "stats": [
                {"value": tf, "label": ""}
                for tf in tmpl["trust_factors"][:4]
            ],
            "problem": {
                "heading": "Common Challenges",
                "points": [
                    f"Struggling with {tmpl['primary_keyword']}",
                    "Low visibility in search results",
                    "Missing out on high-intent traffic",
                    "No clear ROI from current strategy",
                ],
            },
            "solution": {
                "heading": "Our Approach",
                "points": tmpl["secondary_keywords"][:4],
            },
            "services": {
                "heading": f"{tmpl['service_name']} Services",
                "subheading": tmpl["service_description"],
                "items": [
                    {"icon": "✅", "title": h2, "description": ""}
                    for h2 in tmpl["h2_sections"][:6]
                ],
            },
            "testimonials": {
                "heading": "What Our Clients Say",
                "items": testimonials_items,
            },
            "pricing": {
                "heading": "Pricing",
                "subheading": "Transparent, performance-focused pricing.",
                "tiers": [
                    {
                        "name": "Starter",
                        "price": "Contact Us",
                        "period": "",
                        "description": tmpl["cta"]["primary"],
                        "features": tmpl["trust_factors"],
                        "cta_text": tmpl["cta"]["primary"],
                        "cta_url": "#contact",
                        "featured": False,
                    },
                ],
            },
            "footer": {
                "columns": [
                    {
                        "heading": "Related Services",
                        "links": [
                            {"text": svc, "url": "#services"}
                            for svc in tmpl["related_services"]
                        ],
                    }
                ],
                "social": [],
                "copyright": f"© 2026 {tmpl['service_name']}. All rights reserved.",
            },
        }

        return PremiumPageBuilder().build(config)
