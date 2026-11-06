"""Command-line entry point for the read-only optics Q&A assistant."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import PROJECT_ROOT, Settings, load_settings
from .drafting import make_provider
from .filtering import classify_post, excerpt
from .models import RawPost, ReviewItem
from .notify import cleanup_outbox, make_notifier, print_notice, render_body
from .sources.fixture import FixtureSource
from .sources.manual import format_manual_template, parse_manual_input
from .sources.reddit import RedditNotApproved, RedditSource
from .store import Store, iso_utc, utc_now


FIXTURE_PATH = PROJECT_ROOT / "fixtures" / "posts.json"


def _read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def _print_draft(post: RawPost, draft_text: str) -> None:
    print(f"r/{post.subreddit} - {post.permalink or '(no URL)'}")
    print(f"Title: {post.title}")
    print()
    print(draft_text)


def cmd_draft(args: argparse.Namespace, settings: Settings) -> int:
    raw = _read_input(args.input)
    if not raw.strip():
        print("Paste a post on stdin or use --input. Template:\n", file=sys.stderr)
        print(format_manual_template(), file=sys.stderr)
        return 4
    try:
        post = parse_manual_input(raw)
    except ValueError as exc:
        print(f"Could not parse input: {exc}", file=sys.stderr)
        return 4

    classification = classify_post(post)
    if not classification.include:
        print(
            f"Note: this post was classified as {classification.category} "
            f"({', '.join(classification.reasons)}). Drafting anyway because manual mode was requested.",
            file=sys.stderr,
        )

    provider = make_provider(settings, no_llm=args.no_llm)
    draft = provider.draft(post)
    _print_draft(post, draft.text)

    if args.save:
        store = Store(settings.db_path, settings.retention_hours)
        store.save_draft(post, draft, excerpt(post.body))
        store.close()
        print(f"\nSaved to review queue: {settings.db_path}", file=sys.stderr)

    if args.email:
        item = ReviewItem(
            post_id=post.post_id,
            subreddit=post.subreddit,
            permalink=post.permalink,
            excerpt=excerpt(post.body),
            draft_text=draft.text,
            confidence=draft.confidence,
            flags=tuple(draft.flags),
            created_utc=iso_utc(utc_now()),
        )
        paths = make_notifier(settings).send([item])
        print_notice(paths)
    return 0


def cmd_poll(args: argparse.Namespace, settings: Settings) -> int:
    store = Store(settings.db_path, settings.retention_hours)
    purged = store.purge()
    if purged["drafts_deleted"] or purged["posts_deleted"]:
        print(f"Purged expired rows: {purged}", file=sys.stderr)

    if args.source == "fixture":
        source = FixtureSource(Path(args.fixture) if args.fixture else FIXTURE_PATH)
        cursor = 0.0
    else:
        try:
            source = RedditSource(settings)
        except RedditNotApproved as exc:
            print(str(exc), file=sys.stderr)
            store.close()
            return 2
        cursor = float(store.get_state("last_seen_utc", "0") or 0)

    try:
        posts = source.fetch(limit=args.limit)
    except Exception as exc:
        print(f"Source error: {exc}", file=sys.stderr)
        store.close()
        return 3

    rules_text = ""
    if args.source == "reddit":
        try:
            rules_text = source.fetch_rules()
        except Exception as exc:
            print(f"Could not fetch subreddit rules: {exc}", file=sys.stderr)

    provider = make_provider(settings, no_llm=args.no_llm)
    items: list[ReviewItem] = []
    new_count = 0
    skipped_count = 0
    latest = cursor

    for post in posts:
        if post.created_utc:
            latest = max(latest, post.created_utc)
        if args.source == "reddit" and cursor and post.created_utc <= cursor - 120:
            continue
        if store.seen(post.post_id):
            continue
        classification = classify_post(post)
        if not classification.include:
            store.record_skipped(post)
            skipped_count += 1
            continue
        try:
            draft = provider.draft(post, rules_text=rules_text)
        except Exception as exc:
            print(f"Draft failed for {post.post_id}: {exc}", file=sys.stderr)
            continue
        store.save_draft(post, draft, excerpt(post.body))
        new_count += 1
        items.append(
            ReviewItem(
                post_id=post.post_id,
                subreddit=post.subreddit,
                permalink=post.permalink,
                excerpt=excerpt(post.body),
                draft_text=draft.text,
                confidence=draft.confidence,
                flags=tuple(draft.flags),
                created_utc=iso_utc(utc_now()),
            )
        )

    if args.source == "reddit" and latest:
        store.set_state("last_seen_utc", str(latest))

    if args.dry_run:
        print(render_body(items) if items else "Dry run: no new review items.")
    elif items and not args.no_email:
        paths = make_notifier(settings).send(items)
        print_notice(paths)
    elif items:
        print(render_body(items))

    print(
        f"Poll complete: {len(posts)} fetched, {new_count} new draft(s), "
        f"{skipped_count} skipped, {store.stats()}",
        file=sys.stderr,
    )
    store.close()
    return 0


def cmd_review(args: argparse.Namespace, settings: Settings) -> int:
    store = Store(settings.db_path, settings.retention_hours)
    items = store.list_pending()
    store.close()
    if args.json:
        print(json.dumps([item.__dict__ for item in items], ensure_ascii=False, indent=2))
    elif items:
        print(render_body(items))
    else:
        print("Review queue is empty.")
    return 0


def cmd_mark_replied(args: argparse.Namespace, settings: Settings) -> int:
    store = Store(settings.db_path, settings.retention_hours)
    deleted = store.mark_replied(args.post_id)
    store.close()
    if deleted:
        print(f"Removed {args.post_id} from the local queue.")
        return 0
    print(f"Post not found: {args.post_id}", file=sys.stderr)
    return 1


def cmd_purge(args: argparse.Namespace, settings: Settings) -> int:
    store = Store(settings.db_path, settings.retention_hours)
    result = store.purge()
    store.close()
    emails = cleanup_outbox(settings.outbox_dir, settings.retention_hours)
    print(f"Purged drafts={result['drafts_deleted']} posts={result['posts_deleted']} emails={emails}")
    return 0


def _scan_for_write_endpoints(root: Path) -> list[str]:
    # Build these at runtime so this guardrail's own source is not a false positive.
    forbidden = tuple(
        "/api/" + name for name in ("comment", "vote", "submit", "compose", "del")
    )
    hits: list[str] = []
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                hits.append(f"{path}:{token}")
    return hits


def cmd_selftest(args: argparse.Namespace, settings: Settings) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    if sys.version_info < (3, 12):
        errors.append("Python 3.12 or newer is required")
    if settings.retention_hours > 48:
        errors.append("RETENTION_HOURS must be <= 48")
    if settings.reddit_api_approved:
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            errors.append("Reddit is marked approved but client credentials are missing")
        if "by /u/" not in settings.reddit_user_agent:
            errors.append("REDDIT_USER_AGENT must contain 'by /u/<username>'")
    else:
        warnings.append("Reddit API is disabled (expected until written approval). Manual mode only.")
    if not settings.llm_configured:
        warnings.append("LLM_API_KEY is missing; --no-llm template mode will be used.")
    if not settings.email_configured:
        warnings.append("SMTP/EMAIL_TO not configured; review messages will be written to outbox/.")
    write_hits = _scan_for_write_endpoints(PROJECT_ROOT / "src")
    if write_hits:
        errors.extend(f"write endpoint found: {hit}" for hit in write_hits)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Database: {settings.db_path}")
    print(f"Retention: {settings.retention_hours} hours")
    print(f"Reddit approved: {settings.reddit_api_approved}")
    print(f"LLM configured: {settings.llm_configured}")
    print(f"Email configured: {settings.email_configured}")
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Selftest passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optics-qa",
        description="Read-only, human-in-the-loop r/Optics Q&A assistant.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft", help="Draft a reply from manually pasted post text (no Reddit network).")
    draft.add_argument("--stdin", action="store_true", help="Read the post from stdin (default).")
    draft.add_argument("--input", help="Read the post from a local file.")
    draft.add_argument("--save", action="store_true", help="Save the draft to the local review queue.")
    draft.add_argument("--email", action="store_true", help="Send the draft to the review email/outbox.")
    draft.add_argument("--no-llm", action="store_true", help="Use the offline template instead of an LLM.")
    draft.set_defaults(func=cmd_draft)

    poll = sub.add_parser("poll", help="Fetch new posts from a fixture or the approved Reddit API.")
    poll.add_argument("--source", choices=("fixture", "reddit"), default="fixture")
    poll.add_argument("--fixture", help="Path to a fixture JSON file.")
    poll.add_argument("--limit", type=int, default=100)
    poll.add_argument("--once", action="store_true", help="Run one poll and exit (default).")
    poll.add_argument("--dry-run", action="store_true", help="Print drafts instead of sending email.")
    poll.add_argument("--no-email", action="store_true", help="Print drafts to the console.")
    poll.add_argument("--no-llm", action="store_true", help="Use the offline template instead of an LLM.")
    poll.set_defaults(func=cmd_poll)

    review = sub.add_parser("review", help="Show pending drafts.")
    review.add_argument("--json", action="store_true")
    review.set_defaults(func=cmd_review)

    mark = sub.add_parser("mark-replied", help="Delete a post and its draft after a manual reply.")
    mark.add_argument("post_id")
    mark.set_defaults(func=cmd_mark_replied)

    purge = sub.add_parser("purge", help="Hard-delete expired content and outbox emails.")
    purge.set_defaults(func=cmd_purge)

    selftest = sub.add_parser("selftest", help="Check config, retention, and write-endpoint guardrails.")
    selftest.set_defaults(func=cmd_selftest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    try:
        return int(args.func(args, settings))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
