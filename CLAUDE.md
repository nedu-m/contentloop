# ContentLoop — Agent Architecture

ContentLoop is a social media automation agent. It reads content topics from ClickUp,
pulls post metrics from X, generates drafts with Claude, routes them through a Slack
approval loop, and runs nightly evals to detect prompt drift.

## Agent Loop

```
ClickUp (topics) ──┐
                   ├──► drafter.py ──► poster.py ──► Slack approval
X API (metrics) ───┘                                      │
                                                          ▼
                                                    listener.py
                                                          │
                                                          ▼
                                                    SQLite (drafts)
                                                          │
                                                          ▼
                                                     evals.py ──► Slack alert (if drift)
```

## Agents

| File | What it does | Inputs | Outputs |
|---|---|---|---|
| `agents/pull_metrics.py` | Fetches last 28d of X posts with metrics | X API | `posts` table |
| `agents/sync_topics.py` | Fetches this week's ClickUp tasks | ClickUp API | `topics` table |
| `agents/drafter.py` | Generates drafts via Claude | `posts`, `topics`, `brand_voice.md` | `drafts` table |
| `agents/poster.py` | Posts pending drafts to Slack | `drafts` table | Slack messages, `drafts.slack_ts` |
| `agents/listener.py` | Listens for ✅/❌ reactions | Slack events | `drafts.status`, `topics.status` |
| `agents/evals.py` | Computes acceptance rate, flags drift | `drafts`, `eval_runs` | `eval_runs` table, Slack alert |

## Database

SQLite at `contentloop.db`. Initialize with: `python db/init_db.py`

Tables: `posts`, `topics`, `prompt_versions`, `drafts`, `eval_runs`

See `db/schema.sql` for full column definitions.

## Slash Commands

| Command | What it does |
|---|---|
| `/run-content-loop` | Runs the full pipeline: pull → sync → draft → post |
| `/eval-this-week` | Runs evals, interprets results, suggests prompt changes |

Run headless: `claude -p "/run-content-loop" --output-format text`

## Prompt Versioning

Prompts are stored in the `prompt_versions` table (seeded in `db/init_db.py`).
When iterating on the prompt:
1. Add a new row to `prompt_versions` with id `v2`, `v3`, etc.
2. Update `PROMPT_VERSION` constant in `agents/drafter.py`
3. Old drafts retain their version reference — evals track acceptance rate per version

## Adding a New Platform (e.g. LinkedIn)

1. Create `agents/pull_metrics_linkedin.py` — same interface as `pull_metrics.py`
2. Add a `platform` column to `posts` and `drafts` tables via a migration
3. Add platform-specific rules to `config/brand_voice.md`
4. Update the drafter to accept a `platform` argument
5. Update the poster to route to the correct destination

## Environment Variables

```
ANTHROPIC_API_KEY     Anthropic API key
CLICKUP_API_TOKEN     ClickUp personal API token
CLICKUP_LIST_ID       ID of the "Content Topics" list in ClickUp
SLACK_BOT_TOKEN       Slack bot OAuth token (xoxb-...)
SLACK_APP_TOKEN       Slack app-level token for Socket Mode (xapp-...)
SLACK_CHANNEL_ID      Channel ID where drafts are posted
X_BEARER_TOKEN        X API v2 Bearer token
X_USER_ID             X numeric user ID
```

## Common Failure Modes

- **0 drafts generated**: check `topics` table — are there rows for the current ISO week?
- **Slack events not firing**: confirm Socket Mode is enabled in the Slack app settings
- **X API 429**: rate limit hit. Wait and retry; posts are upserted so re-running is safe
- **Draft count mismatch**: Claude returned fewer items than topics. Check the raw output
  logged by `drafter.py`. Usually a formatting issue — the parser expects `N. text` lines.
- **Evals show 0 drafts**: only `approved`/`rejected` drafts are counted — `pending` are excluded
