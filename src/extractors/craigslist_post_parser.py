from __future__ import annotations

from typing import Dict, List, Optional
import json
import re
from bs4 import BeautifulSoup

from .geo_utils import extract_coords_from_map, find_phone_numbers

# Common attribute label mappings for normalization
_ATTR_LABEL_MAP = {
    "condition": "condition",
    "manufacturer": "manufacturer",
    "make / manufacturer": "manufacturer",
    "model name / number": "model",
    "model": "model",
    "available": "availableFrom",
    "available on": "availableFrom",
    "date available": "availableFrom",
    "employment type": "employmentType",
    "compensation": "compensation",
}

def _text(el) -> str:
    return (el.get_text(" ", strip=True) if el else "").strip()

def _get_title(soup: BeautifulSoup) -> Optional[str]:
    return _text(soup.select_one("#titletextonly")) or _text(soup.select_one("h1")) or None

def _get_price(soup: BeautifulSoup) -> Optional[str]:
    price_el = soup.select_one(".price") or soup.select_one(".buyprice") or soup.select_one(".attrgroup .price")
    price = _text(price_el)
    return price or None

def _get_location(soup: BeautifulSoup) -> Optional[str]:
    hood = _text(soup.select_one(".postingtitletext small")) or _text(soup.select_one(".mapaddress"))
    hood = hood.strip("()")
    return hood or None

def _get_datetime(soup: BeautifulSoup) -> Optional[str]:
    time_el = soup.find("time")
    if time_el and time_el.has_attr("datetime"):
        return time_el["datetime"]
    # Sometimes a meta tag holds it
    meta = soup.find("meta", {"property": "og:updated_time"}) or soup.find("meta", {"property": "article:published_time"})
    if meta and meta.has_attr("content"):
        return meta["content"]
    return None

def _get_id(soup: BeautifulSoup, source_url: str) -> Optional[str]:
    # Prefer post ID element
    id_el = soup.select_one(".postinginfos .postinginfo") or soup.find(string=re.compile(r"post id", re.I))
    if id_el:
        m = re.search(r"(\d{7,})", str(id_el))
        if m:
            return m.group(1)
    # Fallback to URL
    m = re.search(r"/(\d+)\.html", source_url or "")
    return m.group(1) if m else None

def _get_body(soup: BeautifulSoup) -> Optional[str]:
    body_el = soup.select_one("#postingbody") or soup.select_one(".userbody") or soup.select_one(".description")
    if body_el:
        # Craigslist often prefixes "QR Code Link to This Post"
        body = _text(body_el)
        body = re.sub(r"^QR Code Link to This Post\s*", "", body, flags=re.I)
        return body
    return None

def _parse_attributes(soup: BeautifulSoup) -> Dict:
    """
    Parse attribute lists found under .attrgroup
    Returns:
      - pics: list[str]
      - amenities: list[str]
      - attributes: list[str]
      - normalized fields like manufacturer/model/condition/etc when present
    """
    out: Dict = {"pics": [], "amenities": [], "attributes": []}
    # Pictures
    for img in soup.select("img"):
        src = img.get("src")
        if src and "images.craigslist.org" in src:
            out["pics"].append(src)

    # Attribute groups
    for group in soup.select(".attrgroup"):
        # Amenities / feature bullets are often inside span + b
        for span in group.select("span"):
            text = _text(span)
            if not text:
                continue
            out["attributes"].append(text)

            # Normalize key:value pairs if present
            if ":" in text:
                k, v = [t.strip() for t in text.split(":", 1)]
                key_norm = _ATTR_LABEL_MAP.get(k.lower())
                if key_norm:
                    out[key_norm] = v
            else:
                # Amenities heuristics (housing)
                lowered = text.lower()
                if any(tok in lowered for tok in ["furnished", "air", "w/d", "dishwasher", "parking", "apartment", "condo", "private", "shared", "studio"]):
                    out["amenities"].append(text)

    # Deduplicate
    out["pics"] = list(dict.fromkeys(out["pics"]))
    out["amenities"] = list(dict.fromkeys(out["amenities"]))
    out["attributes"] = list(dict.fromkeys(out["attributes"]))
    return out

def parse_post_page(soup: BeautifulSoup, *, source_url: str) -> Dict:
    """
    Parse a single Craigslist post page into a record.
    """
    title = _get_title(soup)
    price = _get_price(soup)
    location = _get_location(soup)
    dt = _get_datetime(soup)
    pid = _get_id(soup, source_url)
    body = _get_body(soup)
    coords = extract_coords_from_map(soup)

    attrs = _parse_attributes(soup)

    phones = find_phone_numbers(body or "")

    record: Dict = {
        "id": pid,
        "url": source_url,
        "title": title,
        "datetime": dt,
        "location": location,
        "label": "post",
        "price": price,
        "longitude": coords.get("longitude"),
        "latitude": coords.get("latitude"),
        "mapAccuracy": coords.get("mapAccuracy"),
        "post": body,
        "phoneNumbers": phones or None,
    }

    # Merge attributes and normalized fields
    record.update(attrs)

    # Job-specific fields if present inside attributes/body (heuristic)
    body_lower = (body or "").lower()
    if "full-time" in body_lower:
        record["employmentType"] = record.get("employmentType") or "full-time"
    if "part-time" in body_lower and not record.get("employmentType"):
        record["employmentType"] = "part-time"

    # Compensation heuristics
    comp_match = re.search(r"(?:compensation|pay|salary)\s*[:\-]\s*([^\n\r]+)", body or "", flags=re.I)
    if comp_match and not record.get("compensation"):
        record["compensation"] = comp_match.group(1).strip()

    # Try to guess jobTitle from title by stripping company markers
    if title:
        jt = re.sub(r"\*+|~+|\[.*?\]|\(.*?\)", "", title).strip()
        record["jobTitle"] = jt if jt else None

    # Clean Nones
    record = {k: v for k, v in record.items() if v not in (None, [], {})}
    return record