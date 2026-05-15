from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..models import ArticleDraft, Insight, NewsItem


class LLMClient(Protocol):
    def summarize(self, topic: str, items: Sequence[NewsItem]) -> Insight:
        """Summarize and categorize news items."""

    def generate_article(self, topic: str, insight: Insight, items: Sequence[NewsItem]) -> ArticleDraft:
        """Generate a longer article draft and X thread."""
