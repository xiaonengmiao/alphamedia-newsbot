from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    return _SPACE_RE.sub(" ", (value or "").strip().lower())


def stable_hash(*parts: str | None) -> str:
    payload = "\x1f".join(normalize_text(part) for part in parts if part)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str = ""
    author: str | None = None
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        if self.url:
            return stable_hash(self.url)
        return stable_hash(self.source, self.title, self.summary)

    @property
    def text_for_matching(self) -> str:
        return " ".join(
            part
            for part in (self.title, self.summary, self.raw_text, self.source)
            if part and part.strip()
        )


@dataclass(frozen=True)
class Insight:
    topic: str
    summary: str
    categories: list[str]
    insights: list[str]
    noise: list[str]
    source_urls: list[str]
    raw_response: str = ""


@dataclass(frozen=True)
class ArticleDraft:
    topic: str
    title: str
    body: str
    x_thread: list[str]
    raw_response: str = ""


@dataclass(frozen=True)
class Goal:
    id: int
    chat_id: int
    topic: str
    created_at: str
    last_run_at: str | None


@dataclass(frozen=True)
class NewsRun:
    topic: str
    items: list[NewsItem]
    insight: Insight
    errors: list[str] = field(default_factory=list)
