"""File-based cache for scraped page data. Keyed by normalized URL to avoid re-scraping the same page."""
import hashlib
import json
import os
from datetime import datetime
from urllib.parse import urlparse, urlunparse


def _cache_dir():
    d = os.environ.get("SCRAPE_CACHE_DIR", "scrape_cache")
    os.makedirs(d, exist_ok=True)
    return d


def normalize_url(url):
    """Normalize URL for cache key: strip fragment, lowercase scheme and host."""
    if not url or not url.strip():
        return ""
    url = url.strip()
    try:
        parsed = urlparse(url)
        # Reconstruct without fragment; lowercase scheme and netloc
        normalized = urlunparse((
            (parsed.scheme or "https").lower(),
            (parsed.netloc or "").lower(),
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",  # no fragment
        ))
        return normalized
    except Exception:
        return url


def cache_key(url):
    """Safe filename from URL (hash of normalized URL)."""
    normalized = normalize_url(url)
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return h + ".json"


def get_cached_scrape(url):
    """
    Return cached scraped data for url, or None if not found/expired.
    Returns dict with keys: url, scraped_at, data (the website_data dict).
    """
    if not url or not url.strip():
        return None
    path = os.path.join(_cache_dir(), cache_key(url))
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        return entry.get("data")
    except (json.JSONDecodeError, OSError):
        return None


def set_cached_scrape(url, data):
    """Save scraped data to cache. data is the website_data dict (url + elements)."""
    if not url or not url.strip():
        return
    path = os.path.join(_cache_dir(), cache_key(url))
    entry = {
        "url": normalize_url(url),
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "data": data,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
