from __future__ import annotations

from collections.abc import Sequence

from ..models import Insight, NewsItem


SYSTEM_RULES = """You are an analyst for a real-news monitoring bot.
Use only the supplied items. Do not invent facts, sources, dates, prices, or quotes.
Separate signal from noise. Mention uncertainty when the evidence is thin.
Prefer concise, decision-useful analysis over generic summaries."""


def items_context(items: Sequence[NewsItem], *, max_items: int = 18) -> str:
    if not items:
        return "No relevant items were found."

    lines: list[str] = []
    for index, item in enumerate(items[:max_items], start=1):
        published = item.published_at.isoformat() if item.published_at else "unknown date"
        lines.append(
            "\n".join(
                [
                    f"{index}. {item.title}",
                    f"Source: {item.source}",
                    f"Published: {published}",
                    f"URL: {item.url}",
                    f"Text: {(item.summary or item.raw_text)[:1200]}",
                ]
            )
        )
    return "\n\n".join(lines)


def summary_prompt(topic: str, items: Sequence[NewsItem]) -> str:
    return f"""{SYSTEM_RULES}

Topic: {topic}

News items:
{items_context(items)}

Return JSON only with these keys:
- summary: 3-5 sentence executive summary.
- categories: array of category labels such as Market, Policy, Company, Product, Social, Research, Funding.
- insights: array of 4-8 concrete insights.
- noise: array of items or angles that look weak, repetitive, promotional, or uncertain.
- source_urls: array of the most important source URLs from the supplied items.
"""


def article_prompt(topic: str, insight: Insight, items: Sequence[NewsItem]) -> str:
    return f"""{SYSTEM_RULES}

Topic: {topic}

Executive summary:
{insight.summary}

Insights:
{chr(10).join(f"- {item}" for item in insight.insights)}

Source items:
{items_context(items, max_items=12)}

Draft a publishable article and an X thread. Stay factual and cite source URLs inline where useful.

Return JSON only with these keys:
- title: concise article title.
- body: 600-900 word article body with short paragraphs.
- x_thread: array of 5-8 posts, each under 260 characters.
"""
