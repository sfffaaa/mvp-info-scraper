from models import Article, title_to_slug


def test_article_defaults():
    a = Article(
        url="https://example.com/post",
        title="Test Post",
        content="Some content here",
        source="hn",
        scraped_at="2026-04-13T07:00:00Z",
        topic_hint="ai-agent",
    )
    assert a.origin == "auto"
    assert a.score is None
    assert a.summary is None


def test_article_manual_origin():
    a = Article(
        url="https://example.com",
        title="Manual",
        content="content",
        source="manual",
        scraped_at="2026-04-13T07:00:00Z",
        topic_hint="crypto",
        origin="manual",
    )
    assert a.origin == "manual"


def test_title_to_slug_basic():
    assert title_to_slug("Hello World") == "hello-world"


def test_title_to_slug_special_chars():
    assert title_to_slug("AI agents: 2026 review!") == "ai-agents-2026-review"


def test_title_to_slug_truncates_at_60():
    long_title = "a" * 100
    slug = title_to_slug(long_title)
    assert len(slug) <= 60


def test_title_to_slug_no_trailing_dash():
    slug = title_to_slug("hello world " + "a" * 60)
    assert not slug.endswith("-")
