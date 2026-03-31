"""
html5_page_builder.py

Generates production-ready HTML5 enterprise webpages for the Sturdy Broccoli
SEO Content Factory.  Six distinct layout templates are supported, each
optimised for a different content marketing use-case.

Supported layouts
-----------------
- ``hero_features``   — Big hero section, 3-column features grid, CTA
- ``service_hub``     — Comprehensive service landing page with trust signals
- ``blog_article``    — Long-form article with sidebar table-of-contents
- ``case_study``      — Results-focused layout with metrics / stats bar
- ``lead_gen``        — Conversion-optimised with form integration points
- ``resource_guide``  — Table of contents, downloadable content focus

All generated pages include:
- Proper ``<head>`` with meta tags, OG tags, schema.org JSON-LD (no CDN)
- Responsive CSS using CSS Grid / Flexbox and CSS custom properties
- Smooth CSS-only animations
- Schema.org structured data (LocalBusiness, Service, Article)
- Open Graph and Twitter Card meta tags
- Canonical URL tags
- Proper heading hierarchy (H1 → H2 → H3)
- Internal link placeholders using ``{{hub_url}}`` / ``{{spoke_url}}`` tokens

Usage::

    from src.html5_page_builder import HTML5PageBuilder

    builder = HTML5PageBuilder()
    html = builder.generate_page({
        "layout": "hero_features",
        "business_name": "Acme SEO Agency",
        "service": "Local SEO Services",
        "primary_keyword": "local seo agency london",
        "target_audience": "Small business owners in London",
        "tone": "Professional",
        "color_scheme": "corporate_blue",
        "cta_text": "Get a Free Audit",
        "cta_url": "https://example.com/contact",
        "sections": ["hero", "features", "benefits", "social_proof", "faq", "cta"],
        "canonical_url": "https://example.com/local-seo",
    })
"""
from __future__ import annotations

import html as _html
import json
from typing import Any


class HTML5PageBuilder:
    """Generates production-ready HTML5 enterprise webpages.

    Each of the six layout templates produces a fully self-contained HTML5
    document with embedded CSS (no CDN dependencies) and schema.org markup.
    """

    # -----------------------------------------------------------------------
    # Layout registry
    # -----------------------------------------------------------------------

    LAYOUTS: dict[str, dict[str, Any]] = {
        "hero_features": {
            "label": "Hero + Features Grid",
            "description": "Big hero section, 3-column features, CTA",
            "icon": "🚀",
            "best_for": ["service pages", "SaaS landing pages", "agency home pages"],
        },
        "service_hub": {
            "label": "Service Hub Page",
            "description": "Comprehensive service landing page with trust signals",
            "icon": "🏢",
            "best_for": ["service detail pages", "local business", "B2B services"],
        },
        "blog_article": {
            "label": "Blog / Spoke Article",
            "description": "Long-form content with sidebar table of contents",
            "icon": "📝",
            "best_for": ["blog posts", "educational content", "spoke pages"],
        },
        "case_study": {
            "label": "Case Study",
            "description": "Results-focused layout with metrics / stats bar",
            "icon": "📊",
            "best_for": ["case studies", "project showcases", "success stories"],
        },
        "lead_gen": {
            "label": "Lead Generation",
            "description": "Conversion-optimised with form integration points",
            "icon": "🎯",
            "best_for": ["lead capture", "free trial sign-ups", "consultation booking"],
        },
        "resource_guide": {
            "label": "Resource / Guide",
            "description": "Table of contents, downloadable content focus",
            "icon": "📚",
            "best_for": ["ultimate guides", "whitepapers", "downloadable resources"],
        },
    }

    # -----------------------------------------------------------------------
    # Colour palettes
    # -----------------------------------------------------------------------

    _PALETTES: dict[str, dict[str, str]] = {
        "corporate_blue": {
            "primary": "#1a3c6e",
            "primary_light": "#2563eb",
            "accent": "#f59e0b",
            "bg": "#f8fafc",
            "bg_dark": "#1e293b",
            "text": "#1e293b",
            "text_muted": "#64748b",
            "white": "#ffffff",
            "border": "#e2e8f0",
            "success": "#059669",
        },
        "agency_dark": {
            "primary": "#0f172a",
            "primary_light": "#334155",
            "accent": "#7c3aed",
            "bg": "#f1f5f9",
            "bg_dark": "#0f172a",
            "text": "#0f172a",
            "text_muted": "#94a3b8",
            "white": "#ffffff",
            "border": "#cbd5e1",
            "success": "#10b981",
        },
        "modern_green": {
            "primary": "#065f46",
            "primary_light": "#059669",
            "accent": "#f59e0b",
            "bg": "#f0fdf4",
            "bg_dark": "#064e3b",
            "text": "#064e3b",
            "text_muted": "#6b7280",
            "white": "#ffffff",
            "border": "#d1fae5",
            "success": "#059669",
        },
        "bold_red": {
            "primary": "#7f1d1d",
            "primary_light": "#dc2626",
            "accent": "#1d4ed8",
            "bg": "#fff5f5",
            "bg_dark": "#450a0a",
            "text": "#1c1917",
            "text_muted": "#78716c",
            "white": "#ffffff",
            "border": "#fecaca",
            "success": "#16a34a",
        },
        "midnight_purple": {
            "primary": "#2e1065",
            "primary_light": "#7c3aed",
            "accent": "#06b6d4",
            "bg": "#faf5ff",
            "bg_dark": "#1e1b4b",
            "text": "#1e1b4b",
            "text_muted": "#7c3aed",
            "white": "#ffffff",
            "border": "#e9d5ff",
            "success": "#22c55e",
        },
    }

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def generate_page(self, config: dict[str, Any]) -> str:
        """Generate a complete HTML5 page from *config*.

        Parameters
        ----------
        config:
            Dictionary containing page configuration.  Required keys:
            ``layout``, ``business_name``, ``service``, ``primary_keyword``.

        Returns
        -------
        str
            A fully self-contained HTML5 document string.

        Raises
        ------
        ValueError
            If ``layout`` is missing or unknown.
        """
        layout = config.get("layout", "hero_features")
        if layout not in self.LAYOUTS:
            raise ValueError(
                f"Unknown layout '{layout}'. "
                f"Valid options: {list(self.LAYOUTS)}"
            )

        _dispatch = {
            "hero_features": self._build_hero_features_layout,
            "service_hub": self._build_service_hub_layout,
            "blog_article": self._build_blog_article_layout,
            "case_study": self._build_case_study_layout,
            "lead_gen": self._build_lead_gen_layout,
            "resource_guide": self._build_resource_guide_layout,
        }

        palette = self._PALETTES.get(
            config.get("color_scheme", "corporate_blue"),
            self._PALETTES["corporate_blue"],
        )

        head = self._build_meta_tags(config, palette)
        body = _dispatch[layout](config, palette)
        schema = self._build_schema_markup(config)

        scripts = self._build_page_scripts()

        return "\n".join([
            "<!DOCTYPE html>",
            '<html lang="en">',
            head,
            "<body>",
            body,
            schema,
            scripts,
            "</body>",
            "</html>",
        ])

    # -----------------------------------------------------------------------
    # Layout builders
    # -----------------------------------------------------------------------

    def _build_hero_features_layout(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "Professional Services"))
        keyword = _esc(config.get("primary_keyword", ""))
        audience = _esc(config.get("target_audience", "businesses"))
        cta_text = _esc(config.get("cta_text", "Get Started Today"))
        cta_url = _esc(config.get("cta_url", "#contact"))
        hub_url = config.get("hub_url", "{{hub_url}}")
        tone = config.get("tone", "Professional")

        tagline = _tone_tagline(service, audience, tone)
        subtitle = (
            f"Helping {audience} achieve measurable results with "
            f"enterprise-grade {service.lower()}. Trusted by leading brands."
        )

        features = _default_features(service, keyword)
        benefits = _default_benefits(service, tone)

        sections = config.get("sections", ["hero", "features", "benefits", "cta"])
        parts: list[str] = [_base_css(palette), _nav_html(business, palette)]

        if "hero" in sections:
            parts.append(f"""
<section class="hero" aria-labelledby="hero-heading">
  <div class="container">
    <div class="hero-content">
      <p class="eyebrow">{service}</p>
      <h1 id="hero-heading">{tagline}</h1>
      <p class="hero-subtitle">{subtitle}</p>
      <div class="cta-group">
        <a href="{cta_url}" class="btn btn-primary">{cta_text}</a>
        <a href="{hub_url}" class="btn btn-secondary">Learn More</a>
      </div>
      <p class="trust-note">⭐ Trusted by 500+ businesses · No lock-in contracts</p>
    </div>
  </div>
</section>
""")

        if "features" in sections:
            feature_cards = "".join(
                f"""<div class="feature-card">
  <div class="feature-icon">{f["icon"]}</div>
  <h3>{_esc(f["title"])}</h3>
  <p>{_esc(f["description"])}</p>
</div>"""
                for f in features
            )
            parts.append(f"""
<section class="features section-pad" aria-labelledby="features-heading">
  <div class="container">
    <div class="section-header">
      <h2 id="features-heading">Why Choose Our {service}</h2>
      <p>Everything you need to dominate your market with <strong>{keyword}</strong>.</p>
    </div>
    <div class="features-grid">{feature_cards}</div>
  </div>
</section>
""")

        if "benefits" in sections:
            benefit_items = "".join(
                f"<li>✅ {_esc(b)}</li>" for b in benefits
            )
            parts.append(f"""
<section class="benefits section-pad bg-light" aria-labelledby="benefits-heading">
  <div class="container two-col">
    <div>
      <h2 id="benefits-heading">Results You Can Expect</h2>
      <p>Our {service.lower()} delivers measurable ROI for {audience.lower()}.</p>
      <ul class="benefit-list">{benefit_items}</ul>
    </div>
    <div class="stats-box">
      <div class="stat"><span class="stat-number">300%</span><span class="stat-label">Average ROI</span></div>
      <div class="stat"><span class="stat-number">90</span><span class="stat-label">Days to Results</span></div>
      <div class="stat"><span class="stat-number">500+</span><span class="stat-label">Clients Served</span></div>
      <div class="stat"><span class="stat-number">98%</span><span class="stat-label">Retention Rate</span></div>
    </div>
  </div>
</section>
""")

        if "social_proof" in sections:
            parts.append(_testimonials_section(service, palette))

        if "faq" in sections:
            parts.append(_faq_section(service, keyword))

        if "cta" in sections:
            parts.append(f"""
<section class="cta-section" aria-labelledby="cta-heading">
  <div class="container text-center">
    <h2 id="cta-heading">Ready to Transform Your {service}?</h2>
    <p>Join hundreds of businesses already growing with {business}.</p>
    <a href="{cta_url}" class="btn btn-primary btn-large">{cta_text}</a>
  </div>
</section>
""")

        parts.append(_footer_html(business, palette))
        return "\n".join(parts)

    def _build_service_hub_layout(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "Professional Services"))
        keyword = _esc(config.get("primary_keyword", ""))
        audience = _esc(config.get("target_audience", "businesses"))
        cta_text = _esc(config.get("cta_text", "Get a Free Consultation"))
        cta_url = _esc(config.get("cta_url", "#contact"))
        hub_url = config.get("hub_url", "{{hub_url}}")
        tone = config.get("tone", "Professional")

        sections = config.get("sections", ["hero", "features", "benefits", "social_proof", "faq", "cta"])
        features = _default_features(service, keyword)
        benefits = _default_benefits(service, tone)

        spoke_links = ""
        for spoke in config.get("spoke_pages", []):
            spoke_url = spoke.get("url", "{{spoke_url}}")
            spoke_title = _esc(spoke.get("title", "Related Topic"))
            spoke_links += f'<li><a href="{spoke_url}">{spoke_title} →</a></li>\n'
        if not spoke_links:
            spoke_links = (
                "<li><a href='{{spoke_url_1}}'>Related Guide: Getting Started →</a></li>\n"
                "<li><a href='{{spoke_url_2}}'>Advanced Strategies for Results →</a></li>\n"
                "<li><a href='{{spoke_url_3}}'>Industry-Specific Tips →</a></li>\n"
            )

        parts: list[str] = [_base_css(palette), _nav_html(business, palette)]

        # Page header with breadcrumb
        parts.append(f"""
<div class="page-header">
  <div class="container">
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li><a href="{hub_url}">Home</a></li>
        <li aria-current="page">{service}</li>
      </ol>
    </nav>
    <h1>{service} for {audience}</h1>
    <p class="page-header-sub">
      Comprehensive {keyword.lower()} solutions tailored to {audience.lower()}.
      Proven strategies, measurable results.
    </p>
  </div>
</div>
""")

        if "features" in sections:
            feature_cards = "".join(
                f"""<div class="feature-card">
  <div class="feature-icon">{f["icon"]}</div>
  <h3>{_esc(f["title"])}</h3>
  <p>{_esc(f["description"])}</p>
</div>"""
                for f in features
            )
            parts.append(f"""
<section class="features section-pad" aria-labelledby="services-heading">
  <div class="container">
    <div class="section-header">
      <h2 id="services-heading">Our {service} Services</h2>
      <p>End-to-end solutions for <strong>{keyword}</strong>.</p>
    </div>
    <div class="features-grid">{feature_cards}</div>
  </div>
</section>
""")

        if "benefits" in sections:
            benefit_items = "".join(f"<li>✅ {_esc(b)}</li>" for b in benefits)
            parts.append(f"""
<section class="benefits section-pad bg-light">
  <div class="container">
    <h2>Why Businesses Choose {business}</h2>
    <div class="two-col">
      <ul class="benefit-list">{benefit_items}</ul>
      <div class="trust-signals">
        <h3>Trust Signals</h3>
        <p>🏆 Award-winning agency</p>
        <p>📋 Transparent reporting</p>
        <p>🔒 Data-secure processes</p>
        <p>📞 Dedicated account manager</p>
      </div>
    </div>
  </div>
</section>
""")

        # Related spokes (hub-and-spoke internal linking)
        parts.append(f"""
<section class="spoke-links section-pad">
  <div class="container">
    <h2>Explore Related Resources</h2>
    <p>Deepen your knowledge with our complete guide library:</p>
    <ul class="spoke-nav">{spoke_links}</ul>
  </div>
</section>
""")

        if "social_proof" in sections:
            parts.append(_testimonials_section(service, palette))

        if "faq" in sections:
            parts.append(_faq_section(service, keyword))

        if "cta" in sections:
            parts.append(f"""
<section class="cta-section">
  <div class="container text-center">
    <h2>Start Your {service} Journey Today</h2>
    <p>Get a free audit and discover untapped growth opportunities.</p>
    <a href="{cta_url}" class="btn btn-primary btn-large">{cta_text}</a>
  </div>
</section>
""")

        parts.append(_footer_html(business, palette))
        return "\n".join(parts)

    def _build_blog_article_layout(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "SEO"))
        keyword = _esc(config.get("primary_keyword", ""))
        audience = _esc(config.get("target_audience", "businesses"))
        cta_text = _esc(config.get("cta_text", "Get Expert Help"))
        cta_url = _esc(config.get("cta_url", "#contact"))
        hub_url = config.get("hub_url", "{{hub_url}}")
        tone = config.get("tone", "Professional")

        headings = [
            f"What is {service} and Why Does It Matter?",
            f"Key Benefits of {service} for {audience}",
            f"How to Get Started with {keyword}",
            "Common Mistakes to Avoid",
            "Advanced Strategies for Better Results",
            f"Measuring the Success of Your {service} Campaign",
            "Frequently Asked Questions",
        ]

        toc_items = "".join(
            f'<li><a href="#section-{i + 1}">{_esc(h)}</a></li>'
            for i, h in enumerate(headings)
        )

        article_sections = "".join(
            f"""<section id="section-{i + 1}" class="article-section">
  <h2>{_esc(h)}</h2>
  <p>
    This section covers everything you need to know about {h.lower()}.
    For {audience.lower()}, understanding {keyword.lower()} is critical for
    sustained growth and competitive advantage in today's digital landscape.
  </p>
  <p>
    Our team at <a href="{hub_url}">{business}</a> has helped hundreds of
    organisations implement effective strategies that deliver measurable ROI.
  </p>
</section>"""
            for i, h in enumerate(headings)
        )

        tagline = _tone_tagline(service, audience, tone)

        parts: list[str] = [
            _base_css(palette),
            f"""<style>
.article-layout{{display:grid;grid-template-columns:1fr 300px;gap:2rem;align-items:start;max-width:1100px;margin:0 auto;padding:2rem 1.5rem}}
.article-toc{{position:sticky;top:80px;background:var(--bg-light,#f8fafc);border:1px solid var(--border);border-radius:8px;padding:1.5rem}}
.article-toc h3{{margin:0 0 1rem;font-size:1rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted)}}
.article-toc ol{{padding-left:1.2rem;margin:0}}
.article-toc li{{margin-bottom:.5rem}}
.article-toc a{{color:var(--primary);text-decoration:none;font-size:.9rem}}
.article-toc a:hover{{text-decoration:underline}}
.article-section{{margin-bottom:3rem}}
.article-section h2{{font-size:1.6rem;margin-bottom:1rem;border-bottom:3px solid var(--accent);padding-bottom:.5rem}}
.author-meta{{display:flex;align-items:center;gap:1rem;padding:1rem;background:var(--bg-light,#f8fafc);border-radius:8px;margin-bottom:2rem}}
.author-avatar{{width:48px;height:48px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.2rem}}
@media(max-width:768px){{.article-layout{{grid-template-columns:1fr}}.article-toc{{display:none}}}}
</style>""",
            _nav_html(business, palette),
        ]

        parts.append(f"""
<div class="container" style="padding-top:2rem">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <ol>
      <li><a href="{hub_url}">Hub: {service}</a></li>
      <li aria-current="page">The Complete Guide</li>
    </ol>
  </nav>
</div>
<div class="article-layout">
  <main>
    <h1>{tagline}: A Complete Guide for {audience}</h1>
    <div class="author-meta">
      <div class="author-avatar">✍</div>
      <div>
        <strong>{business} Editorial Team</strong><br>
        <small>Updated regularly · 10 min read · Expert-reviewed</small>
      </div>
    </div>
    <p class="hero-subtitle">
      This comprehensive guide covers everything {audience.lower()} need to know
      about {keyword.lower()}, from foundational concepts to advanced strategies
      that deliver real-world results.
    </p>
    {article_sections}
    <div class="cta-inline">
      <h3>Need Expert {service} Help?</h3>
      <p>Our team is ready to help you implement these strategies.</p>
      <a href="{cta_url}" class="btn btn-primary">{cta_text}</a>
    </div>
  </main>
  <aside>
    <nav class="article-toc" aria-label="Table of contents">
      <h3>Table of Contents</h3>
      <ol>{toc_items}</ol>
    </nav>
    <div class="sidebar-cta" style="margin-top:1.5rem;padding:1.5rem;background:var(--primary);color:#fff;border-radius:8px;text-align:center">
      <p style="font-size:.9rem;margin-bottom:1rem">Get a free {service} audit for your business</p>
      <a href="{cta_url}" class="btn btn-primary">{cta_text}</a>
    </div>
  </aside>
</div>
""")

        parts.append(_footer_html(business, palette))
        return "\n".join(parts)

    def _build_case_study_layout(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "Digital Marketing"))
        keyword = _esc(config.get("primary_keyword", ""))
        audience = _esc(config.get("target_audience", "businesses"))
        cta_text = _esc(config.get("cta_text", "See What We Can Do For You"))
        cta_url = _esc(config.get("cta_url", "#contact"))
        hub_url = config.get("hub_url", "{{hub_url}}")

        client_name = _esc(config.get("client_name", "Global Enterprise Corp"))
        client_industry = _esc(config.get("client_industry", "B2B Technology"))

        metrics = config.get("metrics", [
            {"label": "Organic Traffic Increase", "value": "+340%", "period": "in 6 months"},
            {"label": "Keyword Rankings (Top 3)", "value": "127", "period": "keywords"},
            {"label": "Revenue Generated", "value": "$1.2M", "period": "attributed"},
            {"label": "ROI", "value": "820%", "period": "campaign ROI"},
        ])

        metric_cards = "".join(
            f"""<div class="metric-card">
  <div class="metric-value">{_esc(str(m["value"]))}</div>
  <div class="metric-label">{_esc(m["label"])}</div>
  <div class="metric-period">{_esc(m["period"])}</div>
</div>"""
            for m in metrics
        )

        parts: list[str] = [
            _base_css(palette),
            f"""<style>
.case-study-hero{{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-light) 100%);color:#fff;padding:4rem 0}}
.metrics-bar{{background:#fff;border-radius:12px;padding:2rem;margin:2rem auto;max-width:900px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1.5rem;box-shadow:0 8px 30px rgba(0,0,0,.1)}}
.metric-card{{text-align:center;padding:1rem}}
.metric-value{{font-size:2.5rem;font-weight:800;color:var(--primary);line-height:1}}
.metric-label{{font-size:.9rem;font-weight:600;color:var(--text);margin-top:.5rem}}
.metric-period{{font-size:.75rem;color:var(--text-muted);margin-top:.25rem}}
.case-timeline{{border-left:3px solid var(--accent);padding-left:1.5rem;margin:2rem 0}}
.timeline-item{{margin-bottom:2rem;position:relative}}
.timeline-item::before{{content:"";position:absolute;left:-1.85rem;top:.25rem;width:12px;height:12px;border-radius:50%;background:var(--accent)}}
.timeline-item h3{{font-size:1.1rem;margin-bottom:.5rem}}
</style>""",
            _nav_html(business, palette),
        ]

        parts.append(f"""
<section class="case-study-hero" aria-labelledby="cs-heading">
  <div class="container text-center">
    <p class="eyebrow" style="color:rgba(255,255,255,.8)">Case Study · {client_industry}</p>
    <h1 id="cs-heading">How {business} Helped {client_name} Dominate {service}</h1>
    <p style="font-size:1.2rem;opacity:.9;max-width:700px;margin:1rem auto">
      A data-driven {keyword.lower()} campaign that transformed {client_name}'s
      digital presence and delivered exceptional results for {audience.lower()}.
    </p>
    <a href="{hub_url}" class="btn btn-secondary" style="margin-top:1rem">← Back to {service}</a>
  </div>
</section>
<div class="container">
  <div class="metrics-bar">{metric_cards}</div>
</div>
""")

        parts.append(f"""
<section class="section-pad">
  <div class="container" style="max-width:800px">
    <h2>The Challenge</h2>
    <p>
      {client_name} came to us struggling with low organic visibility despite having an
      excellent product for {audience.lower()}. Their website ranked on page 3+ for core
      {keyword.lower()} terms, resulting in minimal inbound leads and heavy reliance on
      paid advertising.
    </p>
    <h2 style="margin-top:2rem">Our Approach</h2>
    <div class="case-timeline">
      <div class="timeline-item">
        <h3>Month 1–2: Discovery &amp; Strategy</h3>
        <p>Comprehensive technical audit, competitor gap analysis, and keyword mapping
        for {keyword.lower()} across 200+ target terms.</p>
      </div>
      <div class="timeline-item">
        <h3>Month 3–4: On-Page Optimisation</h3>
        <p>Full content rewrite using our hub-and-spoke model, schema markup implementation,
        and page speed improvements that boosted Core Web Vitals scores.</p>
      </div>
      <div class="timeline-item">
        <h3>Month 5–6: Authority Building</h3>
        <p>Strategic link acquisition from relevant industry publications, resulting in
        a 45-point Domain Authority increase and rapid ranking gains.</p>
      </div>
    </div>
    <h2>The Results</h2>
    <p>
      Within six months, {client_name} achieved page 1 rankings for 127 target keywords,
      including the coveted position 1 for their primary {keyword.lower()} term. Organic
      traffic increased by 340%, directly attributable to {business}'s data-driven approach.
    </p>
    <div class="cta-inline">
      <h3>Ready for Similar Results?</h3>
      <a href="{cta_url}" class="btn btn-primary">{cta_text}</a>
    </div>
  </div>
</section>
""")

        parts.append(_footer_html(business, palette))
        return "\n".join(parts)

    def _build_lead_gen_layout(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "Digital Marketing"))
        keyword = _esc(config.get("primary_keyword", ""))
        audience = _esc(config.get("target_audience", "businesses"))
        cta_text = _esc(config.get("cta_text", "Get My Free Audit"))
        cta_url = _esc(config.get("cta_url", "#contact"))
        hub_url = config.get("hub_url", "{{hub_url}}")

        benefits = _default_benefits(service, config.get("tone", "Professional"))

        benefit_items = "".join(
            f"<li>✅ {_esc(b)}</li>" for b in benefits[:5]
        )

        parts: list[str] = [
            _base_css(palette),
            f"""<style>
.lead-gen-split{{display:grid;grid-template-columns:1fr 420px;gap:3rem;align-items:center;padding:4rem 0}}
.lead-form-card{{background:#fff;border-radius:16px;padding:2.5rem;box-shadow:0 20px 60px rgba(0,0,0,.12)}}
.lead-form-card h2{{margin:0 0 .5rem;font-size:1.5rem}}
.form-field{{margin-bottom:1rem}}
.form-field label{{display:block;font-size:.85rem;font-weight:600;margin-bottom:.25rem;color:var(--text)}}
.form-field input,.form-field select{{width:100%;padding:.75rem 1rem;border:2px solid var(--border);border-radius:6px;font-size:1rem;box-sizing:border-box}}
.form-field input:focus,.form-field select:focus{{outline:none;border-color:var(--primary)}}
.form-cta{{width:100%;padding:1rem;background:var(--primary);color:#fff;border:none;border-radius:6px;font-size:1rem;font-weight:700;cursor:pointer}}
.privacy-note{{font-size:.75rem;color:var(--text-muted);text-align:center;margin-top:.75rem}}
.urgency-bar{{background:var(--accent);color:var(--text);text-align:center;padding:.5rem;font-size:.9rem;font-weight:600}}
@media(max-width:768px){{.lead-gen-split{{grid-template-columns:1fr}}}}
</style>""",
            _nav_html(business, palette),
        ]

        parts.append(f"""
<div class="urgency-bar">
  🔥 Limited spots available — Only 3 free audits left this month
</div>
<section class="section-pad">
  <div class="container">
    <div class="lead-gen-split">
      <div>
        <p class="eyebrow">{service} for {audience}</p>
        <h1>Stop Losing Customers to Competitors Ranking Above You</h1>
        <p class="hero-subtitle">
          Get a free, no-obligation {keyword.lower()} audit worth £2,500.
          Discover exactly why you're not ranking and what we'll do about it.
        </p>
        <ul class="benefit-list">{benefit_items}</ul>
        <div style="margin-top:2rem;padding:1.5rem;background:var(--bg-light);border-radius:8px;border-left:4px solid var(--accent)">
          <p style="margin:0;font-style:italic">
            "Working with {business} was transformational. We went from page 3 to position 1
            in just 4 months — and the leads haven't stopped coming."
          </p>
          <strong style="font-size:.9rem">— Marketing Director, {audience}</strong>
        </div>
        <a href="{hub_url}" style="display:inline-block;margin-top:1rem;font-size:.9rem">
          ← Learn more about our {service} →
        </a>
      </div>
      <div>
        <div class="lead-form-card">
          <h2>Get Your Free {service} Audit</h2>
          <p style="color:var(--text-muted);font-size:.9rem;margin-bottom:1.5rem">
            Takes 60 seconds · No credit card required
          </p>
          <!-- FORM_INTEGRATION_POINT: Replace with your CRM form embed -->
          <form action="{cta_url}" method="POST" aria-label="Lead capture form">
            <div class="form-field">
              <label for="lf-name">Full Name *</label>
              <input type="text" id="lf-name" name="name" placeholder="Jane Smith" required>
            </div>
            <div class="form-field">
              <label for="lf-email">Work Email *</label>
              <input type="email" id="lf-email" name="email" placeholder="jane@company.com" required>
            </div>
            <div class="form-field">
              <label for="lf-website">Website URL *</label>
              <input type="url" id="lf-website" name="website" placeholder="https://yoursite.com" required>
            </div>
            <div class="form-field">
              <label for="lf-budget">Monthly Budget</label>
              <select id="lf-budget" name="budget">
                <option value="">Select budget range</option>
                <option value="under-1k">Under £1,000</option>
                <option value="1k-3k">£1,000–£3,000</option>
                <option value="3k-5k">£3,000–£5,000</option>
                <option value="5k-plus">£5,000+</option>
              </select>
            </div>
            <button type="submit" class="form-cta">{cta_text} →</button>
            <p class="privacy-note">🔒 Your data is safe. We never share or sell your information.</p>
          </form>
        </div>
      </div>
    </div>
  </div>
</section>
""")

        parts.append(_testimonials_section(service, palette))
        parts.append(_footer_html(business, palette))
        return "\n".join(parts)

    def _build_resource_guide_layout(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "Digital Marketing"))
        keyword = _esc(config.get("primary_keyword", ""))
        audience = _esc(config.get("target_audience", "businesses"))
        cta_text = _esc(config.get("cta_text", "Download the Full Guide"))
        cta_url = _esc(config.get("cta_url", "#download"))
        hub_url = config.get("hub_url", "{{hub_url}}")

        chapters = config.get("chapters", [
            {"number": 1, "title": f"Introduction to {service}", "topics": [f"What is {keyword}?", "Why it matters in 2025", "Core principles"]},
            {"number": 2, "title": "Strategy & Planning", "topics": ["Setting goals and KPIs", "Competitive analysis", "Resource planning"]},
            {"number": 3, "title": "Implementation Framework", "topics": ["Step-by-step process", "Tools and technology", "Team structure"]},
            {"number": 4, "title": "Measurement & Optimisation", "topics": ["Tracking success metrics", "Iterating on results", "Scaling what works"]},
        ])

        chapter_cards = ""
        for ch in chapters:
            topic_list = "".join(f"<li>{_esc(t)}</li>" for t in ch.get("topics", []))
            chapter_cards += f"""<div class="chapter-card">
  <div class="chapter-number">Chapter {ch["number"]}</div>
  <h3>{_esc(ch["title"])}</h3>
  <ul class="chapter-topics">{topic_list}</ul>
</div>"""

        parts: list[str] = [
            _base_css(palette),
            f"""<style>
.resource-header{{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-light) 100%);color:#fff;padding:5rem 0 4rem}}
.chapter-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1.5rem;margin-top:2rem}}
.chapter-card{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:1.5rem;transition:transform .2s,box-shadow .2s}}
.chapter-card:hover{{transform:translateY(-4px);box-shadow:0 12px 30px rgba(0,0,0,.08)}}
.chapter-number{{font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);margin-bottom:.5rem}}
.chapter-card h3{{font-size:1.1rem;margin:0 0 .75rem}}
.chapter-topics{{padding-left:1.2rem;margin:0;font-size:.85rem;color:var(--text-muted)}}
.chapter-topics li{{margin-bottom:.25rem}}
.download-cta{{background:var(--accent);border-radius:16px;padding:3rem;text-align:center;margin:3rem 0}}
.download-cta h2{{margin:0 0 .75rem;font-size:1.8rem}}
</style>""",
            _nav_html(business, palette),
        ]

        parts.append(f"""
<section class="resource-header" aria-labelledby="guide-heading">
  <div class="container text-center">
    <p class="eyebrow" style="color:rgba(255,255,255,.8)">Free Resource Guide · {service}</p>
    <h1 id="guide-heading">The Ultimate {service} Guide for {audience}</h1>
    <p style="font-size:1.2rem;opacity:.9;max-width:700px;margin:1rem auto 2rem">
      Everything {audience.lower()} need to master {keyword.lower()} —
      from strategy to execution. Compiled by {business} experts.
    </p>
    <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap">
      <a href="{cta_url}" class="btn btn-primary">{cta_text}</a>
      <a href="{hub_url}" class="btn btn-secondary">Explore All Resources</a>
    </div>
    <p style="opacity:.7;font-size:.85rem;margin-top:1rem">
      📄 {len(chapters) * 10}+ pages · ✅ Expert reviewed · 🔄 Updated regularly
    </p>
  </div>
</section>
<section class="section-pad">
  <div class="container">
    <h2>What's Inside This Guide</h2>
    <p>A comprehensive breakdown of everything covered in this {service} resource:</p>
    <div class="chapter-grid">{chapter_cards}</div>
    <div class="download-cta">
      <h2>Ready to Master {service}?</h2>
      <p>Download the complete guide and start implementing today.</p>
      <a href="{cta_url}" class="btn btn-primary btn-large">{cta_text}</a>
    </div>
  </div>
</section>
""")

        parts.append(_testimonials_section(service, palette))
        parts.append(_footer_html(business, palette))
        return "\n".join(parts)

    # -----------------------------------------------------------------------
    # Shared section builders
    # -----------------------------------------------------------------------

    def _build_page_scripts(self) -> str:
        """Return a self-contained <script> block injected before </body>."""
        return """<script>
(function () {
  'use strict';

  /* ── Smooth scroll ─────────────────────────────────────────────────── */
  document.documentElement.style.scrollBehavior = 'smooth';

  /* ── Sticky header shadow ──────────────────────────────────────────── */
  (function () {
    var style = document.createElement('style');
    style.textContent = 'nav.scrolled{box-shadow:0 4px 20px rgba(0,0,0,.15);}';
    document.head.appendChild(style);
    function onScroll() {
      var navs = document.querySelectorAll('nav');
      navs.forEach(function (nav) {
        if (window.scrollY > 10) { nav.classList.add('scrolled'); }
        else { nav.classList.remove('scrolled'); }
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }());

  /* ── Reveal animation CSS ──────────────────────────────────────────── */
  (function () {
    var style = document.createElement('style');
    style.textContent = [
      '.reveal{opacity:0;transform:translateY(24px);transition:opacity .5s ease,transform .5s ease;}',
      '.reveal.is-visible{opacity:1;transform:none;}'
    ].join('');
    document.head.appendChild(style);
  }());

  document.addEventListener('DOMContentLoaded', function () {

    /* ── Add reveal class to key elements ────────────────────────────── */
    var revealSelectors = [
      '.feature-card', '.metric-card', '.benefit-list li',
      '.testimonial-card', '.stat'
    ];
    revealSelectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.classList.add('reveal');
      });
    });

    /* ── Scroll-reveal IntersectionObserver ──────────────────────────── */
    if ('IntersectionObserver' in window) {
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            revealObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12 });
      document.querySelectorAll('.reveal').forEach(function (el) {
        revealObserver.observe(el);
      });
    } else {
      document.querySelectorAll('.reveal').forEach(function (el) {
        el.classList.add('is-visible');
      });
    }

    /* ── Animated counters on scroll ─────────────────────────────────── */
    if ('IntersectionObserver' in window) {
      var counterObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) { return; }
          counterObserver.unobserve(entry.target);
          var el = entry.target;
          var rawText = el.textContent.trim();
          var numMatch = rawText.match(/[\\d,.]+/);
          if (!numMatch) { return; }
          var numStr = numMatch[0].replace(/,/g, '');
          var target = parseFloat(numStr);
          if (isNaN(target)) { return; }
          var suffix = rawText.slice(numMatch.index + numMatch[0].length);
          var prefix = rawText.slice(0, numMatch.index);
          var duration = 1200;
          var startTime = null;
          function easeOutQuad(t) { return t * (2 - t); }
          function step(timestamp) {
            if (!startTime) { startTime = timestamp; }
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var current = Math.floor(easeOutQuad(progress) * target);
            el.textContent = prefix + current.toLocaleString() + suffix;
            if (progress < 1) { requestAnimationFrame(step); }
            else { el.textContent = prefix + target.toLocaleString() + suffix; }
          }
          requestAnimationFrame(step);
        });
      }, { threshold: 0.2 });
      document.querySelectorAll('.stat-number, .metric-value, .kpi-value').forEach(function (el) {
        counterObserver.observe(el);
      });
    }

    /* ── FAQ accordion toggle ─────────────────────────────────────────── */
    document.querySelectorAll('.faq-item').forEach(function (item) {
      var question = item.querySelector('.faq-question');
      var answer = item.querySelector('.faq-answer');
      if (!question || !answer) { return; }
      answer.style.maxHeight = '0';
      answer.style.overflow = 'hidden';
      answer.style.transition = 'max-height 0.35s ease';
      question.style.cursor = 'pointer';
      question.setAttribute('aria-expanded', 'false');
      question.addEventListener('click', function () {
        var isOpen = answer.style.maxHeight !== '0px' && answer.style.maxHeight !== '0';
        if (isOpen) {
          answer.style.maxHeight = '0';
          question.setAttribute('aria-expanded', 'false');
          item.classList.remove('faq-open');
        } else {
          answer.style.maxHeight = answer.scrollHeight + 'px';
          question.setAttribute('aria-expanded', 'true');
          item.classList.add('faq-open');
        }
      });
    });

  });
}());
</script>"""

    def _build_meta_tags(
        self, config: dict[str, Any], palette: dict[str, str]
    ) -> str:
        business = _esc(config.get("business_name", "Your Business"))
        service = _esc(config.get("service", "Professional Services"))
        keyword = _esc(config.get("primary_keyword", ""))
        title = config.get("meta_title") or f"{service} | {business}"
        description = config.get("meta_description") or (
            f"Expert {service.lower()} for {config.get('target_audience', 'businesses')}. "
            f"Proven {keyword.lower()} strategies that deliver measurable ROI. "
            f"Get a free consultation with {business} today."
        )
        canonical = config.get("canonical_url", "https://example.com/page")
        og_image = config.get("og_image", "https://example.com/og-image.jpg")
        primary = palette.get("primary", "#1a3c6e")

        return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(description)}">
  <link rel="canonical" href="{_esc(canonical)}">

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="{_esc(title)}">
  <meta property="og:description" content="{_esc(description)}">
  <meta property="og:url" content="{_esc(canonical)}">
  <meta property="og:image" content="{_esc(og_image)}">
  <meta property="og:site_name" content="{business}">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{_esc(title)}">
  <meta name="twitter:description" content="{_esc(description)}">
  <meta name="twitter:image" content="{_esc(og_image)}">

  <!-- Primary theme colour for browser chrome -->
  <meta name="theme-color" content="{primary}">
</head>"""

    def _build_schema_markup(self, config: dict[str, Any]) -> str:
        """Build schema.org JSON-LD structured data for the page."""
        layout = config.get("layout", "hero_features")
        business = config.get("business_name", "Your Business")
        service = config.get("service", "Professional Services")
        keyword = config.get("primary_keyword", "")
        description = config.get("meta_description") or (
            f"Expert {service} services. {keyword} solutions for businesses."
        )
        url = config.get("canonical_url", "https://example.com/page")
        logo = config.get("logo_url", "https://example.com/logo.png")

        if layout == "blog_article":
            schema = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": f"{service} Guide",
                "description": description,
                "url": url,
                "author": {"@type": "Organization", "name": business},
                "publisher": {
                    "@type": "Organization",
                    "name": business,
                    "logo": {"@type": "ImageObject", "url": logo},
                },
                "mainEntityOfPage": url,
                "keywords": keyword,
            }
        elif layout in ("lead_gen", "service_hub", "hero_features"):
            schema = {
                "@context": "https://schema.org",
                "@type": "Service",
                "name": service,
                "description": description,
                "url": url,
                "provider": {
                    "@type": "Organization",
                    "name": business,
                    "url": config.get("site_url", "https://example.com"),
                    "logo": logo,
                },
                "serviceType": keyword,
                "areaServed": config.get("area_served", "Global"),
            }
        elif layout == "case_study":
            schema = {
                "@context": "https://schema.org",
                "@type": "Article",
                "@subtype": "CaseStudy",
                "headline": f"{service} Case Study",
                "description": description,
                "url": url,
                "author": {"@type": "Organization", "name": business},
                "about": {"@type": "Service", "name": service},
            }
        else:
            schema = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": service,
                "description": description,
                "url": url,
                "publisher": {
                    "@type": "Organization",
                    "name": business,
                    "logo": logo,
                },
            }

        schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
        # Prevent </script> injection in JSON-LD script blocks
        schema_json = schema_json.replace("</", "<\\/")
        return f"""<script type="application/ld+json">
{schema_json}
</script>"""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _esc(value: Any) -> str:
    """HTML-escape a value and coerce to string."""
    return _html.escape(str(value))


def _tone_tagline(service: str, audience: str, tone: str) -> str:
    """Return a headline phrased according to *tone*."""
    tone = tone.lower()
    if tone == "conversational":
        return f"Let's Transform Your {service} Together"
    if tone == "technical":
        return f"Data-Driven {service}: A Systematic Approach"
    if tone == "authority":
        return f"The Industry Standard in {service}"
    # Professional (default)
    return f"Expert {service} Solutions for {audience}"


def _default_features(service: str, keyword: str) -> list[dict[str, str]]:
    return [
        {"icon": "🎯", "title": "Strategic Planning", "description": f"Custom {service.lower()} roadmaps aligned to your business goals and {keyword} opportunities."},
        {"icon": "📈", "title": "Performance Analytics", "description": f"Real-time dashboards tracking every {keyword} metric that matters to your growth."},
        {"icon": "🔗", "title": "Authority Building", "description": f"Systematic {service.lower()} strategies that establish your brand as the go-to authority."},
    ]


def _default_benefits(service: str, tone: str) -> list[str]:
    return [
        f"Increase organic visibility for {service.lower()} target terms",
        "Generate qualified inbound leads 24/7",
        "Reduce cost-per-acquisition vs paid channels",
        "Build lasting brand authority in your market",
        "Get detailed monthly reporting and actionable insights",
        "Dedicated account management and support",
    ]


def _testimonials_section(service: str, palette: dict[str, str]) -> str:
    return f"""
<section class="testimonials section-pad bg-light" aria-labelledby="testimonials-heading">
  <div class="container">
    <div class="section-header">
      <h2 id="testimonials-heading">What Our Clients Say</h2>
      <p>Real results from real businesses using our {service.lower()} services.</p>
    </div>
    <div class="testimonials-grid">
      <blockquote class="testimonial-card">
        <p>"We saw a 250% increase in organic traffic within 6 months. The team's expertise
        in {service.lower()} is unmatched — they genuinely understand our business."</p>
        <footer><strong>Sarah J.</strong> · Marketing Director, B2B SaaS</footer>
      </blockquote>
      <blockquote class="testimonial-card">
        <p>"Finally an agency that delivers what they promise. Our {service.lower()} results
        speak for themselves — page 1 rankings and a 40% increase in qualified leads."</p>
        <footer><strong>Michael T.</strong> · CEO, Professional Services Firm</footer>
      </blockquote>
      <blockquote class="testimonial-card">
        <p>"The ROI from our {service.lower()} investment has been extraordinary.
        Best decision we made for our digital presence."</p>
        <footer><strong>Emma R.</strong> · Head of Growth, E-commerce</footer>
      </blockquote>
    </div>
  </div>
</section>
"""


def _faq_section(service: str, keyword: str) -> str:
    faqs = [
        (f"How long does {service} take to show results?", f"Most {service.lower()} campaigns start showing measurable results within 3–6 months, with significant growth by month 6–12."),
        (f"What makes your {service} different?", f"We combine data-driven strategy with transparent reporting, ensuring every {keyword.lower()} decision is backed by evidence."),
        (f"How do you measure {service} success?", f"We track organic traffic, {keyword.lower()} rankings, conversion rates, and revenue attribution — all reported monthly."),
        (f"Do I need a long-term contract for {service}?", f"No. Our {service.lower()} packages are flexible. We believe our results speak for themselves."),
    ]

    items = ""
    for q, a in faqs:
        items += f"""<details class="faq-item">
  <summary>{_esc(q)}</summary>
  <p>{_esc(a)}</p>
</details>"""

    return f"""
<section class="faq section-pad" aria-labelledby="faq-heading">
  <div class="container" style="max-width:800px">
    <div class="section-header">
      <h2 id="faq-heading">Frequently Asked Questions</h2>
    </div>
    <div class="faq-list">{items}</div>
  </div>
</section>
"""


def _nav_html(business: str, palette: dict[str, str]) -> str:
    return f"""<header class="site-header" role="banner">
  <div class="container nav-inner">
    <a href="{{{{hub_url}}}}" class="site-logo" aria-label="{business} home">{business}</a>
    <nav class="main-nav" aria-label="Main navigation">
      <ul>
        <li><a href="{{{{hub_url}}}}">Home</a></li>
        <li><a href="{{{{hub_url}}}}#services">Services</a></li>
        <li><a href="{{{{hub_url}}}}#about">About</a></li>
        <li><a href="{{{{hub_url}}}}#contact">Contact</a></li>
      </ul>
    </nav>
  </div>
</header>"""


def _footer_html(business: str, palette: dict[str, str]) -> str:
    return f"""<footer class="site-footer" role="contentinfo">
  <div class="container">
    <div class="footer-grid">
      <div>
        <strong class="footer-brand">{business}</strong>
        <p>Enterprise SEO &amp; digital marketing solutions for ambitious businesses.</p>
      </div>
      <div>
        <h3>Services</h3>
        <ul>
          <li><a href="{{{{hub_url}}}}">Home</a></li>
          <li><a href="{{{{spoke_url_1}}}}">Spoke Resource 1</a></li>
          <li><a href="{{{{spoke_url_2}}}}">Spoke Resource 2</a></li>
        </ul>
      </div>
      <div>
        <h3>Company</h3>
        <ul>
          <li><a href="{{{{hub_url}}}}#about">About Us</a></li>
          <li><a href="{{{{hub_url}}}}#case-studies">Case Studies</a></li>
          <li><a href="{{{{hub_url}}}}#contact">Contact</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; 2025 {business}. All rights reserved.</p>
      <p><a href="{{{{hub_url}}}}#privacy">Privacy Policy</a> · <a href="{{{{hub_url}}}}#terms">Terms of Service</a></p>
    </div>
  </div>
</footer>"""


def _base_css(palette: dict[str, str]) -> str:
    p = palette
    return f"""<style>
/* ─── CSS Custom Properties ─────────────────────────────────────────── */
:root{{
  --primary:{p["primary"]};
  --primary-light:{p["primary_light"]};
  --accent:{p["accent"]};
  --bg:{p["bg"]};
  --bg-light:{p["bg"]};
  --bg-dark:{p["bg_dark"]};
  --text:{p["text"]};
  --text-muted:{p["text_muted"]};
  --white:{p["white"]};
  --border:{p["border"]};
  --success:{p["success"]};
  --radius:8px;
  --shadow:0 4px 20px rgba(0,0,0,.08);
  --shadow-lg:0 12px 40px rgba(0,0,0,.12);
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
}}
/* ─── Reset ──────────────────────────────────────────────────────────── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{font-family:var(--font-sans);color:var(--text);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}}
img{{max-width:100%;height:auto;display:block}}
a{{color:var(--primary-light);text-decoration:none}}
a:hover{{text-decoration:underline}}
ul{{list-style:none}}
/* ─── Layout ─────────────────────────────────────────────────────────── */
.container{{max-width:1200px;margin:0 auto;padding:0 1.5rem}}
.section-pad{{padding:5rem 0}}
.text-center{{text-align:center}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:start}}
@media(max-width:768px){{.two-col{{grid-template-columns:1fr}}}}
/* ─── Typography ─────────────────────────────────────────────────────── */
h1{{font-size:clamp(2rem,5vw,3.25rem);font-weight:800;line-height:1.1;letter-spacing:-.02em}}
h2{{font-size:clamp(1.6rem,3vw,2.25rem);font-weight:700;line-height:1.2;letter-spacing:-.01em}}
h3{{font-size:1.25rem;font-weight:600}}
p{{margin-bottom:1rem;color:var(--text)}}
.eyebrow{{font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--primary-light);margin-bottom:.75rem}}
/* ─── Buttons ────────────────────────────────────────────────────────── */
.btn{{display:inline-flex;align-items:center;gap:.5rem;padding:.75rem 1.75rem;border-radius:var(--radius);font-weight:700;font-size:.95rem;cursor:pointer;transition:transform .15s,box-shadow .15s;text-decoration:none;border:2px solid transparent;white-space:nowrap}}
.btn:hover{{transform:translateY(-2px);box-shadow:var(--shadow-lg);text-decoration:none}}
.btn-primary{{background:var(--primary);color:var(--white);border-color:var(--primary)}}
.btn-primary:hover{{background:var(--primary-light);border-color:var(--primary-light);color:var(--white)}}
.btn-secondary{{background:transparent;color:var(--white);border-color:rgba(255,255,255,.6)}}
.btn-secondary:hover{{background:rgba(255,255,255,.1)}}
.btn-large{{padding:1rem 2.5rem;font-size:1.05rem}}
.cta-group{{display:flex;gap:1rem;flex-wrap:wrap;margin-top:2rem}}
/* ─── Navigation ─────────────────────────────────────────────────────── */
.site-header{{background:var(--primary);color:var(--white);position:sticky;top:0;z-index:100;box-shadow:0 2px 20px rgba(0,0,0,.15)}}
.nav-inner{{display:flex;align-items:center;justify-content:space-between;padding:.75rem 1.5rem;max-width:1200px;margin:0 auto}}
.site-logo{{color:var(--white);font-size:1.2rem;font-weight:800;text-decoration:none}}
.main-nav ul{{display:flex;gap:1.5rem}}
.main-nav a{{color:rgba(255,255,255,.85);text-decoration:none;font-size:.9rem;font-weight:500;transition:color .15s}}
.main-nav a:hover{{color:var(--white)}}
/* ─── Hero ───────────────────────────────────────────────────────────── */
.hero{{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-light) 100%);color:var(--white);padding:7rem 0 5rem;overflow:hidden;position:relative}}
.hero-content{{max-width:700px;animation:fadeInUp .6s ease-out}}
.hero h1{{color:var(--white);margin-bottom:1.25rem}}
.hero-subtitle{{font-size:1.15rem;opacity:.9;max-width:600px;color:var(--white)}}
.trust-note{{opacity:.75;font-size:.85rem;margin-top:1.5rem;color:var(--white)}}
/* ─── Page Header ────────────────────────────────────────────────────── */
.page-header{{background:var(--primary);color:var(--white);padding:3rem 0}}
.page-header h1{{color:var(--white);margin-bottom:.75rem}}
.page-header-sub{{color:rgba(255,255,255,.85);font-size:1.05rem;max-width:650px}}
/* ─── Breadcrumb ─────────────────────────────────────────────────────── */
.breadcrumb ol{{display:flex;gap:.5rem;list-style:none;font-size:.85rem;margin-bottom:1rem}}
.breadcrumb li{{color:rgba(255,255,255,.7)}}
.breadcrumb li:not(:last-child)::after{{content:" /";margin-left:.5rem}}
.breadcrumb a{{color:rgba(255,255,255,.85)}}
/* ─── Features ───────────────────────────────────────────────────────── */
.section-header{{text-align:center;max-width:680px;margin:0 auto 3rem}}
.section-header p{{color:var(--text-muted);font-size:1.05rem}}
.features-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem}}
.feature-card{{background:var(--white);border-radius:12px;padding:2rem;border:1px solid var(--border);transition:transform .2s,box-shadow .2s;animation:fadeInUp .5s ease-out}}
.feature-card:hover{{transform:translateY(-4px);box-shadow:var(--shadow-lg)}}
.feature-icon{{font-size:2rem;margin-bottom:1rem}}
.feature-card h3{{margin-bottom:.5rem;color:var(--text)}}
.feature-card p{{font-size:.9rem;color:var(--text-muted);margin:0}}
/* ─── Benefits ───────────────────────────────────────────────────────── */
.bg-light{{background:var(--bg)}}
.benefit-list li{{display:flex;align-items:flex-start;gap:.5rem;margin-bottom:.75rem;font-size:.95rem}}
.stats-box{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}
.stat{{text-align:center;padding:1.5rem;background:var(--white);border-radius:10px;border:1px solid var(--border)}}
.stat-number{{display:block;font-size:2.5rem;font-weight:800;color:var(--primary);line-height:1}}
.stat-label{{display:block;font-size:.85rem;color:var(--text-muted);margin-top:.5rem}}
/* ─── Trust signals & spoke nav ──────────────────────────────────────── */
.trust-signals{{padding:1.5rem;background:var(--white);border-radius:10px;border:1px solid var(--border)}}
.trust-signals p{{margin-bottom:.75rem;font-size:.9rem}}
.spoke-nav li{{margin-bottom:.5rem}}
.spoke-nav a{{font-weight:600;font-size:.95rem}}
/* ─── Testimonials ───────────────────────────────────────────────────── */
.testimonials-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.5rem}}
.testimonial-card{{background:var(--white);border-radius:12px;padding:2rem;border:1px solid var(--border);font-style:italic}}
.testimonial-card p{{margin-bottom:1rem;color:var(--text)}}
.testimonial-card footer{{font-style:normal;font-size:.85rem;color:var(--text-muted)}}
/* ─── FAQ ────────────────────────────────────────────────────────────── */
.faq-list{{margin-top:1.5rem}}
.faq-item{{border-bottom:1px solid var(--border);padding:.25rem 0}}
.faq-item summary{{font-weight:600;padding:.75rem 0;cursor:pointer;list-style:none;position:relative;padding-right:2rem}}
.faq-item summary::after{{content:"+";position:absolute;right:0;top:.75rem;font-size:1.2rem;color:var(--text-muted)}}
.faq-item[open] summary::after{{content:"−"}}
.faq-item p{{padding:.75rem 0;color:var(--text-muted);margin:0}}
/* ─── CTA Section ────────────────────────────────────────────────────── */
.cta-section{{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-light) 100%);color:var(--white);padding:5rem 0}}
.cta-section h2{{color:var(--white);margin-bottom:1rem}}
.cta-section p{{color:rgba(255,255,255,.9);font-size:1.05rem;margin-bottom:2rem}}
.cta-inline{{background:var(--bg);border-radius:12px;padding:2rem;margin-top:3rem;text-align:center}}
/* ─── Footer ─────────────────────────────────────────────────────────── */
.site-footer{{background:var(--bg-dark);color:rgba(255,255,255,.75);padding:4rem 0 2rem}}
.footer-grid{{display:grid;grid-template-columns:2fr 1fr 1fr;gap:3rem;margin-bottom:3rem}}
.footer-brand{{color:var(--white);font-size:1.1rem;font-weight:700;display:block;margin-bottom:.75rem}}
.footer-grid h3{{color:var(--white);font-size:.85rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:1rem}}
.footer-grid ul li{{margin-bottom:.5rem}}
.footer-grid a{{color:rgba(255,255,255,.6);font-size:.9rem}}
.footer-grid a:hover{{color:var(--white)}}
.footer-bottom{{border-top:1px solid rgba(255,255,255,.1);padding-top:1.5rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem;font-size:.8rem}}
@media(max-width:768px){{.footer-grid{{grid-template-columns:1fr}}.footer-bottom{{flex-direction:column}}}}
/* ─── Animations ─────────────────────────────────────────────────────── */
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:translateY(0)}}}}
/* ─── FAQ Accordion ──────────────────────────────────────────────────── */
.faq-question{{cursor:pointer;position:relative;padding-right:2rem;font-weight:600;user-select:none}}
.faq-question::after{{content:"+";position:absolute;right:0;top:0;font-size:1.2rem;color:var(--text-muted);transition:transform .25s ease}}
.faq-item.faq-open .faq-question::after{{transform:rotate(45deg)}}
.faq-answer{{color:var(--text-muted);padding-top:.5rem}}
/* ─── Scroll-reveal ──────────────────────────────────────────────────── */
.reveal{{opacity:0;transform:translateY(24px);transition:opacity .5s ease,transform .5s ease}}
.reveal.is-visible{{opacity:1;transform:none}}
/* ─── Sticky header scrolled ─────────────────────────────────────────── */
nav.scrolled{{box-shadow:0 4px 20px rgba(0,0,0,.15)}}
</style>"""
