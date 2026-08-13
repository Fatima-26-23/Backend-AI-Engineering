"""
The polite scraper — entry point.

Stage 1: fetch and cache HTML.
Stage 2: discover the three catalogue pages and every book link on them.
Stages 3+ (extract/normalize/validate/store/report) not implemented yet.
"""

import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# TODO: replace with the real URL of your repo once it's public — that's the
# whole point of naming yourself in the user-agent.
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR-USERNAME/YOUR-REPO)"
TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
MAX_CATALOGUE_PAGES = 3

CATALOGUE_PAGE_1_URL = "https://books.toscrape.com/catalogue/page-1.html"


def fetch_page(url: str, cache_filename: str) -> str:
    """Return a page's HTML, reading from the local cache if we already have it.

    Prints FETCH on a real network request, or CACHE HIT when reading the
    saved copy — either way it reports the response size, never the HTML
    itself. Only a real (non-cached) fetch pays the politeness delay.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT  {url}  ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: {url} returned status {response.status_code}, expected 200"
        )

    html = response.text
    cache_path.write_text(html, encoding="utf-8")
    print(f"FETCH      {url}  ({len(html)} bytes)")
    time.sleep(REQUEST_DELAY_SECONDS)
    return html


def extract_book_urls(html: str, page_url: str) -> list[str]:
    """Return every book's absolute product URL found on one catalogue page."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for product in soup.select("article.product_pod"):
        link = product.select_one("h3 a")
        if link and link.get("href"):
            urls.append(urljoin(page_url, link["href"]))
    return urls


def find_next_page_url(html: str, page_url: str) -> str | None:
    """Return the absolute URL of the catalogue's own 'next' link, or None."""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        return urljoin(page_url, next_link["href"])
    return None


def discover_book_urls() -> list[str]:
    """Walk the first MAX_CATALOGUE_PAGES catalogue pages via their own
    'next' links, collecting every unique book URL along the way."""
    discovered: list[str] = []
    seen: set[str] = set()
    page_url = CATALOGUE_PAGE_1_URL
    pages_visited = 0

    while page_url and pages_visited < MAX_CATALOGUE_PAGES:
        pages_visited += 1
        cache_filename = f"catalogue-page-{pages_visited}.html"
        html = fetch_page(page_url, cache_filename)

        for book_url in extract_book_urls(html, page_url):
            discovered.append(book_url)
            seen.add(book_url)

        page_url = find_next_page_url(html, page_url)

    unique_urls = list(dict.fromkeys(discovered))  # dedupe, keep order
    print(
        f"catalogue_pages={pages_visited} "
        f"discovered={len(discovered)} "
        f"unique_urls={len(unique_urls)}"
    )
    return unique_urls


def main() -> None:
    discover_book_urls()


if __name__ == "__main__":
    main()