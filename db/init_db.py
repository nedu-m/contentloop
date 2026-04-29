"""Initialize the SQLite database and seed the v1 prompt."""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "contentloop.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

V1_SYSTEM_PROMPT = """You are a social media content writer. Your job is to write punchy, engaging Twitter/X posts.

Rules:
- Max 280 characters per post
- No hashtag spam (max 2 per post)
- Write in first person, direct voice
- Lead with the insight, not the context
- No filler phrases: "I'm excited to share", "Thrilled to announce", "Game-changer"
- Each post must stand alone — no threads, no "1/n"
- Match the tone of the top-performing examples provided"""

V1_FEW_SHOT_TEMPLATE = """Here are the top-performing posts from the last 28 days (use these as style examples):

{top_posts}

---
Brand voice notes:
{brand_voice}

---
Write one post for each of the following topics. Number them 1 through {count}.

Topics:
{topics}

Output format — exactly this, nothing else:
1. [post text]
2. [post text]
...
"""


def init():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    conn.execute(
        """INSERT OR IGNORE INTO prompt_versions (id, system_prompt, few_shot_template)
           VALUES (?, ?, ?)""",
        ("v1", V1_SYSTEM_PROMPT, V1_FEW_SHOT_TEMPLATE),
    )

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init()
