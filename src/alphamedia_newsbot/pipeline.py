from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from .filters import filter_and_sort_items
from .llm.base import LLMClient
from .models import ArticleDraft, NewsItem, NewsRun
from .providers.base import NewsProvider
from .storage import SQLiteStorage

logger = logging.getLogger(__name__)


class NewsPipeline:
    def __init__(
        self,
        *,
        providers: Sequence[NewsProvider],
        llm: LLMClient,
        storage: SQLiteStorage,
        lookback_hours: int,
        max_items_per_provider: int,
        min_relevance_score: float,
    ):
        self.providers = list(providers)
        self.llm = llm
        self.storage = storage
        self.lookback_hours = lookback_hours
        self.max_items_per_provider = max_items_per_provider
        self.min_relevance_score = min_relevance_score

    def run(self, topic: str, *, fresh_only: bool = False) -> NewsRun:
        topic = topic.strip()
        if not topic:
            raise ValueError("topic cannot be empty")

        since = datetime.now(UTC) - timedelta(hours=self.lookback_hours)
        collected: list[NewsItem] = []
        errors: list[str] = []

        for provider in self.providers:
            try:
                collected.extend(
                    provider.fetch(topic, since=since, limit=self.max_items_per_provider)
                )
            except Exception as exc:
                logger.exception("Provider failed: %s", getattr(provider, "name", provider))
                errors.append(f"{getattr(provider, 'name', provider)}: {exc}")

        filtered = filter_and_sort_items(
            topic,
            collected,
            min_score=self.min_relevance_score,
        )
        if fresh_only:
            filtered = self.storage.filter_unseen(topic, filtered)

        self.storage.mark_seen_many(topic, filtered)
        insight = self.llm.summarize(topic, filtered)
        return NewsRun(topic=topic, items=filtered, insight=insight, errors=errors)

    def generate_article(self, run: NewsRun) -> ArticleDraft:
        return self.llm.generate_article(run.topic, run.insight, run.items)
