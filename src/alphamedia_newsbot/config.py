from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - useful before dependencies are installed
    load_dotenv = None


DEFAULT_RSS_FEEDS = [
    "Bloomberg Markets|https://feeds.bloomberg.com/markets/news.rss",
    "Bloomberg Technology|https://feeds.bloomberg.com/technology/news.rss",
]


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _int_set(value: str | None) -> set[int]:
    ids: set[int] = set()
    for part in _csv(value):
        try:
            ids.add(int(part))
        except ValueError:
            raise ValueError(f"Invalid TELEGRAM_ALLOWED_CHAT_IDS value: {part!r}") from None
    return ids


def _float(value: str | None, default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _int(value: str | None, default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_allowed_chat_ids: set[int]
    llm_provider: str
    llm_model: str | None
    anthropic_api_key: str | None
    deepseek_api_key: str | None
    x_bearer_token: str | None
    x_query_template: str
    rss_feeds: list[str]
    yahoo_finance_symbols: list[str]
    news_lookback_hours: int
    max_items_per_provider: int
    min_relevance_score: float
    track_interval_minutes: int
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "newsbot.sqlite3"

    @classmethod
    def from_env(cls) -> "Settings":
        if load_dotenv is not None:
            load_dotenv()

        rss_feeds = _csv(os.getenv("RSS_FEEDS"))
        if not rss_feeds:
            rss_feeds = list(DEFAULT_RSS_FEEDS)

        data_dir = Path(os.getenv("DATA_DIR", ".data")).expanduser().resolve()

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_allowed_chat_ids=_int_set(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS")),
            llm_provider=os.getenv("LLM_PROVIDER", "stub").strip().lower(),
            llm_model=os.getenv("LLM_MODEL", "").strip() or None,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip() or None,
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip() or None,
            x_bearer_token=os.getenv("X_BEARER_TOKEN", "").strip() or None,
            x_query_template=os.getenv(
                "X_QUERY_TEMPLATE", '"{topic}" lang:en -is:retweet -is:reply'
            ),
            rss_feeds=rss_feeds,
            yahoo_finance_symbols=_csv(os.getenv("YAHOO_FINANCE_SYMBOLS", "SPY,QQQ")),
            news_lookback_hours=_int(os.getenv("NEWS_LOOKBACK_HOURS"), 24),
            max_items_per_provider=_int(os.getenv("MAX_ITEMS_PER_PROVIDER"), 40),
            min_relevance_score=_float(os.getenv("MIN_RELEVANCE_SCORE"), 0.30),
            track_interval_minutes=_int(os.getenv("TRACK_INTERVAL_MINUTES"), 30),
            data_dir=data_dir,
        )
