import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from models import Article
from classifier import (
    load_seen_urls,
    save_seen_urls,
    dedup_articles,
    format_article_md,
    load_buffer_articles,
)


def make_article(**kwargs) -> Article:
    defaults = dict(
        url="https://example.com/post",
        title="Test Article",
        content="Some content",
        source="hn",
        scraped_at="2026-04-13T07:00:00Z",
        topic_hint="ai-agent",
        score=8.0,
        summary="A test summary",
    )
    defaults.update(kwargs)
    return Article(**defaults)


def test_load_seen_urls_empty(tmp_path):
    seen_file = tmp_path / "seen_urls.txt"
    seen_file.write_text("")
    urls = load_seen_urls(seen_file)
    assert urls == set()


def test_load_seen_urls_with_entries(tmp_path):
    seen_file = tmp_path / "seen_urls.txt"
    seen_file.write_text("https://a.com\nhttps://b.com\n")
    urls = load_seen_urls(seen_file)
    assert "https://a.com" in urls
    assert len(urls) == 2


def test_load_seen_urls_missing_file(tmp_path):
    seen_file = tmp_path / "nonexistent.txt"
    urls = load_seen_urls(seen_file)
    assert urls == set()


def test_save_seen_urls_appends(tmp_path):
    seen_file = tmp_path / "seen_urls.txt"
    seen_file.write_text("https://existing.com\n")
    articles = [make_article(url="https://new1.com"), make_article(url="https://new2.com")]
    save_seen_urls(articles, seen_file)
    content = seen_file.read_text()
    assert "https://existing.com" in content
    assert "https://new1.com" in content
    assert "https://new2.com" in content


def test_dedup_articles_removes_seen():
    articles = [
        make_article(url="https://new.com"),
        make_article(url="https://seen.com"),
    ]
    seen = {"https://seen.com"}
    result = dedup_articles(articles, seen)
    assert len(result) == 1
    assert result[0].url == "https://new.com"


def test_dedup_articles_all_new():
    articles = [make_article(url="https://a.com"), make_article(url="https://b.com")]
    result = dedup_articles(articles, set())
    assert len(result) == 2


def test_format_article_md_contains_required_fields():
    article = make_article(
        url="https://example.com/post",
        title="Great Article",
        content="Full content here",
        topic_hint="ai-agent",
        score=9.0,
        summary="A great summary",
        scraped_at="2026-04-13T07:00:00Z",
    )
    md = format_article_md(article)
    assert "# Great Article" in md
    assert "> Source: https://example.com/post" in md
    assert "> Score: 9.0/10" in md
    assert "> Topic: ai-agent" in md
    assert "## Summary" in md
    assert "A great summary" in md
    assert "## Content" in md
    assert "Full content here" in md


def test_load_buffer_articles(tmp_path):
    topic_dir = tmp_path / "ai-agent"
    topic_dir.mkdir()
    article_data = {
        "url": "https://example.com",
        "title": "Test",
        "content": "content",
        "source": "hn",
        "scraped_at": "2026-04-13T07:00:00Z",
        "topic_hint": "ai-agent",
        "score": None,
        "summary": None,
        "origin": "auto",
    }
    (topic_dir / "abc123.json").write_text(json.dumps(article_data))

    articles = load_buffer_articles(tmp_path)
    assert len(articles) == 1
    assert articles[0].url == "https://example.com"
    assert articles[0].topic_hint == "ai-agent"
