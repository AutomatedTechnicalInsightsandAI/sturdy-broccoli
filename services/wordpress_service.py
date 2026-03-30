"""WordPress REST API service."""
import requests
from requests.auth import HTTPBasicAuth


def test_connection(wp_url: str, username: str, app_password: str) -> bool:
    """Test WordPress REST API connectivity."""
    if not wp_url:
        return False
    try:
        url = wp_url.rstrip('/') + '/wp-json/wp/v2/users/me'
        resp = requests.get(url, auth=HTTPBasicAuth(username, app_password), timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def publish_content(
    wp_url: str,
    username: str,
    app_password: str,
    title: str,
    content: str,
    content_type: str = 'post',
    status: str = 'draft',
) -> dict:
    """Publish content to WordPress. Returns dict with post_id and post_url."""
    endpoint = wp_url.rstrip('/') + f'/wp-json/wp/v2/{content_type}s'
    payload = {'title': title, 'content': content, 'status': status}
    resp = requests.post(
        endpoint,
        json=payload,
        auth=HTTPBasicAuth(username, app_password),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        'post_id': data.get('id'),
        'post_url': data.get('link', ''),
    }


def update_post(
    wp_url: str,
    username: str,
    app_password: str,
    post_id: int,
    title: str,
    content: str,
    status: str = 'draft',
) -> dict:
    """Update an existing WordPress post."""
    endpoint = wp_url.rstrip('/') + f'/wp-json/wp/v2/posts/{post_id}'
    payload = {'title': title, 'content': content, 'status': status}
    resp = requests.put(
        endpoint,
        json=payload,
        auth=HTTPBasicAuth(username, app_password),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        'post_id': data.get('id'),
        'post_url': data.get('link', ''),
    }
