"""HTML → data. Selectors aim at the product area, never at 'the first thing that looks like a price'."""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def book_links(html: str, page_url: str) -> list[str]:
    """Absolute URLs of every book on one catalogue page (relative hrefs resolved with urljoin)."""
    soup = BeautifulSoup(html, "html.parser")
    return [urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a[href]")]


def next_page(html: str, page_url: str) -> str | None:
    """Follow the catalogue's own 'next' link, so the site tells us what the pages are."""
    a = BeautifulSoup(html, "html.parser").select_one("ul.pager li.next a[href]")
    return urljoin(page_url, a["href"]) if a else None
