"""Spike: verify X API v2 returns posts with public_metrics."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BEARER = os.environ["X_BEARER_TOKEN"]
USER_ID = os.environ["X_USER_ID"]

headers = {"Authorization": f"Bearer {BEARER}"}

resp = requests.get(
    f"https://api.twitter.com/2/users/{USER_ID}/tweets",
    headers=headers,
    params={
        "max_results": 10,
        "tweet.fields": "public_metrics,created_at,text",
    },
)
resp.raise_for_status()

data = resp.json()
tweets = data.get("data", [])

print(f"Found {len(tweets)} tweets\n")
for t in tweets:
    m = t.get("public_metrics", {})
    print(
        f"  {t['created_at'][:10]}  "
        f"imp={m.get('impression_count', 'n/a')}  "
        f"likes={m.get('like_count')}  "
        f"rt={m.get('retweet_count')}  "
        f"text={t['text'][:60]!r}"
    )

if data.get("meta"):
    print(f"\nmeta: {data['meta']}")
