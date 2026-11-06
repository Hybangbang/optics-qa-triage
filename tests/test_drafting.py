from __future__ import annotations

import unittest

from optics_qa.drafting import TemplateProvider, build_user_prompt, postprocess_draft
from optics_qa.models import DraftResult
from tests.helpers import make_post


class DraftingTests(unittest.TestCase):
    def test_template_provider_is_explicitly_offline(self) -> None:
        result = TemplateProvider().draft(make_post())
        self.assertIn("Answer draft", result.text)
        self.assertIn("llm_disabled", result.flags)
        self.assertEqual(result.confidence, "low")

    def test_postprocess_flags_commercial_language(self) -> None:
        text = (
            "Answer draft\n"
            "This is a sufficiently long draft about a lens. Contact us for pricing. "
            "Our factory can supply this.\n\n"
            "Confidence: high\n"
            "Rule flags: none"
        )
        result = postprocess_draft(DraftResult(text=text, confidence="high", flags=[], model="test"))
        self.assertTrue(any(flag.startswith("commercial_language:") for flag in result.flags))
        self.assertNotEqual(result.confidence, "high")

    def test_prompt_contains_rules(self) -> None:
        prompt = build_user_prompt(make_post(), "- No self-promotion")
        self.assertIn("No self-promotion", prompt)
        self.assertIn("Draft a reply", prompt)


if __name__ == "__main__":
    unittest.main()
