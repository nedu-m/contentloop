"""Seed the DB with demo data for Streamlit Cloud deployment."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "contentloop.db"

TOPICS = [
    ("t1", "How I built a content automation agent in 48 hours with Claude Code"),
    ("t2", "Why I added a human approval loop instead of auto-publishing AI drafts"),
    ("t3", "The one thing most AI agent demos skip: evals"),
    ("t4", "SQLite is underrated for solo AI projects — here's why I keep reaching for it"),
    ("t5", "What building ContentLoop taught me about prompt drift"),
    ("t6", "Claude Code as an orchestrator, not just a code assistant"),
    ("t7", "The approval loop is the product — why human-in-loop isn't a limitation"),
]

DRAFTS = [
    ("t1", "Built a full social media automation agent in 48 hours using Claude Code. ClickUp topics in → Claude drafts → Slack approval loop → nightly evals. The whole thing runs headless with custom slash commands. Here's how it works.", "approved"),
    ("t2", "Auto-publish from an LLM is a liability, not a feature. Every ✅ and ❌ in the approval loop is labeled training data for the evals harness. The human judgment gets captured, not bypassed.", "approved"),
    ("t3", "Most AI agent demos show the happy path. None of them show what happens when the prompt drifts over 4 weeks and the acceptance rate quietly drops from 80% to 30%. Build the evals harness first.", "rejected"),
    ("t4", "SQLite ships with Python, fits in a file, and handles everything a solo AI project needs. I keep reaching for Postgres out of habit. I keep switching back to SQLite after 10 minutes of setup pain.", "approved"),
    ("t5", "Ran ContentLoop for 2 weeks. Prompt v1 hit 71% acceptance. Rejection reasons clustered around one thing: too generic, not specific enough. That's the signal the evals harness exists to surface.", "approved"),
    ("t6", "Claude Code isn't just autocomplete for agents. Used as an orchestrator, it reads context, reasons about what happened, and suggests what to change — without me writing that logic explicitly.", "approved"),
    ("t7", "The approval loop is the product. Auto-publish is a feature you unlock after the acceptance rate is consistently above 90% for 4 weeks. Until then, the human checkpoint is the point.", "rejected"),
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    week = datetime.now(timezone.utc).strftime("%G-W%V")
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""CREATE TABLE IF NOT EXISTS topics (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
        week TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending')""")

    conn.execute("""CREATE TABLE IF NOT EXISTS prompt_versions (
        id TEXT PRIMARY KEY, system_prompt TEXT NOT NULL,
        few_shot_template TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    conn.execute("""CREATE TABLE IF NOT EXISTS drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id TEXT NOT NULL,
        content TEXT NOT NULL, prompt_version TEXT NOT NULL DEFAULT 'v1',
        slack_ts TEXT, status TEXT NOT NULL DEFAULT 'pending',
        rejection_reason TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    conn.execute("""CREATE TABLE IF NOT EXISTS eval_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        prompt_version TEXT NOT NULL, total_drafts INTEGER NOT NULL,
        approved INTEGER NOT NULL, rejected INTEGER NOT NULL,
        acceptance_rate REAL NOT NULL, drift_flag BOOLEAN NOT NULL DEFAULT 0)""")

    conn.execute("INSERT OR IGNORE INTO prompt_versions (id, system_prompt, few_shot_template) VALUES ('v1','demo','demo')")

    for tid, title in TOPICS:
        conn.execute("INSERT OR IGNORE INTO topics (id, title, week, status) VALUES (?,?,?,'pending')",
                     (tid, title, week))

    existing = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
    if existing == 0:
        for tid, content, status in DRAFTS:
            conn.execute(
                "INSERT INTO drafts (topic_id, content, prompt_version, status, created_at) VALUES (?,?,'v1',?,?)",
                (tid, content, status, now),
            )

        approved = sum(1 for _, _, s in DRAFTS if s == "approved")
        rejected = sum(1 for _, _, s in DRAFTS if s == "rejected")
        total = len(DRAFTS)
        conn.execute(
            "INSERT INTO eval_runs (run_at, prompt_version, total_drafts, approved, rejected, acceptance_rate, drift_flag) VALUES (?,?,?,?,?,?,?)",
            (now, "v1", total, approved, rejected, approved / total, 0),
        )

    conn.commit()
    conn.close()
    print("Demo data seeded.")

if __name__ == "__main__":
    seed()
