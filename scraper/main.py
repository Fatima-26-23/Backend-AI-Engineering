"""
The polite scraper — entry point.

Stage 1: fetch and cache HTML.
Stage 2: discover the three catalogue pages and every book link on them.
Stage 3: visit every book page and extract the raw record fields.
Stages 4+ (normalize/validate/store/report) not implemented yet.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, field_validator

# TODO: replace with the real URL of your repo once it's public — that's the
# whole point of naming yourself in the user-agent.
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR-USERNAME/YOUR-REPO)"
TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
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


def discover_book_urls() -> list[dict]:
    """Walk the first MAX_CATALOGUE_PAGES catalogue pages via their own
    'next' links, collecting every unique book URL along with which
    catalogue page it was found on (its source_page, for provenance)."""
    discovered: list[dict] = []
    page_url = CATALOGUE_PAGE_1_URL
    pages_visited = 0

    while page_url and pages_visited < MAX_CATALOGUE_PAGES:
        pages_visited += 1
        cache_filename = f"catalogue-page-{pages_visited}.html"
        html = fetch_page(page_url, cache_filename)

        for book_url in extract_book_urls(html, page_url):
            discovered.append({"url": book_url, "source_page": page_url})

        page_url = find_next_page_url(html, page_url)

    # Dedupe by url, keeping the first (source_page, order) we saw it at.
    unique_by_url: dict[str, dict] = {}
    for entry in discovered:
        unique_by_url.setdefault(entry["url"], entry)
    unique_entries = list(unique_by_url.values())

    print(
        f"catalogue_pages={pages_visited} "
        f"discovered={len(discovered)} "
        f"unique_urls={len(unique_entries)}"
    )
    return unique_entries


def cache_filename_for_book(product_url: str) -> str:
    """Turn a book's product URL into a stable, unique cache filename.

    e.g. https://.../catalogue/a-light-in-the-attic_1000/index.html
      -> book-a-light-in-the-attic_1000.html
    """
    slug = product_url.rstrip("/").split("/")[-2]
    return f"book-{slug}.html"


def extract_book_record(html: str, product_url: str, source_page: str) -> dict:
    """Return the raw record for one book detail page. Every field listed in
    the assignment is always present; description is None (never invented)
    when the page has none."""
    soup = BeautifulSoup(html, "html.parser")
    main_panel = soup.select_one(".product_main")

    title = main_panel.select_one("h1").get_text(strip=True)
    price_text = main_panel.select_one(".price_color").get_text(strip=True)
    availability_text = main_panel.select_one(".availability").get_text(strip=True)

    rating_text = None
    rating_tag = main_panel.select_one(".star-rating")
    if rating_tag:
        rating_words = [c for c in rating_tag.get("class", []) if c != "star-rating"]
        if rating_words:
            rating_text = rating_words[0]

    description = None
    description_heading = soup.select_one("#product_description")
    if description_heading:
        description_p = description_heading.find_next_sibling("p")
        if description_p:
            description = description_p.get_text(strip=True)

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def extract_all_book_records(book_entries: list[dict]) -> list[dict]:
    """Fetch (and cache) every book detail page and extract its raw record."""
    records = []
    for entry in book_entries:
        html = fetch_page(entry["url"], cache_filename_for_book(entry["url"]))
        record = extract_book_record(html, entry["url"], entry["source_page"])
        records.append(record)

    print(f"detail_pages={len(records)}")
    return records


class BookRecord(BaseModel):
    """The shape of one finished, storable record. Required fields must be
    present and correctly typed; description and rating_text are the only
    optional ones, since not every book page has them."""

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None = None
    description: str | None = None
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_absolute_https_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError(f"expected an absolute https:// URL, got {value!r}")
        return value

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError(f"price_gbp must be positive, got {value!r}")
        return value


def normalize_price(price_text: str) -> float:
    """Turn '£51.77' into 51.77. Raises ValueError if no number is found,
    rather than silently returning something wrong."""
    match = re.search(r"[\d]+\.?[\d]*", price_text)
    if not match:
        raise ValueError(f"could not find a number in price_text {price_text!r}")
    return float(match.group())


def normalize_record(raw_record: dict) -> dict:
    """Turn one raw record into a normalized one: add price_gbp, keep
    price_text alongside it. Never mutates the input."""
    normalized = dict(raw_record)
    normalized["price_gbp"] = normalize_price(raw_record["price_text"])
    return normalized


def validate_records(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Normalize and schema-validate every raw record. Dedupes on
    product_url (a record's canonical identity) so a rerun — or a book that
    somehow showed up twice — never produces duplicates.

    Returns (valid_records, error_entries). error_entries carry the offending
    raw record plus a human-readable reason, so nothing is silently dropped.
    """
    valid_by_url: dict[str, dict] = {}
    errors: list[dict] = []

    for raw_record in raw_records:
        product_url = raw_record.get("product_url")
        if product_url in valid_by_url:
            continue  # already have a good record for this canonical URL

        try:
            normalized = normalize_record(raw_record)
            book = BookRecord(**normalized)
        except (ValueError, ValidationError) as exc:
            errors.append({"record": raw_record, "reason": str(exc)})
            continue

        valid_by_url[product_url] = book.model_dump()

    valid_records = list(valid_by_url.values())
    print(f"valid_records={len(valid_records)} invalid_records={len(errors)}")
    return valid_records, errors


def store_records(valid_records: list[dict], errors: list[dict]) -> None:
    """Write output/books.json and output/errors.json. Overwrites in full
    each run (rather than appending) so reruns stay idempotent — the same
    input always produces the same 60 records, never 120."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    books_path = OUTPUT_DIR / "books.json"
    books_path.write_text(json.dumps(valid_records, indent=2), encoding="utf-8")

    errors_path = OUTPUT_DIR / "errors.json"
    errors_path.write_text(json.dumps(errors, indent=2), encoding="utf-8")

    print(f"stored books={len(valid_records)} -> {books_path}")
    print(f"stored errors={len(errors)} -> {errors_path}")


def main() -> None:
    book_entries = discover_book_urls()
    records = extract_all_book_records(book_entries)
    valid_records, errors = validate_records(records)
    store_records(valid_records, errors)


if __name__ == "__main__":
    main()