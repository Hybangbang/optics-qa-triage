# Privacy Policy

This is a local, single-operator tool. It is not a public service and does not create user accounts.

## Data processed

- Public post ID, subreddit, permalink, title, and body supplied by the operator or fetched from `r/Optics` after approval.
- A short excerpt and a generated draft answer.
- Technical metadata such as timestamps, confidence, and rule flags.

## What is not collected

- Reddit passwords or refresh tokens.
- Author profile data, avatars, flair, or account IDs.
- Private messages, modmail, or non-public content.
- Payment, advertising, or analytics data.

## How data is used

Only to produce a draft for the operator to review and post manually. Drafts are not sold, licensed, shared, or used to train or fine-tune a model.

## Retention

- Full post bodies are not stored as a separate field; a review excerpt capped at 280 characters is stored with the draft.
- Drafts, excerpts, and permalinks are hard-deleted within 48 hours.
- Post IDs and status metadata are hard-deleted within 48 hours.
- Local outbox emails are deleted by `optics-qa purge` after the retention window.
- Email providers may retain delivered messages according to their own policies; delete the review email after posting.

## Deletion

Run `optics-qa mark-replied <post_id>` after posting to delete that item immediately, or `optics-qa purge` to remove all expired content. Removed or deleted Reddit posts are skipped and their local records are deleted on the next purge.

## Third parties

When enabled, the tool sends the public post text to the configured LLM API. Use a provider with no-training/zero-retention terms. The default configuration requests `store=false`; verify the provider's current policy before use.

## Contact

Open an issue at <https://github.com/Hybangbang/optics-qa-triage/issues> for privacy questions. Do not include personal data or Reddit content in an issue.
