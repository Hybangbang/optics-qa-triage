from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from optics_qa.cli import main


SAMPLE = (
    "URL: https://www.reddit.com/r/Optics/comments/abc123/example/\n"
    "TITLE: How do I specify a window?\n"
    "BODY:\n"
    "I need lambda/10 and 60-40 for a 25 mm BK7 window. What belongs on the drawing?\n"
)


class CliTests(unittest.TestCase):
    def test_selftest_passes_without_false_write_endpoint_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "OPTICS_QA_DB": str(Path(tmp) / "queue.sqlite3"),
                "OPTICS_QA_OUTBOX": str(Path(tmp) / "outbox"),
                "REDDIT_API_APPROVED": "false",
                "LLM_API_KEY": "",
                "SMTP_HOST": "",
                "EMAIL_TO": "",
            }
            with patch.dict(os.environ, env, clear=True):
                output = io.StringIO()
                errors = io.StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    code = main(["selftest"])
            self.assertEqual(code, 0, errors.getvalue())
            self.assertIn("Selftest passed", output.getvalue())

    def test_draft_manual_mode_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "OPTICS_QA_DB": str(Path(tmp) / "queue.sqlite3"),
                "OPTICS_QA_OUTBOX": str(Path(tmp) / "outbox"),
                "LLM_API_KEY": "",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("sys.stdin", io.StringIO(SAMPLE)):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        code = main(["draft", "--no-llm"])
            self.assertEqual(code, 0)
            self.assertIn("Answer draft", output.getvalue())

    def test_poll_fixture_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "queue.sqlite3"
            env = {
                "OPTICS_QA_DB": str(db),
                "OPTICS_QA_OUTBOX": str(Path(tmp) / "outbox"),
                "LLM_API_KEY": "",
            }
            with patch.dict(os.environ, env, clear=False):
                output = io.StringIO()
                errors = io.StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    code = main(["poll", "--source", "fixture", "--no-llm", "--no-email"])
                self.assertEqual(code, 0)
                self.assertIn("Read-only optics Q&A review queue", output.getvalue())
                self.assertIn("Poll complete", errors.getvalue())
                review = io.StringIO()
                with redirect_stdout(review), redirect_stderr(io.StringIO()):
                    code = main(["review"])
                self.assertEqual(code, 0)
                self.assertIn("Answer draft", review.getvalue())


if __name__ == "__main__":
    unittest.main()
