"""
agency_dashboard.py

Agency pipeline + revenue tracking for the proprietary marketing engine.

Provides the ``AgencyDashboard`` facade that aggregates data from the database
to power the Agency Dashboard tab in the Streamlit UI:
- Batch pipeline (draft → staged → approved → deployed)
- Revenue tracker ($2k–$5k per batch)
- Client status (pending approval, deployed, archived)
- Average batch generation time
- Content quality metrics
"""
from __future__ import annotations

from typing import Any

from .database import Database, STAGING_BATCH_STATUSES


class AgencyDashboard:
    """
    Facade for agency-level pipeline and revenue analytics.

    Parameters
    ----------
    db:
        Initialised :class:`~src.database.Database` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Revenue & pipeline stats
    # ------------------------------------------------------------------

    def get_revenue_stats(self) -> dict[str, Any]:
        """
        Return aggregate revenue and batch pipeline statistics.

        Returns
        -------
        dict
            ``total_revenue``, ``draft_batches``, ``staged_batches``,
            ``approved_batches``, ``deployed_batches``, ``total_batches``
        """
        return self._db.get_agency_revenue_stats()

    def get_pipeline_summary(self) -> list[dict[str, Any]]:
        """
        Return all staging batches enriched with review counts.

        Returns
        -------
        list of dict
            Each dict is a ``staging_batches`` row plus a ``review_count`` key.
        """
        batches = self._db.list_staging_batches()
        for batch in batches:
            reviews = self._db.list_staging_reviews(batch["id"])
            batch["review_count"] = len(reviews)
            batch["pending_reviews"] = sum(
                1 for r in reviews if r.get("status") == "pending"
            )
        return batches

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------

    def list_clients(self) -> list[dict[str, Any]]:
        """Return all clients ordered by name."""
        return self._db.list_clients()

    def create_client(
        self,
        name: str,
        slug: str,
        website: str = "",
        industry: str = "",
        email: str = "",
        contract_value: float = 0.0,
    ) -> int:
        """
        Create a new agency client.

        Parameters
        ----------
        name:
            Human-readable client name.
        slug:
            URL-safe unique slug.
        website:
            Client website URL.
        industry:
            Industry label.
        email:
            Contact email.
        contract_value:
            Total contract value in dollars.

        Returns
        -------
        int
            New client id.
        """
        return self._db.create_client(
            name=name,
            slug=slug,
            website=website,
            industry=industry,
            email=email,
            contract_value=contract_value,
        )

    # ------------------------------------------------------------------
    # Staging batch management
    # ------------------------------------------------------------------

    def create_staging_batch(
        self,
        batch_name: str,
        client_name: str = "",
        total_pages: int = 0,
        price_paid: float = 0.0,
    ) -> int:
        """
        Create a new staging batch.

        Parameters
        ----------
        batch_name:
            Descriptive name for the batch.
        client_name:
            Client this batch belongs to.
        total_pages:
            Expected number of pages in this batch.
        price_paid:
            Revenue amount for this batch.

        Returns
        -------
        int
            New staging batch id.
        """
        return self._db.create_staging_batch(
            batch_name=batch_name,
            client_name=client_name,
            total_pages=total_pages,
            price_paid=price_paid,
        )

    def advance_batch_status(
        self,
        batch_id: int,
        new_status: str,
        deployed_url: str = "",
        gcp_bucket_path: str = "",
    ) -> None:
        """
        Advance a batch to the next pipeline stage.

        Valid transitions:
        ``draft`` → ``staged`` → ``approved`` → ``deployed``

        Parameters
        ----------
        batch_id:
            ID of the staging batch to update.
        new_status:
            Target status.
        deployed_url:
            Live URL (set when status becomes ``'deployed'``).
        gcp_bucket_path:
            GCS path (set when status becomes ``'deployed'``).
        """
        valid = set(STAGING_BATCH_STATUSES)
        if new_status not in valid:
            raise ValueError(
                f"Invalid batch status '{new_status}'. Must be one of: {sorted(valid)}"
            )
        self._db.update_staging_batch_status(
            batch_id=batch_id,
            status=new_status,
            deployed_url=deployed_url,
            gcp_bucket_path=gcp_bucket_path,
        )

    # ------------------------------------------------------------------
    # Client review workflow
    # ------------------------------------------------------------------

    def add_client_review(
        self,
        batch_id: int,
        client_comment: str,
        status: str = "pending",
    ) -> int:
        """
        Record a client review comment for a staging batch.

        Parameters
        ----------
        batch_id:
            Staging batch being reviewed.
        client_comment:
            Client's feedback text.
        status:
            Review outcome: ``'pending'``, ``'approved'``, or ``'rejected'``.

        Returns
        -------
        int
            New review id.
        """
        return self._db.create_staging_review(
            batch_id=batch_id,
            client_comment=client_comment,
            status=status,
        )

    def list_reviews(self, batch_id: int) -> list[dict[str, Any]]:
        """Return all client reviews for a staging batch."""
        return self._db.list_staging_reviews(batch_id)

    # ------------------------------------------------------------------
    # Deployment tracking
    # ------------------------------------------------------------------

    def record_deployment(
        self,
        batch_id: int | None,
        deployed_by: str,
        deployed_url: str,
        gcp_bucket_path: str = "",
    ) -> int:
        """
        Record a deployment event in the audit trail.

        Parameters
        ----------
        batch_id:
            Staging batch that was deployed.
        deployed_by:
            Identifier of the user or system that triggered the deployment.
        deployed_url:
            Public URL of the deployed content.
        gcp_bucket_path:
            GCS path for the deployment.

        Returns
        -------
        int
            New deployment record id.
        """
        return self._db.create_deployment(
            batch_id=batch_id,
            deployed_by=deployed_by,
            deployed_url=deployed_url,
            gcp_bucket_path=gcp_bucket_path,
        )

    def list_deployments(self, batch_id: int | None = None) -> list[dict[str, Any]]:
        """Return deployment audit records, optionally filtered by batch."""
        return self._db.list_deployments(batch_id=batch_id)
