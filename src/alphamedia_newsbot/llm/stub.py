from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from ..models import ArticleDraft, Insight, NewsItem


class StubLLMClient:
    """Deterministic local fallback for smoke tests and development."""

    def summarize(self, topic: str, items: Sequence[NewsItem]) -> Insight:
        if not items:
            return Insight(
                topic=topic,
                summary=f"No high-confidence news items were found for {topic}.",
                categories=[],
                insights=[],
                noise=["No items passed the local relevance filter."],
                source_urls=[],
                raw_response="stub",
            )

        categories = Counter(_category(item) for item in items)
        top_titles = [f"{item.source}: {item.title}" for item in items[:6]]
        summary = (
            f"Found {len(items)} relevant items for {topic}. "
            f"The strongest signals come from {', '.join(dict(categories.most_common(3)).keys())}. "
            "Set LLM_PROVIDER=anthropic or LLM_PROVIDER=deepseek for richer analysis."
        )
        return Insight(
            topic=topic,
            summary=summary,
            categories=list(dict(categories.most_common()).keys()),
            insights=top_titles,
            noise=["Stub mode does not perform deep semantic noise filtering."],
            source_urls=[item.url for item in items[:8] if item.url],
            raw_response="stub",
        )

    def generate_article(self, topic: str, insight: Insight, items: Sequence[NewsItem]) -> ArticleDraft:
        title = f"What the latest news suggests about {topic}"
        source_lines = "\n".join(f"- {item.source}: {item.title} ({item.url})" for item in items[:8])
        body = (
            f"{insight.summary}\n\n"
            "Key signals:\n"
            + "\n".join(f"- {item}" for item in insight.insights[:8])
            + "\n\nSources:\n"
            + source_lines
        )
        x_thread = [
            f"{topic}: {insight.summary[:220]}",
            "Top signals: " + "; ".join(insight.insights[:2])[:235],
            "Use a real LLM provider for a polished thread and article draft.",
        ]
        return ArticleDraft(topic=topic, title=title, body=body, x_thread=x_thread, raw_response="stub")


def _category(item: NewsItem) -> str:
    text = f"{item.title} {item.summary}".lower()
    if any(word in text for word in ("sec", "cftc", "regulator", "law", "court", "policy")):
        return "Policy"
    if any(word in text for word in ("funding", "raises", "acquires", "partnership")):
        return "Company"
    if item.source.lower() == "x":
        return "Social"
    if any(word in text for word in ("market", "price", "trading", "stock", "crypto")):
        return "Market"
    return "General"
