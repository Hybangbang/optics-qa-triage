# Operator Guide

## Manual mode

1. Open a public `r/Optics` post in your browser.
2. Copy the URL, title, and body.
3. Run `optics-qa draft --stdin`.
4. Paste the `URL / TITLE / BODY` block and finish input.
5. Read the draft, check every numeric/standard claim, and edit it.
6. Post the answer manually under your own account.
7. Run `optics-qa mark-replied <post_id>` or `optics-qa purge`.

Manual mode does not contact Reddit. The CLI only parses the text you paste.

## Review checklist

- Does the draft answer the actual question?
- Are wavelength, aperture, material, polarization, and environment assumptions stated?
- Is every tolerance/coating/standard claim verifiable?
- Did the draft avoid company names, prices, lead times, sales language, and DMs?
- Does the answer follow the current `r/Optics` rules, including self-promotion and AI-disclosure rules?
- Would you be comfortable defending every sentence as your own technical answer?

## Fixture mode

```powershell
optics-qa poll --source fixture --no-llm --no-email
optics-qa review
```

This is the end-to-end test path. It never calls Reddit or an LLM.

## Approved API mode

1. Confirm you have written approval from Reddit for this exact read-only use case.
2. Create the Reddit app only after approval. See [`reddit-app-setup.md`](reddit-app-setup.md).
3. Put the client ID, secret, and User-Agent in `.env`.
4. Set `REDDIT_API_APPROVED=true`.
5. Run once:

```powershell
optics-qa poll --source reddit --once
```

6. Review the email/outbox, edit, and post manually.
7. Schedule the same command every 10 minutes only after the one-shot run is clean.

## Windows Task Scheduler

Create a task that runs:

```text
python -m optics_qa.cli poll --source reddit --once
```

Start in the repository directory. Use "Run whether user is logged on or not" only if the machine is appropriately secured. Do not enable wake timers unless you understand the power impact.

## Purge

Run at least once per day:

```powershell
optics-qa purge
```

This deletes expired drafts, post metadata, and local `.eml` files, then vacuums SQLite.

## If Reddit rejects the application

Continue using manual mode. Do not create multiple accounts, resubmit the same use case under a different story, scrape the site, or use a third-party mirror to bypass the API. Those actions violate Reddit's policies and put the account at risk.
