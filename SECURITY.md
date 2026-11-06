# Security Policy

## Secrets

- Keep `REDDIT_CLIENT_SECRET`, `LLM_API_KEY`, and `SMTP_PASSWORD` in `.env` or the operating system's credential store.
- Never commit `.env`, tokens, client secrets, or real review emails.
- The public repository contains no credentials and no real Reddit content.

## Reddit access

- The adapter is read-only and uses the `read` scope.
- It refuses to run unless `REDDIT_API_APPROVED=true`.
- It contains no posting, voting, messaging, or moderation endpoints.
- The User-Agent must identify the app and a contact account.

## Reporting

Open a private security advisory at <https://github.com/Hybangbang/optics-qa-triage/security/advisories/new>. Do not open a public issue for a credential leak.

## Local hardening

- Run as a non-administrator.
- Keep the database and outbox directories private.
- Do not expose the CLI or database over a network.
- Delete review emails after posting.
