"""Nightly evals: compute acceptance rate per prompt version, flag drift."""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "contentloop.db"
DRIFT_THRESHOLD = 0.10  # flag if acceptance rate drops >10 percentage points


def run_evals():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """SELECT
               prompt_version,
               COUNT(*) AS total,
               SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected
           FROM drafts
           WHERE status != 'pending'
           GROUP BY prompt_version"""
    ).fetchall()

    if not rows:
        print("No evaluated drafts yet — nothing to report")
        conn.close()
        return

    run_at = datetime.now(timezone.utc).isoformat()
    report_lines = [f"=== ContentLoop Evals — {run_at[:10]} ===\n"]
    alerts = []

    for row in rows:
        version = row["prompt_version"]
        total = row["total"]
        approved = row["approved"]
        rejected = row["rejected"]
        rate = approved / total if total > 0 else 0.0

        # compare to last run for this prompt version
        last_run = conn.execute(
            """SELECT acceptance_rate FROM eval_runs
               WHERE prompt_version = ?
               ORDER BY run_at DESC LIMIT 1""",
            (version,),
        ).fetchone()

        drift = False
        drift_note = ""
        if last_run:
            delta = last_run["acceptance_rate"] - rate
            if delta > DRIFT_THRESHOLD:
                drift = True
                drift_note = f" ⚠️  DRIFT: dropped {delta:.0%} vs last run"
                alerts.append(
                    f"Prompt {version}: acceptance rate fell from "
                    f"{last_run['acceptance_rate']:.0%} to {rate:.0%}"
                )

        conn.execute(
            """INSERT INTO eval_runs
               (run_at, prompt_version, total_drafts, approved, rejected, acceptance_rate, drift_flag)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_at, version, total, approved, rejected, rate, drift),
        )

        status_icon = "OK" if not drift else "DRIFT DETECTED"
        report_lines.append(
            f"Prompt {version}: {approved}/{total} approved ({rate:.0%}) — {status_icon}{drift_note}"
        )

    conn.commit()
    conn.close()

    report = "\n".join(report_lines)
    print(report)

    if alerts and os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_CHANNEL_ID"):
        client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        alert_text = "🚨 *ContentLoop Evals — Drift Detected*\n\n" + "\n".join(alerts)
        client.chat_postMessage(channel=os.environ["SLACK_CHANNEL_ID"], text=alert_text)
        print("Drift alert posted to Slack")


if __name__ == "__main__":
    run_evals()
