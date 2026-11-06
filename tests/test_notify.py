from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from optics_qa.models import ReviewItem
from optics_qa.notify import OutboxNotifier, cleanup_outbox, render_body


def make_item() -> ReviewItem:
    return ReviewItem(
        post_id="t3_example1",
        subreddit="Optics",
        permalink="https://www.reddit.com/r/Optics/comments/example1/example/",
        excerpt="A short excerpt.",
        draft_text="Answer draft\nA technical answer.\n\nConfidence: medium\nRule flags: none",
        confidence="medium",
        flags=("needs_human_review",),
        created_utc="2026-01-01T00:00:00Z",
    )


class NotifyTests(unittest.TestCase):
    def test_outbox_writes_eml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notifier = OutboxNotifier(Path(tmp), "review@example.test")
            paths = notifier.send([make_item()])
            self.assertEqual(len(paths), 1)
            content = Path(paths[0]).read_text(encoding="utf-8")
            self.assertIn("Optics Q&A", content)
            self.assertIn("t3_example1".replace("t3_", ""), content)

    def test_cleanup_removes_old_eml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            notifier = OutboxNotifier(outbox)
            path = Path(notifier.send([make_item()])[0])
            old = time.time() - 49 * 3600
            os.utime(path, (old, old))
            self.assertEqual(cleanup_outbox(outbox, 48), 1)
            self.assertFalse(path.exists())

    def test_render_body_contains_review_fields(self) -> None:
        body = render_body([make_item()])
        self.assertIn("Confidence: medium", body)
        self.assertIn("needs_human_review", body)
        self.assertIn("Delete this message", body)


if __name__ == "__main__":
    unittest.main()
