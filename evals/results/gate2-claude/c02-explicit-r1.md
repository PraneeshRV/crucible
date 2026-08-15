# c02 — explicit — rep 1

```json
{
  "case": "c02",
  "condition": "explicit",
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
  "run_at": "2026-08-15T03:52:20+00:00",
  "seconds_per_turn": [
    91.5
  ]
}
```

## turn 1 prompt

$crucible Users report the dashboard is slow, but only in the afternoon. Could be the database
connection pool exhausting, or it could be the CDN cache expiring on a 6-hour cycle.

I can either (a) read this morning's already-collected pool metrics, which takes a
minute, or (b) run a full load test against staging, which takes about 40 minutes and
needs me to book the environment.

Which should I do?


## turn 1 response

## Verdict: (a) — but read it for a different signal than you're planning to, and don't treat (b) as the fallback.

**First, a framing correction.** You've posed these as exclusive rivals; they aren't. A CDN expiry causes a cache-miss stampede → origin request rate spikes → pool demand spikes → pool exhausts. "Pool exhaustion" is plausibly the *mechanism* and "CDN expiry" the *trigger*, both true at once. A check that assumes exactly one is right will mislead you. The question that actually splits the field is: **is the trigger clock-periodic or load-following?**

### Rivals

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| H1 | DB connection pool exhaustion | `live` | falsifiable — pool wait time, checkout timeouts, active vs max |
| H2 | CDN 6-hour cache expiry → origin stampede | `live`, mildly weakened | falsifiable — origin request rate / cache-hit-ratio periodicity |
| H3 | Afternoon peak concurrency (or a scheduled afternoon batch/report job) saturating the DB, no cyclical trigger | `live` | falsifiable — weekend vs weekday, load-correlation |

H3 is the rival your framing omits, and it's the one I'd rank hardest to dismiss.

H2 starts slightly weakened before any new check: a 6-hour TTL fires ~4×/day, so it predicts ~4 slowdown windows, or at minimum a morning one — yet the report is *afternoon only* `[inferred: 24h ÷ 6h cycle vs. reported symptom]`. H2 survives only in its compound form: expiry *plus* concurrent load high enough that the origin can't absorb the miss burst. Which is to say, H2 surviving probably means H1 is also true.

### Predeclared outcome mapping for (a)

Read the morning pool data as a **time series, looking for a discontinuity at a 6-hour boundary** — not for whether the level looks healthy.

1. **Bump in pool wait time / active connections at a 6h boundary, disproportionate to concurrent request volume** → H2 `leading`, H1 `live` (as mechanism), H3 `weakened`.
2. **Pool tracks request volume smoothly, no boundary discontinuity, morning peak well under max** → H2 `weakened` (its predicted morning expiry left no trace), H3 `leading`, H1 `live`.
3. **Pool already saturated in the morning while nobody reports slowness** → the metric doesn't track user-visible latency; H1-as-sole-explanation `weakened`, and the instrument is suspect for this question.
4. **It's a snapshot, not a series — or doesn't span a 6h boundary** → check *invalid*. Quarantine it; nothing updates, no hypothesis weakens, and the discriminator stays unconsumed. This is the outcome that would make (a) worth zero, so check the shape of the data first.

### Why not (b), and why it isn't the fallback

The load test is the wrong instrument, not merely the expensive one. Drive enough synthetic concurrency at anything and the pool will exhaust — that result arrives in nearly every world, including worlds where the CDN is the real trigger, so it discriminates almost nothing. And it can't test H2 at all: staging's cache state, TTL config, and data volume don't reproduce your production expiry cycle. Forty minutes plus a booking, for a near-foregone conclusion that still wouldn't tell you production's afternoon load reaches that threshold.

(b) becomes the right call *later* — to size the pool once you know the pool is the mechanism. It's a capacity-characterization tool wearing a diagnosis costume.

### Run these alongside (a) — same order of cost, higher yield

- **Weekend vs. weekday.** The strongest discriminator available and it's free: a 6h TTL cycle runs Saturdays too. Same afternoon slowdown, same clock time, lower traffic → clock-periodic (H2). Weekends clean → load-following (H3).
- **Fixed clock time or drifting onset?** TTL-anchored triggers land at the same wall-clock minute daily; traffic saturation drifts with the ramp.
- **CDN origin request rate / cache-hit ratio over several days.** This is the *direct* test of H2 and is almost certainly already collected — strictly better for H2 than pool metrics are.

---

**terminal_state:** `underdetermined` — nothing is established yet; this resolves only the choice of next check.
**action_disposition:** `authorized` for (a) plus the three companion reads; `declined` for (b) at this time.

The trap here was accepting the binary. The morning metrics are worth reading, but their value is periodicity, not health — and the weekend comparison, which neither option named, likely beats both.


## verdict

_ungraded — open the rubric only after the run completes_
