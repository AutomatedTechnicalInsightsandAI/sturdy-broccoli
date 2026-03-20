"""
premium_page_builder.py

Generates complete, production-quality HTML5 landing pages using Tailwind CSS
(via CDN) and vanilla JavaScript.  No external JS libraries are required.

Usage::

    from src.premium_page_builder import PremiumPageBuilder

    builder = PremiumPageBuilder()
    html = builder.build(config)   # config is a dict — see examples/premium_page_example.json

The returned string is a fully self-contained HTML document that can be saved
directly as an ``.html`` file or injected into a CMS (e.g. WordPress) as a
custom page template.
"""
from __future__ import annotations

from typing import Any


class PremiumPageBuilder:
    """
    Builds a complete, production-quality HTML5 page from a configuration
    dictionary.

    The generated page includes:
    - Sticky animated navbar with mobile hamburger menu
    - Full-viewport hero section with background video
    - Stats bar with count-up animation
    - Problem / Solution split section
    - Services grid
    - Testimonials auto-play carousel
    - Pricing tiers
    - CTA banner
    - Footer with columns and social links
    - All required CSS (Tailwind CDN + custom) and vanilla JS inline

    Usage::

        builder = PremiumPageBuilder()
        html_string = builder.build(config_dict)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, config: dict[str, Any]) -> str:
        """
        Build and return a complete HTML5 document string from *config*.

        Parameters
        ----------
        config:
            Dictionary whose structure matches ``examples/premium_page_example.json``.

        Returns
        -------
        str
            A fully self-contained HTML5 document.
        """
        parts: list[str] = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            self._build_head(config),
            "<body class=\"font-sans antialiased\">",
            self._build_nav(config),
            self._build_hero(config),
            self._build_stats(config),
            self._build_problem_solution(config),
            self._build_services(config),
            self._build_testimonials(config),
            self._build_pricing(config),
            self._build_cta_banner(config),
            self._build_footer(config),
            self._build_scripts(config),
            "</body>",
            "</html>",
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_head(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        meta = config.get("meta", {})
        title = meta.get("title", brand.get("name", ""))
        description = meta.get("description", "")
        primary = brand.get("primary", "#1e3a5f")
        accent = brand.get("accent", "#3b82f6")
        dark = brand.get("dark", "#0f172a")
        light = brand.get("light", "#f8fafc")

        return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{self._esc(description)}">
  <title>{self._esc(title)}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            brand: {{
              primary: '{primary}',
              accent: '{accent}',
              dark: '{dark}',
              light: '{light}',
            }}
          }}
        }}
      }}
    }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --brand-primary: {primary};
      --brand-accent: {accent};
      --brand-dark: {dark};
      --brand-light: {light};
    }}
    * {{ font-family: 'Inter', sans-serif; }}

    /* Navbar scroll state */
    .nav-scrolled {{
      background-color: #ffffff !important;
      box-shadow: 0 2px 20px rgba(0,0,0,0.08) !important;
    }}

    /* Hero video overlay */
    .hero-overlay {{
      background: linear-gradient(
        to bottom,
        rgba(15,23,42,0.65) 0%,
        rgba(15,23,42,0.45) 60%,
        rgba(15,23,42,0.75) 100%
      );
    }}

    /* Entrance animations */
    @keyframes fadeInUp {{
      from {{ opacity: 0; transform: translateY(40px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fadeInLeft {{
      from {{ opacity: 0; transform: translateX(-40px); }}
      to   {{ opacity: 1; transform: translateX(0); }}
    }}
    @keyframes fadeInRight {{
      from {{ opacity: 0; transform: translateX(40px); }}
      to   {{ opacity: 1; transform: translateX(0); }}
    }}
    .animate-fade-in-up   {{ animation: fadeInUp   0.8s ease both; }}
    .animate-fade-in-left  {{ animation: fadeInLeft  0.8s ease both; }}
    .animate-fade-in-right {{ animation: fadeInRight 0.8s ease both; }}

    /* Scroll-triggered animation */
    .animate-on-scroll {{
      opacity: 0;
      transform: translateY(20px);
      transition: opacity 0.6s ease, transform 0.6s ease;
    }}
    .animate-on-scroll.is-visible {{
      opacity: 1;
      transform: translateY(0);
    }}
    .animate-on-scroll.slide-left  {{ transform: translateX(-40px); }}
    .animate-on-scroll.slide-right {{ transform: translateX(40px);  }}
    .animate-on-scroll.slide-left.is-visible,
    .animate-on-scroll.slide-right.is-visible {{ transform: translateX(0); }}

    /* Testimonial carousel */
    .carousel-wrapper {{ overflow: hidden; position: relative; }}
    .carousel-track {{
      display: flex;
      transition: transform 0.5s ease;
    }}
    .carousel-item {{
      min-width: 100%;
      box-sizing: border-box;
    }}

    /* Pricing featured ring */
    .pricing-featured {{
      ring-color: var(--brand-accent);
      box-shadow: 0 0 0 3px var(--brand-accent);
    }}

    /* Smooth scroll */
    html {{ scroll-behavior: smooth; }}

    /* Mobile menu hidden by default */
    #mobile-menu {{ display: none; }}
    #mobile-menu.open {{ display: block; }}
  </style>
</head>"""

    def _build_nav(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        name = self._esc(brand.get("name", "Brand"))
        primary = brand.get("primary", "#1e3a5f")
        nav_links = config.get("nav_links", [])
        cta = config.get("cta", {})
        cta_url = self._esc(cta.get("url", "#"))
        cta_text = self._esc(cta.get("primary_text", "Get Started"))

        links_html = "".join(
            f'<a href="{self._esc(lnk.get("url","#"))}" '
            f'class="text-sm font-medium text-white hover:text-blue-300 transition-colors">'
            f'{self._esc(lnk.get("text",""))} </a>'
            for lnk in nav_links
        )
        mobile_links_html = "".join(
            f'<a href="{self._esc(lnk.get("url","#"))}" '
            f'class="block px-4 py-2 text-sm font-medium hover:bg-gray-100">'
            f'{self._esc(lnk.get("text",""))}</a>'
            for lnk in nav_links
        )

        return f"""<nav id="navbar" class="fixed top-0 left-0 right-0 z-50 transition-all duration-300">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between h-16">
      <!-- Logo -->
      <div class="flex-shrink-0">
        <span class="text-xl font-bold text-white nav-logo">{name}</span>
      </div>
      <!-- Desktop nav links -->
      <div class="hidden md:flex items-center gap-6">
        {links_html}
        <a href="{cta_url}"
           class="px-5 py-2 text-sm font-semibold text-white rounded-full transition-all duration-200"
           style="background-color:{primary}; hover:opacity-90;">
          {cta_text}
        </a>
      </div>
      <!-- Mobile hamburger -->
      <button id="hamburger" class="md:hidden text-white focus:outline-none" aria-label="Toggle menu">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path id="hamburger-icon" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      </button>
    </div>
  </div>
  <!-- Mobile menu -->
  <div id="mobile-menu" class="md:hidden bg-white shadow-lg border-t">
    {mobile_links_html}
    <a href="{cta_url}"
       class="block m-4 px-5 py-2 text-sm font-semibold text-white text-center rounded-full"
       style="background-color:{primary};">
      {cta_text}
    </a>
  </div>
</nav>"""

    def _build_hero(self, config: dict[str, Any]) -> str:
        hero = config.get("hero", {})
        cta = config.get("cta", {})
        brand = config.get("brand", {})
        accent = brand.get("accent", "#3b82f6")
        primary = brand.get("primary", "#1e3a5f")

        badge = self._esc(hero.get("badge", ""))
        heading = self._esc(hero.get("heading", "")).replace("&#10;", "<br>").replace("\n", "<br>")
        subheading = self._esc(hero.get("subheading", ""))
        video_url = self._esc(hero.get("video_url", ""))
        poster_url = self._esc(hero.get("poster_url", ""))
        cta_primary = self._esc(cta.get("primary_text", "Get Started"))
        cta_secondary = self._esc(cta.get("secondary_text", "Learn More"))
        cta_url = self._esc(cta.get("url", "#"))

        return f"""<section id="hero" class="relative min-h-screen flex items-center justify-center overflow-hidden">
  <!-- Background video -->
  <video class="absolute inset-0 w-full h-full object-cover"
         autoplay muted loop playsinline poster="{poster_url}">
    <source src="{video_url}" type="video/mp4">
  </video>
  <!-- Overlay -->
  <div class="absolute inset-0 hero-overlay"></div>
  <!-- Content -->
  <div class="relative z-10 text-center text-white px-4 max-w-4xl mx-auto">
    <!-- Badge -->
    <div class="inline-block mb-6 animate-fade-in-up" style="animation-delay:0.1s">
      <span class="px-4 py-1.5 text-sm font-semibold rounded-full text-white"
            style="background-color:{accent};">
        {badge}
      </span>
    </div>
    <!-- Heading -->
    <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight mb-6 animate-fade-in-up"
        style="animation-delay:0.25s">
      {heading}
    </h1>
    <!-- Subheading -->
    <p class="text-lg sm:text-xl text-gray-200 mb-10 max-w-2xl mx-auto animate-fade-in-up"
       style="animation-delay:0.4s">
      {subheading}
    </p>
    <!-- CTA buttons -->
    <div class="flex flex-col sm:flex-row gap-4 justify-center animate-fade-in-up"
         style="animation-delay:0.55s">
      <a href="{cta_url}"
         class="px-8 py-4 text-base font-bold rounded-full text-white shadow-lg transition-all duration-200 hover:opacity-90"
         style="background-color:{accent};">
        {cta_primary}
      </a>
      <a href="#services"
         class="px-8 py-4 text-base font-bold rounded-full border-2 border-white text-white hover:bg-white transition-all duration-200"
         style="hover:color:{primary};">
        {cta_secondary}
      </a>
    </div>
  </div>
  <!-- Scroll indicator -->
  <div class="absolute bottom-8 left-1/2 -translate-x-1/2 text-white animate-bounce">
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
    </svg>
  </div>
</section>"""

    def _build_stats(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        dark = brand.get("dark", "#0f172a")
        accent = brand.get("accent", "#3b82f6")
        stats = config.get("stats", [])

        items_html = "".join(
            f"""<div class="text-center animate-on-scroll">
        <p class="text-4xl font-extrabold stat-value" style="color:{accent};"
           data-target="{self._esc(str(s.get('value','')))}">
          {self._esc(str(s.get('value','')))}
        </p>
        <p class="mt-2 text-sm font-medium text-gray-300 uppercase tracking-wide">
          {self._esc(s.get('label',''))}
        </p>
      </div>"""
            for s in stats
        )

        return f"""<section id="stats" style="background-color:{dark};">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-8">
      {items_html}
    </div>
  </div>
</section>"""

    def _build_problem_solution(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        accent = brand.get("accent", "#3b82f6")
        light = brand.get("light", "#f8fafc")
        problem = config.get("problem", {})
        solution = config.get("solution", {})

        prob_items = "".join(
            f'<li class="flex items-start gap-3">'
            f'<span class="mt-0.5 text-red-500">✕</span>'
            f'<span>{self._esc(p)}</span></li>'
            for p in problem.get("points", [])
        )
        sol_items = "".join(
            f'<li class="flex items-start gap-3">'
            f'<span class="mt-0.5 font-bold" style="color:{accent};">✓</span>'
            f'<span>{self._esc(p)}</span></li>'
            for p in solution.get("points", [])
        )

        return f"""<section id="problem-solution" style="background-color:{light};">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
    <div class="grid md:grid-cols-2 gap-12 items-start">
      <!-- Problem -->
      <div class="animate-on-scroll slide-left bg-white rounded-2xl p-8 shadow-md border-t-4 border-red-400">
        <div class="text-4xl mb-4">⚠️</div>
        <h2 class="text-2xl font-bold text-gray-900 mb-6">
          {self._esc(problem.get('heading','The Problem'))}
        </h2>
        <ul class="space-y-4 text-gray-700">
          {prob_items}
        </ul>
      </div>
      <!-- Solution -->
      <div class="animate-on-scroll slide-right bg-white rounded-2xl p-8 shadow-md border-t-4"
           style="border-color:{accent};">
        <div class="text-4xl mb-4">🚀</div>
        <h2 class="text-2xl font-bold text-gray-900 mb-6">
          {self._esc(solution.get('heading','Our Solution'))}
        </h2>
        <ul class="space-y-4 text-gray-700">
          {sol_items}
        </ul>
      </div>
    </div>
  </div>
</section>"""

    def _build_services(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        accent = brand.get("accent", "#3b82f6")
        services = config.get("services", {})
        heading = self._esc(services.get("heading", "Our Services"))
        subheading = self._esc(services.get("subheading", ""))
        items = services.get("items", [])

        cards_html = "".join(
            f"""<div class="animate-on-scroll bg-white rounded-2xl shadow-md hover:shadow-xl transition-shadow duration-300 p-6 border-t-4"
         style="border-color:{accent};">
        <div class="text-4xl mb-4">{self._esc(item.get('icon',''))}</div>
        <h3 class="text-xl font-bold text-gray-900 mb-2">{self._esc(item.get('title',''))}</h3>
        <p class="text-gray-600 text-sm leading-relaxed">{self._esc(item.get('description',''))}</p>
      </div>"""
            for item in items
        )

        return f"""<section id="services" class="bg-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
    <div class="text-center mb-12 animate-on-scroll">
      <h2 class="text-3xl sm:text-4xl font-extrabold text-gray-900">{heading}</h2>
      <p class="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">{subheading}</p>
    </div>
    <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
      {cards_html}
    </div>
  </div>
</section>"""

    def _build_testimonials(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        dark = brand.get("dark", "#0f172a")
        accent = brand.get("accent", "#3b82f6")
        testimonials = config.get("testimonials", {})
        heading = self._esc(testimonials.get("heading", "What Our Clients Say"))
        items = testimonials.get("items", [])

        slides_html = "".join(
            f"""<div class="carousel-item px-4">
        <div class="bg-white rounded-2xl p-8 max-w-2xl mx-auto shadow-xl">
          <p class="text-5xl font-serif leading-none mb-4" style="color:{accent};">"</p>
          <blockquote class="text-gray-800 text-lg italic mb-6">{self._esc(item.get('quote',''))}</blockquote>
          <div>
            <p class="font-bold text-gray-900">{self._esc(item.get('author',''))}</p>
            <p class="text-sm text-gray-500">
              {self._esc(item.get('role',''))} — {self._esc(item.get('company',''))}
            </p>
          </div>
        </div>
      </div>"""
            for item in items
        )

        dot_count = len(items)
        dots_html = "".join(
            f'<button class="carousel-dot w-3 h-3 rounded-full bg-gray-500 transition-all duration-300" '
            f'data-index="{i}" aria-label="Slide {i+1}"></button>'
            for i in range(dot_count)
        )

        return f"""<section id="testimonials" style="background-color:{dark};">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
    <div class="text-center mb-12 animate-on-scroll">
      <h2 class="text-3xl sm:text-4xl font-extrabold text-white">{heading}</h2>
    </div>
    <div class="relative">
      <!-- Prev arrow -->
      <button id="carousel-prev"
              class="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white bg-opacity-20 hover:bg-opacity-40 text-white rounded-full w-10 h-10 flex items-center justify-center transition-all"
              aria-label="Previous">
        &#8249;
      </button>
      <!-- Track -->
      <div class="carousel-wrapper mx-12" id="carousel-wrapper">
        <div class="carousel-track" id="carousel-track">
          {slides_html}
        </div>
      </div>
      <!-- Next arrow -->
      <button id="carousel-next"
              class="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-white bg-opacity-20 hover:bg-opacity-40 text-white rounded-full w-10 h-10 flex items-center justify-center transition-all"
              aria-label="Next">
        &#8250;
      </button>
    </div>
    <!-- Dots -->
    <div class="flex justify-center gap-2 mt-8" id="carousel-dots">
      {dots_html}
    </div>
  </div>
</section>"""

    def _build_pricing(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        accent = brand.get("accent", "#3b82f6")
        light = brand.get("light", "#f8fafc")
        pricing = config.get("pricing", {})
        heading = self._esc(pricing.get("heading", "Pricing"))
        subheading = self._esc(pricing.get("subheading", ""))
        tiers = pricing.get("tiers", [])

        cards_html = ""
        for tier in tiers:
            featured = tier.get("featured", False)
            name = self._esc(tier.get("name", ""))
            price = self._esc(str(tier.get("price", "")))
            period = self._esc(str(tier.get("period", "")))
            description = self._esc(tier.get("description", ""))
            features = tier.get("features", [])
            cta_text = self._esc(tier.get("cta_text", "Get Started"))
            cta_url = self._esc(tier.get("cta_url", "#"))

            feature_items = "".join(
                f'<li class="flex items-start gap-3 text-sm text-gray-700">'
                f'<span class="mt-0.5 font-bold" style="color:{accent};">✓</span>'
                f'<span>{self._esc(f)}</span></li>'
                for f in features
            )

            badge = (
                f'<div class="absolute -top-4 left-1/2 -translate-x-1/2">'
                f'<span class="px-4 py-1 text-xs font-bold text-white rounded-full" '
                f'style="background-color:{accent};">Most Popular</span></div>'
                if featured else ""
            )

            card_class = (
                "animate-on-scroll relative bg-white rounded-2xl p-8 pricing-featured transform scale-105"
                if featured
                else "animate-on-scroll relative bg-white rounded-2xl p-8 shadow-md"
            )

            cta_style = f'background-color:{accent}; color:#fff;' if featured else f'border:2px solid {accent}; color:{accent};'

            cards_html += f"""<div class="{card_class}">
        {badge}
        <h3 class="text-xl font-bold text-gray-900 mb-1">{name}</h3>
        <div class="flex items-end gap-1 my-4">
          <span class="text-4xl font-extrabold text-gray-900">{price}</span>
          <span class="text-gray-500 mb-1">{period}</span>
        </div>
        <p class="text-gray-600 text-sm mb-6">{description}</p>
        <ul class="space-y-3 mb-8">
          {feature_items}
        </ul>
        <a href="{cta_url}"
           class="block text-center py-3 px-6 rounded-full font-semibold text-sm transition-all duration-200 hover:opacity-90"
           style="{cta_style}">
          {cta_text}
        </a>
      </div>"""

        return f"""<section id="pricing" style="background-color:{light};">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
    <div class="text-center mb-12 animate-on-scroll">
      <h2 class="text-3xl sm:text-4xl font-extrabold text-gray-900">{heading}</h2>
      <p class="mt-4 text-lg text-gray-600">{subheading}</p>
    </div>
    <div class="grid md:grid-cols-3 gap-8 items-center">
      {cards_html}
    </div>
  </div>
</section>"""

    def _build_cta_banner(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        primary = brand.get("primary", "#1e3a5f")
        accent = brand.get("accent", "#3b82f6")
        cta = config.get("cta", {})
        heading = self._esc(cta.get("banner_heading", "Ready to Get Started?"))
        subheading = self._esc(cta.get("banner_subheading", ""))
        cta_url = self._esc(cta.get("url", "#"))
        cta_text = self._esc(cta.get("primary_text", "Get Started"))

        return f"""<section id="cta">
  <div style="background:linear-gradient(135deg, {primary} 0%, {accent} 100%);">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
      <h2 class="text-3xl sm:text-4xl font-extrabold text-white mb-4 animate-on-scroll">
        {heading}
      </h2>
      <p class="text-lg text-blue-100 mb-8 animate-on-scroll">{subheading}</p>
      <a href="{cta_url}"
         class="inline-block px-10 py-4 text-base font-bold rounded-full bg-white transition-all duration-200 hover:opacity-90 animate-on-scroll"
         style="color:{primary};">
        {cta_text}
      </a>
    </div>
  </div>
</section>"""

    def _build_footer(self, config: dict[str, Any]) -> str:
        brand = config.get("brand", {})
        dark = brand.get("dark", "#0f172a")
        accent = brand.get("accent", "#3b82f6")
        name = self._esc(brand.get("name", ""))
        tagline = self._esc(brand.get("tagline", ""))
        footer = config.get("footer", {})
        columns = footer.get("columns", [])
        social = footer.get("social", [])
        copyright_text = self._esc(footer.get("copyright", ""))

        cols_html = "".join(
            f"""<div>
        <h4 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          {self._esc(col.get('heading',''))}
        </h4>
        <ul class="space-y-2">
          {''.join(
            f'<li><a href="{self._esc(lnk.get("url","#"))}" '
            f'class="text-sm text-gray-500 hover:text-white transition-colors">'
            f'{self._esc(lnk.get("text",""))}</a></li>'
            for lnk in col.get('links',[])
          )}
        </ul>
      </div>"""
            for col in columns
        )

        social_html = "".join(
            f'<a href="{self._esc(s.get("url","#"))}" '
            f'class="text-gray-500 hover:text-white transition-colors text-sm">'
            f'{self._esc(s.get("platform",""))}</a>'
            for s in social
        )

        return f"""<footer style="background-color:{dark};">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
    <div class="grid md:grid-cols-4 gap-12 mb-12">
      <!-- Brand -->
      <div class="md:col-span-1">
        <span class="text-xl font-bold text-white">{name}</span>
        <p class="mt-2 text-sm text-gray-400">{tagline}</p>
      </div>
      <!-- Columns -->
      {cols_html}
    </div>
    <!-- Bottom bar -->
    <div class="border-t border-gray-800 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
      <p class="text-sm text-gray-500">{copyright_text}</p>
      <div class="flex gap-6">
        {social_html}
      </div>
    </div>
  </div>
</footer>"""

    def _build_scripts(self, config: dict[str, Any]) -> str:
        return r"""<script>
  // ── Navbar scroll handler ──────────────────────────────────────────
  (function () {
    var navbar = document.getElementById('navbar');
    var logo   = navbar ? navbar.querySelector('.nav-logo') : null;
    var links  = navbar ? navbar.querySelectorAll('a') : [];

    function onScroll() {
      if (!navbar) return;
      if (window.scrollY > 50) {
        navbar.classList.add('nav-scrolled');
        if (logo) logo.style.color = '#111827';
        links.forEach(function(a) {
          if (!a.closest('#mobile-menu')) a.style.color = '#111827';
        });
      } else {
        navbar.classList.remove('nav-scrolled');
        if (logo) logo.style.color = '#ffffff';
        links.forEach(function(a) {
          if (!a.closest('#mobile-menu')) a.style.color = '#ffffff';
        });
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  })();

  // ── Mobile hamburger ────────────────────────────────────────────────
  (function () {
    var btn  = document.getElementById('hamburger');
    var menu = document.getElementById('mobile-menu');
    if (!btn || !menu) return;
    btn.addEventListener('click', function () {
      menu.classList.toggle('open');
    });
  })();

  // ── Intersection Observer for .animate-on-scroll ───────────────────
  (function () {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll('.animate-on-scroll').forEach(function (el) {
      observer.observe(el);
    });
  })();

  // ── Stats count-up animation ───────────────────────────────────────
  (function () {
    function animateValue(el, target, duration) {
      // Only animate simple integer values (digits and commas only, e.g. "2,400").
      // Values containing currency symbols, letters, or other suffixes (e.g. "£2.1M",
      // "94%", "200+") are left as-is to preserve their original display.
      var cleaned = target.replace(/,/g, '');
      if (!/^\d+$/.test(cleaned)) return;
      var end = parseInt(cleaned, 10);
      if (isNaN(end)) return;
      var startTime = null;
      function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        var current = Math.round(progress * end);
        el.textContent = current.toLocaleString();
        if (progress < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    var statsSection = document.getElementById('stats');
    if (!statsSection) return;

    var observer = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        statsSection.querySelectorAll('.stat-value').forEach(function (el) {
          animateValue(el, el.dataset.target || el.textContent, 1500);
        });
        observer.disconnect();
      }
    }, { threshold: 0.3 });
    observer.observe(statsSection);
  })();

  // ── Testimonial carousel ────────────────────────────────────────────
  (function () {
    var track   = document.getElementById('carousel-track');
    var dotsEl  = document.getElementById('carousel-dots');
    var prevBtn = document.getElementById('carousel-prev');
    var nextBtn = document.getElementById('carousel-next');
    var wrapper = document.getElementById('carousel-wrapper');

    if (!track) return;

    var items   = track.querySelectorAll('.carousel-item');
    var dots    = dotsEl ? dotsEl.querySelectorAll('.carousel-dot') : [];
    var total   = items.length;
    var current = 0;
    var timer   = null;

    function goTo(index) {
      current = (index + total) % total;
      track.style.transform = 'translateX(-' + (current * 100) + '%)';
      dots.forEach(function (d, i) {
        d.style.backgroundColor = i === current ? '#fff' : '';
        d.style.opacity         = i === current ? '1'   : '0.5';
      });
    }

    function startAuto() {
      timer = setInterval(function () { goTo(current + 1); }, 3000);
    }
    function stopAuto() { clearInterval(timer); }

    if (prevBtn) prevBtn.addEventListener('click', function () { stopAuto(); goTo(current - 1); startAuto(); });
    if (nextBtn) nextBtn.addEventListener('click', function () { stopAuto(); goTo(current + 1); startAuto(); });

    dots.forEach(function (d) {
      d.addEventListener('click', function () {
        stopAuto();
        goTo(parseInt(d.dataset.index, 10));
        startAuto();
      });
    });

    if (wrapper) {
      wrapper.addEventListener('mouseenter', stopAuto);
      wrapper.addEventListener('mouseleave', startAuto);
    }

    goTo(0);
    startAuto();
  })();
</script>"""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _esc(value: str) -> str:
        """HTML-escape a string to prevent XSS when embedding config values."""
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
