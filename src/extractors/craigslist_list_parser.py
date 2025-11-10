from __future__ import annotations

from typing import Dict, List, Optional
import re
from bs4 import BeautifulSoup

_PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
    re.I,
)

def _text(el) -> str:
    return (el.get_text(" ", strip=True) if el else "").strip()

def _price_text(s: str) -> Optional[str]:
    s = (s or "").strip()
    if not s:
        return None
    # Keep as-is (string), but ensure it looks like a price
    if re.search(r"\d", s):
        return s
    return None

def parse_list_page(soup: BeautifulSoup, *, source_url: str) -> List[Dict]:
    """
    Parse a Craigslist search/list page into a list of lightweight items.
    It targets the common CL layout but includes fallbacks for variants.

    Returns items with keys:
    - id, url, title, datetime, location, price, label="post"
    """
    items: List[Dict] = []

    # Primary selector (modern CL):
    rows = soup.select(".result-row") or soup.select("li.cl-search-result") or []

    if not rows:
        # Some locales wrap in ul.rows > li.result-row
        rows = soup.select("ul.rows li.result-row")

    for row in rows:
        # URL / id
        link = row.select_one("a.result-title") or row.select_one("a.cl-app-anchor") or row.find("a", href=True)
        url = link["href"] if link and link.has_attr("href") else None
        cid = (
            (row.get("data-pid") or row.get("data-id") or (url and re.search(r"/(\d+)\.html", url) and re.search(r"/(\d+)\.html", url).group(1)))
        )

        # Title
        title = _text(link)

        # Date/time
        time_el = row.find("time") or row.select_one(".result-date")
        datetime = time_el.get("datetime") if time_el and time_el.has_attr("datetime") else _text(time_el) or None

        # Price
        price_el = row.select_one(".result-price") or row.select_one(".price") or None
        price = _price_text(_text(price_el))

        # Location (in parentheses or meta)
        hood_el = row.select_one(".result-hood") or row.select_one(".nearby") or None
        location = _text(hood_el).strip("()") if hood_el else None

        # Optional: category token sometimes present
        category = None
        cat_el = row.select_one(".category") or row.select_one("[data-cat]") or None
        if cat_el and cat_el.has_attr("data-cat"):
            category = cat_el["data-cat"]

        item = {
            "id": cid,
            "url": url,
            "title": title or None,
            "datetime": datetime,
            "location": location or None,
            "price": price,
            "label": "post",
        }
        if category:
            item["category"] = category

        # Pull any phone-like strings if snippets are present
        snippet = _text(row.select_one(".result-description") or row.select_one(".snippet"))
        if snippet:
            phones = list({m.group(0) for m in _PHONE_RE.finditer(snippet)})
            if phones:
                item["phoneNumbers"] = phones

        # Skip entries with no URL or title
        if not (item["url"] and item["title"]):
            continue

        items.append(item)

    return items