# Data Retention

Reddit's Data API guidance recommends routinely deleting stored user data and content within 48 hours. This project uses that as a hard upper bound.

| Data | Where | Retention |
|---|---|---|
| Raw post body | Process memory only | Discarded after the draft is produced |
| Draft answer | SQLite + email/outbox | 48 hours, or immediately after `mark-replied` |
| Short excerpt | SQLite + email/outbox | 48 hours |
| Permalink | SQLite + email/outbox | 48 hours |
| Post ID and status | SQLite | 48 hours |
| Last-seen cursor | SQLite state table | Metadata only; no post content |
| Logs | Console/file | Post ID and HTTP status only; no content |
| Local `.eml` files | `outbox/` | 48 hours, then deleted by `purge` |

## Deletion triggers

- `optics-qa mark-replied <post_id>` deletes the post and its draft immediately.
- `optics-qa purge` deletes expired rows and outbox files, then vacuums SQLite.
- Removed/deleted posts are skipped; their local rows expire on the next purge.

## No backups

The tool does not create backups. Do not add the database or outbox to cloud sync, version control, or backup software.

## Email caveat

Once an email is delivered, the email provider controls its retention. Delete the review email after posting. Do not archive review emails.
