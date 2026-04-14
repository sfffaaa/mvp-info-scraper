#!/usr/bin/env python3
"""
Scraper: fetches articles from X, HN, Medium, Reddit into buffer/.
Run twice daily (07:00 and 19:00 via cron).
"""
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import Settings
from email_utils import send_failure_email
from models import Article
from sources.hn import fetch_hn_articles
from sources.medium import fetch_medium_articles
from sources.reddit import fetch_reddit_articles
from sources.twitter import fetch_twitter_articles, setup_twitter_api

CONFIG_PATH = Path(__file__).parent / "config.yaml"
ENV_PATH = Path(__file__).parent / ".env"
DRY_RUN = "--dry-run" in sys.argv


def write_to_buffer(articles: list[Article], buffer_dir: Path, topic: str) -> int:
    if DRY_RUN:
        print(f"[dry-run] Would write {len(articles)} articles for topic '{topic}'")
        return len(articles)
    topic_dir = buffer_dir / topic
    topic_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for article in articles:
        url_hash = hashlib.md5(article.url.encode()).hexdigest()[:16]
        filepath = topic_dir / f"{url_hash}.json"
        if not filepath.exists():
            filepath.write_text(
                json.dumps(article.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            count += 1
    return count


async def scrape_topic(topic: str, topic_cfg: dict, settings: Settings, twitter_api) -> list[Article]:
    limit = settings.config["scraper"]["posts_per_topic_per_run"]
    articles: list[Article] = []
    failed_sources: list[str] = []

    for keyword in topic_cfg.get("keywords", []):
        try:
            articles += await fetch_twitter_articles(keyword, topic_hint=topic, api=twitter_api, limit=limit)
            articles += fetch_hn_articles(keyword, topic_hint=topic, limit=limit)
        except Exception as e:
            failed_sources.append(f"keyword:{keyword} ({e})")

    for tag in topic_cfg.get("medium_tags", []):
        try:
            articles += fetch_medium_articles(tag, topic_hint=topic, limit=limit)
        except Exception as e:
            failed_sources.append(f"medium:{tag} ({e})")

    for sub in topic_cfg.get("reddit", []):
        try:
            articles += fetch_reddit_articles(sub, topic_hint=topic, limit=limit)
        except Exception as e:
            failed_sources.append(f"reddit:{sub} ({e})")

    if failed_sources and not articles:
        error_msg = "\n".join(failed_sources)
        print(f"[scraper] All sources failed for topic '{topic}':\n{error_msg}", file=sys.stderr)
        send_failure_email(f"scraper/topic:{topic}", error_msg, settings)

    return articles


async def main() -> None:
    settings = Settings.load(CONFIG_PATH, ENV_PATH)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    buffer_dir = Path(__file__).parent / settings.buffer_dir / today

    print(f"[scraper] Starting scrape for {today} (dry_run={DRY_RUN})")

    twitter_api = await setup_twitter_api(
        settings.twitter_username,
        settings.twitter_password,
        settings.twitter_email,
        settings.twitter_email_password,
    )

    total = 0
    for topic, topic_cfg in settings.config["topics"].items():
        articles = await scrape_topic(topic, topic_cfg, settings, twitter_api)
        count = write_to_buffer(articles, buffer_dir, topic)
        print(f"[scraper] {topic}: {count} new articles buffered")
        total += count

    print(f"[scraper] Done. {total} total articles written to buffer.")


if __name__ == "__main__":
    asyncio.run(main())
