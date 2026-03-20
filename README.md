# 🥦 Sturdy Broccoli — Enterprise SEO Content Factory

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.0%2B-red?logo=streamlit&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-596%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> **A turnkey SEO marketing platform** that generates enterprise-grade HTML5 webpages at scale and deploys them directly to WordPress — built for SEO agencies, digital marketers, and content teams.

---

## ✨ What It Does

Sturdy Broccoli is a professional **SEO Content Factory CMS** that integrates all the tools an SEO agency needs into a single, cohesive Streamlit platform:

| Module | Description |
|--------|-------------|
| **⚡ Page Builder** | One-click generation of production-ready HTML5 enterprise pages (6 layout templates) |
| **🕸️ Hub & Spoke** | Build entire content clusters with hub + spoke pages, visual diagram, and batch deploy |
| **📝 Prompt Generator** | Build LLM prompts for content creation using the chain-of-thought methodology |
| **🔍 Competitor Analysis** | Identify content gaps, differentiation opportunities, and recommended topics |
| **📢 Multi-Format** | Generate LinkedIn, Twitter, YouTube, Reddit, Email, HTML, and Markdown from one source |
| **🏗️ Landing Page Templates** | 7 professional service templates with quality scoring |
| **📚 Page Library** | Database-backed page storage with filtering, export, and version history |
| **🎭 Staging Review** | Client approval workflow with approve/reject/comment flow |
| **✅ Batch Validator** | Hub-and-spoke SILO structure checker for internal link consistency |
| **💼 Agency Dashboard** | Client pipeline, revenue tracking, and deployment history |
| **✏️ Content Editor** | Live quality scoring, SEO preview, and version comparison |
| **🚀 WordPress Publisher** | Deploy to WordPress with categories, tags, and staggered scheduling |
| **📊 Ranking Tracker** | GSC, SEMrush, and manual keyword ranking tracking |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`

### Run Locally

```bash
git clone https://github.com/AutomatedTechnicalInsightsandAI/sturdy-broccoli
cd sturdy-broccoli
pip install -r requirements.txt
streamlit run gui_wrapper.py
```

### Run on Cloud Shell / GCP

```bash
streamlit run gui_wrapper.py \
  --server.port 8080 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
```

---

## 🏗️ Enterprise Page Builder

The centrepiece of the platform. Generate complete, production-ready HTML5 pages with a single click.

### Supported Layout Templates

| Template | Best For |
|----------|----------|
| 🚀 **Hero + Features Grid** | Service pages, SaaS landing pages, agency home pages |
| 🏢 **Service Hub Page** | Service detail pages, local business, B2B services |
| 📝 **Blog / Spoke Article** | Blog posts, educational content, spoke pages |
| 📊 **Case Study** | Case studies, project showcases, success stories |
| 🎯 **Lead Generation** | Lead capture, free trial sign-ups, consultation booking |
| 📚 **Resource / Guide** | Ultimate guides, whitepapers, downloadable resources |

Every generated page includes:
- ✅ Proper `<head>` with meta tags, OG tags, Twitter Cards
- ✅ Schema.org JSON-LD structured data (Service, Article, WebPage)
- ✅ Canonical URL tags
- ✅ Responsive CSS using CSS Grid/Flexbox (no CDN dependencies)
- ✅ CSS-only animations
- ✅ Internal link placeholders (`{{hub_url}}`, `{{spoke_url_1}}`)
- ✅ Proper H1→H2→H3 heading hierarchy

### Programmatic Usage

```python
from src.html5_page_builder import HTML5PageBuilder

builder = HTML5PageBuilder()
html = builder.generate_page({
    "layout": "hero_features",
    "business_name": "Acme SEO Agency",
    "service": "Local SEO Services",
    "primary_keyword": "local seo agency london",
    "target_audience": "Small businesses in London",
    "tone": "Professional",           # Professional | Conversational | Technical | Authority
    "color_scheme": "corporate_blue", # corporate_blue | agency_dark | modern_green | ...
    "cta_text": "Get a Free Audit",
    "cta_url": "https://example.com/contact",
    "canonical_url": "https://example.com/local-seo",
    "sections": ["hero", "features", "benefits", "social_proof", "faq", "cta"],
})

with open("output/local-seo.html", "w") as f:
    f.write(html)
```

---

## 🕸️ Hub & Spoke Cluster Builder

Build an entire content cluster with consistent branding:

1. Define your hub topic and select a layout template
2. Enter spoke topics (one per line)
3. Click **⚡ Batch Generate HTML5 Cluster**
4. View the visual cluster diagram
5. Download individual pages or deploy the entire cluster to WordPress with staggered scheduling

---

## 🚀 WordPress Integration

### Setup

1. Enable the WordPress REST API on your site (enabled by default in WP 4.7+)
2. Create an Application Password: **Users → Profile → Application Passwords**
3. In the **🚀 WordPress Publisher** tab, add your site URL, username, and application password
4. Click **🔍 Test** to validate your credentials

### Features

- **Connection testing** — validate credentials before publishing
- **Category & tag management** — fetch available categories/tags from your site and assign them before publishing
- **One-click publish** — publish any page from the library to WordPress as draft or published
- **Staggered scheduling** — publish a content cluster with configurable intervals (e.g., one page per day)
- **Publishing status dashboard** — view all published pages with their WP URLs and statuses

### Programmatic Publishing

```python
from src.wordpress_publisher import WordPressPublisher
from src.database import Database

db = Database()
pub = WordPressPublisher(db)

# Add a connection
conn_id = pub.add_connection(
    site_url="https://yoursite.com",
    api_username="admin",
    api_password="xxxx xxxx xxxx xxxx",  # WP Application Password
    site_name="My Site",
)

# Test the connection
result = pub.test_connection(conn_id)
print(result)  # {"success": True, "message": "Connection successful.", ...}

# Fetch categories
cats = pub.get_categories(conn_id)

# Publish with staggered scheduling
results = pub.batch_publish_staggered(
    pages=[
        {"page_id": 1, "title": "Hub Page", "content": hub_html},
        {"page_id": 2, "title": "Spoke 1", "content": spoke1_html},
        {"page_id": 3, "title": "Spoke 2", "content": spoke2_html},
    ],
    connection_id=conn_id,
    start_date="2025-07-01",
    interval_days=1,
    publish_hour=9,  # 9am UTC
)
```

---

## 🏛️ Architecture

```
sturdy-broccoli/
├── gui_wrapper.py              # Streamlit CMS UI (all tabs)
├── generator.py                # CLI for content generation
├── src/
│   ├── html5_page_builder.py   # ⭐ Enterprise HTML5 page generation (6 layouts)
│   ├── premium_page_builder.py # Full-featured premium page builder
│   ├── template_manager.py     # Service landing page templates
│   ├── tailwind_templates.py   # Tailwind CSS base templates
│   ├── wordpress_publisher.py  # WordPress REST API integration
│   ├── prompt_builder.py       # LLM prompt engineering
│   ├── content_generator.py    # Content generation pipeline
│   ├── quality_scorer.py       # 5-axis SEO quality scoring
│   ├── seo_optimizer.py        # SEO analysis and optimisation
│   ├── competitor_analyzer.py  # Competitor content analysis
│   ├── multi_format_generator.py # Multi-platform content generation
│   ├── agency_dashboard.py     # Agency pipeline & revenue tracking
│   ├── staging_manager.py      # Content staging pipeline
│   ├── staging_review.py       # Client approval workflow
│   ├── content_editor.py       # Content editing with versioning
│   ├── ranking_tracker.py      # Keyword ranking tracking
│   ├── batch_processor.py      # Batch content processing
│   ├── batch_validator.py      # Hub-and-spoke SILO validator
│   └── database.py             # SQLite persistence layer
├── config/                     # JSON configuration files
├── examples/                   # Example data files
├── prompts/                    # System prompts and chain-of-thought templates
└── tests/                      # 596 passing unit tests
```

---

## 🧪 Running Tests

```bash
pip install pytest markdown2
python -m pytest tests/ -q
# → 596 passed
```

---

## ☁️ Deployment

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/sturdy-broccoli
gcloud run deploy sturdy-broccoli \
  --image gcr.io/YOUR_PROJECT/sturdy-broccoli \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080
```

### Docker

```bash
docker build -t sturdy-broccoli .
docker run -p 8080:8080 sturdy-broccoli
```

---

## 🔧 Configuration

| Environment Variable | Description | Default |
|---|---|---|
| `STURDY_DB_PATH` | SQLite database path | `sturdy_broccoli.db` |
| `OPENAI_API_KEY` | OpenAI API key for content generation | — |
| `STURDY_WP_OBFUSCATION_SALT` | Hex-encoded salt for credential obfuscation | Built-in default |

---

## 📦 Dependencies

```
pytest>=8.0
streamlit>=1.0.0
openai>=1.0.0
markdown2>=2.4.0
google-cloud-storage>=2.0.0
```

---

## 🤝 Contributing

1. Fork the repo and create a feature branch
2. Write tests for your changes
3. Ensure all tests pass: `python -m pytest tests/ -q`
4. Submit a pull request

---

*Built for SEO agencies that need to generate and deploy enterprise-quality web pages at scale.*