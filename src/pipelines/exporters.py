from __future__ import annotations

from typing import Iterable, List, Dict
import json
import os

def write_json_array(records: List[Dict], path: str) -> None:
    """Write records as a single JSON array to `path` (pretty, UTF-8)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)