from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from optics_qa.sources.reddit import RedditNotApproved, RedditSource
from tests.helpers import make_settings


class FakeResponse:
    def __init__(self, status_code: int, payload, headers=None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[tuple[str, dict]] = []

    def mount(self, *args, **kwargs) -> None:
        return None

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse(200, {"access_token": "token", "expires_in": 3600})

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        if url.endswith("/about/rules"):
            return FakeResponse(
                200,
                {"rules": [{"short_name": "No self-promotion", "description": "Be helpful."}]},
            )
        return FakeResponse(
            200,
            {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "id": "abc123",
                                "subreddit": "Optics",
                                "title": "How to specify a window?",
                                "selftext": "I need lambda/10 and 60-40.",
                                "permalink": "/r/Optics/comments/abc123/example/",
                                "created_utc": 1700000000.0,
                                "over_18": False,
                                "stickied": False,
                                "author": "synthetic-user",
                            },
                        }
                    ]
                }
            },
            headers={"X-Ratelimit-Remaining": "99"},
        )


class RedditSourceTests(unittest.TestCase):
    def test_refuses_without_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp), approved=False)
            with self.assertRaises(RedditNotApproved):
                RedditSource(settings, session=FakeSession())

    def test_fetches_read_only_listing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp), approved=True)
            session = FakeSession()
            source = RedditSource(settings, session=session)
            posts = source.fetch_new(limit=10)
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0].post_id, "t3_abc123")
            self.assertTrue(posts[0].permalink.startswith("https://www.reddit.com/"))
            self.assertEqual(session.gets[0][1]["params"]["limit"], 10)
            self.assertEqual(len(session.posts), 1)

    def test_fetches_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp), approved=True)
            source = RedditSource(settings, session=FakeSession())
            rules = source.fetch_rules()
            self.assertIn("No self-promotion", rules)


if __name__ == "__main__":
    unittest.main()
