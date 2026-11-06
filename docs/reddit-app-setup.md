# Reddit App Setup (After Approval Only)

Do not create the app or set `REDDIT_API_APPROVED=true` before Reddit has approved the use case in writing.

## App fields

- **Name:** `Optics Q&A Triage` (do not use "Reddit" in the name).
- **Type:** `script` (personal use).
- **Description:** `Read-only assistant for r/Optics: finds new technical questions and prepares drafts for human review. No posting, voting, messaging, or moderation. 48-hour retention. No AI training.`
- **About URL:** `https://github.com/Hybangbang/optics-qa-triage`
- **Redirect URI:** `http://localhost:8080` (not used by application-only OAuth, but keep it local).

## Credentials

After creating the app, copy the client ID and secret into `.env`:

```text
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=windows:optics-qa-triage:v0.1.0 (by /u/<your username>)
REDDIT_API_APPROVED=false
```

Keep the approval flag `false` until the written approval is in hand.

## Smoke test

```powershell
optics-qa selftest
optics-qa poll --source reddit --once --dry-run --no-llm
```

Check that:

- The token request succeeds.
- Only `GET /r/Optics/new` and `GET /r/Optics/about/rules` are called.
- The response includes rate-limit headers.
- Logs contain no titles, bodies, or authors.
- `optics-qa purge` removes the test rows.

If the token request fails, verify the app type and credentials with Reddit's developer support. Do not try to bypass OAuth.
