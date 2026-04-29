"""Pull last 28 days of X posts with metrics into SQLite."""
import os
import sqlite3
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "contentloop.db"
BEARER = os.environ.get("X_BEARER_TOKEN")
USER_ID = os.environ.get("X_USER_ID")


def pull_metrics():
    if not BEARER or not USER_ID:
        print("X credentials not set — skipping metrics pull")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    start_time = (datetime.now(timezone.utc) - timedelta(days=28)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    headers = {"Authorization": f"Bearer {BEARER}"}
    params = {
        "max_results": 100,
        "start_time": start_time,
        "tweet.fields": "public_metrics,created_at,text",
    }

    all_tweets = []
    next_token = None

    while True:
        if next_token:
            params["pagination_token"] = next_token

        resp = requests.get(
            f"https://api.twitter.com/2/users/{USER_ID}/tweets",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        tweets = data.get("data", [])
        all_tweets.extend(tweets)

        next_token = data.get("meta", {}).get("next_token")
        if not next_token or not tweets:
            break

    pulled_at = datetime.now(timezone.utc).isoformat()
    upserted = 0

    for t in all_tweets:
        m = t.get("public_metrics", {})
        conn.execute(
            """INSERT OR REPLACE INTO posts
               (id, content, posted_at, impressions, likes, retweets, replies, pulled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                t["id"],
                t["text"],
                t["created_at"],
                m.get("impression_count", 0),
                m.get("like_count", 0),
                m.get("retweet_count", 0),
                m.get("reply_count", 0),
                pulled_at,
            ),
        )
        upserted += 1

    conn.commit()
    conn.close()
    print(f"Pulled and upserted {upserted} posts")


if __name__ == "__main__":
    pull_metrics()
