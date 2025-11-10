from __future__ import annotations

from typing import Dict, Optional
import re
from urllib.parse import urlparse

def _strip_dollar(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return s.strip()

def detect_category_from_url(url: str) -> Optional[str]:
    """
    Attempt to derive a category token from the URL path segment:
    e.g. /search/ggg -> gigs, /mnh/fbh/... -> jobs, /search/roo -> housing, etc.
    """
    if not url:
        return None
    path = urlparse(url).path.lower()
    # craigslist uses 3-letter category codes; map common ones
    # ggg gigs, fbh food/bev/hosp, roo rooms, apts apartments, etc.
    if "/search/" in path:
        code = path.split("/search/", 1)[-1].split("/", 1)[0]
    else:
        # /mnh/fbh/7537...html -> fbh
        parts = [p for p in path.split("/") if p]
        code = parts[1] if len(parts) >= 2 else ""
    code = (code or "").strip()

    mapping = {
        "ggg": "gigs",
        "jjj": "jobs",
        "fbh": "jobs",
        "ofc": "jobs",
        "egr": "jobs",
        "etc": "jobs",
        "roo": "housing",
        "apa": "housing",
        "sub": "housing",
        "rea": "housing",
        "evg": "events",
        "com": "community",
        "res": "resumes",
        "bbb": "services",
        "bbb?": "services",
        "sss": "for sale",
        "sale": "for sale",
    }
    return mapping.get(code, None)

def normalize_record(rec: Dict) -> Dict:
    """
    Normalize a parsed record to match the README schema as closely as possible.
    We preserve string formats (e.g., price as text) but ensure keys exist.
    """
    out = dict(rec)  # shallow copy
    # Price as string without whitespace normalization beyond strip
    out["price"] = _strip_dollar(out.get("price"))

    # Map alternative spellings
    if "attirbutes" in out and "attributes" not in out:
        out["attributes"] = out.pop("attirbutes")

    # Ensure label is 'post'
    out["label"] = "post"

    # Keep consistent key ordering when exporting (not required but nice)
    preferred = [
        "id", "url", "title", "datetime", "dates", "location", "category", "label",
        "price", "longitude", "latitude", "mapAccuracy", "post", "notices",
        "phoneNumbers", "compensation", "employmentType", "jobTitle", "pics",
        "amenities", "availableFrom", "manufacturer", "model", "condition",
        "attributes",
    ]
    # Build ordered dict-like (plain dict in 3.7+ preserves insertion order)
    ordered = {}
    for k in preferred:
        if k in out and out[k] not in (None, [], {}):
            ordered[k] = out[k]
    # Append any remaining keys
    for k, v in out.items():
        if k not in ordered and v not in (None, [], {}):
            ordered[k] = v
    return ordered