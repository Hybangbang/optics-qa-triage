"""Manual paste parser.

Manual mode never fetches reddit.com.  The operator copies the public post
text from their browser and pastes it into stdin or a local file.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone

from ..models import RawPost


_COMMENT_ID = re.compile(r"/comments/([a-z0-9]+)", re.IGNORECASE)


def _manual_id(title: str, body: str) -> str:
    digest = hashlib.sha1(f"{title}\n{body}".encode("utf-8")).hexdigest()[:12]
    return f"manual-{digest}"


def parse_manual_input(text: str) -> RawPost:
    """Parse either a JSON object or a simple URL/TITLE/BODY block."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("empty input; paste a post or provide a JSON object")

    if cleaned.startswith("{"):
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc}") from exc
        title = str(payload.get("title", "")).strip()
        body = str(payload.get("body", payload.get("selftext", ""))).strip()
        permalink = str(payload.get("url", payload.get("permalink", ""))).strip()
        subreddit = str(payload.get("subreddit", "Optics")).strip() or "Optics"
        created = payload.get("created_utc")
        created_utc = float(created) if created is not None else time.time()
    else:
        title = ""
        body_lines: list[str] = []
        permalink = ""
        subreddit = "Optics"
        in_body = False
        for raw_line in cleaned.splitlines():
            line = raw_line.rstrip()
            upper = line.upper()
            if upper.startswith("URL:"):
                permalink = line.split(":", 1)[1].strip()
                continue
            if upper.startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
                continue
            if upper.startswith("SUBREDDIT:"):
                subreddit = line.split(":", 1)[1].strip() or "Optics"
                continue
            if upper.startswith("BODY:"):
                in_body = True
                remainder = line.split(":", 1)[1]
                if remainder.strip():
                    body_lines.append(remainder.lstrip())
                continue
            if in_body or not title:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()
        created_utc = time.time()

    if not title and not body:
        raise ValueError("input must contain a title or body")
    if not title:
        title = body.splitlines()[0][:120]

    match = _COMMENT_ID.search(permalink)
    post_id = f"t3_{match.group(1).lower()}" if match else _manual_id(title, body)
    if permalink and permalink.startswith("/"):
        permalink = "https://www.reddit.com" + permalink

    return RawPost(
        post_id=post_id,
        subreddit=subreddit,
        title=title,
        body=body,
        permalink=permalink,
        created_utc=created_utc,
    )


def format_manual_template() -> str:
    return (
        "URL: https://www.reddit.com/r/Optics/comments/...\n"
        "TITLE: ...\n"
        "BODY:\n"
        "...\n"
    )


def local_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
