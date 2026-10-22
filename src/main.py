"""The polite scraper: Books to Scrape, first 3 catalogue pages, 60 books.

Run from this folder:  python -m src.main
"""
from .fetch import PoliteFetcher
from .parse import book_links, next_page

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


def main() -> None:
    discover(PoliteFetcher("cache"))


if __name__ == "__main__":
    main()
