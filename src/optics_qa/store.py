"""SQLite review queue with hard retention limits."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import DraftResult, RawPost, ReviewItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Store:
    def __init__(self, path: Path, retention_hours: int = 48) -> None:
        self.path = Path(path)
        self.retention_hours = retention_hours
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS posts (
                post_id TEXT PRIMARY KEY,
                subreddit TEXT NOT NULL,
                status TEXT NOT NULL,
                first_seen_utc TEXT NOT NULL,
                last_seen_utc TEXT NOT NULL,
                expires_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                permalink TEXT NOT NULL,
                excerpt TEXT NOT NULL,
                draft_text TEXT NOT NULL,
                confidence TEXT NOT NULL,
                flags_json TEXT NOT NULL,
                model TEXT NOT NULL,
                created_utc TEXT NOT NULL,
                expires_at_utc TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_posts_expires ON posts(expires_at_utc);
            CREATE INDEX IF NOT EXISTS idx_drafts_expires ON drafts(expires_at_utc);
            CREATE INDEX IF NOT EXISTS idx_drafts_post ON drafts(post_id);
            """
        )
        self.conn.commit()

    def _expiry(self) -> str:
        return iso_utc(utc_now() + timedelta(hours=self.retention_hours))

    def seen(self, post_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM posts WHERE post_id = ?", (post_id,)).fetchone()
        return row is not None

    def record_skipped(self, post: RawPost) -> None:
        now = iso_utc(utc_now())
        expiry = self._expiry()
        self.conn.execute(
            """
            INSERT INTO posts(post_id, subreddit, status, first_seen_utc, last_seen_utc, expires_at_utc)
            VALUES(?, ?, 'skipped', ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET last_seen_utc = excluded.last_seen_utc
            """,
            (post.post_id, post.subreddit, now, now, expiry),
        )
        self.conn.commit()

    def save_draft(self, post: RawPost, draft: DraftResult, text_excerpt: str) -> str:
        now = iso_utc(utc_now())
        expiry = self._expiry()
        draft_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO posts(post_id, subreddit, status, first_seen_utc, last_seen_utc, expires_at_utc)
            VALUES(?, ?, 'new', ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                last_seen_utc = excluded.last_seen_utc,
                expires_at_utc = excluded.expires_at_utc
            """,
            (post.post_id, post.subreddit, now, now, expiry),
        )
        self.conn.execute(
            """
            INSERT INTO drafts(draft_id, post_id, permalink, excerpt, draft_text, confidence,
                               flags_json, model, created_utc, expires_at_utc)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                post.post_id,
                post.permalink,
                text_excerpt,
                draft.text,
                draft.confidence,
                json.dumps(list(draft.flags), ensure_ascii=False),
                draft.model,
                now,
                expiry,
            ),
        )
        self.conn.commit()
        return draft_id

    def list_pending(self) -> list[ReviewItem]:
        rows = self.conn.execute(
            """
            SELECT p.post_id, p.subreddit, d.permalink, d.excerpt, d.draft_text,
                   d.confidence, d.flags_json, d.created_utc
            FROM posts p
            JOIN drafts d ON d.post_id = p.post_id
            WHERE p.status = 'new'
            ORDER BY d.created_utc DESC
            """
        ).fetchall()
        return [
            ReviewItem(
                post_id=row["post_id"],
                subreddit=row["subreddit"],
                permalink=row["permalink"],
                excerpt=row["excerpt"],
                draft_text=row["draft_text"],
                confidence=row["confidence"],
                flags=tuple(json.loads(row["flags_json"])),
                created_utc=row["created_utc"],
            )
            for row in rows
        ]

    def mark_replied(self, post_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM posts WHERE post_id = ?", (post_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def purge(self, now: datetime | None = None) -> dict[str, int]:
        cutoff = iso_utc(now or utc_now())
        drafts = self.conn.execute("DELETE FROM drafts WHERE expires_at_utc <= ?", (cutoff,)).rowcount
        posts = self.conn.execute("DELETE FROM posts WHERE expires_at_utc <= ?", (cutoff,)).rowcount
        self.conn.commit()
        self.conn.execute("VACUUM")
        return {"drafts_deleted": max(drafts, 0), "posts_deleted": max(posts, 0)}

    def set_state(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def get_state(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def stats(self) -> dict[str, int]:
        pending = self.conn.execute("SELECT COUNT(*) AS n FROM posts WHERE status = 'new'").fetchone()["n"]
        skipped = self.conn.execute("SELECT COUNT(*) AS n FROM posts WHERE status = 'skipped'").fetchone()["n"]
        drafts = self.conn.execute("SELECT COUNT(*) AS n FROM drafts").fetchone()["n"]
        return {"pending": pending, "skipped": skipped, "drafts": drafts}

    def close(self) -> None:
        self.conn.close()
