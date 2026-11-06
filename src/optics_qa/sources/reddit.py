"""Read-only Reddit Data API adapter.

This module only implements GET requests.  It refuses to operate unless
REDDIT_API_APPROVED=true is set after written approval from Reddit.
"""

from __future__ import annotations

import html
import random
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from ..config import Settings
from ..models import RawPost


class RedditError(RuntimeError):
    pass


class RedditNotApproved(RedditError):
    pass


class RedditAuthError(RedditError):
    pass


class RedditRateLimitError(RedditError):
    pass


class RedditSource:
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    API_BASE = "https://oauth.reddit.com"

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        if not settings.reddit_api_approved:
            raise RedditNotApproved(
                "Reddit API access is not approved. Use manual mode or set "
                "REDDIT_API_APPROVED=true only after written approval."
            )
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise RedditAuthError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are required")
        if not settings.reddit_user_agent or "by /u/" not in settings.reddit_user_agent:
            raise RedditAuthError(
                "REDDIT_USER_AGENT must follow the format "
                "'<platform>:<app ID>:<version> (by /u/<username>)'"
            )
        self.settings = settings
        self.session = session or requests.Session()
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._token = ""
        self._token_expires_at = 0.0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        response = self.session.post(
            self.TOKEN_URL,
            auth=(self.settings.reddit_client_id, self.settings.reddit_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.settings.reddit_user_agent},
            timeout=30,
        )
        if response.status_code >= 400:
            raise RedditAuthError(f"token request failed: HTTP {response.status_code}")
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RedditAuthError("token response did not include access_token")
        self._token = str(token)
        self._token_expires_at = time.time() + float(payload.get("expires_in", 3600))
        return self._token

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self._get_token()
        url = f"{self.API_BASE}{path}"
        for attempt in range(3):
            response = self.session.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.settings.reddit_user_agent,
                },
                timeout=30,
            )
            if response.status_code == 429:
                if attempt == 2:
                    raise RedditRateLimitError("Reddit returned HTTP 429")
                time.sleep(random.uniform(0.5, 1.5))
                continue
            if response.status_code in {500, 502, 503, 504}:
                if attempt == 2:
                    raise RedditError(f"Reddit returned HTTP {response.status_code}")
                time.sleep(random.uniform(0.5, 1.5))
                continue
            if response.status_code == 401:
                raise RedditAuthError("Reddit rejected the access token")
            if response.status_code >= 400:
                raise RedditError(f"Reddit returned HTTP {response.status_code}")
            return response.json()
        raise RedditError("request failed after retries")

    def fetch_new(self, limit: int = 100, after: str | None = None) -> list[RawPost]:
        params: dict[str, Any] = {"limit": min(max(limit, 1), 100), "raw_json": 1}
        if after:
            params["after"] = after
        payload = self._get(f"/r/{self.settings.subreddit}/new", params=params)
        return self._parse_listing(payload)

    def fetch_rules(self) -> str:
        payload = self._get(f"/r/{self.settings.subreddit}/about/rules")
        rules = payload.get("rules", []) if isinstance(payload, dict) else []
        lines = []
        for rule in rules:
            short_name = str(rule.get("short_name", "")).strip()
            description = str(rule.get("description", "")).strip()
            if short_name or description:
                lines.append(f"- {short_name}: {description}".strip())
        return "\n".join(lines)

    def _parse_listing(self, payload: dict[str, Any]) -> list[RawPost]:
        children = payload.get("data", {}).get("children", [])
        posts: list[RawPost] = []
        for child in children:
            if child.get("kind") != "t3":
                continue
            data = child.get("data", {})
            selftext = html.unescape(str(data.get("selftext", "") or ""))
            title = html.unescape(str(data.get("title", "") or ""))
            removed = bool(data.get("removed_by_category")) or selftext in {"[removed]", "[deleted]"}
            permalink = str(data.get("permalink", "") or "")
            if permalink.startswith("/"):
                permalink = "https://www.reddit.com" + permalink
            posts.append(
                RawPost(
                    post_id=f"t3_{data.get('id', '')}",
                    subreddit=str(data.get("subreddit", self.settings.subreddit)),
                    title=title,
                    body=selftext,
                    permalink=permalink,
                    created_utc=float(data.get("created_utc", 0) or 0),
                    removed=removed,
                    over_18=bool(data.get("over_18", False)),
                    stickied=bool(data.get("stickied", False)),
                    author=str(data.get("author", "") or ""),
                )
            )
        return posts

    def fetch(self, limit: int = 100) -> list[RawPost]:
        return self.fetch_new(limit=limit)
