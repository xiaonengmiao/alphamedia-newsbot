from __future__ import annotations

from .config import Settings
from .llm import build_llm
from .pipeline import NewsPipeline
from .providers import build_providers
from .storage import SQLiteStorage


def build_pipeline(settings: Settings) -> NewsPipeline:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    storage = SQLiteStorage(settings.db_path)
    return NewsPipeline(
        providers=build_providers(settings),
        llm=build_llm(settings),
        storage=storage,
        lookback_hours=settings.news_lookback_hours,
        max_items_per_provider=settings.max_items_per_provider,
        min_relevance_score=settings.min_relevance_score,
    )
