"""Spike: verify ClickUp API connection and task shape."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["CLICKUP_API_TOKEN"]
LIST_ID = os.environ["CLICKUP_LIST_ID"]

headers = {"Authorization": TOKEN}

resp = requests.get(
    f"https://api.clickup.com/api/v2/list/{LIST_ID}/task",
    headers=headers,
    params={"include_closed": "false"},
)
resp.raise_for_status()

data = resp.json()
tasks = data.get("tasks", [])

print(f"Found {len(tasks)} tasks\n")
for t in tasks:
    print(f"  id={t['id']}  name={t['name']}  status={t['status']['status']}")

if tasks:
    print("\nFull shape of first task:")
    import json
    print(json.dumps(tasks[0], indent=2))
