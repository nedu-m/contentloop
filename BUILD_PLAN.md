# ContentLoop — Build Plan

A social media automation agent built with Claude Code, Slack, and ClickUp.
Timeline: 48 hours. Stack: Python, SQLite, Anthropic SDK, Slack Bolt, GitHub Actions.

---

## Phase 0 — Environment & Credentials (2 hours)

Goal: prove every external integration works before writing any agent logic.

### 0.1 Repo setup
- [ ] Create GitHub repo: `contentloop`
- [ ] Init Python project: `pyproject.toml` or `requirements.txt`
- [ ] Create `.env.example` with all required keys (never commit `.env`)
- [ ] Add `.gitignore` (`.env`, `*.db`, `__pycache__`, `.claude/`)
- [ ] Create directory structure (see below)

### 0.2 ClickUp
- [ ] Create a ClickUp workspace (free tier)
- [ ] Create a List called "Content Topics" with fields: Topic, Week, Status
- [ ] Add 3–5 sample tasks for this week
- [ ] Generate a ClickUp API token → `CLICKUP_API_TOKEN` in `.env`
- [ ] Note the List ID → `CLICKUP_LIST_ID` in `.env`
- [ ] Spike: write `scripts/test_clickup.py` — fetch tasks, print them, confirm shape

### 0.3 Slack
- [ ] Create a Slack app at api.slack.com/apps
- [ ] Enable Socket Mode (for local dev without a public URL)
- [ ] Add Bot Token Scopes: `chat:write`, `reactions:read`, `channels:history`
- [ ] Subscribe to events: `reaction_added`, `reaction_removed`
- [ ] Install app to workspace → `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` in `.env`
- [ ] Note the channel ID for drafts → `SLACK_CHANNEL_ID` in `.env`
- [ ] Spike: write `scripts/test_slack.py` — post a message, react to it, confirm event fires

### 0.4 X (Twitter) API
- [ ] Apply for X API v2 Basic access (free tier, 1500 reads/month)
- [ ] Create an app → `X_BEARER_TOKEN`, `X_USER_ID` in `.env`
- [ ] Spike: write `scripts/test_x.py` — pull your last 10 posts with metrics, print them
- [ ] Confirm fields available: `public_metrics` (impressions, likes, retweets, replies)

### 0.5 Anthropic
- [ ] Get API key → `ANTHROPIC_API_KEY` in `.env`
- [ ] Spike: write `scripts/test_claude.py` — send a simple prompt, confirm response

---

## Phase 1 — Database Schema (1 hour)

Goal: define all tables before writing any logic. Schema changes mid-build are expensive.

### Tables

**`posts`** — historical X posts with metrics
```
id TEXT PRIMARY KEY        -- X post ID
content TEXT
posted_at TIMESTAMP
impressions INTEGER
likes INTEGER
retweets INTEGER
replies INTEGER
pulled_at TIMESTAMP
```

**`topics`** — this week's content topics from ClickUp
```
id TEXT PRIMARY KEY        -- ClickUp task ID
title TEXT
description TEXT
week TEXT                  -- ISO week e.g. "2026-W18"
status TEXT                -- pending | drafted | approved | rejected
```

**`drafts`** — generated content drafts
```
id INTEGER PRIMARY KEY AUTOINCREMENT
topic_id TEXT              -- FK → topics.id
content TEXT
prompt_version TEXT        -- e.g. "v1", "v2" — tracks which prompt generated this
slack_ts TEXT              -- Slack message timestamp (used to listen for reactions)
status TEXT                -- pending | approved | rejected
rejection_reason TEXT
created_at TIMESTAMP
```

**`prompt_versions`** — prompt templates used for drafting
```
id TEXT PRIMARY KEY        -- e.g. "v1"
system_prompt TEXT
few_shot_template TEXT
created_at TIMESTAMP
```

**`eval_runs`** — nightly evals results
```
id INTEGER PRIMARY KEY AUTOINCREMENT
run_at TIMESTAMP
prompt_version TEXT
total_drafts INTEGER
approved INTEGER
rejected INTEGER
acceptance_rate REAL
drift_flag BOOLEAN         -- true if acceptance_rate dropped >10% vs prior run
```

### 1.1 Implementation
- [ ] Create `db/schema.sql` with all CREATE TABLE statements
- [ ] Create `db/init_db.py` — runs schema.sql, idempotent (`CREATE TABLE IF NOT EXISTS`)
- [ ] Run `python db/init_db.py` — verify `contentloop.db` is created

---

## Phase 2 — Data Ingestion (2 hours)

Goal: populate `posts` from X and `topics` from ClickUp.

### 2.1 X metrics pull (`agents/pull_metrics.py`)
- [ ] Use X API v2 `/users/:id/tweets` with `tweet.fields=public_metrics,created_at`
- [ ] Pull last 28 days (filter by `start_time`)
- [ ] Upsert into `posts` table (INSERT OR REPLACE)
- [ ] Log how many posts pulled
- [ ] Test: run manually, verify rows in SQLite

### 2.2 ClickUp topic sync (`agents/sync_topics.py`)
- [ ] Fetch all tasks from the Content Topics list
- [ ] Filter to current ISO week
- [ ] Upsert into `topics` table
- [ ] Test: run manually, verify rows in SQLite

---

## Phase 3 — Drafting Agent (3 hours)

Goal: given this week's topics + top performers, generate 7 drafts via Claude.

### 3.1 Brand voice doc
- [ ] Create `config/brand_voice.md` — 1 page: tone, banned phrases, format rules, example posts
- [ ] This is a static file committed to the repo

### 3.2 Prompt construction (`agents/drafter.py`)
- [ ] Query `posts` table: ORDER BY impressions DESC LIMIT 5 (top performers, last 28d)
- [ ] Query `topics` table: WHERE week = current_week AND status = 'pending'
- [ ] Load `config/brand_voice.md`
- [ ] Load current prompt template from `prompt_versions` table (latest version)
- [ ] Construct messages array:
  - System: brand voice + drafting instructions
  - User: top 5 performers as few-shot examples + this week's topics
- [ ] Call `anthropic.messages.create()` — `claude-sonnet-4-6`, streaming off
- [ ] Parse response: expect 7 numbered drafts
- [ ] Insert each draft into `drafts` table with `status = 'pending'`

### 3.3 Prompt versioning
- [ ] Seed `prompt_versions` table with `v1` prompt on first run
- [ ] Always reference `prompt_version` when inserting drafts

### 3.4 Test
- [ ] Run `python agents/drafter.py` with real data
- [ ] Verify 7 rows in `drafts` table
- [ ] Read the drafts — do they sound on-brand?

---

## Phase 4 — Slack Approval Loop (3 hours)

Goal: post drafts to Slack, listen for ✅/❌ reactions, update DB.

### 4.1 Post drafts to Slack (`agents/poster.py`)
- [ ] Query `drafts` WHERE status = 'pending' AND slack_ts IS NULL
- [ ] For each draft, post to `SLACK_CHANNEL_ID` as a threaded message:
  ```
  *Draft #N — Topic: {topic title}*
  {draft content}
  React ✅ to approve or ❌ to reject (reply with reason in thread)
  ```
- [ ] Store returned `ts` (Slack message timestamp) in `drafts.slack_ts`

### 4.2 Reaction listener (`agents/listener.py`)
- [ ] Use Slack Bolt with Socket Mode
- [ ] Listen for `reaction_added` events
- [ ] On ✅ (`+1` or `white_check_mark`):
  - Find draft by `slack_ts`
  - Update `drafts.status = 'approved'`
  - Update `topics.status = 'approved'`
- [ ] On ❌ (`x` or `negative_squared_cross_mark`):
  - Find draft by `slack_ts`
  - Fetch thread replies to get rejection reason (first reply after the bot message)
  - Update `drafts.status = 'rejected'`, `drafts.rejection_reason = <reply text>`
  - Update `topics.status = 'rejected'`

### 4.3 Test
- [ ] Run `python agents/listener.py` in one terminal
- [ ] Run `python agents/poster.py` in another
- [ ] React ✅ to one draft, ❌ to another (with a thread reply reason)
- [ ] Verify DB rows updated correctly

---

## Phase 5 — Evals Harness (2 hours)

Goal: nightly subagent that computes acceptance rate per prompt version, flags drift.

### 5.1 Evals agent (`agents/evals.py`)
- [ ] Query `drafts` table grouped by `prompt_version`:
  ```sql
  SELECT prompt_version,
         COUNT(*) as total,
         SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved,
         SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected
  FROM drafts
  WHERE status != 'pending'
  GROUP BY prompt_version
  ```
- [ ] Compute `acceptance_rate = approved / total`
- [ ] Compare to last run in `eval_runs`: if rate dropped >10 percentage points → `drift_flag = True`
- [ ] Insert row into `eval_runs`
- [ ] Print report:
  ```
  === Evals Report — 2026-04-29 ===
  Prompt v1: 5/7 approved (71%) — OK
  Prompt v2: 2/7 approved (28%) — DRIFT DETECTED ⚠️
  ```
- [ ] If drift detected, post a Slack alert to the channel

### 5.2 Test
- [ ] Seed some approved/rejected drafts manually
- [ ] Run `python agents/evals.py`
- [ ] Verify `eval_runs` row inserted, output is correct

---

## Phase 6 — Claude Code Orchestration (2 hours)

Goal: wire everything together via headless `claude -p` calls and custom slash commands.

### 6.1 Custom slash commands
Create these in `.claude/commands/`:

**`/run-content-loop`** (`.claude/commands/run-content-loop.md`)
```
Run the full ContentLoop pipeline:
1. python agents/pull_metrics.py
2. python agents/sync_topics.py
3. python agents/drafter.py
4. python agents/poster.py
Report how many topics processed, drafts created, and drafts posted to Slack.
```

**`/eval-this-week`** (`.claude/commands/eval-this-week.md`)
```
Run the evals harness:
1. python agents/evals.py
Report acceptance rate per prompt version. Flag any drift. Suggest prompt changes if rejection rate > 50%.
```

### 6.2 GitHub Actions cron jobs (`.github/workflows/`)

**`content-loop.yml`** — runs weekly (e.g. Monday 9am UTC)
```yaml
- cron: '0 9 * * 1'
- run: claude -p "/run-content-loop" --output-format text
```

**`evals.yml`** — runs nightly
```yaml
- cron: '0 2 * * *'
- run: claude -p "/eval-this-week" --output-format text
```

- [ ] Add all secrets to GitHub repo Settings → Secrets
- [ ] Test `claude -p "/run-content-loop"` locally first
- [ ] Push and verify Actions trigger

---

## Phase 7 — Documentation (1 hour)

### 7.1 `CLAUDE.md`
Document the agent loop so another Claude Code instance can extend it:
- What each agent does and its inputs/outputs
- How to add a new prompt version
- How to add a new platform (LinkedIn pattern)
- Environment variables reference
- Common failure modes

### 7.2 `README.md`
- What ContentLoop is (1 paragraph)
- Architecture diagram (ASCII or Mermaid)
- Setup instructions (clone → `.env` → `init_db` → run)
- How the approval loop works
- What's next (LinkedIn, auto-publish after N approvals)

### 7.3 `WHY.md`
- Why human-in-loop for v1 (not auto-publish)
- Where Claude Code earned its spot vs. just calling the API
- Design decisions: SQLite over Postgres, Slack as UI, GitHub Actions as scheduler

---

## Directory Structure

```
contentloop/
├── .claude/
│   └── commands/
│       ├── run-content-loop.md
│       └── eval-this-week.md
├── .github/
│   └── workflows/
│       ├── content-loop.yml
│       └── evals.yml
├── agents/
│   ├── pull_metrics.py      # Phase 2.1
│   ├── sync_topics.py       # Phase 2.2
│   ├── drafter.py           # Phase 3
│   ├── poster.py            # Phase 4.1
│   ├── listener.py          # Phase 4.2
│   └── evals.py             # Phase 5
├── config/
│   └── brand_voice.md
├── db/
│   ├── schema.sql
│   └── init_db.py
├── scripts/
│   ├── test_clickup.py
│   ├── test_slack.py
│   ├── test_x.py
│   └── test_claude.py
├── .env.example
├── .gitignore
├── requirements.txt
├── CLAUDE.md
├── README.md
└── WHY.md
```

---

## Build Order (Critical Path)

```
Phase 0 (env/credentials)
    ↓
Phase 1 (schema)
    ↓
Phase 2 (data ingestion) ← unblocks Phase 3
    ↓
Phase 3 (drafting agent) ← unblocks Phase 4
    ↓
Phase 4 (Slack approval loop)
    ↓
Phase 5 (evals) ← can start after Phase 3 with seeded data
    ↓
Phase 6 (orchestration)
    ↓
Phase 7 (docs + Loom)
```

Phases 5 and 6 can partially overlap once Phase 3 is working.

---

## Environment Variables Reference

```
ANTHROPIC_API_KEY=
CLICKUP_API_TOKEN=
CLICKUP_LIST_ID=
SLACK_BOT_TOKEN=
SLACK_APP_TOKEN=
SLACK_CHANNEL_ID=
X_BEARER_TOKEN=
X_USER_ID=
```

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| X API rate limits (1500 reads/month) | High | Cache in SQLite; never re-pull what you have |
| Slack Socket Mode drops in CI | Medium | GitHub Actions uses HTTP mode; swap `SLACK_APP_TOKEN` for a webhook URL |
| ClickUp free tier API limits | Low | 100 req/min — well within bounds for this use case |
| Claude response not parsing to 7 drafts | Medium | Add retry logic; validate count before inserting |
| GitHub Actions can't run `claude -p` | Medium | Install Claude Code CLI in the workflow; test early |
