"""Spike: verify Slack bot can post a message and receive a reaction event."""
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
CHANNEL = os.environ["SLACK_CHANNEL_ID"]

# Post a test message
result = app.client.chat_postMessage(
    channel=CHANNEL,
    text="ContentLoop spike test — react ✅ or ❌ to this message to confirm events fire.",
)
ts = result["ts"]
print(f"Posted message ts={ts}")


@app.event("reaction_added")
def handle_reaction(event, say):
    print(f"reaction_added: reaction={event['reaction']}  item_ts={event['item']['ts']}")


@app.event("reaction_removed")
def handle_reaction_removed(event, say):
    print(f"reaction_removed: reaction={event['reaction']}  item_ts={event['item']['ts']}")


print("Listening for reactions (Ctrl+C to stop)...")
SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
