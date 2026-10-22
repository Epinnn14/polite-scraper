"""The polite scraper: Books to Scrape, first 3 catalogue pages, 60 books.

Run from this folder:  python -m src.main
"""
from .fetch import PoliteFetcher

START_URL = "https://books.toscrape.com/catalogue/page-1.html"


def main() -> None:
    fetcher = PoliteFetcher("cache")
    fetcher.get(START_URL)


if __name__ == "__main__":
    main()
