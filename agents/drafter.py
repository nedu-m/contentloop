"""Generate content drafts using Claude, seeded with top performers and brand voice."""
import os
import sqlite3
import anthropic
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "contentloop.db"
BRAND_VOICE_PATH = Path(__file__).parent.parent / "config" / "brand_voice.md"
PROMPT_VERSION = "v1"


def current_week() -> str:
    return datetime.now(timezone.utc).strftime("%G-W%V")


def get_top_performers(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    rows = conn.execute(
        """SELECT content, impressions, likes, retweets
           FROM posts
           ORDER BY impressions DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_pending_topics(conn: sqlite3.Connection) -> list[dict]:
    week = current_week()
    rows = conn.execute(
        "SELECT id, title, description FROM topics WHERE week = ? AND status = 'pending'",
        (week,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_prompt_version(conn: sqlite3.Connection, version: str) -> dict:
    row = conn.execute(
        "SELECT system_prompt, few_shot_template FROM prompt_versions WHERE id = ?",
        (version,),
    ).fetchone()
    if not row:
        raise ValueError(f"Prompt version '{version}' not found in DB")
    return dict(row)


def format_top_posts(posts: list[dict]) -> str:
    lines = []
    for i, p in enumerate(posts, 1):
        lines.append(
            f"{i}. \"{p['content']}\"\n"
            f"   (impressions: {p['impressions']}, likes: {p['likes']}, retweets: {p['retweets']})"
        )
    return "\n\n".join(lines)


def format_topics(topics: list[dict]) -> str:
    lines = []
    for i, t in enumerate(topics, 1):
        desc = f" — {t['description']}" if t["description"] else ""
        lines.append(f"{i}. {t['title']}{desc}")
    return "\n".join(lines)


def parse_drafts(response_text: str, topics: list[dict]) -> list[str]:
    """Parse numbered drafts from Claude response."""
    lines = response_text.strip().split("\n")
    drafts = []
    current = []

    for line in lines:
        stripped = line.strip()
        # detect lines like "1. text", "2. text"
        if stripped and stripped[0].isdigit() and ". " in stripped[:4]:
            if current:
                drafts.append(" ".join(current).strip())
            # strip the leading number
            current = [stripped.split(". ", 1)[1]]
        elif stripped and current:
            current.append(stripped)

    if current:
        drafts.append(" ".join(current).strip())

    return drafts


def draft_content():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    topics = get_pending_topics(conn)
    if not topics:
        print(f"No pending topics for week {current_week()}")
        conn.close()
        return

    top_posts = get_top_performers(conn)
    brand_voice = BRAND_VOICE_PATH.read_text()
    prompt = get_prompt_version(conn, PROMPT_VERSION)

    user_message = prompt["few_shot_template"].format(
        top_posts=format_top_posts(top_posts) if top_posts else "(no historical posts yet — write fresh)",
        brand_voice=brand_voice,
        count=len(topics),
        topics=format_topics(topics),
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print(f"Generating {len(topics)} drafts with prompt {PROMPT_VERSION}...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=prompt["system_prompt"],
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text
    drafts = parse_drafts(raw, topics)

    if len(drafts) != len(topics):
        print(f"Warning: expected {len(topics)} drafts, got {len(drafts)}. Raw response saved.")
        print(raw)

    inserted = 0
    now = datetime.now(timezone.utc).isoformat()

    for i, topic in enumerate(topics):
        content = drafts[i] if i < len(drafts) else f"[Draft {i+1} missing — check raw output]"
        conn.execute(
            """INSERT INTO drafts (topic_id, content, prompt_version, status, created_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (topic["id"], content, PROMPT_VERSION, now),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Inserted {inserted} drafts into DB")


if __name__ == "__main__":
    draft_content()
