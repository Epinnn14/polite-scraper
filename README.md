# The polite scraper (FlyRank Backend track, A9)

## Target classification

| Question | Answer |
|---|---|
| Which site | **Books to Scrape**: https://books.toscrape.com |
| Why this site | It is a **sandbox built for practising scraping**. toscrape.com describes itself as a place to practise web scraping, and every book page shows: *"Warning! This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning."* |
| How much | Only the **first 3 catalogue pages** (`/catalogue/page-1.html` → page 3) and the **60 book pages** they link to, which is 63 pages in total |
| What data | title, price, availability, star rating, description, product URL, plus where and when it was fetched |
| robots.txt | `GET https://books.toscrape.com/robots.txt` → **404 Not Found**, so **no robots file was found**. A missing file is not permission. The permission here comes from the site being a declared sandbox. |
| Why it's appropriate | The site exists so people can practise exactly this, the data is fake and public, and the scope is small and fixed. |

I will not reuse this code on another site without checking its rules and terms first.

## Run it (one command)

Python 3.10+ (Python lane: Requests, Beautiful Soup, Pydantic).

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m src.main                                        # add --inject-fake-url to prove failures are survived
```

A first run takes about 40 seconds, because there are 63 polite requests with a pause between each. Later runs read the
HTML cache and finish in about 1 second. It writes:

| File | What |
|---|---|
| `output/books.json` | the 60 validated records |
| `output/errors.json` | records that failed the schema, with the reason (normally `[]`) |
| `output/run-report.json` | the honest numbers for this run |
| `output/books.csv` | flat export *(extra)* |
| `cache/*.html` | the saved pages (git-ignored) |

Tests (offline, no network): `pip install -r requirements-dev.txt` then `pytest -q`, **8 pass**.

## The pipeline

| Step | Code | Proof |
|---|---|---|
| Fetch | `src/fetch.py`: user-agent, 10 s timeout, status check, ≥0.6 s delay, cache | `FETCH 200 …` / `CACHE HIT …` lines |
| Discover | `src/parse.py: book_links / next_page`: `urljoin`, follows the site's own **next** link, stops after 3 pages | `catalogue_pages=3 discovered=60 unique_urls=60` |
| Extract | `book_record()`: selectors scoped to `div.product_main` | 8 raw keys per record, `description: null` when missing |
| Normalize | `src/models.py: normalize()`: `"£51.77"` → `51.77`, stock count, rating word → 1–5 | raw and clean values side by side |
| Validate | Pydantic `Book` schema | bad records go to `errors.json`, never into `books.json` |
| Store | `output/books.json`, rewritten each run, de-duplicated by `product_url` | still 60 records after a second run |
| Report | `output/run-report.json` | see below |

## Record schema

```text
title: str (required)            product_url: absolute https URL (identity)   source_page: https URL (provenance)
price_text: str  "£51.77"        price_gbp: float > 0                        fetched_at: ISO-8601 UTC (provenance)
availability_text: str           in_stock: bool      stock_count: int | null
rating_text: One|Two|Three|Four|Five                 rating: 1-5
description: str | null          (some books have none; never invented)
```

## Politeness rules followed

- **Honest user-agent:** `FlyRankInternship-A9/1.0 (+https://github.com/Epinnn14/polite-scraper)`.
- **Timeout:** 10 seconds on every request, so it never waits forever.
- **Delay:** at least 0.6 seconds between real requests. Cache hits don't wait, because they never leave the machine.
- **Cache:** every page is fetched once, and development runs read `cache/`.
- **Retries:** one retry on a timeout, connection error or **5xx**. **No retry on 404** (the page doesn't exist) **or 403**
  (the site said no).
- **Scope:** only the first 3 catalogue pages.

## Run report (proof)

<!-- TODO before submitting: paste the output/run-report.json from your first real run here, and commit output/books.json + output/run-report.json as the sample output. -->

The failure test (`python -m src.main --inject-fake-url`) adds one made-up book URL. The run still finishes, `books.json`
still has 60 records, and the report shows `"failed_pages": 1`.

## Why no browser

The data is already in the HTML the server sends. There's no JavaScript rendering and no hidden API call. A headless
browser would only add cost and time.

## Ethics note

- Use an official API whenever one exists.
- Never bypass logins, paywalls, rate limits or blocks.
- Collect only what you need, go slowly, and say who you are.
- A sandbox like this one is the only kind of site this code is meant for.

## Limitation

- The selectors are tied to this site's current markup. If the page layout changes, the parser fails (loudly, through the
  schema and `errors.json`) instead of adapting.
- The tests use saved fixtures and an offline copy of the site's structure, so they can't notice a change on the real site.

## How AI was used

Built **with an AI assistant (Claude)**, and stated openly here. Verified by running it:

- the 8 offline tests
- parsing a real page saved from books.toscrape.com (`tests/fixtures/`)

The live run against the site has to be done on a machine that can reach it. Its report goes in the section above.
