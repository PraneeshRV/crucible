# c02 — implicit — rep 1

```json
{
  "case": "c02",
  "condition": "implicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "fbf2c42",
  "skill_installed": true,
  "denied_tools": [
    "Task",
    "Agent",
    "Skill(debug)",
    "Skill(verify)",
    "Skill(code-review)",
    "Skill(simplify)",
    "Skill(deep-research)",
    "Skill(claude-api)"
  ],
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T03:50:17+00:00",
  "seconds_per_turn": [
    25.6
  ]
}
```

## turn 1 prompt

Users report the dashboard is slow, but only in the afternoon. Could be the database
connection pool exhausting, or it could be the CDN cache expiring on a 6-hour cycle.

I can either (a) read this morning's already-collected pool metrics, which takes a
minute, or (b) run a full load test against staging, which takes about 40 minutes and
needs me to book the environment.

Which should I do?


## turn 1 response

(a), now — but with one correction to what it buys you, and one thing to grab alongside it.

**Why (a) first:** it costs a minute against 40 minutes plus an environment booking. Even if it were only weakly informative, the ratio makes it a free move. There's no ordering where doing the load test first is better, since you can always escalate to it afterward.

**The caveat:** morning pool metrics don't test the afternoon hypothesis directly — they're off-peak. If the pool looks healthy at 10am, that rules out nothing, because the whole claim is that it saturates under afternoon load. So read them as a *baseline*, not a verdict:

- If the pool is already near-saturated in the morning, that's strong evidence — it means you have little headroom, and afternoon traffic would tip it over.
- If it's comfortable in the morning, you've learned your baseline utilization and checkout-wait times, which is what you need to compare against afternoon numbers.

**Grab this at the same time (also ~free):** you almost certainly already have afternoon-timestamped data that discriminates better than the morning numbers do.

- **Pool metrics from *yesterday* afternoon**, if retention covers it. Same query, right time window. This is the actual test.
- **CDN cache hit ratio** over the last day or two. It's usually already collected and costs nothing to read.

Those two probably settle it without a load test.

**One thing that argues against the CDN theory before you look at anything:** a 6-hour expiry cycle should produce slowness roughly four times a day, not once in the afternoon. For it to look afternoon-only, the expiry would have to land at a time when traffic is high enough for the cache-miss stampede to hurt — which means traffic is the real variable, and that points back at the pool. It's not disqualifying (that alignment is plausible), but it means "afternoon-only" is natively a load-shaped symptom, and the CDN story needs an extra coincidence to explain it. Checking hit-ratio timestamps against the slowdown window tests exactly that.

**Book the load test only if** the afternoon pool data is missing or ambiguous, or if you need to confirm a fix rather than locate the cause. Confirming a fix is a genuinely good use of 40 minutes; hypothesis generation isn't.


## verdict

_ungraded — open the rubric only after the run completes_
