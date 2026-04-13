from unittest.mock import MagicMock, patch
from models import Article
from sources.hn import fetch_hn_articles
from sources.medium import fetch_medium_articles
from sources.reddit import fetch_reddit_articles


def test_fetch_hn_articles_returns_articles(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "hits": [
            {
                "url": "https://example.com/post",
                "title": "AI Agent Architecture",
                "story_text": "Some content about agents",
                "objectID": "12345",
                "created_at": "2026-04-13T07:00:00Z",
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    monkeypatch.setattr("sources.hn.requests.get", lambda *a, **kw: mock_resp)

    articles = fetch_hn_articles("AI agent", topic_hint="ai-agent", limit=15)
    assert len(articles) == 1
    assert articles[0].url == "https://example.com/post"
    assert articles[0].source == "hn"
    assert articles[0].topic_hint == "ai-agent"


def test_fetch_hn_articles_uses_item_url_as_fallback(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "hits": [{"url": None, "title": "Ask HN: something", "objectID": "99", "created_at": "2026-04-13T07:00:00Z"}]
    }
    mock_resp.raise_for_status = MagicMock()
    monkeypatch.setattr("sources.hn.requests.get", lambda *a, **kw: mock_resp)

    articles = fetch_hn_articles("something", topic_hint="ai-tools", limit=5)
    assert "ycombinator.com" in articles[0].url


def test_fetch_hn_articles_returns_empty_on_error(monkeypatch):
    monkeypatch.setattr("sources.hn.requests.get", MagicMock(side_effect=Exception("timeout")))
    articles = fetch_hn_articles("query", topic_hint="ai-agent", limit=5)
    assert articles == []


def test_fetch_medium_articles_returns_articles(monkeypatch):
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            link="https://medium.com/post",
            title="Medium Post",
            summary="Post summary content",
        )
    ]
    monkeypatch.setattr("sources.medium.feedparser.parse", lambda *a, **kw: mock_feed)

    articles = fetch_medium_articles("ai-agents", topic_hint="ai-agent", limit=5)
    assert len(articles) == 1
    assert articles[0].source == "medium"
    assert articles[0].url == "https://medium.com/post"


def test_fetch_medium_articles_returns_empty_on_error(monkeypatch):
    monkeypatch.setattr("sources.medium.feedparser.parse", MagicMock(side_effect=Exception("dns")))
    articles = fetch_medium_articles("tag", topic_hint="ai-agent", limit=5)
    assert articles == []


def test_fetch_reddit_articles_returns_articles(monkeypatch):
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            link="https://reddit.com/r/MachineLearning/comments/abc",
            title="Interesting Reddit Post",
            summary="Some discussion here",
        )
    ]
    monkeypatch.setattr("sources.reddit.feedparser.parse", lambda *a, **kw: mock_feed)

    articles = fetch_reddit_articles("MachineLearning", topic_hint="ai-agent", limit=5)
    assert len(articles) == 1
    assert articles[0].source == "reddit"


def test_fetch_reddit_articles_returns_empty_on_error(monkeypatch):
    monkeypatch.setattr("sources.reddit.feedparser.parse", MagicMock(side_effect=Exception("timeout")))
    articles = fetch_reddit_articles("sub", topic_hint="ai-agent", limit=5)
    assert articles == []
