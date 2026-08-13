"""
The polite scraper — entry point.

Stage 1: fetch and cache HTML.
Stages 2+ (extract/normalize/validate/store/report) not implemented yet.
"""

from pathlib import Path

import requests

# TODO: replace with the real URL of your repo once it's public — that's the
# whole point of naming yourself in the user-agent.
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR-USERNAME/YOUR-REPO)"
TIMEOUT_SECONDS = 10
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

CATALOGUE_PAGE_1_URL = "https://books.toscrape.com/catalogue/page-1.html"


def fetch_page(url: str, cache_filename: str) -> str:
    """Return a page's HTML, reading from the local cache if we already have it.

    Prints FETCH on a real network request, or CACHE HIT when reading the
    saved copy — either way it reports the response size, never the HTML
    itself.
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
    return html


def main() -> None:
    fetch_page(CATALOGUE_PAGE_1_URL, "catalogue-page-1.html")


if __name__ == "__main__":
    main()