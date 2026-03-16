import json
from backend.scraper.parser import parse_tenders

SAMPLE_HTML = """
<html><body>
  <table class="tender-list">
    <tr>
      <td class="title"><a href="/tender/1">IT Infrastructure Upgrade</a></td>
      <td class="deadline">2026-04-30</td>
      <td class="pub-date">2026-03-01</td>
      <td class="value">₹50 Lakh</td>
      <td class="description">Networking equipment for office</td>
    </tr>
    <tr>
      <td class="title"><a href="/tender/2">Cloud Migration Project</a></td>
      <td class="deadline">2026-05-15</td>
      <td class="pub-date">2026-03-05</td>
      <td class="value">₹1.2 Crore</td>
      <td class="description">AWS migration services</td>
    </tr>
  </table>
</body></html>
"""

SCRAPE_CONFIG = json.dumps({
    "render_js": False,
    "list_selector": "table.tender-list tr",
    "fields": {
        "title": "td.title a",
        "source_url": "td.title a@href",
        "deadline": "td.deadline",
        "published_date": "td.pub-date",
        "estimated_value": "td.value",
        "description": "td.description",
    },
    "pagination": {"type": "none"},
})

def test_parse_extracts_tenders():
    tenders = parse_tenders(SAMPLE_HTML, SCRAPE_CONFIG, base_url="https://example.com")
    assert len(tenders) == 2

def test_parse_tender_fields():
    tenders = parse_tenders(SAMPLE_HTML, SCRAPE_CONFIG, base_url="https://example.com")
    t = tenders[0]
    assert t["title"] == "IT Infrastructure Upgrade"
    assert t["source_url"] == "https://example.com/tender/1"
    assert t["deadline"] == "2026-04-30"
    assert t["estimated_value"] == "₹50 Lakh"
    assert t["description"] == "Networking equipment for office"

def test_parse_skips_rows_without_title():
    html = '<html><body><table class="tender-list"><tr><td class="deadline">2026-05-01</td></tr></table></body></html>'
    tenders = parse_tenders(html, SCRAPE_CONFIG, base_url="https://example.com")
    assert len(tenders) == 0

def test_parse_resolves_relative_url():
    tenders = parse_tenders(SAMPLE_HTML, SCRAPE_CONFIG, base_url="https://portal.gov.in")
    assert tenders[0]["source_url"].startswith("https://portal.gov.in")

def test_parse_empty_html():
    tenders = parse_tenders("<html><body></body></html>", SCRAPE_CONFIG, base_url="https://example.com")
    assert tenders == []
