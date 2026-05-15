from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from time import struct_time
from urllib.parse import quote, quote_plus

from ..models import NewsItem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return " ".join(self.parts)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    parser = _Stripper()
    parser.feed(value)
    return parser.text()


def parse_feed_spec(spec: str) -> FeedConfig:
    if "|" in spec:
        name, url = spec.split("|", 1)
        return FeedConfig(name=name.strip(), url=url.strip())
    return FeedConfig(name=spec.strip(), url=spec.strip())


class RSSProvider:
    def __init__(self, feed: FeedConfig):
        self.feed = feed
        self.name = feed.name

    def fetch(self, topic: str, *, since: datetime | None, limit: int) -> list[NewsItem]:
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser is not installed; skipping %s", self.feed.name)
            return []

        url = self._render_url(topic)
        parsed = feedparser.parse(url)
        source_name = self.feed.name or parsed.feed.get("title") or url

        items: list[NewsItem] = []
        for entry in parsed.entries[: max(limit * 2, limit)]:
            published_at = _entry_datetime(entry)
            if since and published_at and published_at < since:
                continue

            title = strip_html(entry.get("title", "")).strip()
            link = (entry.get("link", "") or "").strip()
            summary = strip_html(entry.get("summary") or entry.get("description") or "")
            if not title and not summary:
                continue

            items.append(
                NewsItem(
                    source=source_name,
                    title=title or summary[:120],
                    url=link,
                    published_at=published_at,
                    summary=summary,
                    author=entry.get("author"),
                    raw_text=summary,
                    metadata={"feed_url": url},
                )
            )
            if len(items) >= limit:
                break
        return items

    def _render_url(self, topic: str) -> str:
        return self.feed.url.format(topic=quote(topic), topic_q=quote_plus(topic))


def _entry_datetime(entry: object) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key) if hasattr(entry, "get") else None
        if isinstance(value, struct_time):
            return datetime.fromtimestamp(calendar.timegm(value), UTC)
    return None
