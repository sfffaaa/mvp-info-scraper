import sys
from datetime import datetime, timezone

import feedparser

from models import Article


def fetch_medium_articles(tag: str, topic_hint: str, limit: int = 15) -> list[Article]:
    feed_url = f"https://medium.com/feed/tag/{tag}"
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:limit]:
            content = entry.get("summary") or ""
            articles.append(Article(
                url=entry.link,
                title=entry.title,
                content=content,
                source="medium",
                scraped_at=datetime.now(timezone.utc).isoformat(),
                topic_hint=topic_hint,
            ))
        return articles
    except Exception as e:
        print(f"[medium] Error fetching tag '{tag}': {e}", file=sys.stderr)
        return []
