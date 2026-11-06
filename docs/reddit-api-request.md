# Reddit Data Access Request Pack

Form: <https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164>

Read this first:

- Submit as a personal, non-commercial project.
- Use a personal email, not a company email.
- Do not mention a company, product, pricing, lead generation, or customer data.
- Do not create the Reddit app until the request is approved.
- If Reddit rejects the request, keep using manual mode. Do not resubmit the same use case under a different story.

## Field-by-field answers

### Your email address

`<your personal email>`

### Which role best describes your reason for requesting API access?

`I’m a developer`

### What is your inquiry?

`I’m a developer and want to build a Reddit App that does not work in the Devvit ecosystem.`

### Reddit account name

`<your Reddit username>`

### What benefit/purpose will the bot/app have for Redditors?

> The app is a read-only assistant for r/Optics. It helps a human optics professional notice new technical questions and prepare accurate, well-structured draft answers faster. It does not post, comment, vote, message, or moderate. Every answer is reviewed, edited, and posted manually by the human, so Redditors get more thoughtful replies without automated spam, low-quality AI content, or unsolicited promotion. The app also surfaces the subreddit rules and a verification checklist before posting.

### Provide a detailed description of what the Bot/App will be doing on the Reddit platform.

> The app polls the public r/Optics/new listing and the public rules endpoint at most once every 10 minutes (at most 12 requests/hour, far below the 100 QPM limit) using OAuth with the read scope only. It filters posts for optics-related technical questions such as lens design, tolerances, coatings, metrology, and fabrication. For each candidate, it sends the public post text and current subreddit rules to an LLM API configured for no-training/zero-retention to produce a draft answer grounded in public optics references. The draft, permalink, and a short excerpt are delivered to the operator's local CLI/email review queue. The operator edits the draft and posts it manually under their own account. The app never calls posting, commenting, voting, messaging, or moderation endpoints. The full post body is not stored as a separate field; drafts and a 280-character-or-shorter excerpt are stored for no more than 48 hours and then hard-deleted. Only a post ID/status record is kept for deduplication and is deleted when the post is deleted or after 48 hours. No Reddit content is used to train or fine-tune any model, and no data is sold, licensed, or shared.

### What is missing from Devvit that prevents building on that platform?

> Devvit apps are installed by a subreddit's moderators and run inside Reddit's hosted runtime. This is a personal read-only review assistant for a non-moderator: it must monitor public r/Optics posts without being installed as a subreddit app, send candidate posts to an external LLM for drafting, and deliver the drafts to an external local review queue/email for manual editing and posting. Devvit cannot deliver data to an external human review queue, and it cannot operate as a private standalone read-only monitor without moderator installation. The app needs no write scope, custom post UI, or in-Reddit interaction, which are the parts Devvit is designed for.

### Provide a link to source code or platform that will access the API.

`https://github.com/Hybangbang/optics-qa-triage`

### What subreddits do you intend to use the bot/app in?

`r/Optics`

### If applicable, what username will you be operating this Bot/App under?

`N/A — read-only assistant; no bot account. The human operator posts manually under their own account.`

### Attachments

Attach [`reddit-api-attachment.md`](reddit-api-attachment.md). It is a standalone
one-page summary of the architecture, API usage, Devvit gap, and retention
limits.

## Before submitting

- [ ] The repository is public and contains no secrets.
- [ ] `optics-qa selftest` passes.
- [ ] The manual and fixture modes work.
- [ ] The application text contains no company name, product, price, or lead-generation language.
- [ ] The email is personal.
- [ ] You understand that approval is not guaranteed.
