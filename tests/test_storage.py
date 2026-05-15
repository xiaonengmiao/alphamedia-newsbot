from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alphamedia_newsbot.models import NewsItem
from alphamedia_newsbot.storage import SQLiteStorage


class StorageTest(unittest.TestCase):
    def test_goal_upsert_and_seen_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStorage(Path(tmp) / "test.sqlite3")
            goal = store.upsert_goal(123, "Prediction Markets")
            same_goal = store.upsert_goal(123, "prediction markets")

            self.assertEqual(goal.id, same_goal.id)
            self.assertEqual(len(store.list_goals(123)), 1)

            item = NewsItem(
                source="Example",
                title="Prediction markets make headlines",
                url="https://example.com/a",
            )
            self.assertEqual(store.filter_unseen("Prediction Markets", [item]), [item])
            store.mark_seen_many("Prediction Markets", [item])
            self.assertEqual(store.filter_unseen("Prediction Markets", [item]), [])


if __name__ == "__main__":
    unittest.main()
