Run the full ContentLoop pipeline in order:

1. Run `python agents/pull_metrics.py` — pull last 28 days of X post metrics into SQLite
2. Run `python agents/sync_topics.py` — sync this week's ClickUp topics into SQLite
3. Run `python agents/drafter.py` — generate drafts for each pending topic using Claude
4. Run `python agents/poster.py` — post all unposted pending drafts to Slack for approval

After each step, report what happened (how many posts pulled, topics synced, drafts created, drafts posted).
If any step fails, stop and report the error clearly — do not continue to the next step.
At the end, print a summary:
- Topics this week: N
- Drafts generated: N
- Drafts posted to Slack: N
- Listener status: remind the user to run `python agents/listener.py` if it is not already running
