"""Local fixture source used by tests and dry runs.  Never touches Reddit."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import RawPost


class FixtureSource:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def fetch(self, limit: int = 100) -> list[RawPost]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("fixture must be a JSON list")
        posts: list[RawPost] = []
        for index, item in enumerate(payload[:limit]):
            posts.append(
                RawPost(
                    post_id=str(item.get("id") or f"fixture-{index}"),
                    subreddit=str(item.get("subreddit", "Optics")),
                    title=str(item.get("title", "")),
                    body=str(item.get("selftext", item.get("body", ""))),
                    permalink=str(item.get("permalink", "")),
                    created_utc=float(item.get("created_utc", 0)),
                    removed=bool(item.get("removed", False)),
                    over_18=bool(item.get("over_18", False)),
                    stickied=bool(item.get("stickied", False)),
                )
            )
        return posts
