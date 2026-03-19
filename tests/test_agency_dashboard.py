"""Tests for the AgencyDashboard and new database agency workflow methods."""
from __future__ import annotations

import pytest

from src.database import Database
from src.agency_dashboard import AgencyDashboard


@pytest.fixture
def db() -> Database:
    d = Database(":memory:")
    d.init_schema()
    return d


@pytest.fixture
def dashboard(db: Database) -> AgencyDashboard:
    return AgencyDashboard(db)


class TestAgencyDashboardClients:
    def test_create_and_list_client(self, dashboard: AgencyDashboard) -> None:
        cid = dashboard.create_client(
            name="Acme Corp",
            slug="acme-corp",
            website="https://acme.example.com",
            industry="SaaS",
            email="contact@acme.example.com",
            contract_value=5000.0,
        )
        assert isinstance(cid, int)
        assert cid > 0

        clients = dashboard.list_clients()
        assert len(clients) == 1
        assert clients[0]["name"] == "Acme Corp"
        assert clients[0]["industry"] == "SaaS"
        assert clients[0]["contract_value"] == 5000.0

    def test_multiple_clients(self, dashboard: AgencyDashboard) -> None:
        dashboard.create_client("Client A", "client-a")
        dashboard.create_client("Client B", "client-b")
        clients = dashboard.list_clients()
        assert len(clients) == 2


class TestAgencyDashboardBatches:
    def test_create_and_get_staging_batch(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch(
            batch_name="Q1 Campaign",
            client_name="Acme Corp",
            total_pages=10,
            price_paid=3000.0,
        )
        assert isinstance(bid, int)

        pipeline = dashboard.get_pipeline_summary()
        assert len(pipeline) == 1
        assert pipeline[0]["batch_name"] == "Q1 Campaign"
        assert pipeline[0]["price_paid"] == 3000.0
        assert pipeline[0]["status"] == "draft"

    def test_advance_batch_status(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Test Batch", "Client X")
        dashboard.advance_batch_status(bid, "staged")
        pipeline = dashboard.get_pipeline_summary()
        assert pipeline[0]["status"] == "staged"

    def test_advance_to_deployed_sets_url(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Deploy Batch", "Client Y")
        dashboard.advance_batch_status(
            bid, "deployed",
            deployed_url="https://example.com",
            gcp_bucket_path="gs://bucket/client-y/",
        )
        pipeline = dashboard.get_pipeline_summary()
        assert pipeline[0]["deployed_url"] == "https://example.com"

    def test_invalid_status_raises(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Bad Batch", "Client Z")
        with pytest.raises(ValueError, match="Invalid batch status"):
            dashboard.advance_batch_status(bid, "pending_approval")


class TestAgencyDashboardReviews:
    def test_add_and_list_review(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Review Batch", "Client A")
        rid = dashboard.add_client_review(bid, "Looks great!", "approved")
        assert isinstance(rid, int)

        reviews = dashboard.list_reviews(bid)
        assert len(reviews) == 1
        assert reviews[0]["client_comment"] == "Looks great!"
        assert reviews[0]["status"] == "approved"

    def test_multiple_reviews(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Multi Review", "Client B")
        dashboard.add_client_review(bid, "First comment", "pending")
        dashboard.add_client_review(bid, "Second comment", "approved")
        reviews = dashboard.list_reviews(bid)
        assert len(reviews) == 2

    def test_pipeline_review_count(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Review Count", "Client C")
        dashboard.add_client_review(bid, "Comment 1", "pending")
        dashboard.add_client_review(bid, "Comment 2", "pending")
        pipeline = dashboard.get_pipeline_summary()
        assert pipeline[0]["review_count"] == 2
        assert pipeline[0]["pending_reviews"] == 2


class TestAgencyDashboardDeployments:
    def test_record_and_list_deployment(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Deploy Batch", "Client X")
        did = dashboard.record_deployment(
            batch_id=bid,
            deployed_by="admin",
            deployed_url="https://example.com/pages",
            gcp_bucket_path="gs://bucket/client-x/",
        )
        assert isinstance(did, int)

        deployments = dashboard.list_deployments()
        assert len(deployments) == 1
        assert deployments[0]["deployed_by"] == "admin"
        assert deployments[0]["deployed_url"] == "https://example.com/pages"

    def test_filter_deployments_by_batch(self, dashboard: AgencyDashboard) -> None:
        bid1 = dashboard.create_staging_batch("Batch 1", "Client A")
        bid2 = dashboard.create_staging_batch("Batch 2", "Client B")
        dashboard.record_deployment(bid1, "user1", "https://a.example.com")
        dashboard.record_deployment(bid2, "user2", "https://b.example.com")

        deps_b1 = dashboard.list_deployments(batch_id=bid1)
        assert len(deps_b1) == 1
        assert deps_b1[0]["deployed_url"] == "https://a.example.com"


class TestAgencyRevenueStats:
    def test_empty_database_returns_zeros(self, dashboard: AgencyDashboard) -> None:
        stats = dashboard.get_revenue_stats()
        assert stats["total_revenue"] == 0.0
        assert stats["total_batches"] == 0

    def test_revenue_aggregates_correctly(self, dashboard: AgencyDashboard) -> None:
        dashboard.create_staging_batch("Batch A", "C1", price_paid=2000.0)
        dashboard.create_staging_batch("Batch B", "C2", price_paid=3500.0)
        stats = dashboard.get_revenue_stats()
        assert stats["total_revenue"] == pytest.approx(5500.0)
        assert stats["total_batches"] == 2
        assert stats["draft_batches"] == 2

    def test_deployed_batches_counted_correctly(self, dashboard: AgencyDashboard) -> None:
        bid = dashboard.create_staging_batch("Deployed Batch", "C1", price_paid=4000.0)
        dashboard.advance_batch_status(bid, "deployed", deployed_url="https://x.com")
        stats = dashboard.get_revenue_stats()
        assert stats["deployed_batches"] == 1
        assert stats["draft_batches"] == 0
