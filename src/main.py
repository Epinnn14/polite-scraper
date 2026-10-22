"""The polite scraper: Books to Scrape, first 3 catalogue pages, 60 books.

Run from this folder:  python -m src.main
"""
from .fetch import PoliteFetcher
import json
from pathlib import Path

from pydantic import ValidationError

from .models import Book, normalize
from .parse import book_links, book_record, next_page

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3


def discover(fetcher: PoliteFetcher) -> tuple[list[str], dict[str, str]]:
    """Walk catalogue pages via their 'next' links. Returns unique book URLs and url → source catalogue page."""
    url, pages, found, source = START_URL, 0, [], {}
    while url and pages < MAX_CATALOGUE_PAGES:
        page = fetcher.get(url)
        pages += 1
        for link in book_links(page.html, url):
            found.append(link)
            source.setdefault(link, url)
        url = next_page(page.html, url)
    unique = list(dict.fromkeys(found))  # keeps order, drops duplicates
    print(f"catalogue_pages={pages} discovered={len(found)} unique_urls={len(unique)}")
    return unique, source


def extract(fetcher: PoliteFetcher, urls: list[str], source: dict[str, str]) -> list[dict]:
    records = []
    for url in urls:
        page = fetcher.get(url)
        records.append(book_record(page.html, url, source.get(url, ""), page.fetched_at))
    print(f"detail_pages={len(records)}")
    return records


def validate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Normalise + validate every record. Good ones are de-duplicated by product_url; bad ones keep their reason."""
    good: dict[str, dict] = {}
    bad: list[dict] = []
    for raw in records:
        try:
            book = Book.model_validate(normalize(raw))
        except ValidationError as exc:
            bad.append({"product_url": raw.get("product_url"), "reason": exc.errors(include_url=False), "raw": raw})
            continue
        good.setdefault(book.product_url, book.model_dump())
    return list(good.values()), bad


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def main() -> None:
    fetcher = PoliteFetcher("cache")
    urls, source = discover(fetcher)
    books, errors = validate(extract(fetcher, urls, source))
    write_json(Path("output/books.json"), books)      # overwritten each run → same 60 records, never 120
    write_json(Path("output/errors.json"), errors)
    print(f"valid_records={len(books)} invalid_records={len(errors)}")


if __name__ == "__main__":
    main()
