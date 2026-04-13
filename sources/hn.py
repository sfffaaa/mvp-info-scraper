import sys
from datetime import datetime, timezone

import requests

from models import Article


def fetch_hn_articles(query: str, topic_hint: str, limit: int = 15) -> list[Article]:
    url = (
        f"https://hn.algolia.com/api/v1/search"
        f"?query={requests.utils.quote(query)}&tags=story&hitsPerPage={limit}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        articles = []
        for hit in hits:
            if not hit.get("title"):
                continue
            articles.append(Article(
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                title=hit["title"],
                content=hit.get("story_text") or hit["title"],
                source="hn",
                scraped_at=datetime.now(timezone.utc).isoformat(),
                topic_hint=topic_hint,
            ))
        return articles
    except Exception as e:
        print(f"[hn] Error fetching '{query}': {e}", file=sys.stderr)
        return []
