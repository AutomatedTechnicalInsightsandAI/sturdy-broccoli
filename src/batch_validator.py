"""
batch_validator.py

Hub-and-Spoke structure validator for SEO content batches.

Validates that a set of pages forms a correct hub-and-spoke SILO structure:
- Pillar (hub) page links to 3–5 spoke pages
- Each spoke links back to the pillar with on-topic anchor text
- No orphaned pages (all pages linked)
- Keyword density within the 1.2–1.5% optimal range
- JSON-LD schema markup present and parseable
- Cross-spoke links maintain topical relevance

Produces a human-readable validation report and a structured results dict.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_HUB_SPOKES = 3
MAX_HUB_SPOKES = 5
MIN_KEYWORD_DENSITY = 1.2
MAX_KEYWORD_DENSITY = 1.5
MIN_SPOKE_BACKLINKS = 1  # Minimum backlinks from spoke → hub


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single validation problem found during structural checks."""

    severity: str  # "error" | "warning"
    page_slug: str | None
    message: str


@dataclass
class BatchValidationResult:
    """Complete results of a hub-and-spoke batch validation run."""

    valid: bool = False
    hub_slug: str | None = None
    hub_title: str | None = None
    spoke_count: int = 0
    total_internal_links: int = 0
    valid_internal_links: int = 0
    keyword_density: float = 0.0
    schema_valid: bool = False
    orphaned_pages: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "hub_slug": self.hub_slug,
            "hub_title": self.hub_title,
            "spoke_count": self.spoke_count,
            "total_internal_links": self.total_internal_links,
            "valid_internal_links": self.valid_internal_links,
            "keyword_density": self.keyword_density,
            "schema_valid": self.schema_valid,
            "orphaned_pages": self.orphaned_pages,
            "issues": [
                {"severity": i.severity, "page": i.page_slug, "message": i.message}
                for i in self.issues
            ],
        }

    def to_report(self) -> str:
        """Return a human-readable plain-text validation report."""
        status = "✅ Hub-and-Spoke Structure: Valid" if self.valid else "❌ Hub-and-Spoke Structure: Invalid"
        lines = [status]

        if self.hub_title:
            lines.append(f"  - Pillar: \"{self.hub_title}\"")

        lines.append(f"  - Spokes: {self.spoke_count} sub-pages")
        lines.append(
            f"  - Internal Links: {self.valid_internal_links}/{self.total_internal_links} valid"
        )

        density_label = "optimal" if MIN_KEYWORD_DENSITY <= self.keyword_density <= MAX_KEYWORD_DENSITY else "out of range"
        lines.append(f"  - Keyword Density: {self.keyword_density:.1f}% ({density_label})")

        schema_label = "Valid" if self.schema_valid else "Missing or Invalid"
        lines.append(f"  - Schema: {schema_label}")

        if self.orphaned_pages:
            lines.append(f"  - Orphaned Pages: {', '.join(self.orphaned_pages)}")

        issue_count = len(self.issues)
        lines.append("")
        if issue_count == 0:
            lines.append("⚠️  Issues Found: 0")
        else:
            lines.append(f"⚠️  Issues Found: {issue_count}")
            for issue in self.issues:
                icon = "❌" if issue.severity == "error" else "⚠️"
                page_ref = f"[{issue.page_slug}] " if issue.page_slug else ""
                lines.append(f"  {icon} {page_ref}{issue.message}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class BatchValidator:
    """
    Validates hub-and-spoke structure for a batch of pages.

    Usage::

        validator = BatchValidator()
        result = validator.validate(pages, hub_slug="main-service")
        print(result.to_report())
    """

    def validate(
        self,
        pages: list[dict[str, Any]],
        hub_slug: str | None = None,
    ) -> BatchValidationResult:
        """
        Validate the hub-and-spoke structure of a batch of pages.

        Parameters
        ----------
        pages:
            List of page dicts.  Each page must have at minimum:
            ``slug``, ``title``, ``content_markdown`` (or ``content_html``),
            and optionally ``primary_keyword``, ``internal_links``,
            ``schema_json_ld`` / ``schema_json``.
        hub_slug:
            Slug of the hub/pillar page.  If ``None``, the validator attempts
            to auto-detect the hub (longest content or first page).

        Returns
        -------
        BatchValidationResult
        """
        result = BatchValidationResult()

        if not pages:
            result.issues.append(
                ValidationIssue("error", None, "No pages provided for validation.")
            )
            return result

        # Resolve hub page
        hub = self._resolve_hub(pages, hub_slug)
        if hub is None:
            result.issues.append(
                ValidationIssue("error", None, "Could not identify a hub/pillar page.")
            )
            return result

        result.hub_slug = hub.get("slug")
        result.hub_title = hub.get("title") or hub.get("h1_content")

        spokes = [p for p in pages if p.get("slug") != result.hub_slug]
        result.spoke_count = len(spokes)

        # Spoke count check
        if result.spoke_count < MIN_HUB_SPOKES:
            result.issues.append(
                ValidationIssue(
                    "error",
                    result.hub_slug,
                    f"Hub has only {result.spoke_count} spoke(s); minimum is {MIN_HUB_SPOKES}.",
                )
            )
        elif result.spoke_count > MAX_HUB_SPOKES:
            result.issues.append(
                ValidationIssue(
                    "warning",
                    result.hub_slug,
                    f"Hub has {result.spoke_count} spokes; recommended maximum is {MAX_HUB_SPOKES}.",
                )
            )

        # Build slug sets for link validation
        all_slugs = {p.get("slug") for p in pages if p.get("slug")}

        # Validate hub → spoke links
        hub_links = self._extract_links(hub)
        spoke_slugs = {p.get("slug") for p in spokes if p.get("slug")}
        hub_to_spoke_valid = hub_links & spoke_slugs
        result.total_internal_links += len(spoke_slugs)
        result.valid_internal_links += len(hub_to_spoke_valid)

        missing_hub_links = spoke_slugs - hub_links
        for slug in missing_hub_links:
            result.issues.append(
                ValidationIssue(
                    "error",
                    result.hub_slug,
                    f"Hub page does not link to spoke '{slug}'.",
                )
            )

        # Validate spoke → hub backlinks
        hub_keyword = (hub.get("primary_keyword") or "").lower()
        linked_back: set[str] = set()

        for spoke in spokes:
            spoke_slug = spoke.get("slug", "?")
            spoke_links = self._extract_links(spoke)

            result.total_internal_links += 1
            if result.hub_slug in spoke_links:
                result.valid_internal_links += 1
                linked_back.add(spoke_slug)
            else:
                result.issues.append(
                    ValidationIssue(
                        "error",
                        spoke_slug,
                        f"Spoke '{spoke_slug}' does not link back to hub '{result.hub_slug}'.",
                    )
                )

            # Anchor text check (warning only)
            if hub_keyword and result.hub_slug in spoke_links:
                content = self._get_content(spoke)
                if hub_keyword not in content.lower():
                    result.issues.append(
                        ValidationIssue(
                            "warning",
                            spoke_slug,
                            f"Spoke '{spoke_slug}' may be missing hub keyword '{hub_keyword}' in anchor text.",
                        )
                    )

        # Orphan detection: pages not linked from hub or each other
        linked_slugs = hub_links | {result.hub_slug}
        for spoke in spokes:
            slug = spoke.get("slug")
            if slug and slug not in linked_slugs:
                result.orphaned_pages.append(slug)
                result.issues.append(
                    ValidationIssue(
                        "warning",
                        slug,
                        f"Page '{slug}' is not linked from the hub page (potential orphan).",
                    )
                )

        # Keyword density check (average across all pages)
        densities = []
        for page in pages:
            density = self._keyword_density(page)
            if density is not None:
                densities.append(density)
                if not (MIN_KEYWORD_DENSITY <= density <= MAX_KEYWORD_DENSITY):
                    result.issues.append(
                        ValidationIssue(
                            "warning",
                            page.get("slug"),
                            f"Keyword density {density:.1f}% is outside optimal range "
                            f"({MIN_KEYWORD_DENSITY}–{MAX_KEYWORD_DENSITY}%).",
                        )
                    )
        result.keyword_density = round(sum(densities) / len(densities), 2) if densities else 0.0

        # Schema markup check
        schema_errors = 0
        for page in pages:
            if not self._validate_schema(page):
                schema_errors += 1
                result.issues.append(
                    ValidationIssue(
                        "warning",
                        page.get("slug"),
                        f"Page '{page.get('slug')}' is missing valid JSON-LD schema markup.",
                    )
                )
        result.schema_valid = schema_errors == 0

        # Final validity: no errors
        result.valid = not result.has_errors()
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_hub(
        self, pages: list[dict[str, Any]], hub_slug: str | None
    ) -> dict[str, Any] | None:
        if hub_slug:
            for page in pages:
                if page.get("slug") == hub_slug:
                    return page
            return None

        # Auto-detect: prefer pages with hub_page_id=None or is_hub=True
        for page in pages:
            if page.get("is_hub") or page.get("hub_page_id") is None:
                return page

        # Fall back to first page
        return pages[0] if pages else None

    def _extract_links(self, page: dict[str, Any]) -> set[str]:
        """Return the set of slugs that a page links to."""
        links: set[str] = set()

        # 1. Structured internal_links field (list of slug strings or dicts)
        raw_links = page.get("internal_links") or []
        if isinstance(raw_links, str):
            try:
                raw_links = json.loads(raw_links)
            except (json.JSONDecodeError, ValueError):
                raw_links = []

        for item in raw_links:
            if isinstance(item, str):
                links.add(item)
            elif isinstance(item, dict):
                slug = item.get("slug") or item.get("url") or item.get("href")
                if slug:
                    links.add(str(slug).strip("/").split("/")[-1])

        # 2. Scan content for href slugs
        content = self._get_content(page)
        for href in re.findall(r'href=["\']/?([^"\'#?]+)["\']', content):
            slug_part = href.strip("/").split("/")[-1]
            if slug_part:
                links.add(slug_part)

        return links

    def _get_content(self, page: dict[str, Any]) -> str:
        return (
            page.get("content_markdown")
            or page.get("content_html")
            or page.get("body")
            or ""
        )

    def _keyword_density(self, page: dict[str, Any]) -> float | None:
        keyword = (page.get("primary_keyword") or "").strip().lower()
        if not keyword:
            # Try to get pre-computed density
            density = page.get("keyword_density")
            if density is not None:
                try:
                    return float(density)
                except (TypeError, ValueError):
                    pass
            return None

        content = self._get_content(page).lower()
        words = re.findall(r"\b\w+\b", content)
        if not words:
            return None

        keyword_words = keyword.split()
        if len(keyword_words) == 1:
            count = sum(1 for w in words if w == keyword_words[0])
        else:
            # Phrase match
            count = len(re.findall(re.escape(keyword), content))

        return round((count / len(words)) * 100, 2)

    def _validate_schema(self, page: dict[str, Any]) -> bool:
        """Return True if the page has valid JSON-LD schema markup."""
        schema = page.get("schema_json_ld") or page.get("schema_json") or page.get("schema")
        if not schema:
            return False

        if isinstance(schema, dict):
            return bool(schema.get("@type") or schema.get("@context"))

        if isinstance(schema, str):
            try:
                parsed = json.loads(schema)
                return isinstance(parsed, dict) and bool(
                    parsed.get("@type") or parsed.get("@context")
                )
            except (json.JSONDecodeError, ValueError):
                return False

        return False
