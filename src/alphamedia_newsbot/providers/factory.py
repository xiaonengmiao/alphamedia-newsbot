from __future__ import annotations

from ..config import Settings
from .base import NewsProvider
from .rss import FeedConfig, RSSProvider, parse_feed_spec


def build_providers(settings: Settings) -> list[NewsProvider]:
    providers: list[NewsProvider] = []

    for spec in settings.rss_feeds:
        providers.append(RSSProvider(parse_feed_spec(spec)))

    for symbol in settings.yahoo_finance_symbols:
        providers.append(
            RSSProvider(
                FeedConfig(
                    name=f"Yahoo Finance {symbol}",
                    url=f"https://finance.yahoo.com/rss/headline?s={symbol}",
                )
            )
        )

    if settings.x_bearer_token:
        from .x_api import XRecentSearchProvider

        providers.append(
            XRecentSearchProvider(
                bearer_token=settings.x_bearer_token,
                query_template=settings.x_query_template,
            )
        )

    return providers
