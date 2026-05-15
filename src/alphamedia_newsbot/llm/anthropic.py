from __future__ import annotations

from collections.abc import Sequence

import httpx

from ..models import ArticleDraft, Insight, NewsItem
from .json_utils import parse_json_object, string_list
from .prompts import article_prompt, summary_prompt


class AnthropicClient:
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or "claude-sonnet-4-5"

    def summarize(self, topic: str, items: Sequence[NewsItem]) -> Insight:
        text = self._message(summary_prompt(topic, items), max_tokens=1800)
        data = parse_json_object(text)
        return Insight(
            topic=topic,
            summary=str(data.get("summary", "")).strip(),
            categories=string_list(data.get("categories")),
            insights=string_list(data.get("insights")),
            noise=string_list(data.get("noise")),
            source_urls=string_list(data.get("source_urls")),
            raw_response=text,
        )

    def generate_article(self, topic: str, insight: Insight, items: Sequence[NewsItem]) -> ArticleDraft:
        text = self._message(article_prompt(topic, insight, items), max_tokens=2600)
        data = parse_json_object(text)
        return ArticleDraft(
            topic=topic,
            title=str(data.get("title", f"{topic} news update")).strip(),
            body=str(data.get("body", "")).strip(),
            x_thread=string_list(data.get("x_thread")),
            raw_response=text,
        )

    def _message(self, prompt: str, *, max_tokens: int) -> str:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        parts = [
            block.get("text", "")
            for block in payload.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(part for part in parts if part).strip()
