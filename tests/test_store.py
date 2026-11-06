from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from optics_qa.models import DraftResult
from optics_qa.store import Store
from tests.helpers import make_post


class StoreTests(unittest.TestCase):
    def test_save_list_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "queue.sqlite3")
            post = make_post()
            self.assertFalse(store.seen(post.post_id))
            store.save_draft(post, DraftResult("A" * 200, "medium", ["flag"], "test"), "short excerpt")
            self.assertTrue(store.seen(post.post_id))
            items = store.list_pending()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].post_id, post.post_id)
            self.assertEqual(items[0].flags, ("flag",))
            self.assertTrue(store.mark_replied(post.post_id))
            self.assertFalse(store.seen(post.post_id))
            self.assertEqual(store.list_pending(), [])
            store.close()

    def test_purge_expired_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "queue.sqlite3")
            post = make_post()
            store.save_draft(post, DraftResult("A" * 200, "low", [], "test"), "short")
            store.conn.execute("UPDATE drafts SET expires_at_utc = '2000-01-01T00:00:00Z'")
            store.conn.execute("UPDATE posts SET expires_at_utc = '2000-01-01T00:00:00Z'")
            store.conn.commit()
            result = store.purge()
            self.assertEqual(result["drafts_deleted"], 1)
            self.assertEqual(result["posts_deleted"], 1)
            self.assertEqual(store.stats()["drafts"], 0)
            store.close()

    def test_state_cursor_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "queue.sqlite3")
            store.set_state("last_seen_utc", "1700000000.0")
            self.assertEqual(store.get_state("last_seen_utc"), "1700000000.0")
            store.close()


if __name__ == "__main__":
    unittest.main()
