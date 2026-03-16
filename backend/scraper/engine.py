import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend import models
from backend.scraper.fetcher import fetch_html
from backend.scraper.parser import parse_tenders


def scrape_portal(portal_id: int, db: Session) -> dict:
    """
    Scrape a single portal. Returns dict with tenders_found, tenders_new, status, error_message.
    Writes a ScrapeLog entry to the database.
    """
    result = {"tenders_found": 0, "tenders_new": 0, "status": "failed", "error_message": None}

    portal = db.get(models.Portal, portal_id)
    if portal is None:
        result["error_message"] = f"Portal {portal_id} not found"
        return result  # Cannot write ScrapeLog — portal FK would fail

    result["status"] = "success"

    try:
        # Auth check
        if portal.requires_auth and not portal.password_enc:
            raise ValueError("Auth required but credentials not configured")

        config = json.loads(portal.scrape_config or "{}")
        render_js = config.get("render_js", False)

        html = fetch_html(portal.url, render_js=render_js)
        raw_tenders = parse_tenders(html, portal.scrape_config or "{}", base_url=portal.url)

        # Handle pagination
        pagination = config.get("pagination", {})
        if pagination.get("type") == "next_button":
            from bs4 import BeautifulSoup
            max_pages = pagination.get("max_pages", 10)
            next_selector = pagination.get("selector", "")
            for _ in range(max_pages - 1):
                soup = BeautifulSoup(html, "html.parser")
                next_link = soup.select_one(next_selector)
                if not next_link or not next_link.get("href", "").strip():
                    break
                from urllib.parse import urljoin
                next_url = urljoin(portal.url, next_link.get("href", "").strip())
                html = fetch_html(next_url, render_js=render_js)
                raw_tenders.extend(parse_tenders(html, portal.scrape_config, base_url=portal.url))

        result["tenders_found"] = len(raw_tenders)

        # Get active keywords
        active_keywords = [
            kw.value.lower()
            for kw in db.query(models.Keyword).filter(models.Keyword.active == True).all()
        ]

        if not active_keywords:
            result["error_message"] = "No active keywords configured — no tenders will be saved"
            # Don't fail — continue to scrape (tenders_found will still be recorded)

        now = datetime.utcnow()
        new_count = 0

        for raw in raw_tenders:
            title = raw.get("title", "")
            description = raw.get("description", "")
            source_url = raw.get("source_url", "")
            if not source_url:
                continue

            # Keyword filtering (case-insensitive, title + description)
            text = f"{title} {description}".lower()
            matched = [kw for kw in active_keywords if kw in text]
            if not matched:
                continue

            # Deduplication: check by source_url
            existing = db.query(models.Tender).filter(models.Tender.source_url == source_url).first()
            if existing:
                # Update mutable fields; preserve status and notes
                existing.title = title
                if raw.get("description"):
                    existing.description = raw["description"]
                if raw.get("deadline"):
                    existing.deadline = raw["deadline"]
                if raw.get("estimated_value"):
                    existing.estimated_value = raw["estimated_value"]
                if raw.get("published_date"):
                    existing.published_date = raw["published_date"]
                existing.last_updated_at = now
                db.add(existing)
            else:
                tender = models.Tender(
                    portal_id=portal_id,
                    title=title,
                    description=raw.get("description"),
                    deadline=raw.get("deadline"),
                    published_date=raw.get("published_date"),
                    estimated_value=raw.get("estimated_value"),
                    source_url=source_url,
                    matched_keywords=json.dumps(matched),
                    status="new",
                    scraped_at=now,
                    last_updated_at=now,
                )
                db.add(tender)
                new_count += 1

        portal.last_scraped_at = now
        db.commit()           # commits tenders AND portal.last_scraped_at atomically
        result["tenders_new"] = new_count

    except Exception as e:
        result["status"] = "failed"
        result["error_message"] = str(e)
        db.rollback()

    # Write scrape log (outside try/except so it always runs)
    log = models.ScrapeLog(
        portal_id=portal_id,
        tenders_found=result["tenders_found"],
        tenders_new=result["tenders_new"],
        status=result["status"],
        error_message=result["error_message"],
    )
    db.add(log)
    db.commit()

    return result


def run_all_portals(db: Session):
    """Run scrape for all enabled portals. Each portal is isolated — failures don't stop others."""
    portals = db.query(models.Portal).filter(models.Portal.enabled == True).all()
    for portal in portals:
        scrape_portal(portal_id=portal.id, db=db)
