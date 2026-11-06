"""Shared data models.

The models deliberately keep author identity out of persisted records.  A
RawPost may carry an author for in-process diagnostics, but the store never
writes it to disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawPost:
    post_id: str
    subreddit: str
    title: str
    body: str
    permalink: str
    created_utc: float
    removed: bool = False
    over_18: bool = False
    stickied: bool = False
    author: str = ""


@dataclass(frozen=True)
class Classification:
    include: bool
    category: str
    keywords: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


@dataclass
class DraftResult:
    text: str
    confidence: str = "low"
    flags: list[str] = field(default_factory=list)
    model: str = ""


@dataclass(frozen=True)
class ReviewItem:
    post_id: str
    subreddit: str
    permalink: str
    excerpt: str
    draft_text: str
    confidence: str
    flags: tuple[str, ...]
    created_utc: str
