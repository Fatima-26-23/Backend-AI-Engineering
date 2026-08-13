<<<<<<< HEAD

=======
# The Polite Scraper

A small, polite scraping pipeline for [Books to Scrape](https://books.toscrape.com):
fetch → extract → normalize → validate → store → report.

Built for FlyRank Internship, Backend Track, Week 5, Assignment A9.

## Target classification

- **Site:** [books.toscrape.com](https://books.toscrape.com) — a fictional bookstore
  built by [toscrape.com](https://toscrape.com) explicitly as a scraping sandbox. Its own
  landing page describes it as a site that "desperately wants to be scraped" and calls
  itself "a safe place for beginners learning web scraping."
- **Why this site:** it exists for exactly this purpose, has no login, no paywall, and
  no real user data behind it.
- **Scope:** the first 3 catalogue pages only (60 books total). No other pages, and no
  other site, are touched by this code.
- **Data collected:** title, product URL, price, availability, star rating, description,
  and provenance (source page + fetch timestamp) for each of the 60 books.
- **`robots.txt` result:** requested `https://books.toscrape.com/robots.txt` once —
  it returned **404 Not Found**. No robots file found. (A missing file is not the same
  as permission — the actual permission comes from the site's own "built to be scraped"
  description above.)

I will not reuse this code on another site without checking its rules and terms first.

## Status

Work in progress — stages are being built and checkpointed one at a time. See commit
history for progress; each stage's checkpoint is noted below as it's completed.

- [x] Stage 0: classify scraping target
- [ ] Stage 1: fetch and cache HTML
- [ ] Stage 2: discover three catalogue pages
- [ ] Stage 3: extract book details
- [ ] Stage 4: validate normalized records
- [ ] Stage 5: survive failures, report the run
- [ ] Stage 6: publish scraper evidence
>>>>>>> 8f14e24 (Stage 0: classify scraping target)
