# Reddit Data API Request: Optics Q&A Triage

## Project summary

Optics Q&A Triage is a personal, non-commercial, single-operator tool that helps one human optics professional find new technical questions in `r/Optics` and prepare accurate draft answers. A human verifies, edits, and posts every reply manually. The tool does not post, comment, vote, message, moderate, or create a public service.

Source code: <https://github.com/Hybangbang/optics-qa-triage>

## Data flow

```text
r/Optics/new (OAuth, read only)
        |
        v
Deterministic question filter
        |
        v
External LLM API (no training, zero retention)
        |
        v
Local SQLite queue or operator-only email
        |
        v
Human reviews, edits, and posts manually
```

The tool has no Reddit write path. Any post that is not an optics-related technical question, including sourcing/RFQ and general discussion posts, is skipped.

## API usage

- Authentication: OAuth application-only token.
- Scope: `read` only.
- Endpoint: `GET https://oauth.reddit.com/r/Optics/new`.
- Optional endpoint: `GET https://oauth.reddit.com/r/Optics/about/rules`.
- Frequency: at most once every 10 minutes, about 6 requests per hour.
- Requested fields: post ID, subreddit, title, public selftext, permalink, timestamps, and moderation flags necessary to skip removed/stickied posts.
- No private messages, modmail, account profile data, or non-public content.
- No posting, commenting, voting, messaging, moderation, or advertising endpoints.

## Why Devvit is not suitable

This is a private, standalone monitor operated by a non-moderator. It must run outside Reddit's hosted Devvit runtime, call an external LLM for drafting, and deliver results to an operator-controlled local review queue and email. It does not need an in-Reddit UI, installation by moderators, or any write scope.

## Data minimization and retention

- Raw post content is processed in memory and is not written to SQLite.
- SQLite contains no author name and no full post body.
- Drafts, short excerpts, permalinks, and post IDs are hard-deleted within 48 hours.
- `mark-replied` deletes an item immediately after the human posts.
- `purge` deletes expired rows and local review email files.
- Reddit content is never used to train or fine-tune a model.
- Data is not sold, licensed, shared, or used for advertising or analytics.
- The configured LLM provider must offer no-training and zero-retention terms.

## Human control

Every draft includes assumptions, public-source citations or a "verify" marker, a verification checklist, confidence, and rule flags. The human must check current `r/Optics` rules and every technical claim before posting. No answer is published automatically.
