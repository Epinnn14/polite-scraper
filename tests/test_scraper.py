import json

import pytest

from src import fetch
from src.fetch import FetchError, PoliteFetcher
from src.main import FAKE_URL, discover, run
from src.models import Book, normalize
from src.parse import book_record
from tests.fakesite import BASE, FIX, FakeSession, slug

QUIET = lambda *a, **k: None  # noqa: E731


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)


def fetcher(tmp_path, session=None):
    return PoliteFetcher(tmp_path / "cache", delay=0, session=session or FakeSession(), log=QUIET)


def test_parse_real_book_page():
    html = (FIX / "book-a-light-in-the-attic.html").read_text(encoding="utf-8")
    raw = book_record(html, BASE + "a-light-in-the-attic_1000/index.html", BASE + "page-1.html", "2026-10-22T00:00:00Z")
    assert set(raw) == {"title", "product_url", "price_text", "availability_text", "rating_text",
                        "description", "source_page", "fetched_at"}
    assert raw["title"] == "A Light in the Attic"
    assert raw["price_text"] == "£51.77"            # from the product area, not the £ in the info table
    assert raw["availability_text"] == "In stock (22 available)"
    assert raw["rating_text"] == "Three"
    clean = Book.model_validate(normalize(raw))
    assert (clean.price_gbp, clean.stock_count, clean.rating, clean.in_stock) == (51.77, 22, 3, True)


def test_missing_description_is_null_and_whitespace_is_collapsed():
    html = (FIX / "book-no-description.html").read_text(encoding="utf-8")
    raw = book_record(html, BASE + "alice_1/index.html", BASE + "page-1.html", "t")
    assert raw["description"] is None
    assert raw["title"] == "Alice in Wonderland (Alice's Adventures in Wonderland #1)"
    assert raw["price_text"] == "£55.53"


def test_discover_three_pages_sixty_unique(tmp_path, capsys):
    urls, source = discover(fetcher(tmp_path))
    assert len(urls) == 60 and len(set(urls)) == 60
    assert all(u.startswith("https://") for u in urls)
    assert "catalogue_pages=3 discovered=60 unique_urls=60" in capsys.readouterr().out


def test_full_run_is_idempotent_and_uses_cache(tmp_path):
    out = tmp_path / "out"
    first = run(out, tmp_path / "cache", fetcher=fetcher(tmp_path))
    books = json.loads((out / "books.json").read_text(encoding="utf-8"))
    assert len(books) == 60 and first["valid_records"] == 60 and first["pages_fetched"] == 63
    assert all(isinstance(b["price_gbp"], float) for b in books)
    second = run(out, tmp_path / "cache", fetcher=fetcher(tmp_path))
    assert len(json.loads((out / "books.json").read_text(encoding="utf-8"))) == 60   # not 120
    assert second["pages_fetched"] == 0 and second["cache_hits"] == 63
    assert first["changes_since_last_run"]["new"] == 60
    assert second["changes_since_last_run"] == {"new": 0, "changed": 0, "unchanged": 60, "gone": 0}
    assert (out / "books.csv").read_text(encoding="utf-8").count("\n") == 61   # header + 60 rows


def test_one_bad_page_does_not_kill_the_run(tmp_path):
    report = run(tmp_path / "out", tmp_path / "cache", inject_fake_url=True, fetcher=fetcher(tmp_path))
    assert report["failed_pages"] == 1 and report["valid_records"] == 60
    assert report["failures"][0]["url"] == FAKE_URL


def test_retry_once_on_5xx_but_never_on_404_or_403(tmp_path):
    url = f"{BASE}{slug(1)}/index.html"
    s = FakeSession({url: [503, 200]})
    assert fetcher(tmp_path, s).get(url).html            # 503 → retried once → 200
    assert s.calls.count(url) == 2
    for status in (404, 403):
        s = FakeSession({url: [status, 200]})
        with pytest.raises(FetchError):
            fetcher(tmp_path / str(status), s).get(url)
        assert s.calls.count(url) == 1                    # asked exactly once


def test_invalid_record_goes_to_errors_not_books(tmp_path):
    from src.main import validate
    good = normalize({"title": "Ok", "product_url": "https://x/1", "price_text": "£1.00", "availability_text": "In stock",
                      "rating_text": "Two", "description": None, "source_page": "https://x", "fetched_at": "t"})
    books, errors = validate([good, {**good, "product_url": "https://x/2", "price_text": "free!"}])
    assert len(books) == 1 and len(errors) == 1 and "price_gbp" in json.dumps(errors[0]["reason"])


def test_honest_user_agent_is_sent(tmp_path):
    s = FakeSession()
    fetcher(tmp_path, s)
    assert s.headers["User-Agent"].startswith("FlyRankInternship-A9/1.0")
