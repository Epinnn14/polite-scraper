"""The polite scraper: Books to Scrape, first 3 catalogue pages, 60 books.

Run from this folder:  python -m src.main
"""
from .fetch import FetchError, PoliteFetcher
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
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


def extract(fetcher: PoliteFetcher, urls: list[str], source: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Each page on its own: one broken page is logged and skipped, the other 59 survive."""
    records, failed = [], []
    for url in urls:
        try:
            page = fetcher.get(url)
            records.append(book_record(page.html, url, source.get(url, ""), page.fetched_at))
        except (FetchError, ValueError) as exc:
            print(f"FAILED {url}: {exc}")
            failed.append({"url": url, "error": str(exc)})
    print(f"detail_pages={len(records)} failed_pages={len(failed)}")
    return records, failed


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


CSV_FIELDS = ["title", "price_gbp", "rating", "in_stock", "stock_count", "product_url", "fetched_at"]


def write_csv(path: Path, books: list[dict]) -> None:
    """Flat export. The long description and the raw *_text fields are left out on purpose (CSV is for spreadsheets)."""
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(books)


def diff_against_last_run(path: Path, books: list[dict]) -> dict:
    """Hash each record's content (minus fetched_at) and compare with the previous run: new / changed / unchanged / gone."""
    def digest(b: dict) -> str:
        content = {k: v for k, v in b.items() if k != "fetched_at"}
        return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()[:16]

    now = {b["product_url"]: digest(b) for b in books}
    before = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    result = {
        "new": sum(1 for u in now if u not in before),
        "changed": sum(1 for u in now if u in before and before[u] != now[u]),
        "unchanged": sum(1 for u in now if before.get(u) == now[u]),
        "gone": sum(1 for u in before if u not in now),
    }
    write_json(path, now)
    return result


FAKE_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_0/index.html"


def run(out_dir: Path = Path("output"), cache_dir: Path = Path("cache"), inject_fake_url: bool = False,
        fetcher: PoliteFetcher | None = None) -> dict:
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fetcher = fetcher or PoliteFetcher(cache_dir)
    urls, source = discover(fetcher)
    if inject_fake_url:  # failure test on OUR side: one made-up URL, the real site is never hammered
        urls.append(FAKE_URL)
    raw, failed = extract(fetcher, urls, source)
    books, errors = validate(raw)
    write_json(out_dir / "books.json", books)   # rewritten each run → the same 60 records, never 120
    write_json(out_dir / "errors.json", errors)
    write_csv(out_dir / "books.csv", books)
    changes = diff_against_last_run(out_dir / "fingerprints.json", books)
    report = {
        "started_at": started_at,
        "duration_seconds": round(time.monotonic() - started, 2),
        "catalogue_pages": len({source[u] for u in source}),
        "pages_fetched": fetcher.stats["pages_fetched"],
        "cache_hits": fetcher.stats["cache_hits"],
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": len(failed),
        "changes_since_last_run": changes,
        "failures": failed,
    }
    write_json(out_dir / "run-report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "failures"}))
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Polite scraper for books.toscrape.com (first 3 catalogue pages)")
    ap.add_argument("--inject-fake-url", action="store_true", help="add one made-up book URL to prove failures are survived")
    args = ap.parse_args()
    run(inject_fake_url=args.inject_fake_url)


if __name__ == "__main__":
    main()
