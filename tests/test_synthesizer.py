from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from models import Article
from synthesizer import load_recent_articles, format_synthesis_email


def make_md_file(directory: Path, topic: str, date_str: str, title: str, content: str) -> None:
    topic_dir = directory / topic
    topic_dir.mkdir(parents=True, exist_ok=True)
    md_content = f"""# {title}

> Source: https://example.com
> Date: {date_str}
> Topic: {topic}
> Score: 8.0/10
> Origin: auto

## Summary
Summary of {title}

## Content
{content}
"""
    (topic_dir / f"{date_str}-test.md").write_text(md_content)


def test_load_recent_articles_finds_files(tmp_path):
    make_md_file(tmp_path, "ai-agent", "2026-04-13", "Article One", "Content one")
    make_md_file(tmp_path, "crypto", "2026-04-12", "Article Two", "Content two")

    articles = load_recent_articles(tmp_path, since_date="2026-04-12")
    assert len(articles) == 2
    titles = [a["title"] for a in articles]
    assert "Article One" in titles
    assert "Article Two" in titles


def test_load_recent_articles_excludes_old_files(tmp_path):
    make_md_file(tmp_path, "ai-agent", "2026-04-10", "Old Article", "Old content")
    make_md_file(tmp_path, "ai-agent", "2026-04-13", "New Article", "New content")

    articles = load_recent_articles(tmp_path, since_date="2026-04-12")
    assert len(articles) == 1
    assert articles[0]["title"] == "New Article"


def test_load_recent_articles_skips_synthesis_dir(tmp_path):
    make_md_file(tmp_path, "ai-agent", "2026-04-13", "Real Article", "content")
    synthesis_dir = tmp_path / "synthesis"
    synthesis_dir.mkdir()
    (synthesis_dir / "2026-04-12-synthesis.md").write_text("# Synthesis\nContent")

    articles = load_recent_articles(tmp_path, since_date="2026-04-12")
    assert len(articles) == 1


def test_format_synthesis_email_contains_key_sections():
    html = format_synthesis_email(
        report_text="## Key Themes\n- AI agents are rising\n\n## Actionable\n- Try X",
        article_count=12,
        date_str="2026-04-13",
    )
    assert "Key Themes" in html
    assert "Actionable" in html
    assert "12" in html
    assert "2026-04-13" in html
