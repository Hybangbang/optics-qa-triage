# Optics Q&A Triage

A read-only, human-in-the-loop assistant for finding and drafting answers to technical questions in `r/Optics`.

**Status:** Reddit API access has not been requested or approved. The default workflow is manual paste + local drafting. The Reddit adapter is disabled unless `REDDIT_API_APPROVED=true`, which must only be set after written approval from Reddit.

## What it does

1. Accepts a public post you copied from your browser, or polls `r/Optics/new` after approval.
2. Filters obvious non-questions and sourcing/RFQ posts.
3. Produces a structured draft with assumptions, sources, a verification checklist, confidence, and rule flags.
4. Delivers the draft to a local CLI or email review queue.
5. You edit and post the answer manually.
6. Drafts and excerpts are hard-deleted within 48 hours.

It does **not** post, comment, vote, message, moderate, or train a model on Reddit content.

## Why this is read-only

Reddit requires approval before any API access. Business use, research use, and automated posting have separate rules and approval paths. This project is deliberately scoped to a personal, non-commercial, read-only review workflow. See [`docs/reddit-api-request.md`](docs/reddit-api-request.md) for the application text and [`docs/architecture.md`](docs/architecture.md) for the trust boundaries.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
optics-qa selftest
```

### Manual mode (works without Reddit access)

Open the post in your browser, copy its URL, title, and body, then run:

```powershell
optics-qa draft --stdin
```

Paste this shape into the terminal:

```text
URL: https://www.reddit.com/r/Optics/comments/...
TITLE: ...
BODY:
...
```

Press `Ctrl+Z` then Enter on Windows, or `Ctrl+D` on Linux/macOS. With no LLM key, add `--no-llm` to get an offline template.

### Fixture mode (no network)

```powershell
optics-qa poll --source fixture --no-llm --no-email
optics-qa review
```

### After written approval

Set the Reddit credentials and the approval flag in `.env`, then:

```powershell
optics-qa poll --source reddit --once
```

Do not set `REDDIT_API_APPROVED=true` before you have written approval. The adapter will refuse to run without it.

## Commands

```text
optics-qa draft --stdin [--no-llm] [--save] [--email]
optics-qa poll --source fixture|reddit --once [--dry-run] [--no-email] [--no-llm]
optics-qa review [--json]
optics-qa mark-replied <post_id>
optics-qa purge
optics-qa selftest
```

## Data handling

- Full post bodies are processed in memory and are not stored as a separate SQLite field.
- A review excerpt capped at 280 characters is stored with the draft.
- Drafts, short excerpts, and permalinks are retained for at most 48 hours.
- Author names and profile URLs are not persisted.
- Logs contain post IDs and HTTP status codes, not titles, bodies, or authors.
- Email/outbox messages should be deleted after posting; `optics-qa purge` cleans the local outbox.

See [`PRIVACY.md`](PRIVACY.md) and [`DATA_RETENTION.md`](DATA_RETENTION.md).

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Tests use local fixtures only. CI never calls Reddit or an LLM.

## Scope and non-goals

- One subreddit: `r/Optics`.
- One operator, running locally.
- No public service, no multi-user accounts, no analytics product.
- No automated posting, voting, messaging, or moderation.
- No company branding, pricing, lead-time promises, or lead capture in drafts.

## License

MIT. See [`LICENSE`](LICENSE).
