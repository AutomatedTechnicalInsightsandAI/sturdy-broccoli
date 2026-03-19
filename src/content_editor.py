"""
content_editor.py

Rich content editing engine for the Sturdy Broccoli SEO platform.

Responsibilities
~~~~~~~~~~~~~~~~
- Load and save content versions for pages
- Track edit history with author and change notes
- Compute real-time quality scores on edited content
- Render an SEO preview (title / meta / snippet) for a page
- Compare two versions side-by-side as unified diffs
- Calculate keyword density for the current content

All persistence is delegated to :class:`~src.database.Database`.
"""
from __future__ import annotations

import difflib
import re
from typing import Any

from .database import Database
from .quality_scorer import QualityScorer

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    """Return the number of whitespace-delimited words in *text*."""
    return len(text.split()) if text.strip() else 0


def _keyword_density(text: str, keyword: str) -> float:
    """
    Return keyword density as a percentage (0-100).

    The denominator is the total word count of *text*.  Matching is
    case-insensitive and the keyword phrase may be multi-word.
    """
    if not text.strip() or not keyword.strip():
        return 0.0
    total_words = _word_count(text)
    if total_words == 0:
        return 0.0
    pattern = re.compile(re.escape(keyword.strip()), re.IGNORECASE)
    occurrences = len(pattern.findall(text))
    kw_words = len(keyword.strip().split())
    return round((occurrences * kw_words / total_words) * 100, 2)


def _seo_preview(
    title: str,
    url: str,
    meta_description: str,
    max_title_len: int = 60,
    max_desc_len: int = 160,
) -> dict[str, str]:
    """
    Build a Google-style SEO preview snippet.

    Returns
    -------
    dict
        Keys: ``display_title``, ``display_url``, ``display_description``,
        ``title_length``, ``desc_length``, ``title_ok``, ``desc_ok``.
    """
    display_title = title[:max_title_len] + ("…" if len(title) > max_title_len else "")
    display_desc = (
        meta_description[:max_desc_len]
        + ("…" if len(meta_description) > max_desc_len else "")
    )
    return {
        "display_title": display_title,
        "display_url": url or "https://example.com/page-slug",
        "display_description": display_desc,
        "title_length": len(title),
        "desc_length": len(meta_description),
        "title_ok": len(title) <= max_title_len,
        "desc_ok": len(meta_description) <= max_desc_len,
    }


def _unified_diff(text_a: str, text_b: str, label_a: str = "v1", label_b: str = "v2") -> str:
    """Return a unified-diff string between two text blobs."""
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)
    diff = difflib.unified_diff(lines_a, lines_b, fromfile=label_a, tofile=label_b)
    return "".join(diff)


# ---------------------------------------------------------------------------
# ContentEditor
# ---------------------------------------------------------------------------


class ContentEditor:
    """
    High-level content editing API for the Sturdy Broccoli platform.

    Parameters
    ----------
    db:
        :class:`~src.database.Database` instance to use for persistence.
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._scorer = QualityScorer()

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def save_edit(
        self,
        page_id: int,
        content_markdown: str,
        content_html: str = "",
        version_notes: str = "",
        edited_by: str = "",
    ) -> dict[str, Any]:
        """
        Persist a new edited version of a page and return a result dict.

        A quality score is automatically computed from *content_markdown*
        and stored alongside the version.

        Parameters
        ----------
        page_id:
            ID of the page to edit.
        content_markdown:
            New content in Markdown format.
        content_html:
            Optional pre-rendered HTML.  If empty a minimal conversion is
            performed.
        version_notes:
            Human-readable description of what changed.
        edited_by:
            Name / identifier of the person making the edit.

        Returns
        -------
        dict
            Keys: ``version_id``, ``version``, ``quality_scores``,
            ``word_count``, ``message``.
        """
        from datetime import datetime, timezone

        page = self._db.get_page(page_id)
        if page is None:
            raise ValueError(f"Page {page_id} not found")

        # Score the updated content
        page_data_for_scoring = {
            "primary_keyword": page.get("primary_keyword", ""),
            "topic": page.get("topic", ""),
        }
        quality_result = self._scorer.score(content_markdown, page_data_for_scoring)
        quality = quality_result.as_dict()

        version_id = self._db.save_content_version(
            page_id=page_id,
            content_html=content_html,
            content_markdown=content_markdown,
            quality_report=quality,
            version_notes=version_notes,
            edited_by=edited_by,
            edited_at=datetime.now(timezone.utc).isoformat(),
        )

        # Also update the quality_scores table for dashboard stats
        self._db.save_quality_scores(page_id, quality, version_id=version_id)

        versions = self._db.list_versions(page_id)
        new_version_number = versions[-1]["version"] if versions else 1

        return {
            "version_id": version_id,
            "version": new_version_number,
            "quality_scores": quality,
            "word_count": _word_count(content_markdown),
            "message": f"Version {new_version_number} saved successfully.",
        }

    def get_version(self, page_id: int, version: int) -> dict[str, Any] | None:
        """
        Return a specific version dict for *page_id*, or ``None``.

        Parameters
        ----------
        page_id:
            ID of the page.
        version:
            1-based version number.
        """
        versions = self._db.list_versions(page_id)
        for v in versions:
            if v["version"] == version:
                return v
        return None

    def list_versions(self, page_id: int) -> list[dict[str, Any]]:
        """Return all versions for *page_id* in ascending order."""
        return self._db.list_versions(page_id)

    def get_latest_version(self, page_id: int) -> dict[str, Any] | None:
        """Return the most recent version for *page_id*, or ``None``."""
        return self._db.get_latest_version(page_id)

    # ------------------------------------------------------------------
    # Real-time quality scoring
    # ------------------------------------------------------------------

    def score_content(
        self, content: str, page_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Compute quality scores for *content* without persisting a version.

        Parameters
        ----------
        content:
            Markdown or plain-text content to score.
        page_data:
            Optional context dict with ``primary_keyword``, ``topic``, etc.

        Returns
        -------
        dict
            Quality score report from :class:`~src.quality_scorer.QualityScorer`.
        """
        return self._scorer.score(content, page_data or {}).as_dict()

    # ------------------------------------------------------------------
    # SEO preview
    # ------------------------------------------------------------------

    def build_seo_preview(
        self,
        title: str,
        meta_description: str,
        url: str = "",
    ) -> dict[str, str]:
        """
        Return a Google-style SEO preview card.

        Parameters
        ----------
        title:
            Page title (ideally 50-60 characters).
        meta_description:
            Meta description (ideally 120-160 characters).
        url:
            Canonical URL for the page.

        Returns
        -------
        dict
            See :func:`_seo_preview` for key documentation.
        """
        return _seo_preview(title, url, meta_description)

    # ------------------------------------------------------------------
    # Version comparison
    # ------------------------------------------------------------------

    def compare_versions(
        self,
        page_id: int,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        """
        Compare two versions of a page and return a unified diff plus metadata.

        Parameters
        ----------
        page_id:
            ID of the page.
        version_a:
            First version number (appears as ``from`` in the diff).
        version_b:
            Second version number (appears as ``to`` in the diff).

        Returns
        -------
        dict
            Keys: ``diff``, ``version_a``, ``version_b``,
            ``word_count_a``, ``word_count_b``, ``word_count_delta``.

        Raises
        ------
        ValueError
            If either version cannot be found.
        """
        va = self.get_version(page_id, version_a)
        vb = self.get_version(page_id, version_b)
        if va is None:
            raise ValueError(f"Version {version_a} not found for page {page_id}")
        if vb is None:
            raise ValueError(f"Version {version_b} not found for page {page_id}")

        diff = _unified_diff(
            va["content_markdown"],
            vb["content_markdown"],
            label_a=f"v{version_a}",
            label_b=f"v{version_b}",
        )
        wc_a = _word_count(va["content_markdown"])
        wc_b = _word_count(vb["content_markdown"])
        return {
            "diff": diff,
            "version_a": version_a,
            "version_b": version_b,
            "word_count_a": wc_a,
            "word_count_b": wc_b,
            "word_count_delta": wc_b - wc_a,
        }

    # ------------------------------------------------------------------
    # Keyword density
    # ------------------------------------------------------------------

    def keyword_density(self, content: str, keyword: str) -> float:
        """
        Return the keyword density of *keyword* in *content* as a percentage.

        Parameters
        ----------
        content:
            Full page content (Markdown or plain text).
        keyword:
            Target keyword phrase.

        Returns
        -------
        float
            Density as a percentage value (e.g. ``1.5`` means 1.5 %).
        """
        return _keyword_density(content, keyword)
