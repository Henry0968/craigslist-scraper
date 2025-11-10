from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from bs4 import BeautifulSoup  # noqa: E402

from src.extractors.craigslist_list_parser import parse_list_page  # noqa: E402
from src.extractors.craigslist_post_parser import parse_post_page  # noqa: E402
from src.pipelines.normalizers import normalize_record  # noqa: E402

def test_parse_list_page_minimal():
    html = """
    <html><body>
      <ul class="rows">
        <li class="result-row" data-pid="111">
          <a class="result-title" href="https://example.org/nyc/apa/111.html">Sunny studio</a>
          <time datetime="2024-01-01T12:00:00-0500"></time>
          <span class="result-price">$1800</span>
          <span class="result-hood">(Upper East Side)</span>
        </li>
        <li class="result-row" data-pid="222">
          <a class="result-title" href="https://example.org/nyc/ggg/222.html">Weekend movers call 646-744-6519</a>
          <time datetime="2024-03-05T09:30:00-0500"></time>
          <span class="result-price">$25/hr</span>
          <span class="result-hood">(Queens)</span>
        </li>
      </ul>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    items = parse_list_page(soup, source_url="https://example.org/search/apa")
    assert len(items) == 2
    a = items[0]
    assert a["id"] == "111"
    assert a["title"] == "Sunny studio"
    assert a["price"] == "$1800"
    assert a["location"] == "Upper East Side"
    b = items[1]
    assert "phoneNumbers" in b
    assert any("646" in p for p in b["phoneNumbers"])

def test_parse_post_page_full():
    html = """
    <html><head>
      <meta property="og:updated_time" content="2024-02-10T10:30:00-0500" />
    </head>
    <body>
      <section class="page-container">
        <div class="postinginfos"><span class="postinginfo">post id: 333444555</span></div>
        <div id="map" data-latitude="40.759908" data-longitude="-73.937645" data-accuracy="5"></div>
        <h1 id="titletextonly">**Hiring Floor Managers ($75-90k)**</h1>
        <span class="price">$90000</span>
        <p class="mapaddress">(Upper East Side)</p>
        <section id="postingbody">
          QR Code Link to This Post
          Pay: $75-$90k salary + bonus, benefits. Full-time role.
          Call 909-9909-3322 for details.
        </section>
        <div class="attrgroup">
          <span>employment type: full-time</span>
          <span>compensation: $75-$90k salary + bonus, benefits</span>
        </div>
        <img src="https://images.craigslist.org/abc123.jpg" />
      </section>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    rec = parse_post_page(soup, source_url="https://example.org/mnh/fbh/333444555.html")
    assert rec["id"] == "333444555"
    assert rec["latitude"] == "40.759908"
    assert "909-9909-3322" in " ".join(rec.get("phoneNumbers", []))
    assert rec["employmentType"] == "full-time"
    assert rec["compensation"].startswith("$75-$90k")
    assert rec["pics"][0].endswith(".jpg")

    normalized = normalize_record(rec)
    assert normalized["label"] == "post"
    assert "jobTitle" in normalized