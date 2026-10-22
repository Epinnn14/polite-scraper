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
