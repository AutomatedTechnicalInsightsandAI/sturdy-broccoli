"""
gui_wrapper.py — Streamlit GUI for the sturdy-broccoli content engine.

Run with:
    streamlit run gui_wrapper.py
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime

import streamlit as st

from src.competitor_analyzer import CompetitorAnalyzer
from src.database import Database
from src.html5_page_builder import HTML5PageBuilder
from src.multi_format_generator import MultiFormatGenerator
from src.prompt_builder import PromptBuilder
from src.quality_scorer import QualityScorer
from src.template_manager import TemplateManager
from src.agency_dashboard import AgencyDashboard
from src.batch_validator import BatchValidator
from src.staging_environment import StagingEnvironment
from src.staging_review import StagingReviewManager
from src.content_editor import ContentEditor
from src.wordpress_publisher import WordPressPublisher
from src.ranking_tracker import RankingTracker


def _json_default(obj: object) -> str:
    """Custom JSON encoder fallback for datetime/date objects."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


# ---------------------------------------------------------------------------
# Jeff the Master Barber — Client Configuration (non-sensitive data only)
# Credentials (WordPress Application Password) must be entered at runtime
# in the 🪒 Jeff the Master Barber tab; they are never stored in source code.
# ---------------------------------------------------------------------------
JEFF_SITE_CONFIG: dict = {
    "client": "JEFF THE MASTER BARBER",
    "domain": "jeffthemasterbarber.com",
    "location": {
        "address": "7612 N Lockwood Ridge Rd, Sarasota, FL 34243",
        "city": "Sarasota",
        "state": "FL",
        "zip": "34243",
        "geo_lat": 27.388,
        "geo_long": -82.502,
        "phone": "",  # Add the client's phone number here when available
    },
    "integrations": {
        "booking_url": "https://jeffthemasterbarber.booksy.com/j",
        "youtube_channel": "https://www.youtube.com/@JEFFREYELBARBEROMASTER",
        "amazon_storefront": "https://www.amazon.com/shop/jeffthemasterbarber",
        # Replace these placeholder IDs with real YouTube video/Shorts IDs from the channel.
        # e.g. the ID in https://www.youtube.com/watch?v=XXXXXXXXXXX is "XXXXXXXXXXX".
        # Populate up to 16 entries to fill the 4×4 grid; fewer entries are fine.
        "youtube_video_ids": [],
        "wp_api_user": "orlandovelazquez941",
        "wp_endpoint": "https://jeffthemasterbarber.com/wp-json/wp/v2/",
        "wp_site_url": "https://jeffthemasterbarber.com",
    },
    "ui_elements": {
        "background_fx": "video_overlay_dark_gritty",
        "animation_style": "fade_on_scroll_cards",
        "grid_layout": "4x4_shorts_vids",
        "color_scheme": "agency_dark",
    },
    "seo": {
        "title": "JEFF THE MASTER BARBER | Best Barber in Sarasota, FL",
        "meta_description": (
            "Book Jeff the Master Barber — Sarasota's #1 barber for precision haircuts, "
            "beard trims, VIP grooming & mobile barbering. Serving University Park, "
            "Whitfield, The Meadows & beyond."
        ),
        "primary_keyword": "best barber in Sarasota FL",
        "target_keywords": [
            "best barber near me",
            "best mobile barber",
            "best barbers in sarasota",
            "barbers in sarasota",
            "sarasota barber shop",
            "mobile barber sarasota",
            "haircut sarasota fl",
            "barber near university park sarasota",
            "barber near whitfield sarasota",
            "VIP haircut sarasota",
            "beard trim sarasota",
        ],
    },
    "pricing": {
        "Standard Haircuts": [
            ("Adult Haircut (No Beard)", "$40.00 – $50.00"),
            ("Adult Haircut with Beard", "$50.00 – $60.00"),
            ("Specialty Cut (Pompadour, Mohawk, etc.)", "$40.00 – $55.00"),
            ("Kids/Teen Haircut", "$25.00 – $40.00"),
            ("Senior Haircut", "$30.00 – $35.00"),
        ],
        "Express & Maintenance": [
            ("Clean Up (Edge/Lineup only)", "$20.00 – $30.00"),
            ("Beard Trim & Edge", "$20.00 – $30.00"),
            ("Eyebrows", "$5.00 – $12.00"),
        ],
        "Specialty & Premium": [
            ("VIP Haircut & Beard", "~$100.00"),
            ("Hair Design", "$10.00 – $20.00"),
            ("Color Services", "$120.00+"),
            ("House Calls / Mobile Services", "$125.00 – $250.00+"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper: generate the full barber landing-page HTML
# ---------------------------------------------------------------------------

def _build_jeff_barber_html(video_url: str = "") -> str:
    """Return a complete dark-mode HTML5 landing page for Jeff the Master Barber.

    Features
    --------
    - AOS (Animate On Scroll) scroll-fade card effects
    - Full-screen background video (or dark gradient fallback) with dark overlay
    - 4×4 YouTube Shorts / video grid
    - Pricing table
    - Booksy "Book Now" CTA
    - LocalBusiness JSON-LD schema (Sarasota)
    - SEO meta tags targeting Sarasota barber keywords
    """
    cfg = JEFF_SITE_CONFIG
    loc = cfg["location"]
    inte = cfg["integrations"]
    seo = cfg["seo"]
    pricing = cfg["pricing"]

    video_section = ""
    if video_url.strip():
        video_section = f"""
  <video autoplay muted loop playsinline id="bg-video">
    <source src="{video_url.strip()}" type="video/mp4">
  </video>"""

    # Build pricing rows
    pricing_html = ""
    for category, items in pricing.items():
        rows = "".join(
            f'<tr><td>{name}</td><td class="price">{price}</td></tr>'
            for name, price in items
        )
        pricing_html += f"""
        <div class="pricing-category" data-aos="fade-up">
          <h3>{category}</h3>
          <table class="price-table">
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    # Build 4×4 YouTube grid (16 slots)
    # Uses real video IDs from the config when available; falls back to
    # clickable thumbnail-style placeholder cards that link to the channel.
    video_ids: list[str] = list(inte.get("youtube_video_ids") or [])
    yt_grid_items = ""
    for i in range(16):
        delay = (i % 4) * 80
        if i < len(video_ids):
            vid = video_ids[i]
            yt_grid_items += f"""
        <div class="yt-card" data-aos="zoom-in" data-aos-delay="{delay}">
          <div class="yt-embed-wrapper">
            <iframe
              src="https://www.youtube.com/embed/{vid}?rel=0&modestbranding=1"
              title="Jeff the Master Barber — Video {i + 1}"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
              loading="lazy">
            </iframe>
          </div>
        </div>"""
        else:
            yt_grid_items += f"""
        <div class="yt-card" data-aos="zoom-in" data-aos-delay="{delay}">
          <a href="{inte['youtube_channel']}" target="_blank" rel="noopener"
             style="display:block;text-decoration:none;">
            <div class="yt-embed-wrapper" style="background:#111;display:flex;align-items:center;justify-content:center;position:relative;">
              <img src="https://img.youtube.com/vi/default/hqdefault.jpg"
                   alt="Watch on YouTube" loading="lazy"
                   style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.35;">
              <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.5rem;">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24"
                     fill="#c9a84c"><path d="M10 16.5l6-4.5-6-4.5v9zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/></svg>
                <span style="color:#c9a84c;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;">Watch on YouTube</span>
              </div>
            </div>
          </a>
        </div>"""

    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "Jeff the Master Barber",
        "image": f"https://{cfg['domain']}/logo.jpg",
        "@id": f"https://{cfg['domain']}",
        "url": f"https://{cfg['domain']}",
        "telephone": loc.get("phone", ""),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "7612 N Lockwood Ridge Rd",
            "addressLocality": "Sarasota",
            "addressRegion": "FL",
            "postalCode": "34243",
            "addressCountry": "US",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": loc["geo_lat"],
            "longitude": loc["geo_long"],
        },
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": d, "opens": "09:00", "closes": "19:00"}
            for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        ],
        "priceRange": "$20 – $250",
        "currenciesAccepted": "USD",
        "paymentAccepted": "Cash, Credit Card",
        "sameAs": [inte["youtube_channel"], inte["booking_url"], inte["amazon_storefront"]],
        "hasMap": (
            "https://www.google.com/maps/search/?api=1&query="
            + loc["address"].replace(" ", "+")
        ),
        "areaServed": [
            {"@type": "City", "name": "Sarasota"},
            {"@type": "Neighborhood", "name": "University Park"},
            {"@type": "Neighborhood", "name": "Whitfield"},
            {"@type": "Neighborhood", "name": "The Meadows"},
        ],
    }, indent=2)

    keywords_csv = ", ".join(seo["target_keywords"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{seo['title']}</title>
  <meta name="description" content="{seo['meta_description']}">
  <meta name="keywords" content="{keywords_csv}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://{cfg['domain']}/">

  <!-- Open Graph -->
  <meta property="og:title" content="{seo['title']}">
  <meta property="og:description" content="{seo['meta_description']}">
  <meta property="og:url" content="https://{cfg['domain']}/">
  <meta property="og:type" content="website">
  <meta property="og:image" content="https://{cfg['domain']}/og-image.jpg">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{seo['title']}">
  <meta name="twitter:description" content="{seo['meta_description']}">

  <!-- AOS — Animate On Scroll -->
  <link rel="stylesheet" href="https://unpkg.com/aos@2.3.4/dist/aos.css">

  <style>
    /* ── Reset & base ──────────────────────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --black: #0a0a0a;
      --dark: #111111;
      --dark2: #1a1a1a;
      --gold: #c9a84c;
      --gold-light: #f0d080;
      --white: #ffffff;
      --gray: #888888;
      --light-gray: #cccccc;
      --font-display: 'Arial Black', 'Impact', sans-serif;
      --font-body: 'Arial', 'Helvetica Neue', sans-serif;
      --section-pad: 5rem 1.5rem;
      --radius: 8px;
      --transition: .3s ease;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{
      background: var(--black);
      color: var(--white);
      font-family: var(--font-body);
      line-height: 1.6;
      overflow-x: hidden;
    }}

    /* ── Navigation ────────────────────────────────────────────────── */
    nav {{
      position: fixed; top: 0; left: 0; width: 100%; z-index: 1000;
      background: rgba(10,10,10,.92); backdrop-filter: blur(8px);
      display: flex; align-items: center; justify-content: space-between;
      padding: .9rem 2rem; border-bottom: 1px solid rgba(201,168,76,.25);
    }}
    nav .nav-brand {{
      font-family: var(--font-display);
      font-size: 1.2rem; letter-spacing: .12em; color: var(--gold);
      text-transform: uppercase;
    }}
    nav ul {{ list-style: none; display: flex; gap: 2rem; }}
    nav ul a {{
      color: var(--light-gray); text-decoration: none; font-size: .9rem;
      letter-spacing: .06em; text-transform: uppercase;
      transition: color var(--transition);
    }}
    nav ul a:hover {{ color: var(--gold); }}
    .btn-book-nav {{
      background: var(--gold); color: var(--black);
      padding: .55rem 1.3rem; border-radius: var(--radius);
      font-weight: 700; font-size: .85rem; text-decoration: none;
      letter-spacing: .06em; text-transform: uppercase;
      transition: background var(--transition);
    }}
    .btn-book-nav:hover {{ background: var(--gold-light); }}

    /* ── Hero ──────────────────────────────────────────────────────── */
    #hero {{
      position: relative; min-height: 100vh;
      display: flex; align-items: center; justify-content: center;
      text-align: center; padding: 6rem 1.5rem 4rem;
      overflow: hidden;
      background: linear-gradient(160deg, #0a0a0a 0%, #1a1205 60%, #0a0a0a 100%);
    }}
    #bg-video {{
      position: absolute; top: 50%; left: 50%;
      transform: translate(-50%,-50%);
      min-width: 100%; min-height: 100%;
      width: auto; height: auto;
      object-fit: cover; z-index: 0; opacity: .35;
    }}
    .hero-overlay {{
      position: absolute; inset: 0; z-index: 1;
      background: linear-gradient(180deg,
        rgba(0,0,0,.55) 0%, rgba(0,0,0,.35) 50%, rgba(0,0,0,.8) 100%);
    }}
    .hero-content {{ position: relative; z-index: 2; max-width: 860px; margin: 0 auto; }}
    .hero-eyebrow {{
      display: inline-block; margin-bottom: 1rem;
      font-size: .8rem; letter-spacing: .18em; text-transform: uppercase;
      color: var(--gold); border: 1px solid var(--gold);
      padding: .3rem .9rem; border-radius: 2px;
    }}
    .hero-title {{
      font-family: var(--font-display);
      font-size: clamp(2.6rem, 8vw, 5.5rem);
      font-weight: 900; line-height: 1.05;
      text-transform: uppercase; letter-spacing: .04em;
      color: var(--white); margin-bottom: 1.25rem;
    }}
    .hero-title span {{ color: var(--gold); }}
    .hero-subtitle {{
      font-size: clamp(1rem, 2.5vw, 1.25rem);
      color: var(--light-gray); margin-bottom: 2.2rem; max-width: 580px; margin-inline: auto;
    }}
    .hero-cta-group {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }}
    .btn-primary {{
      background: var(--gold); color: var(--black);
      padding: .85rem 2.2rem; border-radius: var(--radius);
      font-weight: 700; font-size: 1rem; text-decoration: none;
      letter-spacing: .06em; text-transform: uppercase;
      transition: background var(--transition), transform var(--transition);
      display: inline-block;
    }}
    .btn-primary:hover {{ background: var(--gold-light); transform: translateY(-2px); }}
    .btn-outline {{
      background: transparent; color: var(--white);
      padding: .85rem 2.2rem; border-radius: var(--radius);
      border: 2px solid var(--white); font-weight: 600; font-size: 1rem;
      text-decoration: none; letter-spacing: .06em; text-transform: uppercase;
      transition: border-color var(--transition), color var(--transition);
      display: inline-block;
    }}
    .btn-outline:hover {{ border-color: var(--gold); color: var(--gold); }}
    .hero-address {{
      margin-top: 2rem; font-size: .9rem; color: var(--gray);
      letter-spacing: .04em;
    }}
    .hero-address a {{ color: var(--gold); text-decoration: none; }}

    /* ── Section shared ────────────────────────────────────────────── */
    section {{ padding: var(--section-pad); }}
    .section-label {{
      font-size: .78rem; letter-spacing: .2em; text-transform: uppercase;
      color: var(--gold); margin-bottom: .6rem;
    }}
    .section-title {{
      font-family: var(--font-display);
      font-size: clamp(1.8rem, 4vw, 2.8rem);
      text-transform: uppercase; margin-bottom: 1rem; color: var(--white);
    }}
    .section-divider {{
      width: 60px; height: 3px; background: var(--gold); margin-bottom: 2.5rem;
    }}
    .section-center {{ text-align: center; }}
    .section-center .section-divider {{ margin-inline: auto; }}

    /* ── Portfolio / Skills Cards ──────────────────────────────────── */
    #portfolio {{ background: var(--dark2); }}
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 1.5rem; margin-top: 1rem;
    }}
    .card {{
      background: var(--dark); border: 1px solid rgba(201,168,76,.15);
      border-radius: var(--radius); overflow: hidden;
      transition: border-color var(--transition), transform var(--transition);
    }}
    .card:hover {{ border-color: var(--gold); transform: translateY(-4px); }}
    .card-img {{
      width: 100%; aspect-ratio: 4/3; background: #1e1e1e;
      display: flex; align-items: center; justify-content: center;
      font-size: 3rem; color: var(--gold);
    }}
    .card-body {{ padding: 1.1rem; }}
    .card-title {{ font-weight: 700; font-size: 1rem; margin-bottom: .35rem; }}
    .card-desc {{ font-size: .85rem; color: var(--gray); }}

    /* ── Pricing ───────────────────────────────────────────────────── */
    #pricing {{ background: var(--black); }}
    .pricing-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 2rem; margin-top: 1rem;
    }}
    .pricing-category {{
      background: var(--dark2);
      border: 1px solid rgba(201,168,76,.2);
      border-radius: var(--radius); padding: 1.75rem;
    }}
    .pricing-category h3 {{
      font-family: var(--font-display);
      font-size: 1rem; text-transform: uppercase;
      letter-spacing: .1em; color: var(--gold);
      margin-bottom: 1.1rem; padding-bottom: .6rem;
      border-bottom: 1px solid rgba(201,168,76,.25);
    }}
    .price-table {{ width: 100%; border-collapse: collapse; }}
    .price-table tr {{ border-bottom: 1px solid rgba(255,255,255,.06); }}
    .price-table tr:last-child {{ border-bottom: none; }}
    .price-table td {{ padding: .6rem 0; font-size: .9rem; color: var(--light-gray); }}
    .price-table td.price {{
      text-align: right; font-weight: 700; color: var(--gold); white-space: nowrap;
    }}
    .book-cta-bar {{
      text-align: center; margin-top: 3rem;
    }}
    .book-cta-bar p {{ color: var(--gray); margin-bottom: 1.2rem; font-size: .95rem; }}

    /* ── YouTube Grid ──────────────────────────────────────────────── */
    #videos {{ background: var(--dark2); }}
    .yt-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem; margin-top: 1rem;
    }}
    @media (max-width: 900px) {{ .yt-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 500px) {{ .yt-grid {{ grid-template-columns: 1fr; }} }}
    .yt-card {{
      background: var(--dark); border: 1px solid rgba(201,168,76,.12);
      border-radius: var(--radius); overflow: hidden;
      transition: border-color var(--transition);
    }}
    .yt-card:hover {{ border-color: var(--gold); }}
    .yt-embed-wrapper {{
      position: relative; width: 100%; padding-top: 56.25%; /* 16:9 */
    }}
    .yt-embed-wrapper iframe {{
      position: absolute; inset: 0; width: 100%; height: 100%;
    }}
    .yt-channel-link {{
      text-align: center; margin-top: 2.5rem;
    }}
    .yt-channel-link a {{
      color: var(--gold); text-decoration: none; font-size: .95rem;
      border-bottom: 1px solid rgba(201,168,76,.4);
      transition: color var(--transition);
    }}
    .yt-channel-link a:hover {{ color: var(--gold-light); }}

    /* ── Booking ───────────────────────────────────────────────────── */
    #booking {{
      background: linear-gradient(135deg, #0d0d00 0%, #1a1205 50%, #0d0d00 100%);
      text-align: center; padding: 6rem 1.5rem;
    }}
    #booking .section-title {{ font-size: clamp(2rem, 5vw, 3.5rem); }}
    #booking p {{ color: var(--light-gray); max-width: 560px; margin: 0 auto 2.5rem; font-size: 1.05rem; }}

    /* ── Footer ────────────────────────────────────────────────────── */
    footer {{
      background: var(--dark2); border-top: 1px solid rgba(201,168,76,.2);
      padding: 3rem 1.5rem; text-align: center;
    }}
    footer .footer-brand {{
      font-family: var(--font-display); font-size: 1.3rem;
      color: var(--gold); text-transform: uppercase; letter-spacing: .12em;
      margin-bottom: .75rem;
    }}
    footer p {{ font-size: .85rem; color: var(--gray); line-height: 1.8; }}
    footer a {{ color: var(--gold); text-decoration: none; }}
    footer .footer-keywords {{
      font-size: .75rem; color: #444; margin-top: 1.5rem; max-width: 700px;
      margin-inline: auto; line-height: 2;
    }}
  </style>
</head>
<body>

<!-- ── Navigation ──────────────────────────────────────────────────────── -->
<nav>
  <div class="nav-brand">Jeff The Master Barber</div>
  <ul>
    <li><a href="#portfolio">Portfolio</a></li>
    <li><a href="#pricing">Pricing</a></li>
    <li><a href="#videos">Videos</a></li>
    <li><a href="#booking">Book</a></li>
    <li><a href="{inte['amazon_storefront']}" target="_blank" rel="noopener">Shop</a></li>
  </ul>
  <a href="{inte['booking_url']}" target="_blank" rel="noopener" class="btn-book-nav">Book Now</a>
</nav>

<!-- ── Hero ────────────────────────────────────────────────────────────── -->
<section id="hero">
  {video_section}
  <div class="hero-overlay"></div>
  <div class="hero-content" data-aos="fade-up" data-aos-duration="900">
    <div class="hero-eyebrow">Sarasota, FL · Precision Barbering</div>
    <h1 class="hero-title">
      Jeff The<br><span>Master</span> Barber
    </h1>
    <p class="hero-subtitle">
      Precision cuts. Flawless fades. VIP grooming experience.
      The best barber in Sarasota — now available for mobile house calls.
    </p>
    <div class="hero-cta-group">
      <a href="{inte['booking_url']}" target="_blank" rel="noopener" class="btn-primary">Book Your Appointment</a>
      <a href="#pricing" class="btn-outline">View Pricing</a>
    </div>
    <p class="hero-address">
      📍 <a href="https://maps.google.com/?q=7612+N+Lockwood+Ridge+Rd+Sarasota+FL+34243"
           target="_blank" rel="noopener">
        7612 N Lockwood Ridge Rd, Sarasota, FL 34243
      </a>
    </p>
  </div>
</section>

<!-- ── Portfolio ───────────────────────────────────────────────────────── -->
<section id="portfolio">
  <div class="section-center">
    <p class="section-label">The Work</p>
    <h2 class="section-title">Portfolio</h2>
    <div class="section-divider"></div>
  </div>
  <div class="cards-grid">
    <div class="card" data-aos="fade-up" data-aos-delay="0">
      <div class="card-img">✂️</div>
      <div class="card-body">
        <div class="card-title">Precision Fade</div>
        <div class="card-desc">Skin fade blended to perfection — clean lines, sharp edges.</div>
      </div>
    </div>
    <div class="card" data-aos="fade-up" data-aos-delay="80">
      <div class="card-img">🧔</div>
      <div class="card-body">
        <div class="card-title">Beard Sculpt</div>
        <div class="card-desc">Beard shaping, edge-up, and hot-towel finish.</div>
      </div>
    </div>
    <div class="card" data-aos="fade-up" data-aos-delay="160">
      <div class="card-img">👑</div>
      <div class="card-body">
        <div class="card-title">VIP Package</div>
        <div class="card-desc">Full wash, exfoliation, haircut, beard trim &amp; scalp massage.</div>
      </div>
    </div>
    <div class="card" data-aos="fade-up" data-aos-delay="240">
      <div class="card-img">🎨</div>
      <div class="card-body">
        <div class="card-title">Hair Design</div>
        <div class="card-desc">Custom hair art and specialty cuts — Pompadour, Mohawk &amp; more.</div>
      </div>
    </div>
    <div class="card" data-aos="fade-up" data-aos-delay="320">
      <div class="card-img">🚗</div>
      <div class="card-body">
        <div class="card-title">Mobile Service</div>
        <div class="card-desc">Jeff comes to you — house calls across Sarasota &amp; surrounding areas.</div>
      </div>
    </div>
    <div class="card" data-aos="fade-up" data-aos-delay="400">
      <div class="card-img">🎓</div>
      <div class="card-body">
        <div class="card-title">Kids &amp; Teens</div>
        <div class="card-desc">Patient, skilled cuts for the younger clients.</div>
      </div>
    </div>
  </div>
</section>

<!-- ── Pricing ─────────────────────────────────────────────────────────── -->
<section id="pricing">
  <div class="section-center">
    <p class="section-label">Transparent Rates</p>
    <h2 class="section-title">Pricing</h2>
    <div class="section-divider"></div>
  </div>
  <div class="pricing-grid">
    {pricing_html}
  </div>
  <div class="book-cta-bar" data-aos="fade-up">
    <p>All prices vary by complexity. Contact Jeff for a custom quote.</p>
    <a href="{inte['booking_url']}" target="_blank" rel="noopener" class="btn-primary">Book on Booksy</a>
  </div>
</section>

<!-- ── YouTube Videos ──────────────────────────────────────────────────── -->
<section id="videos">
  <div class="section-center">
    <p class="section-label">Watch The Work</p>
    <h2 class="section-title">Videos</h2>
    <div class="section-divider"></div>
  </div>
  <div class="yt-grid">
    {yt_grid_items}
  </div>
  <div class="yt-channel-link" data-aos="fade-up">
    <a href="{inte['youtube_channel']}" target="_blank" rel="noopener">
      ▶ View all videos on YouTube @JEFFREYELBARBEROMASTER
    </a>
  </div>
</section>

<!-- ── Amazon Storefront ──────────────────────────────────────────────────── -->
<section id="amazon-shop" style="background: var(--black); text-align: center; padding: var(--section-pad);">
  <div class="section-center">
    <p class="section-label">Shop My Products</p>
    <h2 class="section-title" data-aos="fade-up">Tools I Use &amp; Recommend</h2>
    <div class="section-divider" style="margin-inline: auto;"></div>
  </div>
  <p data-aos="fade-up" data-aos-delay="80" style="color: var(--light-gray); max-width: 560px; margin: 0 auto 2rem; font-size: 1rem;">
    Check out the exact clippers, guards, blades, and barbering tools I use every day — available on Amazon.
  </p>
  <div data-aos="fade-up" data-aos-delay="160">
    <a href="{inte['amazon_storefront']}" target="_blank" rel="noopener" class="btn-primary" style="font-size:1rem; padding:.85rem 2.2rem;">
      🛒 Visit My Amazon Storefront
    </a>
  </div>
</section>

<!-- ── Booking CTA ──────────────────────────────────────────────────────── -->
<section id="booking">
  <p class="section-label" data-aos="fade-up">Ready for a Fresh Cut?</p>
  <h2 class="section-title" data-aos="fade-up" data-aos-delay="80">Book Your Appointment</h2>
  <p data-aos="fade-up" data-aos-delay="160">
    Serving Sarasota, University Park, Whitfield, The Meadows, and surrounding areas.
    Mobile house calls available throughout Sarasota County.
  </p>
  <div data-aos="fade-up" data-aos-delay="240">
    <a href="{inte['booking_url']}" target="_blank" rel="noopener" class="btn-primary" style="font-size:1.1rem;padding:1rem 2.8rem;">
      Book Now on Booksy
    </a>
  </div>
</section>

<!-- ── Footer ──────────────────────────────────────────────────────────── -->
<footer>
  <div class="footer-brand">Jeff The Master Barber</div>
  <p>
    7612 N Lockwood Ridge Rd, Sarasota, FL 34243<br>
    <a href="{inte['booking_url']}" target="_blank" rel="noopener">Book on Booksy</a>
    &nbsp;·&nbsp;
    <a href="{inte['youtube_channel']}" target="_blank" rel="noopener">YouTube</a>
    &nbsp;·&nbsp;
    <a href="{inte['amazon_storefront']}" target="_blank" rel="noopener">Amazon Shop</a>
  </p>
  <p class="footer-keywords">
    Best Barber in Sarasota · Best Barber Near Me · Mobile Barber Sarasota ·
    Haircut Sarasota FL · Barbers in Sarasota · VIP Haircut Sarasota ·
    Beard Trim Sarasota · University Park Barber · Whitfield Barber ·
    The Meadows Barber · Best Mobile Barber Sarasota
  </p>
</footer>

<!-- ── LocalBusiness Schema Markup ─────────────────────────────────────── -->
<script type="application/ld+json">
{schema_json}
</script>

<!-- ── AOS Init ────────────────────────────────────────────────────────── -->
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<script>
  AOS.init({{
    duration: 700,
    easing: 'ease-out-cubic',
    once: true,
    offset: 80,
  }});
</script>
</body>
</html>"""

st.set_page_config(
    page_title="Sturdy Broccoli — Enterprise SEO Content Factory",
    page_icon="🥦",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Professional CMS styling
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* ─── Global typography & palette ───────────────────────────────────── */
:root {
  --primary: #1a3c6e;
  --primary-light: #2563eb;
  --accent: #f59e0b;
  --success: #059669;
  --bg-card: #f8fafc;
  --border: #e2e8f0;
  --text-muted: #64748b;
}
/* ─── App header ─────────────────────────────────────────────────────── */
header[data-testid="stHeader"] {
  background: linear-gradient(135deg, #0f2044 0%, #1a3c6e 100%);
}
/* ─── KPI / metric cards ─────────────────────────────────────────────── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin: 1.5rem 0;
}
.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 1.5rem;
  border: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
  text-align: center;
  transition: transform .15s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.1); }
.kpi-card .kpi-value { font-size: 2.4rem; font-weight: 800; color: var(--primary); line-height: 1; }
.kpi-card .kpi-label { font-size: .8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-top: .4rem; }
/* Colour variants */
.kpi-card.accent  .kpi-value { color: var(--accent); }
.kpi-card.success .kpi-value { color: var(--success); }
.kpi-card.info    .kpi-value { color: var(--primary-light); }
/* ─── Layout template cards ──────────────────────────────────────────── */
.layout-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin: 1rem 0 1.5rem;
}
.layout-card {
  background: #fff;
  border: 2px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s;
}
.layout-card:hover, .layout-card.selected {
  border-color: var(--primary-light);
  box-shadow: 0 0 0 3px rgba(37,99,235,.15);
}
.layout-card .layout-icon { font-size: 1.8rem; margin-bottom: .5rem; }
.layout-card .layout-name { font-weight: 700; font-size: .95rem; margin-bottom: .25rem; }
.layout-card .layout-desc { font-size: .8rem; color: var(--text-muted); }
/* ─── Activity feed ──────────────────────────────────────────────────── */
.activity-item {
  display: flex;
  gap: .75rem;
  align-items: flex-start;
  padding: .6rem 0;
  border-bottom: 1px solid var(--border);
  font-size: .875rem;
}
.activity-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--primary-light); margin-top: .3rem; flex-shrink: 0; }
/* ─── Cluster diagram ────────────────────────────────────────────────── */
.cluster-hub {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: #fff; border-radius: 12px; padding: 1rem 1.5rem;
  text-align: center; font-weight: 700; font-size: 1rem; margin-bottom: .5rem;
}
.cluster-spoke {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: .65rem 1rem; margin: .25rem 0; font-size: .875rem;
  display: flex; align-items: center; gap: .5rem;
}
/* ─── Section divider ────────────────────────────────────────────────── */
.section-title {
  font-size: 1.4rem; font-weight: 700; color: var(--primary);
  border-left: 4px solid var(--accent); padding-left: .75rem; margin: 1.5rem 0 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Initialise persistent database (stored in Streamlit session state so the
# same in-process instance is reused across reruns within a session).
# ---------------------------------------------------------------------------
if "db" not in st.session_state:
    st.session_state.db = Database()

db: Database = st.session_state.db

tab_dashboard, tab_builder, tab_prompt, tab_hub, tab_competitor, tab_multiformat, tab_template, tab_library, tab_staging, tab_validator, tab_agency, tab_editor, tab_wp, tab_ranking, tab_jeff = st.tabs([
    "🏠 Dashboard",
    "⚡ Page Builder",
    "📝 Prompt Generator",
    "🕸️ Hub & Spoke",
    "🔍 Competitor Analysis",
    "📢 Multi-Format",
    "🏗️ Landing Page Templates",
    "📚 Page Library",
    "🎭 Staging Review",
    "✅ Batch Validator",
    "💼 Agency Dashboard",
    "✏️ Content Editor",
    "🚀 WordPress Publisher",
    "📊 Ranking Tracker",
    "🪒 Jeff the Master Barber",
])

# ---------------------------------------------------------------------------
# Tab 0: Dashboard — Command Centre
# ---------------------------------------------------------------------------

with tab_dashboard:
    st.markdown(
        "<h1 style='color:#1a3c6e;margin-bottom:.25rem'>🥦 Sturdy Broccoli</h1>"
        "<p style='color:#64748b;font-size:1.05rem;margin-bottom:1.5rem'>"
        "Enterprise SEO Content Factory — generate, review, and deploy high-quality webpages at scale.</p>",
        unsafe_allow_html=True,
    )

    # KPI cards
    stats = db.get_dashboard_stats()
    _agency_dash = AgencyDashboard(db)
    agency_stats = _agency_dash.get_revenue_stats()
    avg_quality = stats.get("avg_quality_score", 0.0) or 0.0

    kpi_html = f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-value">{stats.get('total_pages', 0)}</div>
    <div class="kpi-label">Pages Generated</div>
  </div>
  <div class="kpi-card success">
    <div class="kpi-value">{stats.get('published_pages', 0)}</div>
    <div class="kpi-label">Live / Published</div>
  </div>
  <div class="kpi-card info">
    <div class="kpi-value">{len(_agency_dash.list_clients())}</div>
    <div class="kpi-label">Active Clients</div>
  </div>
  <div class="kpi-card accent">
    <div class="kpi-value">{avg_quality:.0f}</div>
    <div class="kpi-label">Avg Quality Score</div>
  </div>
</div>
"""
    st.markdown(kpi_html, unsafe_allow_html=True)

    col_activity, col_quick = st.columns([2, 1])

    with col_activity:
        st.markdown('<div class="section-title">📋 Recent Activity</div>', unsafe_allow_html=True)
        recent_pages = db.list_pages()[:8]
        if not recent_pages:
            st.info("No pages yet — use the **⚡ Page Builder** tab to generate your first enterprise webpage.")
        else:
            activity_html = '<div>'
            for page in recent_pages:
                status_icon = {"published": "🟢", "draft": "📝", "review": "🔍", "archived": "📦"}.get(
                    page.get("status", "draft"), "📄"
                )
                activity_html += (
                    f'<div class="activity-item">'
                    f'<div class="activity-dot"></div>'
                    f'<div><strong>{page.get("topic", "Untitled")}</strong> '
                    f'— {status_icon} {page.get("status", "draft")} '
                    f'<span style="color:#94a3b8;font-size:.8rem">({page.get("created_at", "")[:10]})</span></div>'
                    f'</div>'
                )
            activity_html += "</div>"
            st.markdown(activity_html, unsafe_allow_html=True)

    with col_quick:
        st.markdown('<div class="section-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
        st.markdown("**Start building:**")
        st.markdown("• [⚡ New Enterprise Page](#) → **Page Builder** tab")
        st.markdown("• [🕸️ New Content Cluster](#) → **Hub & Spoke** tab")
        st.markdown("• [📝 Generate Prompts](#) → **Prompt Generator** tab")
        st.markdown("• [🚀 Deploy to WordPress](#) → **WordPress Publisher** tab")
        st.divider()
        st.markdown("**Platform stats:**")
        st.write(f"📄 Draft: **{stats.get('draft_pages', 0)}** · 🔍 In Review: **{stats.get('review_pages', 0)}**")
        st.write(f"📦 Total Batches: **{agency_stats.get('draft_batches', 0) + agency_stats.get('staged_batches', 0) + agency_stats.get('approved_batches', 0) + agency_stats.get('deployed_batches', 0)}**")
        st.write(f"💰 Revenue Tracked: **${agency_stats.get('total_revenue', 0):,.0f}**")

    st.divider()

    # Platform overview
    st.markdown('<div class="section-title">🔧 Platform Modules</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**⚡ Page Builder**")
        st.caption("Generate enterprise HTML5 pages with 6 layout templates")
    with c2:
        st.markdown("**🕸️ Hub & Spoke**")
        st.caption("Build content clusters and batch-generate related pages")
    with c3:
        st.markdown("**🚀 WordPress**")
        st.caption("One-click deploy to any WordPress site with scheduling")
    with c4:
        st.markdown("**📊 Rankings**")
        st.caption("Track GSC & SEMrush rankings across all your clients")


# ---------------------------------------------------------------------------
# Tab 1: Page Builder — Enterprise HTML5 Generator (core feature)
# ---------------------------------------------------------------------------

with tab_builder:
    st.header("⚡ Enterprise Page Builder")
    st.caption(
        "Generate production-ready HTML5 enterprise webpages in one click. "
        "Select a layout, configure your content, and export or deploy directly to WordPress."
    )

    pb = HTML5PageBuilder()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        # -- Layout selector --------------------------------------------------
        st.markdown('<div class="section-title">1️⃣ Choose Layout Template</div>', unsafe_allow_html=True)

        layout_options = list(pb.LAYOUTS.keys())
        layout_labels = [f"{v['icon']} {v['label']}" for v in pb.LAYOUTS.values()]

        selected_layout = st.radio(
            "Layout:",
            layout_options,
            format_func=lambda k: f"{pb.LAYOUTS[k]['icon']} {pb.LAYOUTS[k]['label']}",
            horizontal=False,
            key="pb_layout",
        )

        if selected_layout:
            layout_info = pb.LAYOUTS[selected_layout]
            st.info(
                f"**{layout_info['icon']} {layout_info['label']}** — {layout_info['description']}\n\n"
                f"Best for: {', '.join(layout_info['best_for'])}"
            )

        st.markdown('<div class="section-title">2️⃣ Content Configuration</div>', unsafe_allow_html=True)

        pb_business = st.text_input("Business / Brand Name", placeholder="Acme SEO Agency", key="pb_business")
        pb_service = st.text_input("Service / Topic", placeholder="Local SEO Services", key="pb_service")
        pb_keyword = st.text_input("Primary Keyword", placeholder="local seo agency london", key="pb_keyword")
        pb_audience = st.text_input("Target Audience", placeholder="SMEs in London", key="pb_audience")

        pb_tone = st.selectbox(
            "Tone",
            ["Professional", "Conversational", "Technical", "Authority"],
            key="pb_tone",
        )

        pb_cta_text = st.text_input("CTA Button Text", value="Get a Free Consultation", key="pb_cta_text")
        pb_cta_url = st.text_input("CTA URL", placeholder="https://example.com/contact", key="pb_cta_url")
        pb_canonical = st.text_input("Canonical URL", placeholder="https://example.com/local-seo", key="pb_canonical")

        pb_color = st.selectbox(
            "Colour Scheme",
            list(pb._PALETTES.keys()),
            format_func=lambda k: k.replace("_", " ").title(),
            key="pb_color",
        )

        st.markdown("**Page Sections:**")
        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            sec_hero = st.checkbox("Hero", value=True, key="pb_sec_hero")
            sec_features = st.checkbox("Features Grid", value=True, key="pb_sec_features")
            sec_benefits = st.checkbox("Benefits / Stats", value=True, key="pb_sec_benefits")
        with col_sec2:
            sec_proof = st.checkbox("Social Proof", value=True, key="pb_sec_proof")
            sec_faq = st.checkbox("FAQ", value=True, key="pb_sec_faq")
            sec_cta = st.checkbox("CTA Section", value=True, key="pb_sec_cta")

        selected_sections = [
            s for s, checked in [
                ("hero", sec_hero), ("features", sec_features), ("benefits", sec_benefits),
                ("social_proof", sec_proof), ("faq", sec_faq), ("cta", sec_cta),
            ] if checked
        ]

    with col_right:
        st.markdown('<div class="section-title">3️⃣ Generate & Export</div>', unsafe_allow_html=True)

        if st.button("⚡ Generate Enterprise Page", type="primary", key="btn_generate_page"):
            if not pb_business or not pb_service:
                st.error("Business name and service/topic are required.")
            else:
                config = {
                    "layout": selected_layout,
                    "business_name": pb_business,
                    "service": pb_service,
                    "primary_keyword": pb_keyword or pb_service,
                    "target_audience": pb_audience or "businesses",
                    "tone": pb_tone,
                    "cta_text": pb_cta_text,
                    "cta_url": pb_cta_url or "#contact",
                    "canonical_url": pb_canonical or f"https://example.com/{pb_keyword.replace(' ', '-').lower() if pb_keyword else 'page'}",
                    "color_scheme": pb_color,
                    "sections": selected_sections,
                }
                try:
                    generated_html = pb.generate_page(config)
                    st.session_state["pb_generated_html"] = generated_html
                    st.session_state["pb_generated_config"] = config
                    st.success(
                        f"✅ Enterprise page generated! "
                        f"**{len(generated_html):,} characters** of production-ready HTML5."
                    )
                except Exception as exc:
                    st.error(f"Generation error: {exc}")

        generated = st.session_state.get("pb_generated_html")
        if generated:
            st.markdown("---")

            # Download button
            st.download_button(
                label="⬇️ Download HTML File",
                data=generated,
                file_name=f"{(pb_service or 'page').lower().replace(' ', '-')}.html",
                mime="text/html",
                key="btn_dl_html",
            )

            # Save to Page Library
            if st.button("💾 Save to Page Library", key="btn_save_to_library"):
                cfg = st.session_state.get("pb_generated_config", {})
                pid = db.create_page(
                    service_type="html5_page_builder",
                    topic=cfg.get("service", "Enterprise Page"),
                    primary_keyword=cfg.get("primary_keyword", ""),
                    page_type=cfg.get("layout", "landing_page"),
                )
                db.save_content_version(
                    pid,
                    content_html=generated,
                    content_markdown="",
                    quality_report={},
                )
                st.success(f"✅ Saved to Page Library (ID: {pid})")

            # Deploy to WordPress
            wp_pub = WordPressPublisher(db)
            wp_conns = wp_pub.list_connections()
            if wp_conns:
                st.markdown("---")
                conn_options = {
                    f"{c.get('site_name') or c['site_url']} (id={c['id']})": c["id"]
                    for c in wp_conns
                }
                sel_conn = st.selectbox(
                    "Deploy to WordPress site:",
                    list(conn_options.keys()),
                    key="pb_wp_conn",
                )
                if st.button("🚀 Deploy to WordPress", key="btn_deploy_to_wp"):
                    cfg = st.session_state.get("pb_generated_config", {})
                    result = wp_pub.publish_page(
                        page_id=0,
                        connection_id=conn_options[sel_conn],
                        title=cfg.get("service", "Enterprise Page"),
                        content=generated,
                        status="draft",
                    )
                    if result["success"]:
                        st.success(f"✅ Deployed! View at: {result.get('post_url', '—')}")
                    else:
                        st.error(f"Deploy failed: {result.get('message')}")
            else:
                st.info("💡 Add a WordPress connection in the **🚀 WordPress Publisher** tab to deploy pages.")

            # Live preview
            st.markdown("---")
            with st.expander("🖥️ Live Preview (iframe)", expanded=False):
                try:
                    import streamlit.components.v1 as components
                    components.html(generated, height=600, scrolling=True)
                except Exception:
                    st.code(generated[:3000] + "\n...", language="html")

            with st.expander("📄 View HTML Source"):
                st.code(generated, language="html")


# ---------------------------------------------------------------------------
# Tab 2: Prompt Generator (original functionality)
# ---------------------------------------------------------------------------

with tab_prompt:
    st.header("Prompt Generator")
    st.caption("Build system and chain-of-thought prompts for a single content page.")

    page_data_input = st.text_area(
        "Enter Page Data (JSON):",
        height=300,
        placeholder='{"topic": "...", "primary_keyword": "...", ...}',
        key="prompt_page_data",
    )

    dry_run = st.checkbox("Dry-run mode (show prompts only, no LLM call)", value=True, key="prompt_dry_run")

    if st.button("Generate Prompts", key="btn_generate_prompts"):
        if not page_data_input.strip():
            st.error("Please enter page data JSON before generating.")
        else:
            try:
                page_data = json.loads(page_data_input)
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")
            else:
                try:
                    builder = PromptBuilder()

                    if dry_run:
                        st.subheader("System Prompt")
                        system_prompt = builder.build_system_prompt(page_data)
                        st.code(system_prompt, language="markdown")

                        st.subheader("Chain-of-Thought Prompts")
                        cot_prompts = builder.build_chain_of_thought_prompts(page_data)
                        for stage, prompt in cot_prompts.items():
                            with st.expander(f"Stage: {stage}"):
                                st.code(prompt, language="markdown")
                    else:
                        st.info(
                            "Live generation requires an OpenAI API key. "
                            "Use the CLI for full generation: "
                            "`python generator.py generate --page-data <file> --openai-key <key>`"
                        )
                except ValueError as exc:
                    st.error(f"Page data validation error: {exc}")

# ---------------------------------------------------------------------------
# Tab 3: Hub & Spoke Content Cluster Builder
# ---------------------------------------------------------------------------

with tab_hub:
    st.header("🕸️ Hub & Spoke Content Cluster Builder")
    st.caption(
        "Build an entire content cluster: select a hub layout, auto-generate spoke topics, "
        "assign layout templates to each spoke, and batch-generate all pages with consistent branding."
    )

    _pb_hub = HTML5PageBuilder()

    col_hub_left, col_hub_right = st.columns([1, 1])

    with col_hub_left:
        hub_json_input = st.text_area(
            "Hub Page Data (JSON):",
            height=200,
            placeholder='{"topic": "LinkedIn Marketing", "primary_keyword": "...", ...}',
            key="hub_page_data",
        )
        hub_topic_hint = st.text_input(
            "Or load example:", value="", placeholder="e.g. local_seo, linkedin_marketing",
            key="hub_example_hint",
        )
        if hub_topic_hint:
            tm = TemplateManager()
            if hub_topic_hint in tm.list_service_types():
                rendered = tm.render_page_data(hub_topic_hint)
                st.info(f"Loaded template for: {hub_topic_hint}")
                st.json(rendered)

        st.markdown("**Hub Layout Template:**")
        hub_layout = st.selectbox(
            "Hub page layout:",
            list(_pb_hub.LAYOUTS.keys()),
            format_func=lambda k: f"{_pb_hub.LAYOUTS[k]['icon']} {_pb_hub.LAYOUTS[k]['label']}",
            key="hub_layout",
        )

        hub_business = st.text_input("Business / Brand Name", placeholder="Acme Agency", key="hub_business")
        hub_color = st.selectbox(
            "Brand Colour Scheme",
            list(_pb_hub._PALETTES.keys()),
            format_func=lambda k: k.replace("_", " ").title(),
            key="hub_color",
        )
        hub_cta_text = st.text_input("CTA Text", value="Get a Free Consultation", key="hub_cta_text")
        hub_cta_url = st.text_input("CTA URL", placeholder="https://example.com/contact", key="hub_cta_url")

    with col_hub_right:
        spoke_topics_input = st.text_area(
            "Spoke Topics (one per line):",
            height=150,
            placeholder="LinkedIn Algorithm 2024: How to Maximise Reach\nExecutive Ghostwriting on LinkedIn\n...",
            key="hub_spoke_topics",
        )
        guide_title_input = st.text_input(
            "Thought Leadership Guide Title (optional):",
            placeholder="Ultimate Guide to LinkedIn Marketing",
            key="hub_guide_title",
        )

        st.markdown("**Default Spoke Layout:**")
        spoke_layout = st.selectbox(
            "Spoke page layout:",
            list(_pb_hub.LAYOUTS.keys()),
            format_func=lambda k: f"{_pb_hub.LAYOUTS[k]['icon']} {_pb_hub.LAYOUTS[k]['label']}",
            index=list(_pb_hub.LAYOUTS.keys()).index("blog_article"),
            key="spoke_layout",
        )

    # -- Cluster batch generation -------------------------------------------
    st.divider()
    col_gen1, col_gen2 = st.columns(2)

    with col_gen1:
        if st.button("🔍 Preview Hub & Spoke Prompts", key="btn_hub_spoke"):
            if not hub_json_input.strip() or not spoke_topics_input.strip():
                st.error("Please provide both hub page data and spoke topics.")
            else:
                try:
                    hub_data = json.loads(hub_json_input)
                    spoke_topics = [t.strip() for t in spoke_topics_input.strip().splitlines() if t.strip()]
                    builder = PromptBuilder()

                    with st.expander("Hub Prompt", expanded=True):
                        st.code(builder.build_hub_prompt(hub_data), language="markdown")

                    st.subheader(f"Spoke Prompts ({len(spoke_topics)} spokes)")
                    spoke_prompts = builder.build_spoke_prompts(hub_data, spoke_topics)
                    for sp in spoke_prompts:
                        with st.expander(f"Spoke {sp['spoke_number']}: {sp['topic']}"):
                            st.code(sp["prompt"], language="markdown")

                    if guide_title_input:
                        with st.expander("Thought Leadership Guide Prompt"):
                            st.code(
                                builder.build_thought_leadership_prompt(hub_data, guide_title_input),
                                language="markdown",
                            )
                except json.JSONDecodeError as exc:
                    st.error(f"Invalid hub page data JSON: {exc}")
                except ValueError as exc:
                    st.error(f"Validation error: {exc}")

    with col_gen2:
        if st.button("⚡ Batch Generate HTML5 Cluster", key="btn_batch_gen_cluster", type="primary"):
            spoke_lines = [t.strip() for t in spoke_topics_input.strip().splitlines() if t.strip()]
            if not hub_business or not spoke_lines:
                st.error("Business name and at least one spoke topic are required.")
            else:
                hub_topic = ""
                hub_keyword = ""
                if hub_json_input.strip():
                    try:
                        hd = json.loads(hub_json_input)
                        hub_topic = hd.get("topic", "")
                        hub_keyword = hd.get("primary_keyword", "")
                    except json.JSONDecodeError:
                        pass
                hub_topic = hub_topic or (spoke_lines[0] if spoke_lines else "SEO Services")

                cluster_pages: list[dict] = []

                # Generate hub page
                hub_config = {
                    "layout": hub_layout,
                    "business_name": hub_business,
                    "service": hub_topic,
                    "primary_keyword": hub_keyword or hub_topic,
                    "target_audience": "businesses",
                    "tone": "Professional",
                    "color_scheme": hub_color,
                    "cta_text": hub_cta_text,
                    "cta_url": hub_cta_url or "#contact",
                    "sections": ["hero", "features", "benefits", "social_proof", "faq", "cta"],
                }
                try:
                    hub_html = _pb_hub.generate_page(hub_config)
                    cluster_pages.append({"type": "hub", "topic": hub_topic, "html": hub_html, "config": hub_config})
                except Exception as exc:
                    st.error(f"Hub generation failed: {exc}")

                # Generate spoke pages
                for spoke_topic in spoke_lines:
                    spoke_config = {
                        "layout": spoke_layout,
                        "business_name": hub_business,
                        "service": spoke_topic,
                        "primary_keyword": spoke_topic.lower(),
                        "target_audience": "businesses",
                        "tone": "Professional",
                        "color_scheme": hub_color,
                        "cta_text": hub_cta_text,
                        "cta_url": hub_cta_url or "#contact",
                        "sections": ["hero", "features", "benefits", "faq", "cta"],
                    }
                    try:
                        spoke_html = _pb_hub.generate_page(spoke_config)
                        cluster_pages.append({"type": "spoke", "topic": spoke_topic, "html": spoke_html, "config": spoke_config})
                    except Exception as exc:
                        st.warning(f"Spoke '{spoke_topic}' failed: {exc}")

                st.session_state["hub_cluster_pages"] = cluster_pages
                st.success(f"✅ Generated {len(cluster_pages)} pages in the cluster!")

    # -- Cluster visual diagram + results ------------------------------------
    cluster_pages = st.session_state.get("hub_cluster_pages", [])
    if cluster_pages:
        st.divider()
        st.markdown('<div class="section-title">🌐 Cluster Diagram</div>', unsafe_allow_html=True)

        hub_pages = [p for p in cluster_pages if p["type"] == "hub"]
        spoke_pages = [p for p in cluster_pages if p["type"] == "spoke"]

        hub_name = hub_pages[0]["topic"] if hub_pages else "Hub Page"
        diagram_html = f'<div class="cluster-hub">🏢 HUB: {hub_name}</div>'
        for i, sp in enumerate(spoke_pages, 1):
            diagram_html += f'<div class="cluster-spoke">↳ 📝 Spoke {i}: {sp["topic"]}</div>'
        st.markdown(diagram_html, unsafe_allow_html=True)

        st.divider()
        st.markdown('<div class="section-title">📦 Generated Pages</div>', unsafe_allow_html=True)
        for page in cluster_pages:
            icon = "🏢" if page["type"] == "hub" else "📝"
            with st.expander(f"{icon} {page['topic']} ({len(page['html']):,} chars)"):
                st.download_button(
                    f"⬇️ Download {page['topic']}.html",
                    data=page["html"],
                    file_name=f"{page['topic'].lower().replace(' ', '-')}.html",
                    mime="text/html",
                    key=f"dl_cluster_{page['topic']}",
                )
                if st.button(f"💾 Save to Library", key=f"save_cluster_{page['topic']}"):
                    pid = db.create_page(
                        service_type="hub_and_spoke",
                        topic=page["topic"],
                        primary_keyword=page["config"].get("primary_keyword", ""),
                        page_type=page["config"].get("layout", "landing_page"),
                    )
                    db.save_content_version(pid, content_html=page["html"], content_markdown="", quality_report={})
                    st.success(f"Saved to library (ID: {pid})")

        # Deploy entire cluster to WordPress
        wp_pub_cluster = WordPressPublisher(db)
        wp_conns_cluster = wp_pub_cluster.list_connections()
        if wp_conns_cluster:
            st.divider()
            conn_opts_cluster = {
                f"{c.get('site_name') or c['site_url']} (id={c['id']})": c["id"]
                for c in wp_conns_cluster
            }
            sel_conn_cluster = st.selectbox(
                "Deploy to WordPress site:",
                list(conn_opts_cluster.keys()),
                key="cluster_wp_conn",
            )
            cluster_start_date = st.date_input("Start date for staggered publishing:", key="cluster_start_date")
            if st.button("🚀 Deploy Entire Cluster to WordPress (Staggered)", key="btn_deploy_cluster", type="primary"):
                pages_payload = [
                    {"page_id": 0, "title": p["topic"], "content": p["html"]}
                    for p in cluster_pages
                ]
                results = wp_pub_cluster.batch_publish_staggered(
                    pages=pages_payload,
                    connection_id=conn_opts_cluster[sel_conn_cluster],
                    start_date=cluster_start_date.isoformat(),
                    interval_days=1,
                )
                for r in results:
                    if r["success"]:
                        st.success(f"✅ '{r.get('page_id')}' scheduled for {r.get('scheduled_date', '?')}")
                    else:
                        st.error(f"❌ Failed: {r.get('message')}")

    st.markdown("---")
    st.info(
        "💡 For full hub-and-spoke generation with LLM calls, use the CLI:\n\n"
        "```bash\n"
        "python generator.py hub-and-spoke \\\n"
        "  --config examples/hub_and_spoke_linkedin_marketing.json \\\n"
        "  --output-dir output/cluster/ \\\n"
        "  --openai-key $OPENAI_API_KEY\n"
        "```"
    )

# ---------------------------------------------------------------------------
# Tab 3: Competitor Analysis
# ---------------------------------------------------------------------------

with tab_competitor:
    st.header("Competitor Analysis")
    st.caption(
        "Analyse competitor pages to identify content gaps, differentiation opportunities, "
        "and recommended spoke topics."
    )

    service_topic_input = st.text_input(
        "Service Topic:", placeholder="e.g. Digital PR Agency", key="ca_service_topic"
    )

    st.subheader("Competitors")
    st.caption("Add competitor data. At minimum provide a name and any content you have.")

    num_competitors = st.number_input(
        "Number of competitors:", min_value=1, max_value=10, value=2, key="ca_num_competitors"
    )

    competitors: list[dict] = []
    for i in range(int(num_competitors)):
        with st.expander(f"Competitor {i + 1}", expanded=(i == 0)):
            c_name = st.text_input(f"Name", key=f"ca_name_{i}")
            c_url = st.text_input(f"URL (optional)", key=f"ca_url_{i}")
            c_content = st.text_area(
                f"Page content / excerpt (optional)",
                height=100,
                key=f"ca_content_{i}",
            )
            c_keywords = st.text_input(
                f"Keywords (comma-separated, optional)",
                key=f"ca_keywords_{i}",
            )
            if c_name:
                competitors.append({
                    "name": c_name,
                    "url": c_url,
                    "content": c_content,
                    "keywords": [k.strip() for k in c_keywords.split(",") if k.strip()],
                })

    our_strengths_input = st.text_area(
        "Your Strengths (one per line, optional):",
        height=100,
        placeholder="Data journalism approach\nJournalist relationships with 200+ outlets",
        key="ca_our_strengths",
    )

    if st.button("Run Competitor Analysis", key="btn_competitor_analysis"):
        if not service_topic_input or not competitors:
            st.error("Please provide a service topic and at least one competitor.")
        else:
            our_strengths = [
                s.strip()
                for s in our_strengths_input.strip().splitlines()
                if s.strip()
            ]
            analyzer = CompetitorAnalyzer()
            report = analyzer.analyze(service_topic_input, competitors, our_strengths)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Competitors Analysed", len(report.competitors))
                st.metric("Content Gaps Found", len(report.content_gaps))
            with col2:
                st.metric("Differentiation Opportunities", len(report.differentiation_opportunities))
                st.metric("Recommended Spoke Topics", len(report.recommended_spoke_topics))

            st.subheader("Analysis Summary")
            st.write(report.summary)

            with st.expander("Common Themes Across Competitors"):
                for t in report.common_themes:
                    st.markdown(f"- {t}")

            with st.expander("Content Gaps (What Competitors Don't Cover)"):
                for g in report.content_gaps:
                    st.markdown(f"- ✅ {g}")

            with st.expander("Differentiation Opportunities"):
                for o in report.differentiation_opportunities:
                    st.markdown(f"- 🎯 {o}")

            with st.expander("Unique Positioning Recommendations"):
                for p in report.unique_positioning:
                    st.markdown(f"- 💡 {p}")

            with st.expander("Recommended Spoke Topics"):
                for s in report.recommended_spoke_topics:
                    st.markdown(f"- 📝 {s}")

    st.markdown("---")
    st.info(
        "💡 For CLI usage:\n\n"
        "```bash\n"
        "python generator.py competitor-analysis \\\n"
        "  --config examples/competitor_analysis_digital_pr.json\n"
        "```"
    )

# ---------------------------------------------------------------------------
# Tab 4: Multi-Format Generator
# ---------------------------------------------------------------------------

with tab_multiformat:
    st.header("Multi-Format Content Generator")
    st.caption(
        "Generate platform-specific content (LinkedIn, Twitter, YouTube, Reddit, Email, HTML, Markdown) "
        "from a single content source."
    )

    source_json_input = st.text_area(
        "Content Source (JSON):",
        height=200,
        placeholder='{"topic": "...", "primary_keyword": "...", "key_points": [...], "cta": "..."}',
        key="mf_source",
    )

    available_formats = MultiFormatGenerator.supported_formats()
    selected_formats = st.multiselect(
        "Formats to generate:",
        options=available_formats,
        default=available_formats,
        key="mf_formats",
    )

    if st.button("Generate Multi-Format Content", key="btn_multi_format"):
        if not source_json_input.strip():
            st.error("Please enter a content source JSON.")
        elif not selected_formats:
            st.error("Please select at least one format.")
        else:
            try:
                source = json.loads(source_json_input)
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")
            else:
                gen = MultiFormatGenerator()
                try:
                    bundle = gen.generate_all(source, formats=selected_formats)
                    st.success(f"Generated {len(bundle.outputs)} format(s) for: {bundle.source_topic}")

                    for fmt_name, output in bundle.outputs.items():
                        with st.expander(f"📄 {fmt_name.upper()} — {output.platform_notes}"):
                            st.code(output.content, language="html" if fmt_name == "html" else "markdown")
                            if output.estimated_reach:
                                st.caption(f"Estimated reach: {output.estimated_reach}")
                except ValueError as exc:
                    st.error(f"Generation error: {exc}")

    st.markdown("---")
    st.info(
        "💡 For CLI usage:\n\n"
        "```bash\n"
        "python generator.py multi-format \\\n"
        "  --source examples/multi_platform_geo_ai_seo.json \\\n"
        "  --formats linkedin twitter email \\\n"
        "  --output-dir output/formats/\n"
        "```"
    )

# ---------------------------------------------------------------------------
# Tab 5: Landing Page Templates
# ---------------------------------------------------------------------------

with tab_template:
    st.header("Service Landing Page Templates")
    st.caption(
        "Browse and render landing page templates for CrowdCreate services. "
        "Each template includes H1/H2 structure, trust factors, testimonials, CTAs, and related services."
    )

    tm = TemplateManager()
    service_types = tm.list_service_types()

    selected_service = st.selectbox(
        "Select Service Type:",
        options=service_types,
        key="tmpl_service_type",
    )

    if selected_service:
        template = tm.get_template(selected_service)

        col_t1, col_t2 = st.columns([2, 1])

        with col_t1:
            st.subheader(template["h1"])
            st.write(template["service_description"])

            with st.expander("H2 Structure"):
                for i, h2 in enumerate(template["h2_sections"], 1):
                    st.markdown(f"{i}. **{h2}**")

            with st.expander("Trust Factors"):
                for tf in template["trust_factors"]:
                    st.markdown(f"✅ {tf}")

            with st.expander("Client Testimonials"):
                for t in template["testimonials"]:
                    st.markdown(f'> *"{t["quote"]}"*')
                    st.caption(f'— {t["author"]}')

        with col_t2:
            st.subheader("CTAs")
            st.button(template["cta"]["primary"], key=f"cta_primary_{selected_service}")
            st.button(template["cta"]["secondary"], key=f"cta_secondary_{selected_service}")

            st.subheader("Related Services")
            for svc in template["related_services"]:
                st.markdown(f"→ {svc}")

            st.subheader("Keywords")
            st.markdown(f"**Primary:** `{template['primary_keyword']}`")
            st.markdown("**Secondary:**")
            for kw in template["secondary_keywords"]:
                st.markdown(f"- `{kw}`")

        with st.expander("HTML Structure Preview"):
            html_preview = tm.render_html_structure(selected_service)
            st.code(html_preview, language="html")

        with st.expander("Page Data JSON (for Prompt Generator)"):
            page_data = tm.render_page_data(selected_service)
            st.json(page_data)

        # Quality score for the HTML preview
        with st.expander("📊 Quality Scores for This Template"):
            scorer = QualityScorer()
            result = scorer.score(html_preview, page_data)
            d = result.as_dict()

            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            col_s1.metric("🏛️ Authority", f"{d['authority']:.0f}/100")
            col_s2.metric("🧠 Semantic", f"{d['semantic']:.0f}/100")
            col_s3.metric("🏗️ Structure", f"{d['structure']:.0f}/100")
            col_s4.metric("🎯 Engagement", f"{d['engagement']:.0f}/100")
            col_s5.metric("✨ Uniqueness", f"{d['uniqueness']:.0f}/100")

            st.metric("⭐ Overall Quality Score", f"{d['overall']:.1f}/100")

            for dim, notes in d["explanations"].items():
                with st.expander(f"{dim.capitalize()} Recommendations"):
                    for note in notes:
                        st.write(f"• {note}")

        if st.button(
            f"💾 Save '{template['h1']}' to Page Library",
            key=f"save_template_{selected_service}",
        ):
            pid = db.create_page(
                service_type=selected_service,
                topic=template["h1"],
                primary_keyword=template["primary_keyword"],
                page_type="landing_page",
            )
            db.save_content_version(
                pid,
                content_html=html_preview,
                content_markdown="",
                quality_report=result.as_dict(),
            )
            db.save_quality_scores(pid, d)
            st.success(f"✅ Saved to Page Library (ID: {pid})")

# ---------------------------------------------------------------------------
# Tab 6: Page Library (database-backed)
# ---------------------------------------------------------------------------

with tab_library:
    st.header("📚 Page Library")
    st.caption(
        "Manage all generated pages stored in the persistent database. "
        "Filter, review quality scores, update status, and export content."
    )

    # Dashboard stats
    stats = db.get_dashboard_stats()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Pages", stats["total_pages"])
    c2.metric("Published", stats["published_pages"])
    c3.metric("Draft", stats["draft_pages"])
    c4.metric("In Review", stats["review_pages"])
    c5.metric("Total Words", f"{stats['total_words']:,}")
    c6.metric("Avg Quality", f"{stats['avg_quality_score']:.1f}")

    st.markdown("---")

    # Client management
    with st.expander("👥 Client Management"):
        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            cl_name = st.text_input("Client Name", key="lib_cl_name")
            cl_slug = st.text_input("Client Slug (URL-safe)", key="lib_cl_slug")
            cl_site = st.text_input("Website (optional)", key="lib_cl_site")
            if st.button("Add Client", key="lib_add_client"):
                if cl_name and cl_slug:
                    try:
                        cid = db.create_client(cl_name, cl_slug, cl_site)
                        st.success(f"Client added (ID: {cid})")
                    except Exception as exc:
                        st.error(f"Error: {exc}")
                else:
                    st.warning("Name and slug are required.")
        with col_cl2:
            clients = db.list_clients()
            if clients:
                st.subheader("Existing Clients")
                for c in clients:
                    st.write(f"**{c['name']}** (`{c['slug']}`)")
            else:
                st.info("No clients yet.")

    st.markdown("---")

    # Filter controls
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_status = st.selectbox(
            "Filter by Status",
            ["All", "draft", "review", "published", "archived"],
            key="lib_filter_status",
        )
    with col_f2:
        tm_lib = TemplateManager()
        filter_service = st.selectbox(
            "Filter by Service Type",
            ["All"] + tm_lib.list_service_types(),
            key="lib_filter_service",
        )
    with col_f3:
        clients_list = db.list_clients()
        client_options = {"All": None}
        for cl in clients_list:
            client_options[cl["name"]] = cl["id"]
        selected_client_name = st.selectbox(
            "Filter by Client",
            list(client_options.keys()),
            key="lib_filter_client",
        )

    pages = db.list_pages(
        status=filter_status if filter_status != "All" else None,
        service_type=filter_service if filter_service != "All" else None,
        client_id=client_options.get(selected_client_name),
    )

    if not pages:
        st.info("No pages found. Generate some using the Landing Page Templates tab.")
    else:
        st.write(f"**{len(pages)} page(s) found**")
        for page in pages:
            with st.expander(
                f"[{page['status'].upper()}] {page['topic']} — `{page['primary_keyword']}`",
                expanded=False,
            ):
                col_p1, col_p2, col_p3 = st.columns([2, 1, 1])

                with col_p1:
                    st.write(f"**Service:** {page['service_type']}")
                    st.write(f"**Created:** {page['created_at'][:10]}")
                    st.write(f"**Updated:** {page['updated_at'][:10]}")

                with col_p2:
                    quality = db.get_latest_quality_scores(page["id"])
                    if quality:
                        st.metric("Overall Quality", f"{quality['overall']:.1f}")
                        st.metric("Authority", f"{quality['authority']:.1f}")
                        st.metric("Structure", f"{quality['structure']:.1f}")
                    else:
                        st.info("No quality scores yet.")

                with col_p3:
                    new_status = st.selectbox(
                        "Status",
                        ["draft", "review", "published", "archived"],
                        index=["draft", "review", "published", "archived"].index(
                            page["status"]
                        ),
                        key=f"lib_status_{page['id']}",
                    )
                    if st.button("Update Status", key=f"lib_update_{page['id']}"):
                        db.update_page_status(page["id"], new_status)
                        st.success("Status updated.")
                        st.rerun()
                    if st.button(
                        "🗑️ Delete", key=f"lib_delete_{page['id']}", type="secondary"
                    ):
                        db.delete_page(page["id"])
                        st.warning("Page deleted.")
                        st.rerun()

                # Show latest content version
                version = db.get_latest_version(page["id"])
                if version:
                    st.write(f"**Version {version['version']}** · {version['word_count']} words")
                    with st.expander("View HTML"):
                        st.code(version["content_html"], language="html")
                    if version["content_markdown"]:
                        with st.expander("View Markdown"):
                            st.code(version["content_markdown"], language="markdown")

    # Bulk export section
    st.markdown("---")
    st.subheader("📦 Bulk Export")
    if pages:
        export_format = st.radio(
            "Export format", ["JSON", "HTML files summary"], horizontal=True, key="lib_export_fmt"
        )
        if st.button("Export All Filtered Pages", key="lib_export"):
            if export_format == "JSON":
                export_data = []
                for page in pages:
                    entry = dict(page)
                    version = db.get_latest_version(page["id"])
                    if version:
                        entry["latest_version"] = version
                    scores = db.get_latest_quality_scores(page["id"])
                    if scores:
                        entry["quality_scores"] = scores
                    export_data.append(entry)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json.dumps(export_data, indent=2, default=_json_default),
                    file_name="page_library_export.json",
                    mime="application/json",
                )
            else:
                html_parts: list[str] = [
                    "<html><body>",
                    "<h1>Page Library Export</h1>",
                ]
                for page in pages:
                    version = db.get_latest_version(page["id"])
                    html_content = version["content_html"] if version else ""
                    html_parts.append(f"<section><h2>{page['topic']}</h2>")
                    html_parts.append(html_content)
                    html_parts.append("</section><hr/>")
                html_parts.append("</body></html>")
                st.download_button(
                    label="⬇️ Download HTML",
                    data="\n".join(html_parts),
                    file_name="page_library_export.html",
                    mime="text/html",
                )

# ---------------------------------------------------------------------------
# Tab 7: Staging Review — Client approval workflow
# ---------------------------------------------------------------------------

with tab_staging:
    st.header("🎭 Staging Review")
    st.caption(
        "Review generated pages before deployment. Approve or reject pages, "
        "add client feedback, and track revision history."
    )

    if "staging_env" not in st.session_state:
        st.session_state.staging_env = StagingEnvironment(db)
        st.session_state.staging_review_mgr = StagingReviewManager(db)

    staging_env: StagingEnvironment = st.session_state.staging_env
    staging_review_mgr: StagingReviewManager = st.session_state.staging_review_mgr

    # -- Batch selector -------------------------------------------------------
    batches = staging_review_mgr.list_batches()
    if not batches:
        st.info("No staging batches found. Create a batch first via the Hub & Spoke tab.")
    else:
        batch_options = {f"{b['name']} (id:{b['id']})": b["id"] for b in batches}
        selected_label = st.selectbox("Select Batch", list(batch_options.keys()))
        selected_batch_id = batch_options[selected_label]

        gallery = staging_env.get_batch_gallery(selected_batch_id)
        batch_meta = gallery["batch"]
        pages = gallery["pages"]

        if batch_meta:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Pages", batch_meta.get("total_pages", len(pages)))
            col2.metric("Approved", batch_meta.get("pages_approved", 0))
            col3.metric("Draft", batch_meta.get("pages_draft", 0))

        st.divider()

        # -- Status filter ----------------------------------------------------
        status_filter = st.radio(
            "Filter by Status",
            ["All", "draft", "approved", "needs_revision", "rejected", "deployed"],
            horizontal=True,
        )
        filtered_pages = (
            pages
            if status_filter == "All"
            else [p for p in pages if p.get("status") == status_filter]
        )

        # -- Page gallery -------------------------------------------------
        if not filtered_pages:
            st.info(f"No pages with status '{status_filter}'.")
        else:
            # Bulk action controls
            all_ids = [p["id"] for p in filtered_pages if p.get("id")]
            st.write(f"**{len(filtered_pages)} page(s) shown**")
            col_a, col_r, _ = st.columns([1, 1, 4])
            if col_a.button("✅ Approve All Visible"):
                count = staging_env.bulk_approve(all_ids, reviewer="manager")
                st.success(f"Approved {count} pages.")
                st.rerun()
            if col_r.button("❌ Reject All Visible"):
                count = staging_env.bulk_reject(all_ids, reviewer="manager")
                st.warning(f"Rejected {count} pages.")
                st.rerun()

            for page in filtered_pages:
                with st.expander(
                    f"📄 {page.get('title', 'Untitled')} — {page.get('status', '?')}"
                ):
                    st.write(f"**Slug:** `{page.get('slug')}`")
                    st.write(f"**Keyword:** {page.get('primary_keyword', '—')}")
                    st.write(f"**Word Count:** {page.get('word_count', 0)}")
                    st.write(f"**Template:** {page.get('assigned_template', '—')}")
                    if page.get("meta_description"):
                        st.write(f"**Meta:** {page['meta_description']}")

                    # Individual approve/reject
                    c1, c2 = st.columns(2)
                    pid = page.get("id")
                    if pid:
                        if c1.button("✅ Approve", key=f"approve_{pid}"):
                            staging_env.bulk_approve([pid], reviewer="manager")
                            st.rerun()
                        if c2.button("❌ Reject", key=f"reject_{pid}"):
                            staging_env.bulk_reject([pid], reviewer="manager")
                            st.rerun()

                        # Comment box
                        comment = st.text_input(
                            "Add comment", key=f"comment_{pid}", placeholder="Enter feedback…"
                        )
                        if st.button("💬 Save Comment", key=f"save_comment_{pid}") and comment:
                            staging_env.add_page_comment(pid, comment, reviewer="client")
                            st.success("Comment saved.")

        st.divider()

        # -- Deployment readiness --------------------------------------------
        readiness = staging_env.get_deploy_readiness(selected_batch_id)
        if readiness["ready"]:
            st.success(
                f"✅ All {readiness['approved_count']} pages approved — "
                "ready for deployment!"
            )
        else:
            st.warning(
                f"⚠️ {readiness['approved_count']}/{readiness['total_count']} "
                f"pages approved. {len(readiness['blocked_pages'])} page(s) blocked."
            )


# ---------------------------------------------------------------------------
# Tab 8: Batch Validator — Hub-and-Spoke structure checker
# ---------------------------------------------------------------------------

with tab_validator:
    st.header("✅ Batch Validator")
    st.caption(
        "Validate your hub-and-spoke SILO structure before deployment. "
        "Checks internal links, keyword density, schema markup, and orphaned pages."
    )

    if "batch_validator" not in st.session_state:
        st.session_state.batch_validator = BatchValidator()
        st.session_state.validator_review_mgr = StagingReviewManager(db)

    validator: BatchValidator = st.session_state.batch_validator
    val_review_mgr: StagingReviewManager = st.session_state.validator_review_mgr

    val_batches = val_review_mgr.list_batches()
    if not val_batches:
        st.info("No batches found. Generate pages first.")
    else:
        val_batch_options = {
            f"{b['name']} (id:{b['id']})": b["id"] for b in val_batches
        }
        val_selected_label = st.selectbox(
            "Select Batch to Validate", list(val_batch_options.keys()), key="val_batch"
        )
        val_batch_id = val_batch_options[val_selected_label]

        hub_slug_input = st.text_input(
            "Hub Page Slug (leave blank for auto-detect)",
            placeholder="e.g. postgresql-optimisation",
        )

        if st.button("🔍 Run Validation"):
            val_pages = val_review_mgr.get_batch_pages(val_batch_id)

            # Convert content_pages format to batch_validator format
            normalised = []
            for p in val_pages:
                normalised.append(
                    {
                        "slug": p.get("slug"),
                        "title": p.get("title"),
                        "h1_content": p.get("h1_content"),
                        "primary_keyword": p.get("primary_keyword", ""),
                        "content_markdown": p.get("content_markdown", ""),
                        "internal_links": p.get("internal_links") or [],
                        "schema_json_ld": None,
                        "hub_page_id": p.get("hub_page_id"),
                        "is_hub": p.get("hub_page_id") is None,
                    }
                )

            result = validator.validate(
                normalised,
                hub_slug=hub_slug_input.strip() or None,
            )

            # Display result
            if result.valid:
                st.success("✅ Hub-and-Spoke structure is valid!")
            else:
                st.error("❌ Validation failed — see issues below.")

            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Spokes", result.spoke_count)
            col_b.metric(
                "Internal Links",
                f"{result.valid_internal_links}/{result.total_internal_links}",
            )
            col_c.metric("Keyword Density", f"{result.keyword_density:.1f}%")
            col_d.metric("Schema Valid", "✅" if result.schema_valid else "❌")

            st.subheader("Validation Report")
            st.code(result.to_report(), language="text")

            if result.orphaned_pages:
                st.warning(f"Orphaned pages: {', '.join(result.orphaned_pages)}")

            if result.issues:
                st.subheader(f"Issues ({len(result.issues)})")
                for issue in result.issues:
                    icon = "❌" if issue.severity == "error" else "⚠️"
                    page_ref = f"`{issue.page_slug}` — " if issue.page_slug else ""
                    st.write(f"{icon} {page_ref}{issue.message}")


# ---------------------------------------------------------------------------
# Tab 9: Agency Dashboard — Client pipeline + revenue tracking
# ---------------------------------------------------------------------------

with tab_agency:
    st.header("💼 Agency Dashboard")
    st.caption(
        "Track your client pipeline, batch statuses, revenue, "
        "and deployment history."
    )

    if "agency_dashboard" not in st.session_state:
        st.session_state.agency_dashboard = AgencyDashboard(db)

    agency: AgencyDashboard = st.session_state.agency_dashboard

    # -- Revenue KPIs ---------------------------------------------------------
    stats = agency.get_revenue_stats()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💰 Total Revenue", f"${stats['total_revenue']:,.0f}")
    k2.metric("📝 Draft", stats["draft_batches"])
    k3.metric("🎭 Staged", stats["staged_batches"])
    k4.metric("✅ Approved", stats["approved_batches"])
    k5.metric("🚀 Deployed", stats["deployed_batches"])

    st.divider()

    # -- Add new client -------------------------------------------------------
    with st.expander("➕ Add New Client"):
        with st.form("add_client_form"):
            c_name = st.text_input("Client Name", placeholder="Acme Corp")
            c_slug = st.text_input("Slug", placeholder="acme-corp")
            c_industry = st.text_input("Industry", placeholder="SaaS")
            c_email = st.text_input("Email", placeholder="contact@acme.com")
            c_website = st.text_input("Website", placeholder="https://acme.com")
            c_value = st.number_input(
                "Contract Value ($)", min_value=0.0, step=500.0, value=2000.0
            )
            if st.form_submit_button("Save Client"):
                if c_name and c_slug:
                    try:
                        agency.create_client(
                            name=c_name,
                            slug=c_slug,
                            industry=c_industry,
                            email=c_email,
                            website=c_website,
                            contract_value=c_value,
                        )
                        st.success(f"Client '{c_name}' created.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error: {exc}")
                else:
                    st.warning("Name and slug are required.")

    # -- Add new batch --------------------------------------------------------
    with st.expander("➕ Create New Staging Batch"):
        with st.form("add_batch_form"):
            b_name = st.text_input("Batch Name", placeholder="Q2 Campaign — Landing Pages")
            b_client = st.text_input("Client Name", placeholder="Acme Corp")
            b_pages = st.number_input("Total Pages", min_value=1, value=10, step=1)
            b_price = st.number_input(
                "Price Paid ($)", min_value=0.0, step=500.0, value=3000.0
            )
            if st.form_submit_button("Create Batch"):
                if b_name:
                    bid = agency.create_staging_batch(
                        batch_name=b_name,
                        client_name=b_client,
                        total_pages=int(b_pages),
                        price_paid=b_price,
                    )
                    st.success(f"Batch '{b_name}' created (id: {bid}).")
                    st.rerun()

    st.divider()

    # -- Pipeline view --------------------------------------------------------
    st.subheader("📊 Batch Pipeline")
    pipeline = agency.get_pipeline_summary()
    if not pipeline:
        st.info("No batches yet. Create one above.")
    else:
        for batch in pipeline:
            status_icon = {
                "draft": "📝",
                "staged": "🎭",
                "approved": "✅",
                "deployed": "🚀",
            }.get(batch.get("status", "draft"), "📄")

            with st.expander(
                f"{status_icon} {batch.get('batch_name')} — "
                f"{batch.get('client_name', '—')} | "
                f"${batch.get('price_paid', 0):,.0f}"
            ):
                col_s, col_p, col_r = st.columns(3)
                col_s.write(f"**Status:** {batch.get('status')}")
                col_p.write(f"**Pages:** {batch.get('total_pages', 0)}")
                col_r.write(f"**Reviews:** {batch.get('review_count', 0)}")

                if batch.get("deployed_url"):
                    st.write(f"**Live URL:** {batch['deployed_url']}")

                # Status advancement
                current = batch.get("status", "draft")
                next_status_map = {
                    "draft": "staged",
                    "staged": "approved",
                    "approved": "deployed",
                }
                next_status = next_status_map.get(current)
                if next_status:
                    deploy_url = ""
                    if next_status == "deployed":
                        deploy_url = st.text_input(
                            "Deployed URL",
                            key=f"deploy_url_{batch['id']}",
                            placeholder="https://client-site.com",
                        )
                    if st.button(
                        f"Advance to {next_status.upper()} →",
                        key=f"advance_{batch['id']}",
                    ):
                        agency.advance_batch_status(
                            batch["id"], next_status, deployed_url=deploy_url
                        )
                        if next_status == "deployed":
                            agency.record_deployment(
                                batch_id=batch["id"],
                                deployed_by="admin",
                                deployed_url=deploy_url,
                            )
                        st.success(f"Batch advanced to '{next_status}'.")
                        st.rerun()

                # Client comments
                new_comment = st.text_input(
                    "Add Client Comment",
                    key=f"batch_comment_{batch['id']}",
                    placeholder="Client feedback…",
                )
                comment_status = st.radio(
                    "Comment Status",
                    ["pending", "approved", "rejected"],
                    horizontal=True,
                    key=f"comment_status_{batch['id']}",
                )
                if (
                    st.button("💬 Save Comment", key=f"save_batch_comment_{batch['id']}")
                    and new_comment
                ):
                    agency.add_client_review(
                        batch["id"], new_comment, status=comment_status
                    )
                    st.success("Comment saved.")

    st.divider()

    # -- Client list ----------------------------------------------------------
    st.subheader("👥 Clients")
    clients = agency.list_clients()
    if not clients:
        st.info("No clients yet. Add one above.")
    else:
        for client in clients:
            st.write(
                f"**{client['name']}** — {client.get('industry', '—')} | "
                f"${client.get('contract_value', 0):,.0f} | "
                f"{client.get('email', '—')} | {client.get('status', 'active')}"
            )

# ===========================================================================
# Tab: Content Editor
# ===========================================================================

with tab_editor:
    st.header("✏️ Content Editor")
    st.caption("Edit and refine page content with real-time quality scoring, SEO preview, and version history.")

    editor = ContentEditor(db)

    # -- Page selector --------------------------------------------------------
    pages = db.list_pages()
    if not pages:
        st.info("No pages in the library yet. Create some in the Landing Page Templates tab.")
    else:
        page_options = {f"[{p['id']}] {p['topic']} ({p.get('primary_keyword','')})": p["id"] for p in pages}
        selected_page_label = st.selectbox("Select a page to edit:", list(page_options.keys()), key="editor_page_select")
        selected_page_id = page_options[selected_page_label]
        selected_page = db.get_page(selected_page_id)

        st.divider()

        # Split pane: editor left, quality score right
        col_editor, col_quality = st.columns([2, 1])

        with col_editor:
            st.subheader("📝 Edit Content")

            latest = editor.get_latest_version(selected_page_id)
            existing_content = latest["content_markdown"] if latest else ""

            new_title = st.text_input(
                "Page Title",
                value=selected_page.get("topic", "") if selected_page else "",
                key="editor_title",
            )
            new_h1 = st.text_input(
                "H1 Heading",
                value=selected_page.get("topic", "") if selected_page else "",
                key="editor_h1",
            )
            new_meta = st.text_area(
                "Meta Description",
                value="",
                height=80,
                key="editor_meta",
                placeholder="150-160 characters for best results",
            )
            new_content = st.text_area(
                "Content (Markdown)",
                value=existing_content,
                height=400,
                key="editor_content",
            )
            version_notes = st.text_input(
                "Version Notes (what changed?)",
                placeholder="e.g. Fixed typos, added statistics",
                key="editor_version_notes",
            )
            edited_by = st.text_input("Your name / initials", key="editor_edited_by")

            save_col, kw_col = st.columns(2)
            with save_col:
                if st.button("💾 Save Version", key="btn_save_version"):
                    if not new_content.strip():
                        st.error("Content cannot be empty.")
                    else:
                        result = editor.save_edit(
                            selected_page_id,
                            content_markdown=new_content,
                            version_notes=version_notes,
                            edited_by=edited_by,
                        )
                        st.success(result["message"])
                        st.metric("Word Count", result["word_count"])

            with kw_col:
                if new_content.strip():
                    primary_kw = selected_page.get("primary_keyword", "") if selected_page else ""
                    if primary_kw:
                        density = editor.keyword_density(new_content, primary_kw)
                        color = "green" if 1.0 <= density <= 2.5 else "orange"
                        st.markdown(
                            f"**Keyword density** for *{primary_kw}*: "
                            f"<span style='color:{color};font-weight:bold'>{density:.2f}%</span> "
                            f"(target: 1.0–2.5%)",
                            unsafe_allow_html=True,
                        )

        with col_quality:
            st.subheader("📊 Quality Score")
            if new_content.strip():
                live_scores = editor.score_content(
                    new_content,
                    {"primary_keyword": selected_page.get("primary_keyword", "")} if selected_page else {},
                )
                overall = live_scores.get("overall", 0)
                score_color = "🟢" if overall >= 75 else "🟡" if overall >= 50 else "🔴"
                st.metric("Overall", f"{score_color} {overall:.1f} / 100")
                for dim in ("authority", "semantic", "structure", "engagement", "uniqueness"):
                    st.metric(dim.capitalize(), f"{live_scores.get(dim, 0):.1f}")
            else:
                st.info("Start typing to see live quality scores.")

            st.divider()
            st.subheader("🔍 SEO Preview")
            if new_title or new_meta:
                preview = editor.build_seo_preview(new_title, new_meta)
                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff">
                      <p style="color:#1a0dab;font-size:18px;margin:0">{preview['display_title']}</p>
                      <p style="color:#006621;font-size:13px;margin:2px 0">{preview['display_url']}</p>
                      <p style="color:#545454;font-size:14px;margin:4px 0">{preview['display_description']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                t_ok = "✅" if preview["title_ok"] else "⚠️"
                d_ok = "✅" if preview["desc_ok"] else "⚠️"
                st.caption(
                    f"{t_ok} Title: {preview['title_length']} chars  "
                    f"{d_ok} Meta: {preview['desc_length']} chars"
                )

        st.divider()

        # Version history
        st.subheader("🕐 Version History")
        versions = editor.list_versions(selected_page_id)
        if not versions:
            st.info("No saved versions yet.")
        else:
            for v in reversed(versions):
                with st.expander(
                    f"v{v['version']} — {v['word_count']} words — "
                    f"{v.get('edited_by') or 'unknown'} — {v.get('edited_at', v['created_at'])[:10]}"
                ):
                    st.markdown(f"**Notes:** {v.get('version_notes') or '—'}")
                    st.text_area("Content", value=v["content_markdown"], height=200, disabled=True,
                                 key=f"ver_content_{v['id']}")

            # Side-by-side comparison
            if len(versions) >= 2:
                st.subheader("🔄 Compare Versions")
                v_nums = [v["version"] for v in versions]
                c1, c2 = st.columns(2)
                va = c1.selectbox("Version A", v_nums, index=0, key="compare_va")
                vb = c2.selectbox("Version B", v_nums, index=len(v_nums) - 1, key="compare_vb")
                if st.button("Compare", key="btn_compare"):
                    if va == vb:
                        st.warning("Select two different versions to compare.")
                    else:
                        comp = editor.compare_versions(selected_page_id, va, vb)
                        st.metric("Word count delta", comp["word_count_delta"],
                                  delta=comp["word_count_delta"])
                        if comp["diff"]:
                            st.code(comp["diff"], language="diff")
                        else:
                            st.info("No textual differences found.")


# ===========================================================================
# Tab: WordPress Publisher
# ===========================================================================

with tab_wp:
    st.header("🚀 WordPress Publisher")
    st.caption("Connect WordPress sites and publish pages with one click. Test connections, manage categories, and schedule publishing.")

    wp_publisher = WordPressPublisher(db)

    # -- Connection management ------------------------------------------------
    st.subheader("🔌 WordPress Connections")

    with st.expander("➕ Add New WordPress Site", expanded=False):
        wp_url = st.text_input("Site URL (e.g. https://yoursite.com)", key="wp_site_url")
        wp_name = st.text_input("Site Name (label)", key="wp_site_name")
        wp_user = st.text_input("API Username", key="wp_api_user")
        wp_pass = st.text_input("Application Password", type="password", key="wp_api_pass")

        clients_for_wp = db.list_clients()
        wp_client_options = {"— None —": None}
        wp_client_options.update({c["name"]: c["id"] for c in clients_for_wp})
        wp_client_sel = st.selectbox("Associate with client (optional)", list(wp_client_options.keys()), key="wp_client_sel")
        wp_client_id = wp_client_options[wp_client_sel]

        if st.button("Save Connection", key="btn_save_wp_conn"):
            if not wp_url or not wp_user or not wp_pass:
                st.error("Site URL, username, and password are required.")
            else:
                conn_id = wp_publisher.add_connection(
                    site_url=wp_url,
                    api_username=wp_user,
                    api_password=wp_pass,
                    site_name=wp_name or wp_url,
                    client_id=wp_client_id,
                )
                st.success(f"Connection saved (id={conn_id}). Credentials stored securely.")

    connections = wp_publisher.list_connections()
    if not connections:
        st.info("No WordPress connections yet. Add one above.")
    else:
        st.write(f"**{len(connections)} connection(s) configured:**")
        for conn in connections:
            col_a, col_b, col_c, col_d = st.columns([3, 2, 1, 1])
            col_a.markdown(f"🌐 **{conn.get('site_name') or conn['site_url']}** — `{conn['site_url']}`")
            col_b.caption(f"User: {conn.get('api_username', '—')}  |  id: {conn['id']}")
            if col_c.button("🔍 Test", key=f"test_wp_{conn['id']}", help="Test connection"):
                result = wp_publisher.test_connection(conn["id"])
                if result["success"]:
                    st.success(f"✅ Connection OK: {result.get('message')}")
                else:
                    st.error(f"❌ {result.get('message')}")
            if col_d.button("🗑️", key=f"del_wp_{conn['id']}", help="Delete connection"):
                wp_publisher.remove_connection(conn["id"])
                st.rerun()

    st.divider()

    # -- Category / Tag management -------------------------------------------
    st.subheader("🏷️ Categories & Tags")
    if connections:
        cat_conn_options = {
            f"{c.get('site_name') or c['site_url']} (id={c['id']})": c["id"]
            for c in connections
        }
        cat_conn_sel = st.selectbox("WordPress site:", list(cat_conn_options.keys()), key="wp_cat_conn")
        cat_conn_id = cat_conn_options[cat_conn_sel]

        col_cat, col_tag = st.columns(2)
        with col_cat:
            if st.button("📋 Fetch Categories", key="btn_fetch_cats"):
                cats = wp_publisher.get_categories(cat_conn_id)
                if cats:
                    st.session_state[f"wp_cats_{cat_conn_id}"] = cats
                    st.success(f"Found {len(cats)} categories.")
                else:
                    st.warning("No categories found or connection failed.")
            cached_cats = st.session_state.get(f"wp_cats_{cat_conn_id}", [])
            if cached_cats:
                for cat in cached_cats[:20]:
                    st.write(f"📂 **{cat['name']}** (id={cat['id']}, count={cat['count']})")
        with col_tag:
            if st.button("🔖 Fetch Tags", key="btn_fetch_tags"):
                tags = wp_publisher.get_tags(cat_conn_id)
                if tags:
                    st.session_state[f"wp_tags_{cat_conn_id}"] = tags
                    st.success(f"Found {len(tags)} tags.")
                else:
                    st.warning("No tags found or connection failed.")
            cached_tags = st.session_state.get(f"wp_tags_{cat_conn_id}", [])
            if cached_tags:
                for tag in cached_tags[:20]:
                    st.write(f"🏷️ **{tag['name']}** (id={tag['id']}, count={tag['count']})")
    else:
        st.info("Add a WordPress connection above to manage categories and tags.")

    st.divider()

    # -- Publish pages --------------------------------------------------------
    st.subheader("📤 Publish Pages")

    pages_for_pub = db.list_pages()
    wp_connections_for_pub = wp_publisher.list_connections()

    if not pages_for_pub:
        st.info("No pages in the library yet.")
    elif not wp_connections_for_pub:
        st.warning("Add a WordPress connection above before publishing.")
    else:
        conn_options = {f"{c.get('site_name') or c['site_url']} (id={c['id']})": c["id"] for c in wp_connections_for_pub}
        selected_conn_label = st.selectbox("Target WordPress site:", list(conn_options.keys()), key="pub_conn_sel")
        selected_conn_id = conn_options[selected_conn_label]

        page_options_pub = {f"[{p['id']}] {p['topic']}": p["id"] for p in pages_for_pub}
        selected_pages_labels = st.multiselect("Select pages to publish:", list(page_options_pub.keys()), key="pub_pages_sel")

        pub_status = st.radio("Publish status:", ["draft", "publish"], horizontal=True, key="pub_status_radio")

        pub_mode = st.radio("Publishing mode:", ["Immediate", "Staggered Schedule"], horizontal=True, key="pub_mode_radio")

        schedule_dt = None
        stagger_start = None
        stagger_interval = 1
        if pub_mode == "Immediate":
            schedule_dt = st.text_input("Schedule date (ISO 8601, optional):", placeholder="2025-12-01T09:00:00", key="pub_schedule")
        else:
            stagger_start = st.date_input("Start date:", key="pub_stagger_start")
            stagger_interval = st.number_input("Interval (days between posts):", min_value=1, max_value=30, value=1, key="pub_stagger_interval")
            pub_hour = st.number_input("Publish hour (UTC, 0-23):", min_value=0, max_value=23, value=9, key="pub_hour")

        # Optional category/tag assignment
        cached_cats_pub = st.session_state.get(f"wp_cats_{selected_conn_id}", [])
        cached_tags_pub = st.session_state.get(f"wp_tags_{selected_conn_id}", [])
        selected_cat_ids: list[int] = []
        selected_tag_ids: list[int] = []

        if cached_cats_pub:
            cat_label_to_id = {f"{c['name']} (id={c['id']})": c["id"] for c in cached_cats_pub}
            chosen_cats = st.multiselect("Assign categories:", list(cat_label_to_id.keys()), key="pub_cats_sel")
            selected_cat_ids = [cat_label_to_id[c] for c in chosen_cats]

        if cached_tags_pub:
            tag_label_to_id = {f"{t['name']} (id={t['id']})": t["id"] for t in cached_tags_pub}
            chosen_tags = st.multiselect("Assign tags:", list(tag_label_to_id.keys()), key="pub_tags_sel")
            selected_tag_ids = [tag_label_to_id[t] for t in chosen_tags]

        if st.button("🚀 Publish Selected Pages", key="btn_publish_pages"):
            if not selected_pages_labels:
                st.error("Select at least one page to publish.")
            else:
                pages_payload = []
                for label in selected_pages_labels:
                    pid = page_options_pub[label]
                    page = db.get_page(pid)
                    latest_ver = db.get_latest_version(pid)
                    pages_payload.append({
                        "page_id": pid,
                        "title": page.get("topic", f"Page {pid}") if page else f"Page {pid}",
                        "content": latest_ver["content_markdown"] if latest_ver else "",
                        "status": pub_status,
                        "schedule_date": schedule_dt or None,
                        "categories": selected_cat_ids or None,
                        "tags": selected_tag_ids or None,
                    })

                if pub_mode == "Staggered Schedule" and stagger_start:
                    results = wp_publisher.batch_publish_staggered(
                        pages=pages_payload,
                        connection_id=selected_conn_id,
                        start_date=stagger_start.isoformat(),
                        interval_days=int(stagger_interval),
                        publish_hour=int(pub_hour),
                    )
                    for r in results:
                        pid = r.get("page_id")
                        if r["success"]:
                            st.success(f"✅ Page {pid}: Scheduled for {r.get('scheduled_date', '?')}")
                        else:
                            st.error(f"❌ Page {pid}: {r.get('message', 'Unknown error')}")
                else:
                    results = wp_publisher.batch_publish(pages_payload, selected_conn_id)
                    for r in results:
                        pid = r.get("page_id")
                        if r["success"]:
                            st.success(f"✅ Page {pid}: Published — {r.get('post_url', '')}")
                        else:
                            st.error(f"❌ Page {pid}: {r.get('message', 'Unknown error')}")

    st.divider()

    # -- Publishing history ---------------------------------------------------
    st.subheader("📋 Publishing Status Dashboard")
    all_wp_posts = db.list_wordpress_posts()
    if not all_wp_posts:
        st.info("No publishing records yet.")
    else:
        st.write(f"**{len(all_wp_posts)} publishing record(s):**")
        for rec in all_wp_posts[:20]:
            status_icon = "✅" if rec["status"] in ("published", "publish") else "📝" if rec["status"] == "draft" else "⏰" if rec["status"] in ("scheduled", "future") else "❌"
            col1, col2, col3 = st.columns([1, 3, 2])
            col1.write(f"{status_icon} {rec['status']}")
            col2.write(f"Page {rec.get('page_id', '—')} → {rec.get('post_url') or '—'}")
            col3.caption(rec.get("created_at", "")[:10])


# ===========================================================================
# Tab: Ranking Tracker
# ===========================================================================

with tab_ranking:
    st.header("📊 Ranking Tracker")
    st.caption("Track keyword rankings from Google Search Console, SEMrush, or manual entry.")

    tracker = RankingTracker(db)

    inner_tabs = st.tabs(["📈 Dashboard", "🔗 Connections", "➕ Add Data", "📄 Monthly Report"])

    # -- Dashboard tab --------------------------------------------------------
    with inner_tabs[0]:
        st.subheader("Rankings Dashboard")

        pages_for_rank = db.list_pages()
        rank_page_options = {"All Pages": None}
        rank_page_options.update({f"[{p['id']}] {p['topic']}": p["id"] for p in pages_for_rank})
        rank_page_sel = st.selectbox("Filter by page:", list(rank_page_options.keys()), key="rank_page_sel")
        rank_page_id = rank_page_options[rank_page_sel]

        days_window = st.select_slider("Rolling window (days):", [7, 14, 30, 60, 90, 180], value=30, key="rank_days")

        dashboard = tracker.get_ranking_dashboard(page_id=rank_page_id, days=days_window)

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Top 3 Keywords", len(dashboard["top3"]))
        m2.metric("Top 10 Keywords", len(dashboard["top10"]) + len(dashboard["top3"]))
        m3.metric("Est. Traffic", f"{dashboard['traffic_estimate']:,.0f}")
        m4.metric("Avg CTR", f"{dashboard['avg_ctr']*100:.1f}%")

        col_left, col_right = st.columns(2)
        with col_left:
            if dashboard["quick_wins"]:
                st.subheader("⚡ Quick Wins (positions 5–20)")
                for qw in dashboard["quick_wins"][:10]:
                    st.write(
                        f"**{qw['keyword']}** — position {qw['position']:.1f} "
                        f"| {qw['impressions']} impressions | est. traffic: {qw['traffic_estimate']:.0f}"
                    )
            else:
                st.info("No quick wins found. Add ranking data to see opportunities.")

        with col_right:
            if dashboard["keyword_clusters"]:
                st.subheader("🗂️ Keyword Clusters")
                for cluster, kws in list(dashboard["keyword_clusters"].items())[:8]:
                    st.write(f"**{cluster}**: {', '.join(kws)}")

        # Position bucket breakdown
        st.divider()
        st.subheader("Position Distribution")
        bucket_cols = st.columns(5)
        for i, (label, key) in enumerate([
            ("🥇 Top 3", "top3"), ("🏆 4–10", "top10"),
            ("📊 11–20", "top20"), ("📉 21–50", "top50"), ("🔍 51+", "beyond50"),
        ]):
            bucket_cols[i].metric(label, len(dashboard[key]))

    # -- Connections tab ------------------------------------------------------
    with inner_tabs[1]:
        st.subheader("Google Search Console")

        with st.expander("➕ Add GSC Property", expanded=False):
            gsc_url = st.text_input("Property URL (e.g. https://example.com/)", key="gsc_prop_url")
            gsc_prop_id = st.text_input("GSC Property ID (optional)", key="gsc_prop_id")
            gsc_access = st.text_input("Access Token (from OAuth)", key="gsc_access_token")
            gsc_refresh = st.text_input("Refresh Token (from OAuth)", key="gsc_refresh_token")

            gsc_clients = db.list_clients()
            gsc_client_opts = {"— None —": None}
            gsc_client_opts.update({c["name"]: c["id"] for c in gsc_clients})
            gsc_client_sel = st.selectbox("Client:", list(gsc_client_opts.keys()), key="gsc_client_sel")

            if st.button("Save GSC Connection", key="btn_save_gsc"):
                if not gsc_url:
                    st.error("Property URL is required.")
                else:
                    gsc_id = tracker.add_gsc_connection(
                        property_url=gsc_url,
                        client_id=gsc_client_opts[gsc_client_sel],
                        gsc_property_id=gsc_prop_id,
                        access_token=gsc_access,
                        refresh_token=gsc_refresh,
                    )
                    st.success(f"GSC connection saved (id={gsc_id}).")

        gsc_conns = tracker.list_gsc_connections()
        if gsc_conns:
            for gc in gsc_conns:
                st.write(f"🔍 **{gc['property_url']}** (id={gc['id']})")
        else:
            st.info("No GSC connections yet.")

        st.divider()
        st.subheader("SEMrush")

        with st.expander("➕ Add SEMrush Connection", expanded=False):
            sem_domain = st.text_input("Domain (e.g. example.com)", key="sem_domain")
            sem_key = st.text_input("API Key", type="password", key="sem_api_key")
            sem_domain_id = st.text_input("SEMrush Domain ID (optional)", key="sem_domain_id")

            sem_clients = db.list_clients()
            sem_client_opts = {"— None —": None}
            sem_client_opts.update({c["name"]: c["id"] for c in sem_clients})
            sem_client_sel = st.selectbox("Client:", list(sem_client_opts.keys()), key="sem_client_sel")

            if st.button("Save SEMrush Connection", key="btn_save_semrush"):
                if not sem_domain or not sem_key:
                    st.error("Domain and API key are required.")
                else:
                    sem_id = tracker.add_semrush_connection(
                        domain=sem_domain,
                        api_key=sem_key,
                        client_id=sem_client_opts[sem_client_sel],
                        semrush_domain_id=sem_domain_id,
                    )
                    st.success(f"SEMrush connection saved (id={sem_id}).")

        sem_conns = tracker.list_semrush_connections()
        if sem_conns:
            for sc in sem_conns:
                st.write(f"📊 **{sc['domain']}** (id={sc['id']})")
        else:
            st.info("No SEMrush connections yet.")

    # -- Add Data tab ---------------------------------------------------------
    with inner_tabs[2]:
        st.subheader("➕ Add Ranking Data")
        st.caption("Manually enter ranking data or trigger a sync from connected sources.")

        add_type = st.radio("Data source:", ["Manual Entry", "Sync from GSC", "Sync from SEMrush"], horizontal=True, key="add_rank_type")

        if add_type == "Manual Entry":
            pages_m = db.list_pages()
            m_page_opts = {"— No page —": None}
            m_page_opts.update({f"[{p['id']}] {p['topic']}": p["id"] for p in pages_m})
            m_page_sel = st.selectbox("Associated page (optional):", list(m_page_opts.keys()), key="manual_rank_page")

            m_kw = st.text_input("Keyword", key="manual_rank_kw")
            m_pos = st.number_input("Position", min_value=1.0, max_value=1000.0, value=10.0, step=0.1, key="manual_rank_pos")
            m_impr = st.number_input("Impressions", min_value=0, value=0, key="manual_rank_impr")
            m_clicks = st.number_input("Clicks", min_value=0, value=0, key="manual_rank_clicks")
            m_ctr = st.number_input("CTR (0-1)", min_value=0.0, max_value=1.0, value=0.0, step=0.01, key="manual_rank_ctr")
            m_date = st.date_input("Date", key="manual_rank_date")

            if st.button("Add Entry", key="btn_add_manual_rank"):
                if not m_kw.strip():
                    st.error("Keyword is required.")
                else:
                    rid = tracker.add_manual_ranking(
                        keyword=m_kw,
                        position=m_pos,
                        page_id=m_page_opts[m_page_sel],
                        impressions=int(m_impr),
                        clicks=int(m_clicks),
                        ctr=float(m_ctr),
                        recorded_date=m_date.isoformat(),
                    )
                    st.success(f"Ranking entry added (id={rid}).")

        elif add_type == "Sync from GSC":
            gsc_sync_conns = tracker.list_gsc_connections()
            if not gsc_sync_conns:
                st.warning("No GSC connections configured. Add one in the Connections tab.")
            else:
                gsc_sync_opts = {f"{c['property_url']} (id={c['id']})": c["id"] for c in gsc_sync_conns}
                gsc_sel = st.selectbox("GSC Connection:", list(gsc_sync_opts.keys()), key="gsc_sync_sel")
                if st.button("🔄 Sync from GSC", key="btn_gsc_sync"):
                    result = tracker.sync_gsc(gsc_sync_opts[gsc_sel])
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])

        else:
            sem_sync_conns = tracker.list_semrush_connections()
            if not sem_sync_conns:
                st.warning("No SEMrush connections configured. Add one in the Connections tab.")
            else:
                sem_sync_opts = {f"{c['domain']} (id={c['id']})": c["id"] for c in sem_sync_conns}
                sem_sel = st.selectbox("SEMrush Connection:", list(sem_sync_opts.keys()), key="sem_sync_sel")
                if st.button("🔄 Sync from SEMrush", key="btn_sem_sync"):
                    result = tracker.sync_semrush(sem_sync_opts[sem_sel])
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])

    # -- Monthly Report tab ---------------------------------------------------
    with inner_tabs[3]:
        st.subheader("📄 Monthly Ranking Report")

        pages_rep = db.list_pages()
        rep_page_opts = {"All Pages": None}
        rep_page_opts.update({f"[{p['id']}] {p['topic']}": p["id"] for p in pages_rep})
        rep_page_sel = st.selectbox("Scope:", list(rep_page_opts.keys()), key="rep_page_sel")
        rep_page_id = rep_page_opts[rep_page_sel]

        if st.button("Generate Monthly Report", key="btn_gen_report"):
            report = tracker.generate_monthly_report(page_id=rep_page_id)
            st.info(report["summary_text"])

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Improved", len(report["improvements"]))
            r2.metric("Declined", len(report["declines"]))
            r3.metric("New Keywords", len(report["new_keywords"]))
            r4.metric("Lost Keywords", len(report["lost_keywords"]))

            if report["improvements"]:
                st.subheader("📈 Improvements")
                for item in report["improvements"][:10]:
                    st.write(f"✅ **{item['keyword']}** — moved up {item['delta']:.1f} spots (now #{item['current']:.0f})")

            if report["declines"]:
                st.subheader("📉 Declines")
                for item in report["declines"][:10]:
                    st.write(f"⚠️ **{item['keyword']}** — dropped {abs(item['delta']):.1f} spots (now #{item['current']:.0f})")

            if report["new_keywords"]:
                st.subheader("🆕 New Keywords")
                for item in report["new_keywords"][:10]:
                    st.write(f"🔷 **{item['keyword']}** — position #{item['position']:.0f}")

            if report["lost_keywords"]:
                st.subheader("🔴 Lost Keywords")
                for item in report["lost_keywords"][:10]:
                    st.write(f"🔻 **{item['keyword']}** — last seen at #{item['last_position']:.0f}")


# ===========================================================================
# Tab: Jeff the Master Barber — Client Quick-Start
# ===========================================================================

with tab_jeff:
    st.header("🪒 Jeff the Master Barber — Client Quick-Start")
    st.caption(
        "Pre-configured client profile for jeffthemasterbarber.com. "
        "Generate the full dark-mode SEO landing page, connect to WordPress, "
        "and load Sarasota barber ranking keywords — all in one place."
    )

    cfg_jeff = JEFF_SITE_CONFIG
    loc_jeff = cfg_jeff["location"]
    inte_jeff = cfg_jeff["integrations"]
    seo_jeff = cfg_jeff["seo"]

    # -- Client Info Panel ----------------------------------------------------
    st.markdown('<div class="section-title">📋 Client Profile</div>', unsafe_allow_html=True)
    col_j1, col_j2, col_j3 = st.columns(3)
    col_j1.markdown(
        f"**Client:** {cfg_jeff['client']}\n\n"
        f"**Domain:** [{cfg_jeff['domain']}](https://{cfg_jeff['domain']})\n\n"
        f"**Address:** {loc_jeff['address']}"
    )
    col_j2.markdown(
        f"**Booksy:** [{inte_jeff['booking_url']}]({inte_jeff['booking_url']})\n\n"
        f"**YouTube:** [@JEFFREYELBARBEROMASTER]({inte_jeff['youtube_channel']})\n\n"
        f"**Amazon:** [Shop My Products]({inte_jeff['amazon_storefront']})\n\n"
        f"**WP User:** `{inte_jeff['wp_api_user']}`"
    )
    col_j3.markdown(
        f"**Primary Keyword:** {seo_jeff['primary_keyword']}\n\n"
        f"**Color Scheme:** {cfg_jeff['ui_elements']['color_scheme']}\n\n"
        f"**Location:** {loc_jeff['geo_lat']}°N, {abs(loc_jeff['geo_long'])}°W"
    )

    st.divider()

    # -- Landing Page Generator -----------------------------------------------
    st.markdown('<div class="section-title">🌐 Generate Landing Page</div>', unsafe_allow_html=True)
    st.caption(
        "Generates a complete dark-mode HTML5 landing page with AOS scroll animations, "
        "video background support, 4×4 YouTube grid, pricing table, Booksy CTA, "
        "and LocalBusiness JSON-LD schema."
    )

    jeff_video_url = st.text_input(
        "Background Video URL (.mp4 or .webm)",
        placeholder="https://jeffthemasterbarber.com/wp-content/uploads/barber-loop.mp4",
        key="jeff_video_url",
        help="Direct link to an MP4/WebM file. Leave blank for dark-gradient fallback.",
    )

    if st.button("⚡ Generate Jeff's Landing Page", type="primary", key="btn_gen_jeff"):
        jeff_html = _build_jeff_barber_html(video_url=jeff_video_url)
        st.session_state["jeff_generated_html"] = jeff_html
        st.success(f"✅ Landing page generated! {len(jeff_html):,} characters of production-ready HTML5.")

    jeff_html_out = st.session_state.get("jeff_generated_html")
    if jeff_html_out:
        col_dl, col_dep = st.columns([1, 2])
        with col_dl:
            st.download_button(
                label="⬇️ Download HTML",
                data=jeff_html_out,
                file_name="jeffthemasterbarber-landing.html",
                mime="text/html",
                key="btn_dl_jeff",
            )
            if st.button("💾 Save to Page Library", key="btn_save_jeff"):
                pid = db.create_page(
                    service_type="barber_landing_page",
                    topic="Jeff the Master Barber — Sarasota Landing Page",
                    primary_keyword=seo_jeff["primary_keyword"],
                    page_type="service_hub",
                )
                db.save_content_version(pid, content_html=jeff_html_out, content_markdown="", quality_report={})
                st.success(f"✅ Saved to Page Library (ID: {pid})")

        with col_dep:
            jeff_wp_pub = WordPressPublisher(db)
            jeff_wp_conns = jeff_wp_pub.list_connections()
            if jeff_wp_conns:
                jeff_conn_options = {
                    f"{c.get('site_name') or c['site_url']} (id={c['id']})": c["id"]
                    for c in jeff_wp_conns
                }
                jeff_sel_conn = st.selectbox(
                    "Deploy to WordPress site:",
                    list(jeff_conn_options.keys()),
                    key="jeff_wp_conn_sel",
                )
                jeff_pub_status = st.radio(
                    "Publish status:", ["draft", "publish"], horizontal=True, key="jeff_pub_status"
                )
                if st.button("🚀 Deploy to WordPress", key="btn_deploy_jeff"):
                    result = jeff_wp_pub.publish_page(
                        page_id=0,
                        connection_id=jeff_conn_options[jeff_sel_conn],
                        title=seo_jeff["title"],
                        content=jeff_html_out,
                        status=jeff_pub_status,
                    )
                    if result["success"]:
                        st.success(f"✅ Deployed! View at: {result.get('post_url', '—')}")
                    else:
                        st.error(f"Deploy failed: {result.get('message')}")
            else:
                st.info("💡 Add the WordPress connection below and then deploy.")

        with st.expander("🖥️ Live Preview", expanded=False):
            try:
                import streamlit.components.v1 as components
                components.html(jeff_html_out, height=700, scrolling=True)
            except Exception:
                st.code(jeff_html_out[:3000] + "\n...", language="html")

        with st.expander("📄 View HTML Source"):
            st.code(jeff_html_out, language="html")

    st.divider()

    # -- WordPress Quick Connect ----------------------------------------------
    st.markdown('<div class="section-title">🔌 WordPress Quick Connect</div>', unsafe_allow_html=True)
    st.caption(
        "The site URL and username are pre-filled from the client profile. "
        "Enter the WordPress Application Password to save the connection. "
        "**Never share or commit your Application Password.**"
    )

    with st.form("jeff_wp_quick_connect"):
        jqc_url = st.text_input(
            "Site URL",
            value=inte_jeff["wp_site_url"],
            key="jqc_url",
        )
        jqc_name = st.text_input(
            "Site Name (label)",
            value="Jeff the Master Barber",
            key="jqc_name",
        )
        jqc_user = st.text_input(
            "API Username",
            value=inte_jeff["wp_api_user"],
            key="jqc_user",
        )
        jqc_pass = st.text_input(
            "Application Password",
            type="password",
            key="jqc_pass",
            help=(
                "Generate one at: WordPress Admin → Users → Profile → "
                "Application Passwords. Do NOT paste it into code or commit it."
            ),
        )
        if st.form_submit_button("💾 Save WordPress Connection"):
            if not jqc_pass.strip():
                st.error("Application Password is required.")
            else:
                jeff_wp_pub2 = WordPressPublisher(db)
                conn_id = jeff_wp_pub2.add_connection(
                    site_url=jqc_url,
                    api_username=jqc_user,
                    api_password=jqc_pass,
                    site_name=jqc_name or jqc_url,
                    client_id=None,
                )
                st.success(
                    f"✅ WordPress connection saved (id={conn_id}). "
                    "You can now deploy the landing page above."
                )
                st.rerun()

    st.divider()

    # -- Sarasota SEO Ranking Keywords ----------------------------------------
    st.markdown('<div class="section-title">📊 Sarasota SEO Ranking Keywords</div>', unsafe_allow_html=True)
    st.caption("Pre-loaded target keywords for tracking. Add them to the Ranking Tracker tab.")

    jeff_tracker = RankingTracker(db)
    jeff_kw_cols = st.columns(2)
    for i, kw in enumerate(seo_jeff["target_keywords"]):
        jeff_kw_cols[i % 2].write(f"🔑 {kw}")

    st.markdown("")
    with st.expander("➕ Bulk-Add Keywords to Ranking Tracker"):
        jeff_pages_for_rank = db.list_pages()
        jeff_rank_page_opts = {"— No page —": None}
        jeff_rank_page_opts.update(
            {f"[{p['id']}] {p['topic']}": p["id"] for p in jeff_pages_for_rank}
        )
        jeff_rank_page_sel = st.selectbox(
            "Associate with page (optional):",
            list(jeff_rank_page_opts.keys()),
            key="jeff_rank_page_sel",
        )
        jeff_rank_page_id = jeff_rank_page_opts[jeff_rank_page_sel]

        if st.button("📥 Add All Sarasota Keywords", key="btn_add_jeff_kws"):
            added = 0
            for kw in seo_jeff["target_keywords"]:
                jeff_tracker.add_manual_ranking(
                    keyword=kw,
                    position=100.0,
                    page_id=jeff_rank_page_id,
                    impressions=0,
                    clicks=0,
                    ctr=0.0,
                    recorded_date=date.today().isoformat(),
                )
                added += 1
            st.success(
                f"✅ Added {added} keywords to the Ranking Tracker. "
                "Visit the 📊 Ranking Tracker tab to monitor progress."
            )

    st.divider()

    # -- LocalBusiness JSON-LD Preview ----------------------------------------
    st.markdown('<div class="section-title">🗺️ LocalBusiness Schema Preview</div>', unsafe_allow_html=True)
    st.caption("The JSON-LD below is automatically embedded in every generated landing page.")
    schema_preview = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "Jeff the Master Barber",
        "url": f"https://{cfg_jeff['domain']}",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "7612 N Lockwood Ridge Rd",
            "addressLocality": "Sarasota",
            "addressRegion": "FL",
            "postalCode": "34243",
            "addressCountry": "US",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": loc_jeff["geo_lat"],
            "longitude": loc_jeff["geo_long"],
        },
        "priceRange": "$20 – $250",
        "sameAs": [inte_jeff["youtube_channel"], inte_jeff["booking_url"]],
    }
    st.code(json.dumps(schema_preview, indent=2), language="json")
