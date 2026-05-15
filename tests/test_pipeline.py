from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alphamedia_newsbot.llm.stub import StubLLMClient
from alphamedia_newsbot.models import NewsItem
from alphamedia_newsbot.pipeline import NewsPipeline
from alphamedia_newsbot.storage import SQLiteStorage


class FakeProvider:
    name = "Fake"

    def fetch(self, topic: str, *, since: datetime | None, limit: int) -> list[NewsItem]:
        return [
            NewsItem(
                source="Fake",
                title="Prediction markets add new contracts",
                url="https://example.com/prediction",
                published_at=datetime.now(UTC),
            ),
            NewsItem(
                source="Fake",
                title="Generic markets move lower",
                url="https://example.com/markets",
                published_at=datetime.now(UTC),
            ),
        ]


class PipelineTest(unittest.TestCase):
    def test_run_filters_and_marks_seen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStorage(Path(tmp) / "test.sqlite3")
            pipeline = NewsPipeline(
                providers=[FakeProvider()],
                llm=StubLLMClient(),
                storage=store,
                lookback_hours=24,
                max_items_per_provider=20,
                min_relevance_score=0.3,
            )

            run = pipeline.run("Prediction Markets")
            fresh = pipeline.run("Prediction Markets", fresh_only=True)

            self.assertEqual(len(run.items), 1)
            self.assertEqual(len(fresh.items), 0)


if __name__ == "__main__":
    unittest.main()
