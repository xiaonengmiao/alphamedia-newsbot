from __future__ import annotations

import math
import re
from collections.abc import Iterable

from .models import NewsItem, normalize_text


STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "all",
    "and",
    "are",
    "because",
    "been",
    "before",
    "being",
    "between",
    "from",
    "have",
    "into",
    "more",
    "news",
    "over",
    "some",
    "that",
    "the",
    "their",
    "there",
    "this",
    "with",
    "would",
}


TOKEN_RE = re.compile(r"[a-z0-9$][a-z0-9$._-]*")


def tokenize_topic(topic: str) -> list[str]:
    tokens = TOKEN_RE.findall(normalize_text(topic))
    return [token for token in tokens if len(token) > 2 and token not in STOPWORDS]


def relevance_score(topic: str, item: NewsItem) -> float:
    tokens = tokenize_topic(topic)
    if not tokens:
        return 0.0

    haystack = normalize_text(item.text_for_matching)
    title = normalize_text(item.title)
    phrase = normalize_text(topic)

    score = 0.0
    if phrase and phrase in haystack:
        score += 0.45

    token_hits = sum(1 for token in tokens if token in haystack)
    title_hits = sum(1 for token in tokens if token in title)
    score += (token_hits / len(tokens)) * 0.40
    score += (title_hits / len(tokens)) * 0.15

    metrics = item.metadata.get("public_metrics") or {}
    engagement = sum(
        int(metrics.get(name, 0) or 0)
        for name in ("like_count", "retweet_count", "reply_count", "quote_count")
    )
    if engagement > 0:
        score += min(math.log10(engagement + 1) / 40, 0.05)

    return min(score, 1.0)


def deduplicate_items(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.fingerprint
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def filter_and_sort_items(
    topic: str,
    items: Iterable[NewsItem],
    *,
    min_score: float,
) -> list[NewsItem]:
    scored = [
        (relevance_score(topic, item), item)
        for item in deduplicate_items(items)
        if relevance_score(topic, item) >= min_score
    ]
    scored.sort(key=lambda pair: (pair[0], pair[1].published_at or 0), reverse=True)
    return [item for _, item in scored]
