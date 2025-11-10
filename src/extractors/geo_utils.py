from __future__ import annotations

from typing import Dict, Optional
import json
import re
from bs4 import BeautifulSoup

_PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
    re.I,
)

def extract_coords_from_map(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Craigslist usually embeds coords in data-latitude/data-longitude on a #map or meta tags.
    Returns dict with latitude, longitude, and optional mapAccuracy.
    """
    # <div id="map" data-latitude="40.759908" data-longitude="-73.937645" data-accuracy="5">
    m = soup.select_one("#map") or soup.select_one("#mapcontainer #map")
    if m:
        lat = m.get("data-latitude")
        lon = m.get("data-longitude")
        acc = m.get("data-accuracy") or m.get("data-accuracy-meters")
        return {"latitude": lat, "longitude": lon, "mapAccuracy": acc}

    # Try JSON inside a script
    for sc in soup.find_all("script"):
        txt = sc.string or sc.get_text()
        if not txt:
            continue
        if "latitude" in txt and "longitude" in txt:
            # crude parse
            lat_match = re.search(r'"latitude"\s*:\s*("?)(-?\d+(\.\d+)?)\1', txt)
            lon_match = re.search(r'"longitude"\s*:\s*("?)(-?\d+(\.\d+)?)\1', txt)
            acc_match = re.search(r'"accuracy"\s*:\s*("?)(\d+(\.\d+)?)\1', txt)
            if lat_match and lon_match:
                return {
                    "latitude": lat_match.group(2),
                    "longitude": lon_match.group(2),
                    "mapAccuracy": acc_match.group(2) if acc_match else None,
                }

    # Fallback: sometimes meta tags hold coords
    meta_lat = soup.find("meta", {"property": "place:location:latitude"})
    meta_lon = soup.find("meta", {"property": "place:location:longitude"})
    if meta_lat and meta_lon and meta_lat.get("content") and meta_lon.get("content"):
        return {
            "latitude": meta_lat["content"],
            "longitude": meta_lon["content"],
            "mapAccuracy": None,
        }

    return {"latitude": None, "longitude": None, "mapAccuracy": None}

def find_phone_numbers(text: str) -> list[str]:
    """Return unique phone-like strings found."""
    phones = list({m.group(0) for m in _PHONE_RE.finditer(text or "")})
    return phones