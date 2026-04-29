"""Post pending drafts to Slack for approval."""
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "contentloop.db"
CHANNEL = os.environ["SLACK_CHANNEL_ID"]


def post_drafts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    drafts = conn.execute(
        """SELECT d.id, d.content, t.title
           FROM drafts d
           JOIN topics t ON d.topic_id = t.id
           WHERE d.status = 'pending' AND d.slack_ts IS NULL""",
    ).fetchall()

    if not drafts:
        print("No unposted pending drafts")
        conn.close()
        return

    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    posted = 0

    for draft in drafts:
        text = (
            f"*Draft #{draft['id']} — Topic: {draft['title']}*\n\n"
            f"{draft['content']}\n\n"
            f"React ✅ to approve or ❌ to reject. "
            f"If rejecting, reply in thread with the reason."
        )

        try:
            result = client.chat_postMessage(channel=CHANNEL, text=text)
            ts = result["ts"]
            conn.execute(
                "UPDATE drafts SET slack_ts = ? WHERE id = ?",
                (ts, draft["id"]),
            )
            posted += 1
            print(f"  Posted draft #{draft['id']} (ts={ts})")
        except SlackApiError as e:
            print(f"  Failed to post draft #{draft['id']}: {e.response['error']}")

    conn.commit()
    conn.close()
    print(f"Posted {posted} drafts to Slack channel {CHANNEL}")


if __name__ == "__main__":
    post_drafts()
