from __future__ import annotations

import unittest

from optics_qa.filtering import classify_post, commercial_flags, excerpt
from tests.helpers import make_post


class FilteringTests(unittest.TestCase):
    def test_technical_question_included(self) -> None:
        result = classify_post(make_post())
        self.assertTrue(result.include)
        self.assertEqual(result.category, "technical_question")

    def test_sourcing_skipped(self) -> None:
        result = classify_post(
            make_post(
                title="Looking for a custom prism supplier",
                body="We need 500 pieces and a quote. Please DM me.",
            )
        )
        self.assertFalse(result.include)
        self.assertEqual(result.category, "skip")
        self.assertIn("sourcing_or_rfq", result.reasons)

    def test_discussion_without_question_skipped(self) -> None:
        result = classify_post(
            make_post(
                title="My new lens arrived today",
                body="Here is a photo of the unboxing.",
            )
        )
        self.assertFalse(result.include)
        self.assertEqual(result.category, "skip")
        self.assertIn("discussion_not_question", result.reasons)

    def test_meme_skipped(self) -> None:
        result = classify_post(make_post(title="Weekly meme thread", body="post memes here"))
        self.assertFalse(result.include)
        self.assertEqual(result.category, "skip")

    def test_removed_skipped(self) -> None:
        result = classify_post(make_post(removed=True))
        self.assertFalse(result.include)
        self.assertIn("removed_or_deleted", result.reasons)

    def test_over_18_skipped(self) -> None:
        result = classify_post(make_post(over_18=True))
        self.assertFalse(result.include)
        self.assertIn("over_18", result.reasons)

    def test_stickied_skipped(self) -> None:
        result = classify_post(make_post(stickied=True))
        self.assertFalse(result.include)
        self.assertIn("stickied", result.reasons)

    def test_commercial_language_flagged(self) -> None:
        flags = commercial_flags("Contact us for pricing. Our factory can supply this.")
        self.assertTrue(any(flag.startswith("commercial_language:") for flag in flags))

    def test_excerpt_is_short(self) -> None:
        text = " ".join(["word"] * 200)
        result = excerpt(text, max_chars=50)
        self.assertLessEqual(len(result), 53)
        self.assertTrue(result.endswith("..."))


if __name__ == "__main__":
    unittest.main()
