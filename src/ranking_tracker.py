"""
ranking_tracker.py

Keyword ranking tracking engine for the Sturdy Broccoli SEO platform.

Responsibilities
~~~~~~~~~~~~~~~~
- Manage Google Search Console (GSC) and SEMrush API connections
- Store ranking history in the database
- Compute position trends, quick-win candidates, and traffic estimates
- Generate monthly ranking summary reports
- Surface cluster-level keyword groupings

All persistence is delegated to :class:`~src.database.Database`.

.. note::
    Live GSC and SEMrush API calls require the ``google-auth`` /
    ``google-auth-httplib2`` / ``google-api-python-client`` and ``requests``
    libraries respectively.  In test environments these can be replaced with
    mock callables via the constructor parameters.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .database import Database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_QUICK_WIN_MIN_POSITION = 5
_QUICK_WIN_MAX_POSITION = 20

# Average CTR by position (simplified model)
_POSITION_CTR = {
    1: 0.317,
    2: 0.245,
    3: 0.195,
    4: 0.124,
    5: 0.093,
    6: 0.073,
    7: 0.058,
    8: 0.047,
    9: 0.038,
    10: 0.032,
}

# ---------------------------------------------------------------------------
# Lightweight key obfuscation (same approach as wordpress_publisher)
# ---------------------------------------------------------------------------

_OBFUSCATION_SALT = b"sturdy-broccoli-semrush"


def _obfuscate(plaintext: str) -> str:
    key = hashlib.sha256(_OBFUSCATION_SALT).digest()
    data = plaintext.encode()
    out = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(out).decode()


def _deobfuscate(ciphertext: str) -> str:
    key = hashlib.sha256(_OBFUSCATION_SALT).digest()
    data = base64.urlsafe_b64decode(ciphertext.encode())
    out = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return out.decode()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _estimate_traffic(impressions: int, position: float) -> float:
    """Estimate clicks using the average CTR table for a given position."""
    pos_int = max(1, min(10, int(round(position))))
    ctr = _POSITION_CTR.get(pos_int, 0.01)
    return round(impressions * ctr, 1)


def _cluster_keywords(keywords: list[str]) -> dict[str, list[str]]:
    """
    Group keywords into simple clusters based on shared root words.

    Returns a dict mapping cluster label → list of keyword strings.
    """
    clusters: dict[str, list[str]] = defaultdict(list)
    for kw in keywords:
        words = re.split(r"\W+", kw.lower())
        root = words[0] if words else kw.lower()[:8]
        clusters[root].append(kw)
    return dict(clusters)


# ---------------------------------------------------------------------------
# RankingTracker
# ---------------------------------------------------------------------------


class RankingTracker:
    """
    High-level ranking tracking API for the Sturdy Broccoli platform.

    Parameters
    ----------
    db:
        :class:`~src.database.Database` instance.
    gsc_fetcher:
        Optional callable that accepts ``(connection_dict, start_date, end_date)``
        and returns a list of ranking dicts with keys ``keyword``, ``position``,
        ``impressions``, ``clicks``, ``ctr``, ``page_id`` (optional).
        Used to inject a mock in tests.
    semrush_fetcher:
        Optional callable that accepts ``(connection_dict, start_date, end_date)``
        and returns a list of ranking dicts with the same shape.
        Used to inject a mock in tests.
    """

    def __init__(
        self,
        db: Database,
        gsc_fetcher: Callable[..., list[dict[str, Any]]] | None = None,
        semrush_fetcher: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        self._db = db
        self._gsc_fetcher = gsc_fetcher
        self._semrush_fetcher = semrush_fetcher

    # ------------------------------------------------------------------
    # GSC connection management
    # ------------------------------------------------------------------

    def add_gsc_connection(
        self,
        property_url: str,
        client_id: int | None = None,
        gsc_property_id: str = "",
        access_token: str = "",
        refresh_token: str = "",
    ) -> int:
        """Store a GSC connection and return its id."""
        return self._db.create_gsc_connection(
            property_url=property_url,
            client_id=client_id,
            gsc_property_id=gsc_property_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def list_gsc_connections(self, client_id: int | None = None) -> list[dict[str, Any]]:
        """Return all GSC connections, optionally filtered by client."""
        return self._db.list_gsc_connections(client_id=client_id)

    def remove_gsc_connection(self, connection_id: int) -> None:
        """Delete a GSC connection."""
        self._db.delete_gsc_connection(connection_id)

    # ------------------------------------------------------------------
    # SEMrush connection management
    # ------------------------------------------------------------------

    def add_semrush_connection(
        self,
        domain: str,
        api_key: str,
        client_id: int | None = None,
        semrush_domain_id: str = "",
    ) -> int:
        """Store a SEMrush connection (API key is obfuscated) and return its id."""
        encrypted = _obfuscate(api_key)
        return self._db.create_semrush_connection(
            domain=domain,
            client_id=client_id,
            api_key_encrypted=encrypted,
            semrush_domain_id=semrush_domain_id,
        )

    def list_semrush_connections(self, client_id: int | None = None) -> list[dict[str, Any]]:
        """Return all SEMrush connections (API keys redacted)."""
        conns = self._db.list_semrush_connections(client_id=client_id)
        for c in conns:
            c.pop("api_key_encrypted", None)
        return conns

    def remove_semrush_connection(self, connection_id: int) -> None:
        """Delete a SEMrush connection."""
        self._db.delete_semrush_connection(connection_id)

    # ------------------------------------------------------------------
    # Syncing rankings
    # ------------------------------------------------------------------

    def sync_gsc(
        self,
        connection_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Pull ranking data from Google Search Console and persist it.

        Parameters
        ----------
        connection_id:
            ID of the GSC connection to use.
        start_date:
            ISO-8601 date string (``YYYY-MM-DD``).  Defaults to 30 days ago.
        end_date:
            ISO-8601 date string.  Defaults to today.

        Returns
        -------
        dict
            Keys: ``success``, ``rows_imported``, ``message``.
        """
        conn = self._db.get_gsc_connection(connection_id)
        if conn is None:
            return {"success": False, "rows_imported": 0, "message": "GSC connection not found."}

        now = datetime.now(timezone.utc)
        start = start_date or _date_str(now - timedelta(days=30))
        end = end_date or _date_str(now)

        if self._gsc_fetcher is None:
            return {
                "success": False,
                "rows_imported": 0,
                "message": (
                    "No GSC fetcher configured.  Provide a gsc_fetcher callable or "
                    "use the Google Search Console OAuth flow to obtain tokens."
                ),
            }

        try:
            rows = self._gsc_fetcher(conn, start, end)
        except Exception as exc:
            logger.exception("GSC sync failed for connection %d", connection_id)
            return {"success": False, "rows_imported": 0, "message": str(exc)}

        count = 0
        for row in rows:
            self._db.add_ranking_entry(
                keyword=row.get("keyword", ""),
                position=float(row.get("position", 0)),
                page_id=row.get("page_id"),
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                ctr=float(row.get("ctr", 0)),
                recorded_date=row.get("recorded_date", end),
                source="gsc",
            )
            count += 1

        return {"success": True, "rows_imported": count, "message": f"Imported {count} rows from GSC."}

    def sync_semrush(
        self,
        connection_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Pull ranking data from SEMrush and persist it.

        Returns
        -------
        dict
            Keys: ``success``, ``rows_imported``, ``message``.
        """
        conn = self._db.get_semrush_connection(connection_id)
        if conn is None:
            return {"success": False, "rows_imported": 0, "message": "SEMrush connection not found."}

        now = datetime.now(timezone.utc)
        start = start_date or _date_str(now - timedelta(days=7))
        end = end_date or _date_str(now)

        if self._semrush_fetcher is None:
            return {
                "success": False,
                "rows_imported": 0,
                "message": (
                    "No SEMrush fetcher configured.  Provide a semrush_fetcher callable "
                    "or enter your API key in the SEMrush connection settings."
                ),
            }

        try:
            rows = self._semrush_fetcher(conn, start, end)
        except Exception as exc:
            logger.exception("SEMrush sync failed for connection %d", connection_id)
            return {"success": False, "rows_imported": 0, "message": str(exc)}

        count = 0
        for row in rows:
            self._db.add_ranking_entry(
                keyword=row.get("keyword", ""),
                position=float(row.get("position", 0)),
                page_id=row.get("page_id"),
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                ctr=float(row.get("ctr", 0)),
                recorded_date=row.get("recorded_date", end),
                source="semrush",
            )
            count += 1

        return {"success": True, "rows_imported": count, "message": f"Imported {count} rows from SEMrush."}

    def add_manual_ranking(
        self,
        keyword: str,
        position: float,
        page_id: int | None = None,
        impressions: int = 0,
        clicks: int = 0,
        ctr: float = 0.0,
        recorded_date: str = "",
    ) -> int:
        """
        Manually add a ranking data point (source = ``'manual'``).

        Returns the id of the new ranking_history row.
        """
        return self._db.add_ranking_entry(
            keyword=keyword,
            position=position,
            page_id=page_id,
            impressions=impressions,
            clicks=clicks,
            ctr=ctr,
            recorded_date=recorded_date or _now_iso(),
            source="manual",
        )

    # ------------------------------------------------------------------
    # Analytics and reporting
    # ------------------------------------------------------------------

    def get_position_trend(
        self,
        page_id: int,
        keyword: str,
        days: int = 90,
    ) -> list[dict[str, Any]]:
        """
        Return the position history for *keyword* on *page_id* over the
        last *days* days, ordered by date ascending.
        """
        history = self._db.get_ranking_history(page_id=page_id, keyword=keyword, days=days)
        return sorted(history, key=lambda r: r["recorded_date"])

    def get_quick_wins(
        self,
        page_id: int | None = None,
        min_position: float = _QUICK_WIN_MIN_POSITION,
        max_position: float = _QUICK_WIN_MAX_POSITION,
    ) -> list[dict[str, Any]]:
        """
        Return keywords currently ranked between *min_position* and
        *max_position* that are strong candidates for reaching position 1.

        Parameters
        ----------
        page_id:
            Scope to a specific page.  ``None`` returns across all pages.
        min_position:
            Lower position bound (default: 5).
        max_position:
            Upper position bound (default: 20).

        Returns
        -------
        list[dict]
            Each dict contains ``keyword``, ``position``, ``page_id``,
            ``impressions``, ``clicks``, ``traffic_estimate``.
        """
        history = self._db.get_ranking_history(page_id=page_id)
        # Group by (page_id, keyword) and keep the most recent entry
        latest: dict[tuple[Any, str], dict[str, Any]] = {}
        for row in history:
            key = (row.get("page_id"), row["keyword"])
            existing = latest.get(key)
            if existing is None or row["recorded_date"] > existing["recorded_date"]:
                latest[key] = row

        results = []
        for row in latest.values():
            pos = row["position"]
            if min_position <= pos <= max_position:
                results.append(
                    {
                        "keyword": row["keyword"],
                        "position": pos,
                        "page_id": row.get("page_id"),
                        "impressions": row["impressions"],
                        "clicks": row["clicks"],
                        "traffic_estimate": _estimate_traffic(row["impressions"], pos),
                        "recorded_date": row["recorded_date"],
                        "source": row["source"],
                    }
                )
        results.sort(key=lambda r: r["position"])
        return results

    def get_ranking_dashboard(
        self,
        page_id: int | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Return a comprehensive ranking dashboard summary.

        Parameters
        ----------
        page_id:
            Scope to a specific page (``None`` = all pages).
        days:
            Rolling window in days.

        Returns
        -------
        dict
            Keys:

            - ``top3`` — keywords in positions 1-3
            - ``top10`` — keywords in positions 4-10
            - ``top20`` — keywords in positions 11-20
            - ``top50`` — keywords in positions 21-50
            - ``beyond50`` — keywords in positions 51+
            - ``quick_wins`` — quick-win keywords (see :meth:`get_quick_wins`)
            - ``total_impressions``
            - ``total_clicks``
            - ``avg_ctr``
            - ``traffic_estimate``
            - ``keyword_clusters``
        """
        history = self._db.get_ranking_history(page_id=page_id, days=days)

        # Deduplicate to latest entry per (page_id, keyword)
        latest: dict[tuple[Any, str], dict[str, Any]] = {}
        for row in history:
            key = (row.get("page_id"), row["keyword"])
            existing = latest.get(key)
            if existing is None or row["recorded_date"] > existing["recorded_date"]:
                latest[key] = row

        rows = list(latest.values())

        def _bucket(pos: float) -> str:
            if pos <= 3:
                return "top3"
            if pos <= 10:
                return "top10"
            if pos <= 20:
                return "top20"
            if pos <= 50:
                return "top50"
            return "beyond50"

        buckets: dict[str, list[dict[str, Any]]] = {
            "top3": [], "top10": [], "top20": [], "top50": [], "beyond50": []
        }
        total_impressions = 0
        total_clicks = 0
        ctr_values: list[float] = []

        for row in rows:
            pos = row["position"]
            buckets[_bucket(pos)].append(row)
            total_impressions += row["impressions"]
            total_clicks += row["clicks"]
            if row["ctr"]:
                ctr_values.append(row["ctr"])

        avg_ctr = round(sum(ctr_values) / len(ctr_values), 4) if ctr_values else 0.0
        traffic_estimate = sum(
            _estimate_traffic(r["impressions"], r["position"]) for r in rows
        )
        quick_wins = self.get_quick_wins(page_id=page_id)
        keyword_clusters = _cluster_keywords([r["keyword"] for r in rows])

        return {
            "top3": buckets["top3"],
            "top10": buckets["top10"],
            "top20": buckets["top20"],
            "top50": buckets["top50"],
            "beyond50": buckets["beyond50"],
            "quick_wins": quick_wins,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "avg_ctr": avg_ctr,
            "traffic_estimate": traffic_estimate,
            "keyword_clusters": keyword_clusters,
        }

    def generate_monthly_report(
        self,
        page_id: int | None = None,
        client_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate a monthly ranking report covering the current and prior month.

        Returns
        -------
        dict
            Keys: ``current_month``, ``previous_month``, ``improvements``,
            ``declines``, ``new_keywords``, ``lost_keywords``,
            ``summary_text``.
        """
        now = datetime.now(timezone.utc)
        # Current month: last 30 days
        # Previous month: 31-60 days ago
        current = self._db.get_ranking_history(page_id=page_id, days=30)
        all_60 = self._db.get_ranking_history(page_id=page_id, days=60)

        cutoff = _date_str(now - timedelta(days=30))
        previous = [r for r in all_60 if r["recorded_date"] < cutoff]

        def _latest_by_keyword(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                kw = row["keyword"]
                if kw not in result or row["recorded_date"] > result[kw]["recorded_date"]:
                    result[kw] = row
            return result

        curr_map = _latest_by_keyword(current)
        prev_map = _latest_by_keyword(previous)

        improvements = []
        declines = []
        new_keywords = []
        lost_keywords = []

        all_keywords = set(curr_map) | set(prev_map)
        for kw in all_keywords:
            if kw in curr_map and kw in prev_map:
                delta = prev_map[kw]["position"] - curr_map[kw]["position"]
                if delta > 0:
                    improvements.append(
                        {"keyword": kw, "delta": round(delta, 1), "current": curr_map[kw]["position"]}
                    )
                elif delta < 0:
                    declines.append(
                        {"keyword": kw, "delta": round(delta, 1), "current": curr_map[kw]["position"]}
                    )
            elif kw in curr_map:
                new_keywords.append({"keyword": kw, "position": curr_map[kw]["position"]})
            else:
                lost_keywords.append({"keyword": kw, "last_position": prev_map[kw]["position"]})

        improvements.sort(key=lambda x: x["delta"], reverse=True)
        declines.sort(key=lambda x: x["delta"])

        summary = (
            f"This month: {len(curr_map)} keywords tracked. "
            f"{len(improvements)} improved, {len(declines)} declined. "
            f"{len(new_keywords)} new keywords entered rankings, "
            f"{len(lost_keywords)} keywords dropped out."
        )

        return {
            "current_month": list(curr_map.values()),
            "previous_month": list(prev_map.values()),
            "improvements": improvements,
            "declines": declines,
            "new_keywords": new_keywords,
            "lost_keywords": lost_keywords,
            "summary_text": summary,
        }
