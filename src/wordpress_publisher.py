"""
wordpress_publisher.py

WordPress REST API publishing engine for the Sturdy Broccoli SEO platform.

Responsibilities
~~~~~~~~~~~~~~~~
- Manage WordPress site connections (store encrypted credentials)
- Publish or update pages as WordPress posts via the WP REST API
- Batch-publish multiple pages to one or more WordPress sites
- Schedule posts for future publication dates
- Track publish status, post URLs, and errors in the database
- Replace internal Sturdy Broccoli page references with live WordPress URLs

All persistence is delegated to :class:`~src.database.Database`.

.. note::
    Real HTTP calls to the WordPress REST API require the ``requests``
    library.  When ``requests`` is unavailable (e.g. in unit-test
    environments that mock the network) the publisher falls back to a
    simulated mode.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from .database import Database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lightweight credential obfuscation
# ---------------------------------------------------------------------------
# NOTE: This is NOT real encryption.  Production deployments should replace
# the obfuscation helpers below with a proper key-management solution such
# as Google Cloud KMS or HashiCorp Vault.
#
# The obfuscation salt can be overridden by setting the environment variable
# ``STURDY_WP_OBFUSCATION_SALT`` to a custom bytes value (hex-encoded string).
# Using a non-default salt does NOT make this cryptographically secure.

import os as _os

_OBFUSCATION_SALT = bytes.fromhex(
    _os.environ.get("STURDY_WP_OBFUSCATION_SALT", "")
) if _os.environ.get("STURDY_WP_OBFUSCATION_SALT") else b"sturdy-broccoli-wp"


def _obfuscate(plaintext: str) -> str:
    """XOR-based Base64 obfuscation (NOT cryptographically secure)."""
    key = hashlib.sha256(_OBFUSCATION_SALT).digest()
    data = plaintext.encode()
    out = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(out).decode()


def _deobfuscate(ciphertext: str) -> str:
    """Reverse of :func:`_obfuscate`."""
    key = hashlib.sha256(_OBFUSCATION_SALT).digest()
    data = base64.urlsafe_b64decode(ciphertext.encode())
    out = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return out.decode()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wp_date_format(dt_iso: str) -> str:
    """
    Convert an ISO-8601 timestamp string to WordPress GMT date format
    (``YYYY-MM-DDTHH:MM:SS``).
    """
    try:
        dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError):
        return dt_iso


def _build_wp_post_payload(
    title: str,
    content: str,
    status: str = "draft",
    slug: str = "",
    excerpt: str = "",
    date_gmt: str | None = None,
    categories: list[int] | None = None,
    tags: list[int] | None = None,
    author: int | None = None,
) -> dict[str, Any]:
    """Build the JSON payload for a WordPress REST API post create/update."""
    payload: dict[str, Any] = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        payload["slug"] = slug
    if excerpt:
        payload["excerpt"] = excerpt
    if date_gmt:
        payload["date_gmt"] = _wp_date_format(date_gmt)
    if categories:
        payload["categories"] = categories
    if tags:
        payload["tags"] = tags
    if author:
        payload["author"] = author
    return payload


def _normalize_wp_status(wp_status: str) -> str:
    """
    Map WordPress REST API post statuses to the internal DB statuses.

    WordPress uses ``'publish'`` and ``'future'``; our DB schema stores
    ``'published'`` and ``'scheduled'``.
    """
    mapping = {
        "publish": "published",
        "future": "scheduled",
    }
    return mapping.get(wp_status, wp_status)


def _replace_internal_links(
    content: str,
    link_map: dict[str, str],
) -> str:
    """
    Replace Sturdy Broccoli internal page references with live WordPress URLs.

    Parameters
    ----------
    content:
        HTML or Markdown content body.
    link_map:
        Dict mapping Sturdy Broccoli slugs (or internal URLs) to published
        WordPress post URLs.

    Returns
    -------
    str
        Content with internal references replaced.
    """
    for internal, external in link_map.items():
        content = content.replace(internal, external)
    return content


# ---------------------------------------------------------------------------
# WordPressPublisher
# ---------------------------------------------------------------------------


class WordPressPublisher:
    """
    High-level WordPress publishing API for the Sturdy Broccoli platform.

    Parameters
    ----------
    db:
        :class:`~src.database.Database` instance to use for persistence.
    http_client:
        Optional callable used to make HTTP requests.  Signature::

            http_client(method, url, *, auth, json) -> response_like

        where ``response_like`` exposes ``.status_code``, ``.json()``, and
        ``.text``.  When ``None`` the publisher attempts to import
        ``requests``; if that also fails it raises ``RuntimeError``.
    """

    def __init__(
        self,
        db: Database,
        http_client: Any = None,
    ) -> None:
        self._db = db
        self._http = http_client

    def _get_http(self) -> Any:
        if self._http is not None:
            return self._http
        try:
            import requests  # type: ignore[import-not-found]
            return requests
        except ImportError as exc:
            raise RuntimeError(
                "The 'requests' library is required for live WordPress publishing. "
                "Install it with: pip install requests"
            ) from exc

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def add_connection(
        self,
        site_url: str,
        api_username: str,
        api_password: str,
        site_name: str = "",
        client_id: int | None = None,
    ) -> int:
        """
        Register a new WordPress site connection.

        Credentials are obfuscated before storage.  Returns the database id
        of the new connection.
        """
        site_url = site_url.rstrip("/")
        encrypted = _obfuscate(api_password)
        return self._db.create_wordpress_connection(
            site_url=site_url,
            site_name=site_name or site_url,
            api_username=api_username,
            api_password_encrypted=encrypted,
            client_id=client_id,
        )

    def list_connections(self, client_id: int | None = None) -> list[dict[str, Any]]:
        """Return all stored WordPress connections (passwords redacted)."""
        conns = self._db.list_wordpress_connections(client_id=client_id)
        for c in conns:
            c.pop("api_password_encrypted", None)
        return conns

    def remove_connection(self, connection_id: int) -> None:
        """Delete a WordPress connection and all its post records."""
        self._db.delete_wordpress_connection(connection_id)

    def test_connection(self, connection_id: int) -> dict[str, Any]:
        """
        Attempt a lightweight call to the WordPress REST API to verify
        credentials.

        Returns
        -------
        dict
            Keys: ``success`` (bool), ``message`` (str), ``site_name`` (str).
        """
        conn = self._db.get_wordpress_connection(connection_id)
        if conn is None:
            return {"success": False, "message": "Connection not found.", "site_name": ""}

        try:
            http = self._get_http()
        except RuntimeError as exc:
            return {"success": False, "message": str(exc), "site_name": ""}

        password = _deobfuscate(conn["api_password_encrypted"])
        url = f"{conn['site_url']}/wp-json/wp/v2/users/me"
        try:
            resp = http.get(url, auth=(conn["api_username"], password), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "message": "Connection successful.",
                    "site_name": data.get("name", conn.get("site_name", "")),
                }
            return {
                "success": False,
                "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "site_name": "",
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "site_name": ""}

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_page(
        self,
        page_id: int,
        connection_id: int,
        title: str,
        content: str,
        status: str = "draft",
        slug: str = "",
        excerpt: str = "",
        schedule_date: str | None = None,
        categories: list[int] | None = None,
        tags: list[int] | None = None,
        author: int | None = None,
        link_map: dict[str, str] | None = None,
        client_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Publish a single page to a WordPress site.

        Parameters
        ----------
        page_id:
            Sturdy Broccoli page ID.
        connection_id:
            WordPress connection to use.
        title:
            Post title.
        content:
            Post content (HTML or Markdown).
        status:
            WordPress post status (``'draft'``, ``'publish'``, or
            ``'future'`` for scheduled posts).
        slug:
            Optional URL slug override.
        excerpt:
            Optional post excerpt / meta description.
        schedule_date:
            ISO-8601 date/time string for scheduled publication.  Forces
            *status* to ``'future'``.
        categories:
            List of WP category IDs.
        tags:
            List of WP tag IDs.
        author:
            WP author user ID.
        link_map:
            Dict mapping internal slugs to live WordPress URLs for
            internal-link replacement.
        client_id:
            Optional client ID to associate with the post record.

        Returns
        -------
        dict
            Keys: ``success`` (bool), ``wp_record_id``, ``post_id``,
            ``post_url``, ``status``, ``message``.
        """
        conn = self._db.get_wordpress_connection(connection_id)
        if conn is None:
            return {
                "success": False,
                "wp_record_id": None,
                "post_id": "",
                "post_url": "",
                "status": "failed",
                "message": f"WordPress connection {connection_id} not found.",
            }

        if schedule_date:
            status = "future"

        # Replace internal links
        if link_map:
            content = _replace_internal_links(content, link_map)

        # Record the attempt in the database before making the HTTP call
        record_id = self._db.create_wordpress_post(
            wordpress_connection_id=connection_id,
            page_id=page_id,
            client_id=client_id,
            status="draft",
        )

        try:
            http = self._get_http()
        except RuntimeError as exc:
            self._db.update_wordpress_post_status(
                record_id, "failed", error_message=str(exc)
            )
            return {
                "success": False,
                "wp_record_id": record_id,
                "post_id": "",
                "post_url": "",
                "status": "failed",
                "message": str(exc),
            }

        password = _deobfuscate(conn["api_password_encrypted"])
        api_url = f"{conn['site_url']}/wp-json/wp/v2/posts"
        payload = _build_wp_post_payload(
            title=title,
            content=content,
            status=status,
            slug=slug,
            excerpt=excerpt,
            date_gmt=schedule_date,
            categories=categories,
            tags=tags,
            author=author,
        )

        try:
            resp = http.post(
                api_url,
                auth=(conn["api_username"], password),
                json=payload,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                post_id = str(data.get("id", ""))
                post_url = data.get("link", "")
                final_status = _normalize_wp_status(data.get("status", status))
                self._db.update_wordpress_post_status(
                    record_id, final_status, post_id=post_id, post_url=post_url
                )
                return {
                    "success": True,
                    "wp_record_id": record_id,
                    "post_id": post_id,
                    "post_url": post_url,
                    "status": final_status,
                    "message": "Published successfully.",
                }
            error_msg = f"HTTP {resp.status_code}: {resp.text[:300]}"
            self._db.update_wordpress_post_status(
                record_id, "failed", error_message=error_msg
            )
            return {
                "success": False,
                "wp_record_id": record_id,
                "post_id": "",
                "post_url": "",
                "status": "failed",
                "message": error_msg,
            }
        except Exception as exc:
            self._db.update_wordpress_post_status(
                record_id, "failed", error_message=str(exc)
            )
            return {
                "success": False,
                "wp_record_id": record_id,
                "post_id": "",
                "post_url": "",
                "status": "failed",
                "message": str(exc),
            }

    def update_post(
        self,
        wp_record_id: int,
        title: str | None = None,
        content: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an already-published WordPress post.

        Retrieves the stored post record, then issues a PUT request to the
        WordPress REST API.

        Returns
        -------
        dict
            Keys: ``success``, ``post_id``, ``post_url``, ``status``,
            ``message``.
        """
        record = self._db.get_wordpress_post(wp_record_id)
        if record is None:
            return {"success": False, "message": "WP post record not found.", "post_id": ""}

        conn = self._db.get_wordpress_connection(record["wordpress_connection_id"])
        if conn is None:
            return {"success": False, "message": "WordPress connection not found.", "post_id": ""}

        try:
            http = self._get_http()
        except RuntimeError as exc:
            return {"success": False, "message": str(exc), "post_id": ""}

        password = _deobfuscate(conn["api_password_encrypted"])
        api_url = f"{conn['site_url']}/wp-json/wp/v2/posts/{record['post_id']}"
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if status is not None:
            payload["status"] = status

        try:
            resp = http.put(
                api_url,
                auth=(conn["api_username"], password),
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                new_status = _normalize_wp_status(data.get("status", record["status"]))
                post_url = data.get("link", record["post_url"])
                self._db.update_wordpress_post_status(
                    wp_record_id,
                    new_status,
                    post_id=str(record["post_id"]),
                    post_url=post_url,
                )
                return {
                    "success": True,
                    "post_id": str(record["post_id"]),
                    "post_url": post_url,
                    "status": new_status,
                    "message": "Post updated successfully.",
                }
            error_msg = f"HTTP {resp.status_code}: {resp.text[:300]}"
            return {
                "success": False,
                "post_id": str(record["post_id"]),
                "post_url": "",
                "status": "failed",
                "message": error_msg,
            }
        except Exception as exc:
            return {"success": False, "post_id": "", "post_url": "", "status": "failed", "message": str(exc)}

    def batch_publish(
        self,
        pages: list[dict[str, Any]],
        connection_id: int,
        default_status: str = "draft",
        client_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Publish multiple pages to a single WordPress connection.

        Parameters
        ----------
        pages:
            List of dicts.  Each dict must contain at least ``page_id``,
            ``title``, and ``content``.  Optional keys: ``slug``,
            ``excerpt``, ``schedule_date``, ``categories``, ``tags``,
            ``author``, ``link_map``.
        connection_id:
            WordPress connection to use for all pages.
        default_status:
            Fallback ``status`` when not specified per page.
        client_id:
            Optional client ID for all records.

        Returns
        -------
        list[dict]
            One result dict per page (see :meth:`publish_page`).
        """
        results = []
        for page in pages:
            result = self.publish_page(
                page_id=page["page_id"],
                connection_id=connection_id,
                title=page["title"],
                content=page["content"],
                status=page.get("status", default_status),
                slug=page.get("slug", ""),
                excerpt=page.get("excerpt", ""),
                schedule_date=page.get("schedule_date"),
                categories=page.get("categories"),
                tags=page.get("tags"),
                author=page.get("author"),
                link_map=page.get("link_map"),
                client_id=client_id,
            )
            result["page_id"] = page["page_id"]
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Publishing history / status
    # ------------------------------------------------------------------

    def get_publish_history(
        self,
        page_id: int | None = None,
        client_id: int | None = None,
        connection_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return WordPress post records with optional filters."""
        return self._db.list_wordpress_posts(
            page_id=page_id,
            client_id=client_id,
            connection_id=connection_id,
        )

    def get_publish_status(self, page_id: int) -> dict[str, Any]:
        """
        Return a summary of the most recent publish attempt for *page_id*.

        Returns
        -------
        dict
            Keys: ``published`` (bool), ``status``, ``post_url``,
            ``post_id``, ``created_at``.  All values are empty/False if
            the page has never been published.
        """
        records = self._db.list_wordpress_posts(page_id=page_id)
        if not records:
            return {
                "published": False,
                "status": "",
                "post_url": "",
                "post_id": "",
                "created_at": "",
            }
        latest = records[0]
        return {
            "published": latest["status"] in ("publish", "published", "future"),
            "status": latest["status"],
            "post_url": latest["post_url"],
            "post_id": latest["post_id"],
            "created_at": latest["created_at"],
        }

    def get_categories(self, connection_id: int) -> list[dict[str, Any]]:
        """
        Fetch available categories from a WordPress site.

        Returns
        -------
        list[dict]
            Each dict contains ``id``, ``name``, ``slug``, and ``count``.
            Returns an empty list on failure.
        """
        conn = self._db.get_wordpress_connection(connection_id)
        if conn is None:
            return []

        try:
            http = self._get_http()
        except RuntimeError:
            return []

        password = _deobfuscate(conn["api_password_encrypted"])
        url = f"{conn['site_url']}/wp-json/wp/v2/categories"
        try:
            resp = http.get(
                url,
                auth=(conn["api_username"], password),
                params={"per_page": 100},
                timeout=15,
            )
            if resp.status_code == 200:
                raw = resp.json()
                return [
                    {
                        "id": item.get("id"),
                        "name": item.get("name", ""),
                        "slug": item.get("slug", ""),
                        "count": item.get("count", 0),
                    }
                    for item in (raw if isinstance(raw, list) else [])
                ]
        except Exception:
            pass
        return []

    def get_tags(self, connection_id: int) -> list[dict[str, Any]]:
        """
        Fetch available tags from a WordPress site.

        Returns
        -------
        list[dict]
            Each dict contains ``id``, ``name``, ``slug``, and ``count``.
            Returns an empty list on failure.
        """
        conn = self._db.get_wordpress_connection(connection_id)
        if conn is None:
            return []

        try:
            http = self._get_http()
        except RuntimeError:
            return []

        password = _deobfuscate(conn["api_password_encrypted"])
        url = f"{conn['site_url']}/wp-json/wp/v2/tags"
        try:
            resp = http.get(
                url,
                auth=(conn["api_username"], password),
                params={"per_page": 100},
                timeout=15,
            )
            if resp.status_code == 200:
                raw = resp.json()
                return [
                    {
                        "id": item.get("id"),
                        "name": item.get("name", ""),
                        "slug": item.get("slug", ""),
                        "count": item.get("count", 0),
                    }
                    for item in (raw if isinstance(raw, list) else [])
                ]
        except Exception:
            pass
        return []

    def batch_publish_staggered(
        self,
        pages: list[dict[str, Any]],
        connection_id: int,
        start_date: str,
        interval_days: int = 1,
        publish_hour: int = 9,
        default_status: str = "future",
        client_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Publish multiple pages with staggered scheduling.

        Each page is assigned an ``schedule_date`` that is *interval_days*
        apart, starting from *start_date*.

        Parameters
        ----------
        pages:
            List of page dicts (same format as :meth:`batch_publish`).
        connection_id:
            WordPress connection to publish to.
        start_date:
            ISO-8601 date string for the first page (``YYYY-MM-DD``).
        interval_days:
            Number of days between each page publication.
        publish_hour:
            Hour of day (0-23) to schedule each post (UTC).
        default_status:
            WP status to use (``'future'`` or ``'publish'``).
        client_id:
            Optional client ID for all records.

        Returns
        -------
        list[dict]
            One result dict per page, same format as :meth:`publish_page`.
        """
        from datetime import date, timedelta

        try:
            base = date.fromisoformat(start_date)
        except ValueError:
            base = date.today()

        results = []
        for i, page in enumerate(pages):
            scheduled_dt = base + timedelta(days=i * interval_days)
            schedule_iso = (
                f"{scheduled_dt.isoformat()}T{publish_hour:02d}:00:00"
            )
            page_copy = dict(page)
            page_copy.setdefault("status", default_status)
            page_copy["schedule_date"] = schedule_iso

            result = self.publish_page(
                page_id=page_copy["page_id"],
                connection_id=connection_id,
                title=page_copy["title"],
                content=page_copy["content"],
                status=page_copy.get("status", default_status),
                slug=page_copy.get("slug", ""),
                excerpt=page_copy.get("excerpt", ""),
                schedule_date=page_copy["schedule_date"],
                categories=page_copy.get("categories"),
                tags=page_copy.get("tags"),
                author=page_copy.get("author"),
                link_map=page_copy.get("link_map"),
                client_id=client_id,
            )
            result["page_id"] = page_copy["page_id"]
            result["scheduled_date"] = schedule_iso
            results.append(result)
        return results
