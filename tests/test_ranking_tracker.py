"""Tests for the RankingTracker module."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.database import Database
from src.ranking_tracker import (
    RankingTracker,
    _cluster_keywords,
    _estimate_traffic,
    _obfuscate,
    _deobfuscate,
)


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


@pytest.fixture
def db() -> Database:
    return Database(":memory:")


@pytest.fixture
def tracker(db: Database) -> RankingTracker:
    return RankingTracker(db)


@pytest.fixture
def page_id(db: Database) -> int:
    return db.create_page("blog", "SEO Guide", "seo guide")


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestObfuscation:
    def test_roundtrip(self) -> None:
        plain = "my-semrush-api-key-12345"
        assert _deobfuscate(_obfuscate(plain)) == plain

    def test_obfuscated_differs_from_plaintext(self) -> None:
        plain = "apikey"
        assert _obfuscate(plain) != plain


class TestEstimateTraffic:
    def test_position_1_high_traffic(self) -> None:
        traffic = _estimate_traffic(1000, 1)
        assert traffic > 200

    def test_position_10_lower_traffic(self) -> None:
        t1 = _estimate_traffic(1000, 1)
        t10 = _estimate_traffic(1000, 10)
        assert t1 > t10

    def test_zero_impressions(self) -> None:
        assert _estimate_traffic(0, 1) == 0.0


class TestClusterKeywords:
    def test_groups_by_first_word(self) -> None:
        kws = ["seo strategy", "seo tools", "marketing tips"]
        clusters = _cluster_keywords(kws)
        assert "seo" in clusters
        assert len(clusters["seo"]) == 2

    def test_empty_list(self) -> None:
        assert _cluster_keywords([]) == {}


# ---------------------------------------------------------------------------
# GSC connection management
# ---------------------------------------------------------------------------


class TestGscConnections:
    def test_add_and_list(self, tracker: RankingTracker, db: Database) -> None:
        cid = tracker.add_gsc_connection("https://example.com/")
        conns = tracker.list_gsc_connections()
        assert len(conns) == 1
        assert conns[0]["property_url"] == "https://example.com/"

    def test_filter_by_client(self, tracker: RankingTracker, db: Database) -> None:
        client_id = db.create_client("Acme", "acme-gsc")
        tracker.add_gsc_connection("https://acme.com/", client_id=client_id)
        tracker.add_gsc_connection("https://other.com/")
        filtered = tracker.list_gsc_connections(client_id=client_id)
        assert len(filtered) == 1

    def test_remove(self, tracker: RankingTracker, db: Database) -> None:
        cid = tracker.add_gsc_connection("https://remove.com/")
        tracker.remove_gsc_connection(cid)
        assert db.get_gsc_connection(cid) is None


# ---------------------------------------------------------------------------
# SEMrush connection management
# ---------------------------------------------------------------------------


class TestSemrushConnections:
    def test_add_and_list_redacts_key(self, tracker: RankingTracker) -> None:
        tracker.add_semrush_connection("example.com", "my-secret-api-key")
        conns = tracker.list_semrush_connections()
        assert len(conns) == 1
        assert "api_key_encrypted" not in conns[0]
        assert conns[0]["domain"] == "example.com"

    def test_api_key_stored_obfuscated(self, tracker: RankingTracker, db: Database) -> None:
        cid = tracker.add_semrush_connection("test.com", "plainkey")
        conn = db.get_semrush_connection(cid)
        assert conn is not None
        assert conn["api_key_encrypted"] != "plainkey"

    def test_remove(self, tracker: RankingTracker, db: Database) -> None:
        cid = tracker.add_semrush_connection("del.com", "key")
        tracker.remove_semrush_connection(cid)
        assert db.get_semrush_connection(cid) is None


# ---------------------------------------------------------------------------
# Sync methods
# ---------------------------------------------------------------------------


class TestSyncGsc:
    def test_no_fetcher_returns_failure(self, tracker: RankingTracker) -> None:
        cid = tracker.add_gsc_connection("https://site.com/")
        result = tracker.sync_gsc(cid)
        assert result["success"] is False
        assert result["rows_imported"] == 0

    def test_missing_connection(self, tracker: RankingTracker) -> None:
        result = tracker.sync_gsc(9999)
        assert result["success"] is False

    def test_with_mock_fetcher(self, db: Database) -> None:
        rows = [
            {"keyword": "seo", "position": 5.0, "impressions": 100, "clicks": 10, "ctr": 0.1},
            {"keyword": "local seo", "position": 12.0, "impressions": 50, "clicks": 3, "ctr": 0.06},
        ]
        tracker = RankingTracker(db, gsc_fetcher=lambda conn, s, e: rows)
        cid = tracker.add_gsc_connection("https://site.com/")
        result = tracker.sync_gsc(cid)
        assert result["success"] is True
        assert result["rows_imported"] == 2

    def test_fetcher_exception_returns_failure(self, db: Database) -> None:
        def bad_fetcher(conn, s, e):
            raise RuntimeError("API error")
        tracker = RankingTracker(db, gsc_fetcher=bad_fetcher)
        cid = tracker.add_gsc_connection("https://site.com/")
        result = tracker.sync_gsc(cid)
        assert result["success"] is False


class TestSyncSemrush:
    def test_no_fetcher_returns_failure(self, tracker: RankingTracker) -> None:
        cid = tracker.add_semrush_connection("site.com", "key")
        result = tracker.sync_semrush(cid)
        assert result["success"] is False

    def test_missing_connection(self, tracker: RankingTracker) -> None:
        result = tracker.sync_semrush(9999)
        assert result["success"] is False

    def test_with_mock_fetcher(self, db: Database) -> None:
        rows = [
            {"keyword": "enterprise seo", "position": 8.0, "impressions": 200, "clicks": 20, "ctr": 0.1},
        ]
        tracker = RankingTracker(db, semrush_fetcher=lambda conn, s, e: rows)
        cid = tracker.add_semrush_connection("site.com", "key")
        result = tracker.sync_semrush(cid)
        assert result["success"] is True
        assert result["rows_imported"] == 1


# ---------------------------------------------------------------------------
# Manual ranking entry
# ---------------------------------------------------------------------------


class TestAddManualRanking:
    def test_adds_entry(self, tracker: RankingTracker, db: Database, page_id: int) -> None:
        rid = tracker.add_manual_ranking("seo guide", 7.0, page_id=page_id, impressions=500)
        assert isinstance(rid, int)
        history = db.get_ranking_history(page_id=page_id)
        assert len(history) == 1
        assert history[0]["source"] == "manual"
        assert history[0]["impressions"] == 500


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestGetPositionTrend:
    def test_returns_sorted_history(self, tracker: RankingTracker, page_id: int) -> None:
        now = datetime.now(timezone.utc)
        tracker.add_manual_ranking("seo", 10.0, page_id=page_id,
                                   recorded_date=_date_str(now - timedelta(days=5)))
        tracker.add_manual_ranking("seo", 8.0, page_id=page_id,
                                   recorded_date=_date_str(now - timedelta(days=1)))
        trend = tracker.get_position_trend(page_id, "seo")
        assert len(trend) == 2
        assert trend[0]["position"] == 10.0
        assert trend[1]["position"] == 8.0


class TestGetQuickWins:
    def test_identifies_quick_wins(self, tracker: RankingTracker, page_id: int) -> None:
        tracker.add_manual_ranking("quick win kw", 8.0, page_id=page_id, impressions=1000)
        tracker.add_manual_ranking("top kw", 1.0, page_id=page_id, impressions=2000)
        tracker.add_manual_ranking("deep kw", 45.0, page_id=page_id, impressions=100)
        wins = tracker.get_quick_wins()
        kws = [w["keyword"] for w in wins]
        assert "quick win kw" in kws
        assert "top kw" not in kws
        assert "deep kw" not in kws

    def test_custom_position_range(self, tracker: RankingTracker, page_id: int) -> None:
        tracker.add_manual_ranking("mid kw", 25.0, page_id=page_id)
        wins = tracker.get_quick_wins(min_position=20, max_position=30)
        kws = [w["keyword"] for w in wins]
        assert "mid kw" in kws

    def test_page_scoped(self, tracker: RankingTracker, db: Database) -> None:
        p1 = db.create_page("blog", "Page 1", "kw1")
        p2 = db.create_page("blog", "Page 2", "kw2")
        tracker.add_manual_ranking("kw from p1", 10.0, page_id=p1)
        tracker.add_manual_ranking("kw from p2", 12.0, page_id=p2)
        wins = tracker.get_quick_wins(page_id=p1)
        assert all(w["page_id"] == p1 for w in wins)


class TestGetRankingDashboard:
    def test_returns_all_keys(self, tracker: RankingTracker, page_id: int) -> None:
        tracker.add_manual_ranking("seo", 2.0, page_id=page_id, impressions=500, clicks=100, ctr=0.2)
        tracker.add_manual_ranking("local seo", 7.0, page_id=page_id, impressions=200)
        dashboard = tracker.get_ranking_dashboard()
        for key in ("top3", "top10", "top20", "top50", "beyond50",
                    "quick_wins", "total_impressions", "total_clicks",
                    "avg_ctr", "traffic_estimate", "keyword_clusters"):
            assert key in dashboard

    def test_bucket_distribution(self, tracker: RankingTracker, page_id: int) -> None:
        tracker.add_manual_ranking("kw1", 1.0, page_id=page_id)
        tracker.add_manual_ranking("kw2", 5.0, page_id=page_id)
        tracker.add_manual_ranking("kw3", 15.0, page_id=page_id)
        tracker.add_manual_ranking("kw4", 30.0, page_id=page_id)
        tracker.add_manual_ranking("kw5", 60.0, page_id=page_id)
        d = tracker.get_ranking_dashboard()
        assert len(d["top3"]) == 1
        assert len(d["top10"]) == 1
        assert len(d["top20"]) == 1
        assert len(d["top50"]) == 1
        assert len(d["beyond50"]) == 1

    def test_traffic_estimate_nonzero_for_impressions(
        self, tracker: RankingTracker, page_id: int
    ) -> None:
        tracker.add_manual_ranking("kw", 3.0, page_id=page_id, impressions=1000)
        d = tracker.get_ranking_dashboard()
        assert d["traffic_estimate"] > 0


class TestGenerateMonthlyReport:
    def test_returns_required_keys(self, tracker: RankingTracker, page_id: int) -> None:
        tracker.add_manual_ranking("seo", 5.0, page_id=page_id)
        report = tracker.generate_monthly_report(page_id=page_id)
        for key in ("current_month", "previous_month", "improvements",
                    "declines", "new_keywords", "lost_keywords", "summary_text"):
            assert key in report

    def test_new_keywords_detected(self, tracker: RankingTracker, page_id: int) -> None:
        now = datetime.now(timezone.utc)
        # Add a keyword only in the current month window
        tracker.add_manual_ranking(
            "brand new kw", 10.0, page_id=page_id,
            recorded_date=_date_str(now - timedelta(days=5))
        )
        report = tracker.generate_monthly_report(page_id=page_id)
        kws = [k["keyword"] for k in report["new_keywords"]]
        assert "brand new kw" in kws

    def test_improvements_detected(self, tracker: RankingTracker, page_id: int) -> None:
        now = datetime.now(timezone.utc)
        # Position improved: was 15, now 5
        tracker.add_manual_ranking(
            "improved kw", 15.0, page_id=page_id,
            recorded_date=_date_str(now - timedelta(days=45))
        )
        tracker.add_manual_ranking(
            "improved kw", 5.0, page_id=page_id,
            recorded_date=_date_str(now - timedelta(days=5))
        )
        report = tracker.generate_monthly_report(page_id=page_id)
        kws = [i["keyword"] for i in report["improvements"]]
        assert "improved kw" in kws

    def test_summary_text_is_string(self, tracker: RankingTracker) -> None:
        report = tracker.generate_monthly_report()
        assert isinstance(report["summary_text"], str)
