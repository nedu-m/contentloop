Run the ContentLoop evals harness:

1. Run `python agents/evals.py` — compute acceptance rate per prompt version and flag drift

After running, interpret the output:
- If acceptance rate for any prompt version is below 50%, suggest specific changes to the prompt in `db/init_db.py` (V1_SYSTEM_PROMPT or V1_FEW_SHOT_TEMPLATE). Explain what the rejections suggest about what is going wrong.
- If drift is flagged (rate dropped >10% vs prior run), investigate: query the `drafts` table for recent rejections and their `rejection_reason` values. Summarize patterns in the rejection reasons.
- If everything looks healthy, confirm it and report the current acceptance rate.

To investigate rejections directly:
```
SELECT content, rejection_reason, created_at
FROM drafts
WHERE status = 'rejected'
ORDER BY created_at DESC
LIMIT 20
```
