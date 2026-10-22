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


def _text(el) -> str | None:
    return " ".join(el.get_text(" ", strip=True).split()) if el else None


def book_record(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """The raw record: strings exactly as the page shows them (cleaning happens in Stage 4)."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("article.product_page div.product_main")  # the product area only
    if main is None:
        raise ValueError("product area (div.product_main) not found: not a book page?")
    rating = main.select_one("p.star-rating")
    rating_words = [c for c in (rating.get("class", []) if rating else []) if c != "star-rating"]
    desc = soup.select_one("article.product_page #product_description ~ p")
    return {
        "title": _text(main.select_one("h1")),
        "product_url": product_url,
        "price_text": _text(main.select_one("p.price_color")),
        "availability_text": _text(main.select_one("p.availability")),
        "rating_text": rating_words[0] if rating_words else None,
        "description": _text(desc) or None,  # missing description → null, never invented text
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
