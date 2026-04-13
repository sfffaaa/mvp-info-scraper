#!/usr/bin/env python3
"""
Classifier: reads today's buffer, scores with Claude CLI, saves top articles as .md.
Run at 21:00 daily via cron.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import Settings
from email_utils import send_failure_email
from models import Article, title_to_slug

CONFIG_PATH = Path(__file__).parent / "config.yaml"
ENV_PATH = Path(__file__).parent / ".env"
DRY_RUN = "--dry-run" in sys.argv


def load_seen_urls(seen_file: Path) -> set[str]:
    if not seen_file.exists():
        return set()
    return {line.strip() for line in seen_file.read_text().splitlines() if line.strip()}


def save_seen_urls(articles: list[Article], seen_file: Path) -> None:
    existing = load_seen_urls(seen_file)
    existing.update(a.url for a in articles)
    seen_file.write_text("\n".join(sorted(existing)) + "\n")


def dedup_articles(articles: list[Article], seen: set[str]) -> list[Article]:
    return [a for a in articles if a.url not in seen]


def load_buffer_articles(buffer_date_dir: Path) -> list[Article]:
    articles = []
    for json_file in buffer_date_dir.rglob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            articles.append(Article(**data))
        except Exception as e:
            print(f"[classifier] Could not load {json_file}: {e}", file=sys.stderr)
    return articles


def format_article_md(article: Article) -> str:
    score_str = f"{article.score}/10" if article.score is not None else "N/A"
    return f"""# {article.title}

> Source: {article.url}
> Date: {article.scraped_at[:10]}
> Topic: {article.topic_hint}
> Score: {score_str}
> Origin: {article.origin}

## Summary
{article.summary or ""}

## Content
{article.content}
"""


def score_articles_with_claude(
    articles: list[Article],
    topic: str,
    preferences_text: str,
    top_n: int = 5,
) -> list[Article]:
    if not articles:
        return []

    article_list = "\n".join(
        f"[{i}] URL: {a.url}\nTitle: {a.title}\nContent (truncated): {a.content[:500]}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are curating articles for a reader interested in: {topic}

User taste profile:
{preferences_text}

Rate each article 1-10 based on:
- Originality (first-hand analysis, not news summaries)
- Depth (concrete data, specific insights)
- Relevance to topic
- Alignment with user preferences

Articles:
{article_list}

Return ONLY a JSON array, no extra text:
[
  {{"index": 0, "score": 8.5, "summary": "2-3 sentence summary of key insight"}},
  ...
]
Include all {len(articles)} articles. Use index matching the [N] above."""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        text = result.stdout.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            text = text.rsplit("```", 1)[0].strip()
        scored = json.loads(text)
        for item in scored:
            idx = item["index"]
            if 0 <= idx < len(articles):
                articles[idx].score = item["score"]
                articles[idx].summary = item["summary"]
        articles.sort(key=lambda a: a.score or 0, reverse=True)
        return articles[:top_n]
    except Exception as e:
        print(f"[classifier] Claude scoring failed for {topic}: {e}", file=sys.stderr)
        return articles[:top_n]


def save_article(article: Article, output_dir: Path) -> None:
    topic_dir = output_dir / article.topic_hint
    topic_dir.mkdir(parents=True, exist_ok=True)
    slug = title_to_slug(article.title)
    date_prefix = article.scraped_at[:10]
    filepath = topic_dir / f"{date_prefix}-{slug}.md"
    counter = 1
    while filepath.exists():
        filepath = topic_dir / f"{date_prefix}-{slug}-{counter}.md"
        counter += 1
    filepath.write_text(format_article_md(article), encoding="utf-8")
    print(f"[classifier] Saved: {filepath}")


def main() -> None:
    settings = Settings.load(CONFIG_PATH, ENV_PATH)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    buffer_date_dir = Path(__file__).parent / settings.buffer_dir / today
    seen_file = Path(__file__).parent / settings.seen_urls_path
    preferences_text = (Path(__file__).parent / settings.preferences_path).read_text()
    output_dir = settings.output_dir
    top_n = settings.config["scraper"]["save_top_per_topic"]

    if not buffer_date_dir.exists():
        print(f"[classifier] No buffer for {today}, nothing to classify.")
        return

    print(f"[classifier] Loading buffer for {today}...")
    all_articles = load_buffer_articles(buffer_date_dir)
    seen_urls = load_seen_urls(seen_file)
    new_articles = dedup_articles(all_articles, seen_urls)
    print(f"[classifier] {len(new_articles)} new articles after dedup (of {len(all_articles)} total)")

    by_topic: dict[str, list[Article]] = {}
    for article in new_articles:
        by_topic.setdefault(article.topic_hint, []).append(article)

    saved: list[Article] = []
    for topic, articles in by_topic.items():
        print(f"[classifier] Scoring {len(articles)} articles for '{topic}'...")
        top = score_articles_with_claude(articles, topic, preferences_text, top_n)
        for article in top:
            if DRY_RUN:
                print(f"[dry-run] Would save: {article.title} (score={article.score})")
            else:
                save_article(article, output_dir)
                saved.append(article)

    if not DRY_RUN:
        save_seen_urls(new_articles, seen_file)
        print(f"[classifier] Done. {len(saved)} articles saved.")


if __name__ == "__main__":
    main()
