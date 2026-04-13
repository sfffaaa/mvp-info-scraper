import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from models import Article

if TYPE_CHECKING:
    from twscrape import API as TwAPI


async def setup_twitter_api(username: str, password: str, email: str = "", email_password: str = "") -> "TwAPI":
    from twscrape import API as TwAPI
    api = TwAPI()
    existing = await api.pool.get_all()
    if not any(a.username == username for a in existing):
        await api.pool.add_account(username, password, email, email_password)
        await api.pool.login_all()
    return api


async def fetch_twitter_articles(
    query: str,
    topic_hint: str,
    api: "TwAPI",
    limit: int = 15,
) -> list[Article]:
    articles = []
    try:
        async for tweet in api.search(query, limit=limit):
            articles.append(Article(
                url=f"https://twitter.com/i/web/status/{tweet.id}",
                title=tweet.rawContent[:120].replace("\n", " "),
                content=tweet.rawContent,
                source="twitter",
                scraped_at=datetime.now(timezone.utc).isoformat(),
                topic_hint=topic_hint,
            ))
    except Exception as e:
        print(f"[twitter] Error fetching '{query}': {e}", file=sys.stderr)
    return articles
