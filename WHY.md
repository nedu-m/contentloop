# Why ContentLoop is built this way

## Why human-in-loop for v1, not auto-publish

The obvious move is to wire Claude output directly to the X API. I didn't do that.

Auto-publishing from a language model without a human checkpoint is a liability, not a
feature. LLMs hallucinate, drift, and occasionally produce outputs that are technically
within spec but contextually wrong — a sarcastic tone that lands badly, a claim that
turns out to be stale, a post that misreads the room on a given day.

The approval loop is the product. It is not a limitation to be removed later.

It also serves a second purpose: it generates a labeled dataset. Every ✅ and ❌ reaction,
paired with the rejection reason, is training signal for the evals harness. The human
judgment is captured, not bypassed.

Auto-publish belongs as a feature you unlock after the acceptance rate is consistently
above a threshold (say, 90% over 4 consecutive weeks). At that point you have evidence
the agent is reliable, not just a hypothesis.

## Where Claude Code earned its spot vs. just calling the API

There are two places I could have used the Claude API directly and gotten similar results:

1. The drafting step (`agents/drafter.py`) — a vanilla API call with a prompt
2. The evals step (`agents/evals.py`) — could be pure Python

Claude Code adds value in a different layer: **orchestration and extension**.

The `/run-content-loop` and `/eval-this-week` slash commands are not just wrappers around
Python scripts. They give Claude Code the ability to observe what happened, reason about
it, and take follow-up action — posting a summary, investigating an anomaly, suggesting
a prompt fix — without me writing that logic explicitly.

When `/eval-this-week` detects drift, it doesn't just print a number. It reads the
rejection reasons from the database, identifies patterns, and proposes a concrete change
to the prompt. That's not something a cron job calling `python evals.py` does. It requires
a reasoning agent that can read context and produce a recommendation.

Claude Code as orchestrator also means the system is extensible by another Claude Code
instance. The CLAUDE.md documents the agent loop well enough that a fresh instance can
pick it up and add a new platform or a new prompt version without me explaining the
architecture from scratch.

## Why SQLite, not Postgres

This is a single-tenant local tool on a 48-hour build. Postgres adds an infra dependency
(connection strings, a running server, migrations tooling) with zero upside at this scale.
SQLite is a file. It ships with Python. The whole database is one file you can `cp` or
inspect with any SQL client.

If this were multi-tenant — multiple teams running their own loops — Postgres would be
the right call. It is not, so SQLite is.

## Why Slack is the UI

A web dashboard would have taken 30% of the build time and added no unique value.
Slack is where the approver already works. The approval workflow fits naturally in a
reaction-based thread. No new tool to learn, no new tab to open, no login.

The constraint also clarifies scope: if something can't be expressed as a Slack message
or reaction, it probably doesn't belong in v1.

## Why GitHub Actions for the cron schedule

Free, public, and leaves an audit trail. Every pipeline run is a visible workflow
execution with logs. That audit trail matters when you're demonstrating a system to
someone else — they can see that the cron ran, what it output, and when.

The alternative (a local cron or a hosted scheduler) is invisible. GitHub Actions is not.
