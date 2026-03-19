"""
gcp_persistent_deployer.py

Persistent GCP deployer using a service account JSON key.

Uploads approved pages from a batch to Google Cloud Storage, making them
publicly accessible as static HTML landing pages.  Unlike ``gcloud auth login``
(which is session-scoped), this module authenticates via a service account
JSON key stored in the environment, suitable for automated / SaaS deployments.

Environment variables
---------------------
GOOGLE_APPLICATION_CREDENTIALS
    Path to the service account JSON key file.
GCP_PROJECT_ID
    Google Cloud project ID (e.g. ``my-content-gen-app``).
GCP_BUCKET_NAME
    Target GCS bucket name (e.g. ``my-seo-site-bucket``).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _gcs_client():  # type: ignore[return]
    """
    Return an authenticated GCS client.

    Imports ``google.cloud.storage`` lazily so the rest of the application
    works when the package is not installed (non-GCP environments).

    Raises
    ------
    ImportError
        If ``google-cloud-storage`` is not installed.
    EnvironmentError
        If required environment variables are missing.
    """
    try:
        from google.cloud import storage  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "google-cloud-storage is required for GCP deployment. "
            "Install it with: pip install google-cloud-storage"
        ) from exc

    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. "
            "Point it to your service account JSON key file."
        )
    if not Path(credentials_path).exists():
        raise EnvironmentError(
            f"Service account key file not found: {credentials_path}"
        )

    return storage.Client()


class GCPPersistentDeployer:
    """
    Deploys static HTML pages to Google Cloud Storage using a persistent
    service account key.

    Parameters
    ----------
    bucket_name:
        GCS bucket name.  Falls back to the ``GCP_BUCKET_NAME`` environment
        variable if not supplied.
    prefix:
        Optional path prefix for all uploaded objects (e.g. ``"client-name/"``).
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        prefix: str = "",
    ) -> None:
        self.bucket_name = bucket_name or os.environ.get("GCP_BUCKET_NAME", "")
        if not self.bucket_name:
            raise EnvironmentError(
                "GCP bucket name must be provided either as a constructor argument "
                "or via the GCP_BUCKET_NAME environment variable."
            )
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deploy_page(
        self,
        slug: str,
        html_content: str,
        content_type: str = "text/html; charset=utf-8",
        make_public: bool = True,
    ) -> str:
        """
        Upload a single HTML page to GCS.

        Parameters
        ----------
        slug:
            URL slug for the page (used as the GCS object name).
        html_content:
            Full HTML string to upload.
        content_type:
            MIME type for the object.
        make_public:
            If ``True``, grant public read access to the uploaded object.

        Returns
        -------
        str
            Public URL of the deployed page.
        """
        client = _gcs_client()
        bucket = client.bucket(self.bucket_name)

        object_name = f"{self.prefix}{slug}/index.html"
        blob = bucket.blob(object_name)
        blob.upload_from_string(
            html_content.encode("utf-8"), content_type=content_type
        )
        if make_public:
            blob.make_public()

        url = f"https://storage.googleapis.com/{self.bucket_name}/{object_name}"
        logger.info("Deployed page '%s' → %s", slug, url)
        return url

    def deploy_batch(
        self,
        pages: list[dict[str, Any]],
        deployed_by: str = "system",
    ) -> dict[str, Any]:
        """
        Deploy a list of approved pages to GCS.

        Parameters
        ----------
        pages:
            List of page dicts.  Each must have ``slug`` and
            ``content_html`` (or ``content_markdown`` as fallback).
        deployed_by:
            Identifier of the user or system triggering the deployment.

        Returns
        -------
        dict
            Deployment manifest:
            ``{deployed_count, failed_count, pages, deployed_at, gcp_bucket_path}``
        """
        deployed: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        deployed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        for page in pages:
            slug = page.get("slug", "")
            html = page.get("content_html") or _markdown_fallback(
                page.get("content_markdown", "")
            )

            if not slug:
                failed.append({"page": page.get("title", "?"), "reason": "missing slug"})
                continue
            if not html:
                failed.append({"page": slug, "reason": "no HTML content"})
                continue

            try:
                url = self.deploy_page(slug, html)
                deployed.append(
                    {
                        "slug": slug,
                        "title": page.get("title", slug),
                        "url": url,
                        "deployed_at": deployed_at,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to deploy page '%s': %s", slug, exc)
                failed.append({"page": slug, "reason": str(exc)})

        return {
            "deployed_count": len(deployed),
            "failed_count": len(failed),
            "pages": deployed,
            "failed_pages": failed,
            "deployed_at": deployed_at,
            "deployed_by": deployed_by,
            "gcp_bucket_path": f"gs://{self.bucket_name}/{self.prefix}",
        }

    def check_credentials(self) -> dict[str, Any]:
        """
        Verify that GCP credentials are properly configured.

        Returns
        -------
        dict
            ``{"valid": bool, "project_id": str | None, "error": str | None}``
        """
        try:
            client = _gcs_client()
            project = client.project or os.environ.get("GCP_PROJECT_ID", "unknown")
            return {"valid": True, "project_id": project, "error": None}
        except (ImportError, EnvironmentError, Exception) as exc:  # noqa: BLE001
            return {"valid": False, "project_id": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _markdown_fallback(markdown: str) -> str:
    """Wrap bare Markdown in a minimal HTML scaffold for deployment."""
    if not markdown:
        return ""
    return (
        "<!DOCTYPE html>\n<html>\n<head>"
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "</head>\n<body>\n"
        f"<pre>{markdown}</pre>\n"
        "</body>\n</html>"
    )
