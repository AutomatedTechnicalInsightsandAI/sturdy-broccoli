"""SerpApi SEO data service."""
import requests


def keyword_research(seed_keyword: str, location: str, api_key: str) -> list:
    """Return list of keyword dicts for a seed keyword and location."""
    if not api_key:
        return [
            {'keyword': seed_keyword, 'search_volume': 0, 'cpc': 0.0, 'competition': 'N/A'},
        ]
    params = {
        'engine': 'google_keyword_planner',
        'q': seed_keyword,
        'location': location or 'United States',
        'api_key': api_key,
    }
    try:
        resp = requests.get('https://serpapi.com/search', params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        keywords = []
        for item in data.get('results', []):
            keywords.append({
                'keyword': item.get('keyword', seed_keyword),
                'search_volume': item.get('avg_monthly_searches', 0),
                'cpc': item.get('cpc', {}).get('value', 0.0),
                'competition': item.get('competition', 'N/A'),
            })
        return keywords or [
            {'keyword': seed_keyword, 'search_volume': 0, 'cpc': 0.0, 'competition': 'N/A'}
        ]
    except Exception as exc:
        raise RuntimeError(f'SerpApi keyword research failed: {exc}') from exc


def site_audit(domain: str, api_key: str) -> list:
    """Return list of SEO issue dicts for a domain."""
    import re
    issues = []
    # Validate domain: allow only safe hostname characters to prevent SSRF
    clean_domain = re.sub(r'^https?://', '', domain.strip()).split('/')[0]
    if not re.match(r'^[A-Za-z0-9.\-]+$', clean_domain):
        issues.append({'type': 'Invalid Domain', 'detail': 'Domain contains invalid characters', 'severity': 'critical'})
        return issues
    url = f'https://{clean_domain}'
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        if resp.status_code >= 400:
            issues.append({'type': 'HTTP Error', 'detail': f'Status {resp.status_code}', 'severity': 'critical'})
        content = resp.text.lower()
        if '<title>' not in content:
            issues.append({'type': 'Missing Title Tag', 'detail': 'No <title> tag found', 'severity': 'high'})
        if 'meta name="description"' not in content:
            issues.append({'type': 'Missing Meta Description', 'detail': 'No meta description found', 'severity': 'medium'})
        if '<h1' not in content:
            issues.append({'type': 'Missing H1', 'detail': 'No H1 heading found', 'severity': 'medium'})
        if not resp.url.startswith('https://'):
            issues.append({'type': 'Not HTTPS', 'detail': 'Site does not use HTTPS', 'severity': 'high'})
    except Exception as exc:
        issues.append({'type': 'Crawl Error', 'detail': str(exc), 'severity': 'critical'})
    return issues
