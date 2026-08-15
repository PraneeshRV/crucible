# c02 — explicit — rep 3

```json
{
  "case": "c02",
  "condition": "explicit",
  "rep": 3,
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
  "run_at": "2026-08-15T03:51:58+00:00",
  "seconds_per_turn": [
    60.8
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

The commitment isn't "which hypothesis is right" — it's "which check to buy." Being wrong costs 40 minutes plus an environment booking, so the gate is worth running, but a compressed one.

## Rivals

**R1 — DB connection pool exhaustion.** `testability: falsifiable`
**R2 — CDN cache expiring on a ~6h cycle.** `testability: falsifiable`
**R3 (constructed rival / null) — afternoon peak concurrency, mechanism unspecified.** `testability: falsifiable` — the dashboard is simply slow at peak load, and pool pressure and cache misses are both downstream symptoms rather than the cause. This matters because R1 and R2 are not mutually exclusive and both correlate with traffic; a check that only shows "pool was busy in the afternoon" cannot separate any of the three.

Current ranking, seeded from what you've told me only: all three `live`. Nothing is `leading` — "slow in the afternoon" is consistent with all of them `[inferred: symptom timing alone does not discriminate]`.

## The problem with both of your options

**Option (a) reads the wrong window.** Morning metrics sample a period when the symptom is absent. The most likely outcome — pool looks healthy — is exactly what R1 *predicts* if exhaustion is an afternoon-only phenomenon. That outcome weakens nothing and moves no rival `[inferred: absence of symptom in a non-symptomatic window is not evidence against a load-dependent mechanism]`. You'd spend a minute and still be at three live rivals.

**Option (b) tests the wrong environment, and only one rival.** A staging load test exercises R1 and R3. It says essentially nothing about R2, because staging almost never reproduces production CDN TTLs, edge population, or cache-key cardinality `[inferred: standard staging/CDN topology; verify against your actual staging config]`. So it's 40 minutes plus a booking to interrogate two of three rivals, in a system whose cache layer isn't the one that's misbehaving.

## What I'd actually do instead

Two checks that are both cheaper than (a) and discriminate better:

**Check 1 — read the CDN TTL config.** One lookup. Predeclared:
- TTL is not ~6h and no 6h invalidation/purge schedule exists → **R2 `contradicted`** (the hypothesis names a specific period; a different configured period falsifies it directly) `[predicted; would be measured: CDN config]`
- TTL is ~6h → R2 stays `live`, and you now know the expiry boundaries, which gives you a timestamp to check symptoms against.

This is the highest decision value per cost on the board, and it's free.

**Check 2 — pull *yesterday afternoon's* pool metrics and CDN cache-hit-ratio timeseries** — the incident window, not the quiet one. If they're retained, this is the same one-minute class of work as your option (a). Predeclared:
- Pool at max, checkout wait times spiking, cache hit ratio flat → **R1 `leading`**, R2 `weakened`
- Cache hit ratio collapsing at a 6h boundary with latency following it, pool with headroom → **R2 `leading`**, R1 `weakened`
- Both degrade together, tracking request rate with no discontinuity at any cache boundary → **R3 `leading`**, R1 and R2 `weakened` to symptom status
- Neither degrades but latency is real → all three `weakened`; look elsewhere (afternoon batch job, cron, backup window, timezone-driven traffic shift)

One more free discriminator: a strict 6-hour cycle fires four times a day, so it should produce a morning episode too (e.g. 00:00 / 06:00 / 12:00 / 18:00). "Only in the afternoon" is already awkward for R2 unless exactly one boundary lands on peak traffic — which is really R3 wearing R2's coat `[inferred: periodicity arithmetic; assumes users would notice and report a morning episode]`.

## Resolution

`terminal_state: underdetermined` — no rival is established, and neither of your two proposed checks would have established one.

`action_disposition` on the load test: **hold**. Don't book it yet. If check 2 lands on R1 `leading` and you need to find the actual pool ceiling before resizing it, the load test becomes worth its 40 minutes — at that point it's confirmatory sizing work, not discrimination.

Between your two as posed, (a) — it's a minute and you should never buy the 40-minute check first. But I'd spend that minute on the afternoon window rather than the morning one, and read the CDN TTL before either.


## verdict

_ungraded — open the rubric only after the run completes_
