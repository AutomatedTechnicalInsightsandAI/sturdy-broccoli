"""
staging_manager.py

High-level orchestration layer for the SEO Site Factory staging pipeline.

Responsibilities
----------------
1. Batch creation — creates a Batch record + N Page records from a list of
   page-data dicts, marking every page ``status: pending_review``.
2. Preview rendering — converts a page's Markdown to HTML and injects it
   into the selected Tailwind CSS template.
3. Quality score aggregation — computes the five-axis score from the
   existing SEOOptimizer.
4. Batch style application — broadcasts brand colour, CTA link, font, and
   template changes across a set of page IDs.
5. Deployment — validates and deploys all approved pages, produces a
   deployment manifest.

This module does NOT make LLM calls.  Generation is still handled by the
existing ``ContentGenerator`` / CLI pipeline; the staging manager receives
already-generated page data.
"""
from __future__ import annotations

import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import markdown2  # type: ignore
    _USE_MARKDOWN2 = True
except ImportError:
    _USE_MARKDOWN2 = False

from .database import Database
from .tailwind_templates import render_template, list_templates, TEMPLATE_NAMES
from .seo_optimizer import SEOOptimizer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower().strip()).strip("-")[:80]


def _markdown_to_html(md: str) -> str:
    if _USE_MARKDOWN2:
        return markdown2.markdown(
            md,
            extras=["fenced-code-blocks", "tables", "header-ids"],
        )
    # Minimal fallback: wrap in <pre> so content is visible
    import html as _html_mod
    return f"<pre style='white-space:pre-wrap'>{_html_mod.escape(md)}</pre>"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_quality_scores(content_markdown: str, page_data: dict[str, Any]) -> dict[str, Any]:
    """Run SEOOptimizer and map its output to our five-axis schema."""
    try:
        optimizer = SEOOptimizer()
        result = optimizer.analyze(content_markdown, page_data)
        overall = round(result.overall_score * 100)
        breakdown = result.breakdown or {}

        def _pct(key: str) -> int:
            val = breakdown.get(key, 0.5)
            return round(float(val) * 100)

        return {
            "authority": _pct("eeat"),
            "semantic": _pct("semantic_triplet_density"),
            "structure": _pct("heading_structure"),
            "engagement": _pct("intent_alignment"),
            "uniqueness": _pct("long_tail_coverage"),
            "overall": overall,
        }
    except Exception:  # noqa: BLE001
        # Return neutral scores if optimizer fails (e.g., missing content)
        return {
            "authority": 50,
            "semantic": 50,
            "structure": 50,
            "engagement": 50,
            "uniqueness": 50,
            "overall": 50,
        }


# ---------------------------------------------------------------------------
# StagingManager
# ---------------------------------------------------------------------------


class StagingManager:
    """
    Manages the three-tier staging pipeline:
    Generation → Staging → Deployment.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Defaults to ``seo_factory.db``
        in the project root.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db = Database(db_path)

    # ------------------------------------------------------------------
    # Batch creation
    # ------------------------------------------------------------------

    def create_batch_from_pages(
        self,
        batch_name: str,
        pages: list[dict[str, Any]],
        batch_description: str = "",
        created_by: str = "user",
    ) -> int:
        """
        Insert a new Batch + all supplied pages into the database.

        Each page dict should contain at minimum:
          - title
          - topic
          - primary_keyword
          - content_markdown  (may be empty for stub pages)
          - h1_content, meta_title, meta_description  (optional)

        Returns the new batch_id.
        """
        batch_id = self.db.create_batch(
            name=batch_name,
            description=batch_description,
            created_by=created_by,
        )

        seen_slugs: set[str] = set()
        for i, page_data in enumerate(pages):
            title = page_data.get("title") or page_data.get("topic", f"Page {i + 1}")
            base_slug = _slugify(title)
            slug = base_slug
            counter = 1
            while slug in seen_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1
            seen_slugs.add(slug)

            md = page_data.get("content_markdown", "")
            body_html = _markdown_to_html(md) if md else ""
            word_count = len(md.split()) if md else 0

            quality_scores = _compute_quality_scores(md, page_data) if md else {}

            self.db.create_page(
                {
                    "batch_id": batch_id,
                    "title": title,
                    "slug": slug,
                    "topic": page_data.get("topic", title),
                    "primary_keyword": page_data.get("primary_keyword", ""),
                    "status": "pending_review",
                    "preview_state": page_data.get("preview_state", {}),
                    "assigned_template": page_data.get("assigned_template", "modern_saas"),
                    "h1_content": page_data.get("h1_content", ""),
                    "meta_title": page_data.get("meta_title", title),
                    "meta_description": page_data.get("meta_description", ""),
                    "content_markdown": md,
                    "content_html": body_html,
                    "quality_scores": quality_scores,
                    "word_count": word_count,
                    "assigned_by": "system",
                }
            )

        self.db.update_batch_counts(batch_id)
        return batch_id

    # ------------------------------------------------------------------
    # Preview rendering
    # ------------------------------------------------------------------

    def render_page_preview(
        self,
        page_id: int,
        template_override: str | None = None,
        color_override: str | None = None,
        cta_link_override: str | None = None,
        cta_text_override: str | None = None,
    ) -> str:
        """Return fully rendered HTML for the given page."""
        page = self.db.get_page(page_id)
        if not page:
            raise ValueError(f"Page {page_id} not found")

        preview_state = page.get("preview_state") or {}
        template_key = template_override or preview_state.get("current_layout") or page.get("assigned_template", "modern_saas")
        color = color_override or preview_state.get("color_override") or "blue"
        cta_link = cta_link_override or preview_state.get("cta_link") or "#get-started"
        cta_text = cta_text_override or "Get Started"

        # Ensure we have rendered HTML
        body_html = page.get("content_html") or ""
        if not body_html and page.get("content_markdown"):
            body_html = _markdown_to_html(page["content_markdown"])

        return render_template(
            template_key=template_key,
            h1=page.get("h1_content") or page.get("title", ""),
            meta_title=page.get("meta_title") or page.get("title", ""),
            meta_description=page.get("meta_description", ""),
            body_html=body_html,
            primary_color=color,
            cta_link=cta_link,
            cta_text=cta_text,
        )

    # ------------------------------------------------------------------
    # Page updates (called from UI)
    # ------------------------------------------------------------------

    def update_page_markdown(self, page_id: int, markdown: str) -> None:
        """Update markdown + re-render HTML and recompute quality scores."""
        page = self.db.get_page(page_id)
        if not page:
            raise ValueError(f"Page {page_id} not found")
        body_html = _markdown_to_html(markdown)
        word_count = len(markdown.split())
        quality_scores = _compute_quality_scores(markdown, page)
        self.db.update_page(
            page_id,
            {
                "content_markdown": markdown,
                "content_html": body_html,
                "word_count": word_count,
                "quality_scores": quality_scores,
            },
        )

    def save_preview_state(
        self,
        page_id: int,
        template: str | None = None,
        color: str | None = None,
        cta_link: str | None = None,
    ) -> None:
        page = self.db.get_page(page_id)
        if not page:
            return
        state: dict[str, Any] = page.get("preview_state") or {}
        if template:
            state["current_layout"] = template
        if color:
            state["color_override"] = color
        if cta_link:
            state["cta_link"] = cta_link
        self.db.update_page(page_id, {"preview_state": state})

    # ------------------------------------------------------------------
    # Batch style application
    # ------------------------------------------------------------------

    def apply_batch_style(
        self,
        page_ids: list[int],
        template: str | None = None,
        brand_color: str | None = None,
        cta_link: str | None = None,
        font_family: str | None = None,
    ) -> int:
        """Apply global style settings to a list of pages. Returns count updated."""
        if not page_ids:
            return 0

        patch: dict[str, Any] = {}
        if brand_color:
            patch["color_override"] = brand_color
        if cta_link:
            patch["cta_link"] = cta_link
        if font_family:
            patch["font_family"] = font_family

        if patch:
            self.db.bulk_update_preview_state(page_ids, patch)

        if template:
            self.db.bulk_set_template(page_ids, template)

        return len(page_ids)

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def approve_pages(self, page_ids: list[int]) -> None:
        self.db.bulk_set_status(page_ids, "approved")

    def review_pages(self, page_ids: list[int]) -> None:
        self.db.bulk_set_status(page_ids, "reviewed")

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy_batch(self, batch_id: int) -> dict[str, Any]:
        """
        Deploy all approved pages in a batch.

        Returns a deployment manifest dict containing:
          - deployed_count
          - pages  (list of slug + URL for each deployed page)
          - deployed_at
          - warnings  (pages that failed pre-flight checks)
        """
        pages = self.db.list_pages(batch_id=batch_id, status="approved")

        warnings: list[str] = []
        deployable: list[dict[str, Any]] = []

        for page in pages:
            issues: list[str] = []
            if not page.get("h1_content"):
                issues.append("missing H1")
            if not page.get("meta_description"):
                issues.append("missing meta description")
            qs = page.get("quality_scores") or {}
            if isinstance(qs, dict) and qs.get("overall", 100) < 20:
                issues.append(f"quality score too low ({qs.get('overall')})")
            if issues:
                warnings.append(f"'{page['title']}': {', '.join(issues)}")
            else:
                deployable.append(page)

        deployed_pages = self.db.deploy_approved_pages(batch_id)

        deployed_at = _utcnow()
        urls = [
            {
                "title": p["title"],
                "slug": p["slug"],
                "url": f"/pages/{p['slug']}",
                "meta_title": p.get("meta_title", ""),
                "meta_description": p.get("meta_description", ""),
            }
            for p in deployed_pages
        ]

        return {
            "deployed_count": len(deployed_pages),
            "pages": urls,
            "deployed_at": deployed_at,
            "warnings": warnings,
        }

    def generate_deployment_csv(self, manifest: dict[str, Any]) -> str:
        """Return a CSV string from a deployment manifest."""
        lines = ["title,slug,url,meta_title,meta_description"]
        for p in manifest.get("pages", []):
            def _esc(v: str) -> str:
                return '"' + str(v).replace('"', '""') + '"'
            lines.append(
                ",".join(
                    _esc(p.get(k, ""))
                    for k in ("title", "slug", "url", "meta_title", "meta_description")
                )
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Stub page generation (for demo / testing without LLM)
    # ------------------------------------------------------------------

    def generate_stub_pages(
        self,
        service_name: str,
        primary_keyword: str,
        count: int = 5,
        competitor_urls: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate lightweight stub page dicts without LLM calls.

        These represent what the full prompt-engineering pipeline would
        produce.  Each stub has a unique topic, H1, meta description, and
        placeholder Markdown body.
        """
        subtopics = [
            f"{service_name} Guide",
            f"Best {service_name} Strategies",
            f"How to Choose a {service_name} Provider",
            f"{service_name} vs DIY: What Works",
            f"Ultimate {service_name} Checklist",
            f"Case Study: {service_name} Results",
            f"{service_name} Cost Breakdown",
            f"Top {service_name} Tools",
            f"Common {service_name} Mistakes",
            f"{service_name} ROI Calculator",
        ]

        pages = []
        for i in range(count):
            topic = subtopics[i % len(subtopics)]
            if i >= len(subtopics):
                topic = f"{topic} — Part {i // len(subtopics) + 1}"

            kw = primary_keyword.lower()
            h1 = f"{topic}: The Definitive {service_name} Resource"
            meta_desc = (
                f"Discover expert insights on {kw} with our comprehensive guide to {topic.lower()}. "
                f"Learn actionable strategies that deliver real results."
            )
            md_body = textwrap.dedent(f"""\
                ## Introduction

                Whether you're new to {kw} or looking to scale your results,
                this guide covers everything you need to know about {topic.lower()}.

                ## Key Benefits

                - Proven frameworks used by top agencies
                - Step-by-step implementation guidance
                - Real-world case studies and data

                ## How It Works

                Our approach to {kw} is built on three pillars:

                1. **Research** — Deep competitor and keyword analysis
                2. **Execution** — Content that earns authority
                3. **Measurement** — Tracking what actually moves rankings

                ## Common Mistakes to Avoid

                Most businesses fail at {kw} because they focus on volume
                rather than quality. Here's what separates top performers.

                ## Conclusion

                Investing in {kw} is one of the highest-ROI decisions
                a growing business can make. Start with our checklist below.
            """)

            pages.append(
                {
                    "title": f"{topic} | {service_name}",
                    "topic": topic,
                    "primary_keyword": primary_keyword,
                    "h1_content": h1,
                    "meta_title": f"{topic} — {service_name} Guide",
                    "meta_description": meta_desc,
                    "content_markdown": md_body,
                    "assigned_template": "modern_saas",
                }
            )

        return pages

    # ------------------------------------------------------------------
    # Read helpers (pass-through to DB)
    # ------------------------------------------------------------------

    def get_batch(self, batch_id: int) -> dict[str, Any] | None:
        return self.db.get_batch(batch_id)

    def list_batches(self) -> list[dict[str, Any]]:
        return self.db.list_batches()

    def list_pages(
        self,
        batch_id: int | None = None,
        status: str | None = None,
        template: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.db.list_pages(batch_id=batch_id, status=status, template=template)

    def get_page(self, page_id: int) -> dict[str, Any] | None:
        return self.db.get_page(page_id)

    def delete_page(self, page_id: int) -> None:
        self.db.delete_page(page_id)

    def list_templates(self) -> dict[str, str]:
        return list_templates()
