import json
from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def parse_tenders(html: str, scrape_config: str, base_url: str) -> list[dict]:
    """
    Parse tender entries from HTML using CSS selectors defined in scrape_config.
    Returns list of dicts with tender fields. Skips rows with no title or source_url.
    """
    config = json.loads(scrape_config)
    list_selector = config.get("list_selector", "")
    fields = config.get("fields", {})

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(list_selector)

    tenders = []
    for row in rows:
        tender = {}
        for field_name, selector in fields.items():
            value = _extract_field(row, selector, base_url)
            if value:
                tender[field_name] = value

        # Must have at minimum a title and source_url
        if not tender.get("title") or not tender.get("source_url"):
            continue

        tenders.append(tender)

    return tenders


def _extract_field(element, selector: str, base_url: str) -> Optional[str]:
    """
    Extract a field value from an element using a CSS selector.
    Append @attr to extract an attribute (e.g., 'a@href').
    """
    attr = None
    if "@" in selector:
        selector, attr = selector.rsplit("@", 1)

    found = element.select_one(selector)
    if not found:
        return None

    if attr:
        value = found.get(attr, "")
        # Resolve relative URLs for href attributes
        if attr == "href" and value:
            value = urljoin(base_url, value)
    else:
        value = found.get_text(strip=True)

    return value or None
