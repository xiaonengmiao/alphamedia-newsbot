from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from ..models import NewsItem


class NewsProvider(Protocol):
    name: str

    def fetch(self, topic: str, *, since: datetime | None, limit: int) -> Sequence[NewsItem]:
        """Return recent items that may be relevant to the topic."""
