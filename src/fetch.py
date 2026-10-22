"""Polite fetching: honest user-agent, a real timeout, a status check, a delay, and a local HTML cache."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Epinnn14/polite-scraper)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.6  # at least half a second between REAL requests; cache hits never wait


class FetchError(Exception):
    def __init__(self, url: str, reason: str, status: int | None = None):
        super().__init__(f"{reason} ({url})")
        self.url, self.reason, self.status = url, reason, status


@dataclass
class Page:
    url: str
    html: str
    from_cache: bool
    fetched_at: str  # when the HTML actually came from the site (provenance), ISO-8601 UTC


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_name(url: str) -> str:
    """https://books.toscrape.com/catalogue/page-1.html → catalogue-page-1.html (safe, readable file names)."""
    path = urlparse(url).path.strip("/") or "index"
    path = path.removesuffix("/index.html").removesuffix(".html")
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", path) + ".html"


class PoliteFetcher:
    def __init__(self, cache_dir: str | Path = "cache", delay: float = DELAY_SECONDS, session=None, log=print):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.log = log
        self._last_request = 0.0
        self.stats = {"pages_fetched": 0, "cache_hits": 0}

    def get(self, url: str) -> Page:
        cached = self.cache_dir / cache_name(url)
        if cached.exists():
            html = cached.read_text(encoding="utf-8")
            self.stats["cache_hits"] += 1
            self.log(f"CACHE HIT {url} ({len(html):,} chars)")
            return Page(url, html, from_cache=True, fetched_at=_iso(cached.stat().st_mtime))

        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        resp = self.session.get(url, timeout=TIMEOUT_SECONDS)
        if resp.status_code != 200:
            raise FetchError(url, f"HTTP {resp.status_code}", resp.status_code)
        resp.encoding = "utf-8"
        html = resp.text
        cached.write_text(html, encoding="utf-8")
        self.stats["pages_fetched"] += 1
        self.log(f"FETCH {resp.status_code} {url} ({len(html):,} chars)")
        return Page(url, html, from_cache=False, fetched_at=_iso(time.time()))
