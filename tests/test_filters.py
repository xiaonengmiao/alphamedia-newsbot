from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alphamedia_newsbot.filters import filter_and_sort_items, relevance_score
from alphamedia_newsbot.models import NewsItem


class FiltersTest(unittest.TestCase):
    def test_relevance_prefers_topic_phrase(self) -> None:
        strong = NewsItem(
            source="Example",
            title="Prediction markets volume surges after election debate",
            url="https://example.com/a",
        )
        weak = NewsItem(
            source="Example",
            title="Markets rally after earnings surprise",
            url="https://example.com/b",
        )

        self.assertGreater(relevance_score("Prediction Markets", strong), 0.8)
        self.assertLess(relevance_score("Prediction Markets", weak), 0.3)

    def test_filter_deduplicates_by_url(self) -> None:
        one = NewsItem(
            source="A",
            title="Prediction markets face new regulation",
            url="https://example.com/a",
        )
        duplicate = NewsItem(
            source="B",
            title="Different headline about prediction markets",
            url="https://example.com/a",
        )

        items = filter_and_sort_items("Prediction Markets", [one, duplicate], min_score=0.3)

        self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
