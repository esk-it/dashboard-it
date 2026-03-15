from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])

BACKEND_DIR = Path(__file__).resolve().parent.parent
RSS_FILE = BACKEND_DIR / "rss_feeds.json"

DEFAULT_FEEDS = [
    {"name": "CERT-FR", "url": "https://www.cert.ssi.gouv.fr/feed/", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "IT Connect", "url": "https://www.it-connect.fr/feed/", "category": "Infra", "enabled": True},
    {"name": "ZATAZ", "url": "https://www.zataz.com/feed/", "category": "S\u00e9curit\u00e9", "enabled": True},
    {"name": "01net", "url": "https://www.01net.com/rss/info/flux-rss/flux-toutes-les-actualites/", "category": "Tech", "enabled": True},
    {"name": "LeMagIT", "url": "https://www.lemagit.fr/rss/ContentSyndication.xml", "category": "Tech", "enabled": True},
]


def _load_feeds():
    """Load feeds from the shared RSS file, falling back to defaults."""
    if RSS_FILE.exists():
        try:
            feeds = json.loads(RSS_FILE.read_text(encoding="utf-8"))
            # Only return enabled feeds
            return [f for f in feeds if f.get("enabled", True)]
        except Exception:
            pass
    return DEFAULT_FEEDS


@router.get("/feeds")
async def list_feeds():
    return _load_feeds()


@router.get("/articles")
async def fetch_articles(feed_url: str = Query(..., description="RSS feed URL to fetch")):
    try:
        import feedparser
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="feedparser library is not installed. Run: pip install feedparser",
        )

    try:
        feed = feedparser.parse(feed_url)
    except Exception as exc:
        logger.error("Failed to parse feed %s: %s", feed_url, exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch feed: {exc}")

    if feed.bozo and not feed.entries:
        raise HTTPException(status_code=502, detail="Failed to parse RSS feed")

    articles = []
    for entry in feed.entries:
        published = ""
        if hasattr(entry, "published"):
            published = entry.published
        elif hasattr(entry, "updated"):
            published = entry.updated

        summary = ""
        if hasattr(entry, "summary"):
            summary = entry.summary
        elif hasattr(entry, "description"):
            summary = entry.description

        articles.append({
            "title": getattr(entry, "title", ""),
            "link": getattr(entry, "link", ""),
            "published": published,
            "summary": summary,
        })

    return articles
