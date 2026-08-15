# c02 — implicit — rep 2

```json
{
  "case": "c02",
  "condition": "implicit",
  "rep": 2,
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
  "run_at": "2026-08-15T03:50:49+00:00",
  "seconds_per_turn": [
    32.1
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

Do (a) — and honestly, it isn't close. A minute of work has to be wrong essentially always to lose to 40 minutes plus booking a shared environment.

But go in knowing what the morning metrics can and can't settle:

**What they can do:** show headroom. If the morning peak already sits near the pool ceiling — high checkout wait times, queue depth above zero, utilization at 80–90% — then a modest afternoon traffic bump tips it, and the pool hypothesis is suddenly very live. If the morning peak is at 20% utilization with zero wait time, pool exhaustion in the afternoon requires a multiple-times traffic increase, which you can check against your traffic graph in the same minute.

**What they can't do:** prove anything about the afternoon. Absence of morning pressure isn't absence of afternoon pressure.

**The free check worth doing alongside it:** the two hypotheses predict different *shapes*, and you probably already have the data. CDN expiry means a sharp onset at a fixed clock time, repeating at the same time daily, recovering within minutes as the cache refills. Pool exhaustion ramps with concurrency, tracks the traffic curve, and recovers gradually. Look at the onset edge of one afternoon incident.

One thing to weigh before booking staging: a synthetic load test only exercises hypothesis (a), and only if staging's pool config matches prod. It cannot reproduce a time-of-day cache expiry at all. So the expensive option isn't just expensive — it's blind to half the question.

Book staging only if the metrics show real pool pressure and you need to find the breaking point.


## verdict

_ungraded — open the rubric only after the run completes_
