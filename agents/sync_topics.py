"""Sync this week's content topics from ClickUp into SQLite."""
import os
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "contentloop.db"
TOKEN = os.environ["CLICKUP_API_TOKEN"]
LIST_ID = os.environ["CLICKUP_LIST_ID"]


def current_week() -> str:
    return datetime.now(timezone.utc).strftime("%G-W%V")


def sync_topics():
    conn = sqlite3.connect(DB_PATH)

    headers = {"Authorization": TOKEN}
    resp = requests.get(
        f"https://api.clickup.com/api/v2/list/{LIST_ID}/task",
        headers=headers,
        params={"include_closed": "false"},
    )
    resp.raise_for_status()

    tasks = resp.json().get("tasks", [])
    week = current_week()
    synced = 0

    for t in tasks:
        description = t.get("description") or t.get("text_content") or ""
        conn.execute(
            """INSERT OR IGNORE INTO topics (id, title, description, week, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (t["id"], t["name"], description.strip(), week),
        )
        synced += 1

    conn.commit()
    conn.close()
    print(f"Synced {synced} topics for week {week}")


if __name__ == "__main__":
    sync_topics()
