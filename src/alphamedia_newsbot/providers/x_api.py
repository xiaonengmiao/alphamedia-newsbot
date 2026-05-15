from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..models import NewsItem

logger = logging.getLogger(__name__)


class XRecentSearchProvider:
    name = "X"
    endpoint = "https://api.x.com/2/tweets/search/recent"

    def __init__(self, bearer_token: str | None, query_template: str):
        self.bearer_token = bearer_token
        self.query_template = query_template

    def fetch(self, topic: str, *, since: datetime | None, limit: int) -> list[NewsItem]:
        if not self.bearer_token:
            return []

        try:
            import httpx
        except ImportError:
            logger.warning("httpx is not installed; skipping X recent search")
            return []

        query = self.query_template.format(topic=topic)
        params: dict[str, str | int] = {
            "query": query,
            "max_results": max(10, min(limit, 100)),
            "tweet.fields": "created_at,public_metrics,author_id,lang,entities",
            "expansions": "author_id",
            "user.fields": "username,name,verified,public_metrics",
        }
        if since:
            params["start_time"] = since.astimezone(UTC).isoformat().replace("+00:00", "Z")

        try:
            response = httpx.get(
                self.endpoint,
                params=params,
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                timeout=20,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("X recent search failed: %s", exc)
            return []

        payload = response.json()
        users = {
            user["id"]: user
            for user in payload.get("includes", {}).get("users", [])
            if isinstance(user, dict) and "id" in user
        }

        items: list[NewsItem] = []
        for tweet in payload.get("data", []):
            text = (tweet.get("text") or "").strip()
            if not text:
                continue

            author = users.get(tweet.get("author_id"), {})
            username = author.get("username") or tweet.get("author_id") or "i"
            tweet_id = tweet.get("id")
            created_at = _parse_datetime(tweet.get("created_at"))
            title = text.splitlines()[0][:180]

            items.append(
                NewsItem(
                    source="X",
                    title=title,
                    url=f"https://x.com/{username}/status/{tweet_id}",
                    published_at=created_at,
                    summary=text,
                    author=author.get("name") or username,
                    raw_text=text,
                    metadata={
                        "tweet_id": tweet_id,
                        "username": username,
                        "public_metrics": tweet.get("public_metrics") or {},
                        "query": query,
                    },
                )
            )
        return items


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
