from __future__ import annotations

import html
from collections.abc import Iterable

from .models import ArticleDraft, NewsItem, NewsRun


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_run(run: NewsRun) -> str:
    if not run.items:
        lines = [
            f"<b>{e(run.topic)}</b>",
            "",
            e(run.insight.summary),
        ]
        if run.errors:
            lines.extend(["", "<b>Source errors</b>", *[f"- {e(error)}" for error in run.errors[:4]]])
        return "\n".join(lines)

    lines = [
        f"<b>{e(run.topic)}</b>",
        "",
        e(run.insight.summary),
    ]
    if run.insight.categories:
        lines.extend(["", "<b>Categories</b>", e(", ".join(run.insight.categories[:8]))])
    if run.insight.insights:
        lines.extend(["", "<b>Insights</b>"])
        lines.extend(f"- {e(item)}" for item in run.insight.insights[:8])
    if run.insight.noise:
        lines.extend(["", "<b>Noise filter</b>"])
        lines.extend(f"- {e(item)}" for item in run.insight.noise[:4])
    lines.extend(["", "<b>Top sources</b>"])
    lines.extend(_source_lines(run.items[:8]))
    if run.errors:
        lines.extend(["", "<b>Source errors</b>", *[f"- {e(error)}" for error in run.errors[:4]]])
    return "\n".join(lines)


def format_article(article: ArticleDraft) -> str:
    lines = [
        f"<b>{e(article.title)}</b>",
        "",
        e(article.body),
    ]
    if article.x_thread:
        lines.extend(["", "<b>X thread draft</b>"])
        for index, post in enumerate(article.x_thread, start=1):
            lines.append(f"{index}. {e(post)}")
    return "\n".join(lines)


def split_telegram_message(text: str, *, max_chars: int = 3500) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in text.split("\n"):
        addition = len(paragraph) + 1
        if current and current_len + addition > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += addition
    if current:
        chunks.append("\n".join(current))
    return chunks


def _source_lines(items: Iterable[NewsItem]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        title = e(item.title)
        source = e(item.source)
        if item.url:
            lines.append(f'{index}. <a href="{e(item.url)}">{title}</a> - {source}')
        else:
            lines.append(f"{index}. {title} - {source}")
    return lines
