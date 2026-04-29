"""ContentLoop — demo dashboard for recruiters and stakeholders."""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

import streamlit as st
from demo_data import seed as seed_demo

DB_PATH = Path(__file__).parent / "contentloop.db"

# Auto-seed demo data if DB is empty (Streamlit Cloud deployment)
if not DB_PATH.exists():
    seed_demo()

st.set_page_config(
    page_title="ContentLoop",
    page_icon="🔁",
    layout="wide",
)

# ── helpers ──────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_drafts():
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.id, t.title AS topic, d.content, d.status,
               d.rejection_reason, d.prompt_version, d.created_at
        FROM drafts d
        JOIN topics t ON d.topic_id = t.id
        ORDER BY d.id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_evals():
    conn = get_conn()
    rows = conn.execute("""
        SELECT prompt_version, run_at, total_drafts, approved,
               rejected, acceptance_rate, drift_flag
        FROM eval_runs
        ORDER BY run_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_topics():
    conn = get_conn()
    rows = conn.execute(
        "SELECT title, week, status FROM topics ORDER BY week DESC, title"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── header ────────────────────────────────────────────────────────────────────

st.markdown("# 🔁 ContentLoop")
st.markdown(
    "A social media automation agent built with **Claude Code**. "
    "Reads content topics from ClickUp, generates drafts via Claude, "
    "routes them through a Slack approval loop, and runs nightly evals to detect prompt drift."
)

st.divider()

# ── architecture ─────────────────────────────────────────────────────────────

st.markdown("## How it works")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("""
    **1. Topics**

    🗂️ ClickUp board

    Weekly content topics synced into SQLite
    """)

with col2:
    st.markdown("""
    **2. Metrics**

    📊 X API

    Last 28d of post performance pulled as few-shot examples
    """)

with col3:
    st.markdown("""
    **3. Draft**

    🤖 Claude API

    Top performers + brand voice → 7 drafts generated
    """)

with col4:
    st.markdown("""
    **4. Approve**

    ✅ Slack

    Drafts posted as threads. React ✅ or ❌ to approve or reject.
    """)

with col5:
    st.markdown("""
    **5. Evals**

    📈 Nightly

    Acceptance rate per prompt version. Drift flagged automatically.
    """)

st.divider()

# ── pipeline stats ────────────────────────────────────────────────────────────

drafts = load_drafts()
evals = load_evals()
topics = load_topics()

approved = [d for d in drafts if d["status"] == "approved"]
rejected = [d for d in drafts if d["status"] == "rejected"]
pending  = [d for d in drafts if d["status"] == "pending"]

st.markdown("## Pipeline stats")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Topics this week", len([t for t in topics if t["status"] != "closed"]))
m2.metric("Drafts generated", len(drafts))
m3.metric("Approved", len(approved), delta=f"{len(approved)}/{len(drafts)}" if drafts else None)
m4.metric("Acceptance rate",
          f"{len(approved)/len(drafts)*100:.0f}%" if drafts else "—",
          delta="v1 prompt" if drafts else None)

st.divider()

# ── drafts ────────────────────────────────────────────────────────────────────

st.markdown("## Drafts")

tab_all, tab_approved, tab_rejected, tab_pending = st.tabs([
    f"All ({len(drafts)})",
    f"✅ Approved ({len(approved)})",
    f"❌ Rejected ({len(rejected)})",
    f"⏳ Pending ({len(pending)})",
])

STATUS_ICON = {"approved": "✅", "rejected": "❌", "pending": "⏳"}
STATUS_COLOR = {"approved": "green", "rejected": "red", "pending": "orange"}


def render_drafts(items):
    if not items:
        st.info("No drafts in this category.")
        return
    for d in items:
        icon = STATUS_ICON.get(d["status"], "")
        with st.expander(f"{icon} Draft #{d['id']} — {d['topic']}", expanded=False):
            st.markdown(f"**Content:**")
            st.info(d["content"])
            cols = st.columns(3)
            cols[0].markdown(f"**Status:** `{d['status']}`")
            cols[1].markdown(f"**Prompt:** `{d['prompt_version']}`")
            cols[2].markdown(f"**Created:** {d['created_at'][:10]}")
            if d["rejection_reason"]:
                st.warning(f"**Rejection reason:** {d['rejection_reason']}")


with tab_all:
    render_drafts(drafts)

with tab_approved:
    render_drafts(approved)

with tab_rejected:
    render_drafts(rejected)

with tab_pending:
    render_drafts(pending)

st.divider()

# ── evals ─────────────────────────────────────────────────────────────────────

st.markdown("## Evals")

if not evals:
    st.info("No eval runs yet. Run `python agents/evals.py` to generate the first report.")
else:
    for e in evals:
        drift = e["drift_flag"]
        rate = f"{e['acceptance_rate']*100:.0f}%"
        label = f"Prompt `{e['prompt_version']}` — {rate} acceptance rate"
        if drift:
            st.error(f"⚠️ {label} — **DRIFT DETECTED**")
        else:
            st.success(f"✅ {label} — OK")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total drafts", e["total_drafts"])
        c2.metric("Approved", e["approved"])
        c3.metric("Rejected", e["rejected"])
        c4.metric("Run at", e["run_at"][:10])

st.divider()

# ── orchestration ─────────────────────────────────────────────────────────────

st.markdown("## Orchestration")

st.markdown("ContentLoop runs headless via **Claude Code** custom slash commands:")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Run the full pipeline**")
    st.code("claude -p \"/run-content-loop\"", language="bash")
    st.caption("Pull metrics → sync topics → draft → post to Slack")

with col_b:
    st.markdown("**Run nightly evals**")
    st.code("claude -p \"/eval-this-week\"", language="bash")
    st.caption("Compute acceptance rate, flag drift, suggest prompt changes")

st.markdown("Scheduled via **GitHub Actions** — runs every Monday at 9am UTC, evals nightly at 2am UTC.")

st.divider()

# ── footer ────────────────────────────────────────────────────────────────────

st.markdown(
    "<div style='text-align:center; color: gray; font-size: 0.85em;'>"
    "Built with Claude Code · "
    "<a href='https://github.com/nedu-m/contentloop' target='_blank'>View on GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
