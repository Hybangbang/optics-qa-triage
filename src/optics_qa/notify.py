"""Local review delivery: SMTP email, .eml fallback, or console."""

from __future__ import annotations

import smtplib
import sys
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from .models import ReviewItem


def render_item(item: ReviewItem, index: int) -> str:
    flags = ", ".join(item.flags) if item.flags else "none"
    return (
        f"{index}. r/{item.subreddit} - {item.permalink}\n"
        f"Excerpt: {item.excerpt}\n"
        f"Confidence: {item.confidence}\n"
        f"Flags: {flags}\n\n"
        f"{item.draft_text}\n"
        + "-" * 72
        + "\n"
    )


def render_body(items: list[ReviewItem]) -> str:
    header = (
        "Read-only optics Q&A review queue.\n"
        "Review, edit, and post manually. Do not auto-post.\n"
        "Delete this message after posting; local drafts expire within 48 hours.\n\n"
    )
    return header + "\n".join(render_item(item, i) for i, item in enumerate(items, start=1))


def render_subject(items: list[ReviewItem]) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"[Optics Q&A] {len(items)} draft(s) - {day}"


class ConsoleNotifier:
    def send(self, items: list[ReviewItem]) -> list[str]:
        if items:
            print(render_body(items))
        return []


class OutboxNotifier:
    def __init__(self, outbox_dir: Path, email_to: str = "") -> None:
        self.outbox_dir = Path(outbox_dir)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.email_to = email_to

    def send(self, items: list[ReviewItem]) -> list[str]:
        if not items:
            return []
        message = EmailMessage()
        message["Subject"] = render_subject(items)
        message["From"] = "optics-qa-triage@localhost"
        message["To"] = self.email_to or "local-review@localhost"
        message.set_content(render_body(items))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = self.outbox_dir / f"optics-qa-{stamp}-{uuid.uuid4().hex[:8]}.eml"
        path.write_bytes(bytes(message))
        return [str(path)]


class SmtpNotifier:
    def __init__(self, host: str, port: int, user: str, password: str, email_to: str) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.email_to = email_to

    def send(self, items: list[ReviewItem]) -> list[str]:
        if not items:
            return []
        message = EmailMessage()
        message["Subject"] = render_subject(items)
        message["From"] = self.user or "optics-qa-triage@localhost"
        message["To"] = self.email_to
        message.set_content(render_body(items))
        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.ehlo()
            if self.port != 25:
                smtp.starttls()
                smtp.ehlo()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)
        return []


def cleanup_outbox(outbox_dir: Path, retention_hours: int) -> int:
    if not outbox_dir.is_dir():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - retention_hours * 3600
    deleted = 0
    for path in outbox_dir.glob("*.eml"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        except OSError:
            continue
    return deleted


def make_notifier(settings, console: bool = False):
    if console:
        return ConsoleNotifier()
    if settings.email_configured:
        return SmtpNotifier(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_password,
            settings.email_to,
        )
    return OutboxNotifier(settings.outbox_dir, settings.email_to)


def print_notice(paths: list[str]) -> None:
    for path in paths:
        print(f"Review email written to: {path}", file=sys.stderr)
