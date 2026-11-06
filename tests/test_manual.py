from __future__ import annotations

import json
import unittest

from optics_qa.sources.manual import parse_manual_input


class ManualParserTests(unittest.TestCase):
    def test_parses_text_block(self) -> None:
        post = parse_manual_input(
            "URL: https://www.reddit.com/r/Optics/comments/abc123/example/\n"
            "TITLE: AR coating question\n"
            "BODY:\n"
            "What coating should I use for 1064 nm?\n"
            "The substrate is fused silica.\n"
        )
        self.assertEqual(post.post_id, "t3_abc123")
        self.assertEqual(post.title, "AR coating question")
        self.assertIn("1064 nm", post.body)
        self.assertTrue(post.permalink.endswith("/example/"))

    def test_parses_json(self) -> None:
        post = parse_manual_input(
            json.dumps(
                {
                    "url": "https://www.reddit.com/r/Optics/comments/xyz789/example/",
                    "title": "Prism tolerance",
                    "body": "How do I specify angle tolerance?",
                }
            )
        )
        self.assertEqual(post.post_id, "t3_xyz789")
        self.assertEqual(post.subreddit, "Optics")

    def test_manual_hash_is_stable(self) -> None:
        first = parse_manual_input("TITLE: Same\nBODY: Same body")
        second = parse_manual_input("TITLE: Same\nBODY: Same body")
        self.assertEqual(first.post_id, second.post_id)
        self.assertTrue(first.post_id.startswith("manual-"))

    def test_empty_input_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_manual_input("   ")


if __name__ == "__main__":
    unittest.main()
