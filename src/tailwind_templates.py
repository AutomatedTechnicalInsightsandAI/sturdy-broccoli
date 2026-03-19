"""
tailwind_templates.py

Five Tailwind CSS HTML layout templates used by the SEO Site Factory for
live preview rendering.

Each template is a Python string containing a full HTML page with Tailwind
CSS (loaded from CDN) and three placeholder tokens:

    {h1}               — page H1 heading
    {meta_title}       — <title> tag content
    {meta_description} — <meta name="description"> content
    {body_html}        — rendered HTML body (from Markdown)
    {primary_color}    — Tailwind colour class prefix  (e.g. "blue", "indigo")
    {cta_link}         — primary CTA href
    {cta_text}         — primary CTA label

Available templates
-------------------
- modern_saas         — clean, minimal, large hero CTA
- professional_service — trust-focused, testimonials prominent
- content_guide        — academic, detailed H2/H3, sidebar nav
- ecommerce            — product-focused, social proof
- enterprise           — data-driven, ROI-focused, charts placeholder
"""
from __future__ import annotations

import html as _html

TEMPLATE_NAMES: dict[str, str] = {
    "modern_saas": "Modern SaaS",
    "professional_service": "Professional Service",
    "content_guide": "Content-Heavy Guide",
    "ecommerce": "E-commerce",
    "enterprise": "B2B Enterprise",
}

# ---------------------------------------------------------------------------
# Shared head / CDN block
# ---------------------------------------------------------------------------

_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="description" content="{meta_description}"/>
  <title>{meta_title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>"""

# ---------------------------------------------------------------------------
# Template 1: Modern SaaS
# ---------------------------------------------------------------------------

_MODERN_SAAS = (
    _HEAD
    + """
<body class="bg-white text-gray-900 font-sans">
  <!-- Header -->
  <header class="border-b border-gray-100 px-6 py-4 flex items-center justify-between">
    <span class="text-xl font-bold text-{primary_color}-600">YourBrand</span>
    <nav class="hidden md:flex gap-6 text-sm text-gray-600">
      <a href="#" class="hover:text-{primary_color}-600">Features</a>
      <a href="#" class="hover:text-{primary_color}-600">Pricing</a>
      <a href="#" class="hover:text-{primary_color}-600">About</a>
    </nav>
    <a href="{cta_link}" class="bg-{primary_color}-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-{primary_color}-700 transition">{cta_text}</a>
  </header>

  <!-- Hero -->
  <section class="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
    <h1 class="text-5xl font-extrabold leading-tight text-gray-900 mb-6">{h1}</h1>
    <p class="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">{meta_description}</p>
    <a href="{cta_link}" class="inline-block bg-{primary_color}-600 text-white text-lg font-semibold px-8 py-4 rounded-xl shadow-lg hover:bg-{primary_color}-700 transition">{cta_text}</a>
  </section>

  <!-- Content -->
  <main class="max-w-4xl mx-auto px-6 pb-24 prose prose-lg">
    {body_html}
  </main>

  <!-- Footer -->
  <footer class="bg-gray-50 border-t border-gray-100 py-10 text-center text-sm text-gray-400">
    &copy; 2025 YourBrand. All rights reserved.
  </footer>
</body>
</html>"""
)

# ---------------------------------------------------------------------------
# Template 2: Professional Service
# ---------------------------------------------------------------------------

_PROFESSIONAL_SERVICE = (
    _HEAD
    + """
<body class="bg-gray-50 text-gray-900 font-serif">
  <header class="bg-white shadow-sm px-8 py-5 flex items-center justify-between">
    <span class="text-2xl font-bold text-{primary_color}-700">YourFirm</span>
    <a href="{cta_link}" class="bg-{primary_color}-700 text-white text-sm font-semibold px-5 py-2 rounded hover:bg-{primary_color}-800 transition">{cta_text}</a>
  </header>

  <!-- Hero with trust bar -->
  <section class="bg-{primary_color}-700 text-white py-16 px-6 text-center">
    <h1 class="text-4xl font-bold mb-4">{h1}</h1>
    <p class="text-lg opacity-90 max-w-2xl mx-auto">{meta_description}</p>
  </section>

  <!-- Trust signals -->
  <div class="bg-white border-b border-gray-200">
    <div class="max-w-5xl mx-auto px-6 py-4 flex flex-wrap gap-6 justify-center text-sm text-gray-600">
      <span>✅ 500+ Clients Served</span>
      <span>✅ Google Partner Certified</span>
      <span>✅ 15+ Years Experience</span>
      <span>✅ 4.9★ Average Rating</span>
    </div>
  </div>

  <!-- Content -->
  <main class="max-w-3xl mx-auto px-6 py-12 prose prose-lg">
    {body_html}
  </main>

  <!-- Testimonial -->
  <section class="bg-{primary_color}-50 py-12 px-6">
    <div class="max-w-2xl mx-auto text-center">
      <blockquote class="text-xl italic text-gray-700 mb-4">
        "The results exceeded every expectation — we saw a 3× increase in qualified leads within 90 days."
      </blockquote>
      <cite class="text-sm text-gray-500">— Sarah M., CEO</cite>
    </div>
  </section>

  <footer class="bg-gray-800 text-gray-300 py-8 text-center text-sm">
    &copy; 2025 YourFirm. All rights reserved.
  </footer>
</body>
</html>"""
)

# ---------------------------------------------------------------------------
# Template 3: Content-Heavy Guide
# ---------------------------------------------------------------------------

_CONTENT_GUIDE = (
    _HEAD
    + """
<body class="bg-white text-gray-900 font-sans">
  <header class="border-b border-gray-200 px-6 py-4">
    <span class="text-lg font-bold text-{primary_color}-600">YourSite</span>
  </header>

  <div class="max-w-6xl mx-auto px-6 py-10 flex gap-10">
    <!-- Sidebar TOC -->
    <aside class="hidden lg:block w-56 shrink-0">
      <div class="sticky top-6 bg-gray-50 rounded-lg p-4 border border-gray-200">
        <p class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">Contents</p>
        <nav class="text-sm text-{primary_color}-700 space-y-2">
          <a href="#intro" class="block hover:underline">Introduction</a>
          <a href="#section1" class="block hover:underline">Key Concepts</a>
          <a href="#section2" class="block hover:underline">Step-by-Step</a>
          <a href="#section3" class="block hover:underline">Best Practices</a>
          <a href="#conclusion" class="block hover:underline">Conclusion</a>
        </nav>
      </div>
    </aside>

    <!-- Main content -->
    <article class="flex-1 min-w-0">
      <h1 id="intro" class="text-4xl font-extrabold mb-4 text-gray-900">{h1}</h1>
      <p class="text-gray-500 text-sm mb-8">Last updated · 2025 · 15 min read</p>

      <div class="prose prose-lg max-w-none">
        {body_html}
      </div>

      <!-- CTA box -->
      <div class="mt-12 bg-{primary_color}-50 border border-{primary_color}-200 rounded-xl p-6 text-center">
        <p class="text-lg font-semibold text-gray-800 mb-3">Ready to put this into practice?</p>
        <a href="{cta_link}" class="inline-block bg-{primary_color}-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-{primary_color}-700 transition">{cta_text}</a>
      </div>
    </article>
  </div>

  <footer class="border-t border-gray-200 py-6 text-center text-sm text-gray-400">
    &copy; 2025 YourSite
  </footer>
</body>
</html>"""
)

# ---------------------------------------------------------------------------
# Template 4: E-commerce
# ---------------------------------------------------------------------------

_ECOMMERCE = (
    _HEAD
    + """
<body class="bg-white text-gray-900 font-sans">
  <!-- Top bar -->
  <div class="bg-{primary_color}-600 text-white text-center text-sm py-2">
    🚚 Free shipping on orders over $50 &nbsp;|&nbsp; Use code <strong>SEO20</strong> for 20% off
  </div>

  <header class="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
    <span class="text-xl font-bold text-{primary_color}-600">YourStore</span>
    <a href="{cta_link}" class="bg-{primary_color}-600 text-white text-sm font-semibold px-5 py-2 rounded-lg hover:bg-{primary_color}-700 transition">{cta_text}</a>
  </header>

  <!-- Product hero -->
  <section class="bg-gradient-to-r from-{primary_color}-600 to-{primary_color}-800 text-white py-16 px-6 text-center">
    <h1 class="text-4xl font-extrabold mb-4">{h1}</h1>
    <p class="text-lg opacity-90 max-w-2xl mx-auto mb-8">{meta_description}</p>
    <a href="{cta_link}" class="inline-block bg-white text-{primary_color}-700 font-bold px-8 py-4 rounded-xl text-lg shadow hover:bg-gray-100 transition">{cta_text}</a>
  </section>

  <!-- Social proof -->
  <div class="bg-gray-50 border-b border-gray-200 py-4 px-6">
    <div class="max-w-4xl mx-auto flex flex-wrap gap-6 justify-center text-sm text-gray-600">
      <span>⭐ 4.8/5 from 2,400+ reviews</span>
      <span>📦 Ships in 24 hours</span>
      <span>🔒 Secure checkout</span>
      <span>↩️ 30-day returns</span>
    </div>
  </div>

  <!-- Content -->
  <main class="max-w-4xl mx-auto px-6 py-12 prose prose-lg">
    {body_html}
  </main>

  <footer class="bg-gray-900 text-gray-400 py-8 text-center text-sm">
    &copy; 2025 YourStore. All rights reserved.
  </footer>
</body>
</html>"""
)

# ---------------------------------------------------------------------------
# Template 5: B2B Enterprise
# ---------------------------------------------------------------------------

_ENTERPRISE = (
    _HEAD
    + """
<body class="bg-slate-50 text-gray-900 font-sans">
  <header class="bg-slate-900 text-white px-8 py-5 flex items-center justify-between">
    <span class="text-xl font-semibold tracking-tight">YourEnterprise</span>
    <nav class="hidden md:flex gap-8 text-sm text-slate-300">
      <a href="#" class="hover:text-white">Solutions</a>
      <a href="#" class="hover:text-white">Customers</a>
      <a href="#" class="hover:text-white">Resources</a>
    </nav>
    <a href="{cta_link}" class="border border-{primary_color}-400 text-{primary_color}-300 text-sm px-4 py-2 rounded hover:bg-{primary_color}-900 transition">{cta_text}</a>
  </header>

  <!-- Hero -->
  <section class="bg-slate-900 text-white py-20 px-6 text-center">
    <div class="max-w-3xl mx-auto">
      <span class="text-{primary_color}-400 text-sm font-semibold uppercase tracking-widest">Enterprise Solution</span>
      <h1 class="text-5xl font-bold mt-4 mb-6 leading-tight">{h1}</h1>
      <p class="text-slate-300 text-lg mb-10">{meta_description}</p>
      <div class="flex justify-center gap-4">
        <a href="{cta_link}" class="bg-{primary_color}-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-{primary_color}-700 transition">{cta_text}</a>
        <a href="#" class="border border-slate-500 text-slate-300 px-6 py-3 rounded-lg hover:border-slate-300 transition">View Demo</a>
      </div>
    </div>
  </section>

  <!-- ROI metrics -->
  <div class="bg-white border-b border-gray-200 py-6 px-6">
    <div class="max-w-5xl mx-auto grid grid-cols-3 gap-6 text-center">
      <div><p class="text-3xl font-bold text-{primary_color}-600">340%</p><p class="text-sm text-gray-500">Average ROI</p></div>
      <div><p class="text-3xl font-bold text-{primary_color}-600">48h</p><p class="text-sm text-gray-500">Time to Deploy</p></div>
      <div><p class="text-3xl font-bold text-{primary_color}-600">99.9%</p><p class="text-sm text-gray-500">Uptime SLA</p></div>
    </div>
  </div>

  <!-- Content -->
  <main class="max-w-4xl mx-auto px-6 py-14 prose prose-slate prose-lg">
    {body_html}
  </main>

  <footer class="bg-slate-900 text-slate-400 py-8 text-center text-sm">
    &copy; 2025 YourEnterprise Inc. All rights reserved.
  </footer>
</body>
</html>"""
)

# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, str] = {
    "modern_saas": _MODERN_SAAS,
    "professional_service": _PROFESSIONAL_SERVICE,
    "content_guide": _CONTENT_GUIDE,
    "ecommerce": _ECOMMERCE,
    "enterprise": _ENTERPRISE,
}


def render_template(
    template_key: str,
    h1: str,
    meta_title: str,
    meta_description: str,
    body_html: str,
    primary_color: str = "blue",
    cta_link: str = "#get-started",
    cta_text: str = "Get Started",
) -> str:
    """Render a named template with the supplied content variables."""
    if template_key not in _TEMPLATES:
        raise ValueError(f"Unknown template '{template_key}'. Choose from: {list(_TEMPLATES)}")

    return _TEMPLATES[template_key].format(
        h1=_html.escape(h1),
        meta_title=_html.escape(meta_title) or _html.escape(h1),
        meta_description=_html.escape(meta_description),
        body_html=body_html,          # already HTML — do NOT escape
        primary_color=primary_color,
        cta_link=cta_link,
        cta_text=_html.escape(cta_text),
    )


def list_templates() -> dict[str, str]:
    """Return a mapping of template_key → display_name."""
    return dict(TEMPLATE_NAMES)
