"""
The polite scraper — entry point.

Stage 1: fetch and cache HTML.
Stage 2: discover the three catalogue pages and every book link on them.
Stage 3: visit every book page and extract the raw record fields.
Stage 4: normalize, schema-validate, and store the records.
Stage 5: survive a broken page without crashing, and report the run.
Stage 6 (publish) not implemented yet.
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
MAX_RETRIES = 1  # one extra attempt for a timeout or 5xx — never for 404/403


class FetchError(Exception):
    """One page failed to fetch, after retries where retries were allowed.
    Carries enough context that the caller can log it and move on."""

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"{url}: {reason}")


class RunStats:
    """Honest numbers about one run, collected as it happens and written to
    output/run-report.json at the end — so a silent failure can't hide."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.pages_fetched = 0  # real network requests (cache misses)
        self.cache_hits = 0
        self.failed_pages: list[dict] = []  # [{"url": ..., "reason": ...}]

    def record_failure(self, url: str, reason: str) -> None:
        self.failed_pages.append({"url": url, "reason": reason})

    def to_report(self, valid_records: int, invalid_records: int) -> dict:
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return {
            "start_time": self.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": round(duration, 2),
            "pages_fetched": self.pages_fetched,
            "cache_hits": self.cache_hits,
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "failed_pages": len(self.failed_pages),
            "failed_page_details": self.failed_pages,
        }


def fetch_page(url: str, cache_filename: str, stats: RunStats) -> str:
    """Return a page's HTML, reading from the local cache if we already have it.

    Prints FETCH on a real network request, or CACHE HIT when reading the
    saved copy — either way it reports the response size, never the HTML
    itself. Only a real (non-cached) fetch pays the politeness delay.

    A timeout or a 5xx gets one retry after a short wait. A 404 or 403 is
    never retried — asking again won't change a missing page or a refusal.
    Raises FetchError (not a bare exception) so callers can log it and move
    on to the next page instead of crashing the whole run.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT  {url}  ({len(html)} bytes)")
        stats.cache_hits += 1
        return html

    headers = {"User-Agent": USER_AGENT}
    attempt = 0

    while True:
        attempt += 1
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.exceptions.RequestException as exc:
            if attempt <= MAX_RETRIES:
                print(f"RETRY      {url}  (attempt {attempt} raised {exc!r})")
                time.sleep(REQUEST_DELAY_SECONDS * 2)
                continue
            raise FetchError(url, f"request failed after {attempt} attempts: {exc}") from exc

        if response.status_code == 200:
            html = response.text
            cache_path.write_text(html, encoding="utf-8")
            print(f"FETCH      {url}  ({len(html)} bytes)")
            stats.pages_fetched += 1
            time.sleep(REQUEST_DELAY_SECONDS)
            return html

        if response.status_code in (404, 403):
            raise FetchError(url, f"returned {response.status_code}, not retrying")

        if response.status_code >= 500 and attempt <= MAX_RETRIES:
            print(f"RETRY      {url}  (status {response.status_code}, attempt {attempt})")
            time.sleep(REQUEST_DELAY_SECONDS * 2)
            continue

        raise FetchError(url, f"returned status {response.status_code}, expected 200")


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


def discover_book_urls(stats: RunStats) -> list[dict]:
    """Walk the first MAX_CATALOGUE_PAGES catalogue pages via their own
    'next' links, collecting every unique book URL along with which
    catalogue page it was found on (its source_page, for provenance).

    If a catalogue page itself fails, that's logged as a failed page and
    pagination stops there — we keep whatever books we'd already found
    rather than crashing the whole run.
    """
    discovered: list[dict] = []
    page_url = CATALOGUE_PAGE_1_URL
    pages_visited = 0

    while page_url and pages_visited < MAX_CATALOGUE_PAGES:
        pages_visited += 1
        cache_filename = f"catalogue-page-{pages_visited}.html"
        try:
            html = fetch_page(page_url, cache_filename, stats)
        except FetchError as exc:
            print(f"FAILED     {page_url}  ({exc.reason})")
            stats.record_failure(page_url, exc.reason)
            break

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


def extract_all_book_records(book_entries: list[dict], stats: RunStats) -> list[dict]:
    """Fetch (and cache) every book detail page and extract its raw record.

    Each book is handled independently: a fetch failure (already retried
    once where that made sense) or an unexpected page shape is logged to
    stats and skipped, so one broken book never takes the other 59 down.
    """
    records = []
    for entry in book_entries:
        try:
            html = fetch_page(entry["url"], cache_filename_for_book(entry["url"]), stats)
            record = extract_book_record(html, entry["url"], entry["source_page"])
        except FetchError as exc:
            print(f"FAILED     {entry['url']}  ({exc.reason})")
            stats.record_failure(entry["url"], exc.reason)
            continue
        except Exception as exc:  # malformed/unexpected page shape
            print(f"FAILED     {entry['url']}  (unexpected error: {exc})")
            stats.record_failure(entry["url"], f"unexpected error: {exc}")
            continue

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


def write_run_report(stats: RunStats, valid_records: int, invalid_records: int) -> None:
    """Write output/run-report.json — a few honest numbers proving the run
    happened and how it went, so a bad run can't fail silently."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    report = stats.to_report(valid_records, invalid_records)
    report_path = OUTPUT_DIR / "run-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"run_report pages_fetched={report['pages_fetched']} "
        f"cache_hits={report['cache_hits']} "
        f"valid_records={report['valid_records']} "
        f"invalid_records={report['invalid_records']} "
        f"failed_pages={report['failed_pages']} "
        f"duration_seconds={report['duration_seconds']}"
    )


def main() -> None:
    stats = RunStats()
    book_entries = discover_book_urls(stats)
    # To prove Stage 5 survives a broken page: temporarily add a fake entry
    # here, e.g. book_entries.append({"url": CATALOGUE_PAGE_1_URL.replace(
    # "page-1.html", "catalogue/does-not-exist_9999/index.html"),
    # "source_page": CATALOGUE_PAGE_1_URL}) — run once, confirm
    # run-report.json shows failed_pages: 1 and books.json still has 60,
    # then remove it again.
    records = extract_all_book_records(book_entries, stats)
    valid_records, errors = validate_records(records)
    store_records(valid_records, errors)
    write_run_report(stats, len(valid_records), len(errors))


if __name__ == "__main__":
    main()