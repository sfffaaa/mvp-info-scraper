import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    url: str
    title: str
    content: str
    source: str           # "twitter" | "hn" | "medium" | "reddit" | "manual"
    scraped_at: str       # ISO 8601 datetime string
    topic_hint: str       # topic name from config
    score: Optional[float] = None
    summary: Optional[str] = None
    origin: str = "auto"  # "auto" | "manual"


def title_to_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return slug[:60].strip("-")
