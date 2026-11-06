from __future__ import annotations

from pathlib import Path

from optics_qa.config import Settings
from optics_qa.models import RawPost


def make_settings(tmp_path: Path, *, approved: bool = False) -> Settings:
    return Settings(
        db_path=tmp_path / "queue.sqlite3",
        outbox_dir=tmp_path / "outbox",
        retention_hours=48,
        subreddit="Optics",
        reddit_client_id="client-id",
        reddit_client_secret="client-secret",
        reddit_user_agent="windows:optics-qa-triage:v0.1.0 (by /u/tester)",
        reddit_api_approved=approved,
        llm_base_url="https://api.example.test/v1",
        llm_api_key="",
        llm_model="test-model",
        llm_store=False,
        llm_timeout_seconds=5,
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_password="",
        email_to="",
    )


def make_post(
    post_id: str = "t3_example1",
    *,
    title: str = "How do I specify surface figure for a 25 mm window?",
    body: str = "I need a lambda/10 window with 60-40 scratch-dig. What should I put on the drawing?",
    removed: bool = False,
    over_18: bool = False,
    stickied: bool = False,
) -> RawPost:
    return RawPost(
        post_id=post_id,
        subreddit="Optics",
        title=title,
        body=body,
        permalink=f"https://www.reddit.com/r/Optics/comments/{post_id.replace('t3_', '')}/example/",
        created_utc=1_700_000_000.0,
        removed=removed,
        over_18=over_18,
        stickied=stickied,
        author="synthetic-user",
    )
