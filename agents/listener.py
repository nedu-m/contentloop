"""Listen for Slack reactions and update draft status in SQLite."""
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "contentloop.db"

app = App(token=os.environ["SLACK_BOT_TOKEN"])

APPROVE_REACTIONS = {"white_check_mark", "+1", "heavy_check_mark"}
REJECT_REACTIONS = {"x", "negative_squared_cross_mark", "no_entry", "thumbsdown"}


def get_rejection_reason(client, channel: str, thread_ts: str, bot_user_id: str) -> str:
    """Fetch the first non-bot reply in the thread as the rejection reason."""
    try:
        result = client.conversations_replies(channel=channel, ts=thread_ts)
        messages = result.get("messages", [])
        for msg in messages[1:]:  # skip the original bot message
            if msg.get("user") != bot_user_id:
                return msg.get("text", "").strip()
    except Exception:
        pass
    return ""


@app.event("reaction_added")
def handle_reaction_added(event, client):
    reaction = event.get("reaction", "")
    item = event.get("item", {})
    item_ts = item.get("ts")
    channel = item.get("channel")

    if item.get("type") != "message" or not item_ts:
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    draft = conn.execute(
        "SELECT id, topic_id FROM drafts WHERE slack_ts = ?", (item_ts,)
    ).fetchone()

    if not draft:
        conn.close()
        return

    if reaction in APPROVE_REACTIONS:
        conn.execute(
            "UPDATE drafts SET status = 'approved' WHERE id = ?", (draft["id"],)
        )
        conn.execute(
            "UPDATE topics SET status = 'approved' WHERE id = ?", (draft["topic_id"],)
        )
        print(f"Draft #{draft['id']} approved")

    elif reaction in REJECT_REACTIONS:
        bot_info = client.auth_test()
        bot_user_id = bot_info["user_id"]
        reason = get_rejection_reason(client, channel, item_ts, bot_user_id)

        conn.execute(
            "UPDATE drafts SET status = 'rejected', rejection_reason = ? WHERE id = ?",
            (reason, draft["id"]),
        )
        conn.execute(
            "UPDATE topics SET status = 'rejected' WHERE id = ?", (draft["topic_id"],)
        )
        print(f"Draft #{draft['id']} rejected — reason: {reason!r}")

    conn.commit()
    conn.close()


@app.event("reaction_removed")
def handle_reaction_removed(event, client):
    """Reset draft to pending if a reaction is removed."""
    reaction = event.get("reaction", "")
    item_ts = event.get("item", {}).get("ts")

    if not item_ts:
        return

    if reaction not in APPROVE_REACTIONS and reaction not in REJECT_REACTIONS:
        return

    conn = sqlite3.connect(DB_PATH)

    draft = conn.execute(
        "SELECT id, topic_id FROM drafts WHERE slack_ts = ?", (item_ts,)
    ).fetchone()

    if draft:
        conn.execute(
            "UPDATE drafts SET status = 'pending', rejection_reason = NULL WHERE id = ?",
            (draft[0],),
        )
        conn.execute(
            "UPDATE topics SET status = 'pending' WHERE id = ?", (draft[1],)
        )
        conn.commit()
        print(f"Draft #{draft[0]} reset to pending (reaction removed)")

    conn.close()


if __name__ == "__main__":
    print("ContentLoop listener started. Waiting for reactions...")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
