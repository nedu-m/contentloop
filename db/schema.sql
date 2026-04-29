CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    impressions INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    pulled_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    week TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    system_prompt TEXT NOT NULL,
    few_shot_template TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topics(id),
    content TEXT NOT NULL,
    prompt_version TEXT NOT NULL REFERENCES prompt_versions(id),
    slack_ts TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prompt_version TEXT NOT NULL,
    total_drafts INTEGER NOT NULL,
    approved INTEGER NOT NULL,
    rejected INTEGER NOT NULL,
    acceptance_rate REAL NOT NULL,
    drift_flag BOOLEAN NOT NULL DEFAULT 0
);
