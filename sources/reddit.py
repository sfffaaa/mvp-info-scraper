import sys
from datetime import datetime, timezone

import feedparser

from models import Article


def fetch_reddit_articles(subreddit: str, topic_hint: str, limit: int = 15) -> list[Article]:
    sub = subreddit.lstrip("r/")
    feed_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit={limit}"
    headers = {"User-Agent": "info-scraper/1.0"}
    try:
        feed = feedparser.parse(feed_url, request_headers=headers)
        articles = []
        for entry in feed.entries[:limit]:
            articles.append(Article(
                url=entry.link,
                title=entry.title,
                content=entry.get("summary", ""),
                source="reddit",
                scraped_at=datetime.now(timezone.utc).isoformat(),
                topic_hint=topic_hint,
            ))
        return articles
    except Exception as e:
        print(f"[reddit] Error fetching r/{sub}: {e}", file=sys.stderr)
        return []
