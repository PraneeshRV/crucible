# c02 — explicit — rep 2

```json
{
  "case": "c02",
  "condition": "explicit",
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
  "run_at": "2026-08-15T03:51:56+00:00",
  "seconds_per_turn": [
    63.1
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

## Gate

The commitment being gated is **booking the 40-minute staging load test**, not the diagnosis itself. That's the expensive, hard-to-reverse move (environment booking, someone else's afternoon).

## Rivals

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| H1 | DB connection pool exhaustion | `live` | falsifiable |
| H2 | CDN cache expiring on a 6-hour cycle | `live` | falsifiable |
| H3 | Afternoon peak traffic alone — no broken mechanism, just the load curve crossing a soft limit | `live` | falsifiable |
| H4 | A scheduled afternoon job (batch/report/cron/analytics) contending for the same resource | `live` | falsifiable |

H3 and H4 matter because the load test is scoped to H1-vs-H2 and would leave both standing `[inferred: "only in the afternoon" is a time-correlation, and time correlates with more than these two mechanisms]`.

## Answer: (a), and it isn't close

Not because (a) is a strong check — it's a **weak** one — but because it's ~1 minute and forecloses nothing. (b) remains available afterward, unchanged. Sequencing costs you a minute; that argument holds no matter which hypothesis is true, which is why I can resolve this gate without resolving the diagnosis.

The comparison that actually decides it:

**(b) is badly targeted at the rival you'd be spending 40 minutes to rule out.** A synthetic load test on staging reproduces load-driven pool exhaustion reasonably well, but it does *not* reproduce a production CDN's cache-expiry cycle — different edge config, different cache population, no accumulated real traffic `[inferred: staging CDN state is not production CDN state; flag if your staging fronts the same edge with production-identical TTLs, that changes this]`. It also can't reproduce *time-of-day dependence*, which is the single most distinctive feature of the symptom. So (b) can promote H1 but can barely touch H2, H3, or H4. Its predicted outcomes are poorly grounded — obligation 3 penalizes that.

## Predeclared reading of (a) — before you look

- **Pool at/near max, wait-queue non-zero, or connections climbing without release (leak shape) even in the quiet morning** → H1 `leading`, H2 `weakened`. This is the outcome that earns the load test.
- **Pool flat, low, wide headroom, no waits** → H1 stays `live`, *not* `contradicted`. Morning is outside the symptom window; a null there is close to no evidence. Say this out loud now so nobody over-reads it in ten minutes.
- **A morning latency/origin-fetch spike at a 6-hour boundary (~06:00)** → H2 `leading`. **No morning spike at all** → H2 `weakened` only mildly: a 6-hour cycle fires ~4×/day, so it should leave a morning fingerprint — unless the phase happens to land the other refills in low-traffic hours and only the afternoon one collides with peak. That escape hatch is plausible, so absence weakens rather than contradicts.
- **The export lacks wait-time/high-water-mark fields** → check *failed*, not hypothesis weakened. Quarantine it; the discriminator never ran.

## The check you didn't list is better than both

Neither (a) nor (b) is the strongest cheap move. That's **the afternoon window's existing telemetry** — you almost certainly already have it, and nobody appears to have looked at its *shape*:

- **Pool exhaustion** → sustained plateau of degradation tracking concurrency, with acquire-wait times and timeout errors rising together.
- **CDN expiry** → a sawtooth: sharp latency spike at the boundary, decaying as the cache refills, origin request rate spiking inversely to hit ratio.
- **H3** → latency curve is a smooth monotone function of request rate with no discontinuity.
- **H4** → step change at a fixed wall-clock time, independent of traffic level.

These four shapes are mutually exclusive on a single latency-vs-time plot overlaid with CDN hit ratio. That's minutes of work and discriminates all four rivals — strictly more decision value than the 40-minute test, at lower cost.

## Transitions this turn

All four rivals: `live` → `live`. Nothing has been observed yet; this gate only ranked checks. `[inferred: no observation performed]`

---

- `terminal_state: underdetermined` — for the diagnosis. Nothing is established.
- `terminal_state: justified` — for the narrow selection decision: (a) before (b), on a dominance argument independent of which hypothesis holds.
- `action_disposition: hold` on booking staging. Book it only if (a) or the afternoon-shape check promotes H1 to `leading`.

Booking now is yours to authorize if there's a reason I can't see — a deadline, or the environment being scarce next week. `underdetermined` + `authorized` is honest. I'd just want it on record that you'd be spending 40 minutes on a test that can't see H2.


## verdict

_ungraded — open the rubric only after the run completes_
