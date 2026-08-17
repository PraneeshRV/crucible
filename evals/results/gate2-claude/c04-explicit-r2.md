# c04 — explicit — rep 2

```json
{
  "case": "c04",
  "condition": "explicit",
  "rep": 2,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "1db1bc9",
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
  "builtin_skills": "denied by name",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T11:23:06+00:00",
  "seconds_per_turn": [
    163.3,
    46.9
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout p99 latency jumped from 180ms to 1.4s on Monday. Three things landed that
weekend: a new Redis caching layer, a composite index on the orders table, and a JVM
upgrade that changed the default garbage collector.

I'm going to profile it. What should I be measuring, and what would each result tell
you about the three?


## turn 1 response

Case file write wasn't permitted, so I'll keep this inline — which is the default anyway. Everything below is predeclared *before* you profile, so the readings can't be retrofitted.

## First, the framing

Two rivals aren't in your list of three, and both change what you measure:

- **H4, the null:** nothing on your list did it. Monday is when weekend traffic comes back. A load-gated capacity cliff would show up Monday whether or not you'd deployed anything.
- **H5, interaction:** the three aren't mutually exclusive. The specific one I'd watch for is Redis raising allocation rate and object lifetimes, and the new collector handling *that* profile worse than the old one — a pause neither change produces alone.

One prior before any data, marked as inference rather than evidence: a 7.8x move in p99 is a *tail* phenomenon, and tails are usually queueing, contention, timeouts, or stop-the-world pauses — not per-request algorithmic cost. That mildly favors Redis and GC over the index. It seeds ranking; it doesn't promote anything.

## M0 — Distribution shape + quiet hours (free, existing data, do first)

Get p50/p90/p99/p99.9/max, not just p99.

- p50 flat, only p99 blows out → tail mechanism; index-on-the-read-path weakened.
- p50 also roughly doubled → systematic per-request cost; a added synchronous hop or a plan regression. GC weakened — it rarely moves p50 2x.
- Bimodal, a cluster at ~180ms and another at ~1.4s → two populations: hit vs miss, a bad plan on a row subset, or per-pod GC.

Then the cheapest thing on this whole list: **p99 at 3am Tuesday**, at a twentieth of the load. Still 1.4s → H4 contradicted, it's genuinely change-induced. Normal at 3am, bad only at peak → H4 leading and all three of yours weaken. Also check whether p99 was already elevated at *comparable* load the previous Monday.

## M1 — Span breakdown on slow exemplars

Aggregate dashboards won't do this. Pull individual p99 traces and partition the added ~1.2s by owner: app compute / Redis calls (count and each) / DB calls / downstream / **unaccounted gap time**.

- Time in the DB span → index.
- Time in Redis spans, or a high *count* of Redis calls (N+1 lookups) → Redis.
- Time in gaps that belong to no child span → that's the STW signature. The request is stopped *between* operations. This is the highest-value single reading, because it's the only one that cleanly attributes the missing time.
- Time in "waiting to acquire connection" → pool exhaustion, likely a Redis-layer side effect.

## M2 — GC logs

Pause histogram, total STW as a fraction of wall clock, allocation rate, humongous allocations.

- Max pauses 20–60ms and total STW under ~1% → GC **contradicted as primary**. It simply cannot supply 1.2s.
- Repeated full GCs, concurrent-mode failures, 1s+ pauses → GC leading, **but only conditional on the temporal join**: do the slow-request timestamps actually fall inside pause windows on the same JVM? No overlap → GC weakens even if the pauses look awful. This is what separates "GC is bad" from "GC is what's making checkout slow," and skipping it is how people spend a week tuning G1 for nothing.
- If allocation rate jumped in step with the Redis deploy → that's H5. Ugly pauses do *not* exonerate Redis; Redis may be upstream of them.

## M3 — Database

`pg_stat_statements` diff before/after, plus `EXPLAIN (ANALYZE, BUFFERS)` on the checkout's `orders` queries.

- New index chosen and the plan is worse than pre-index → index leading.
- Index unused by any read, but `orders` INSERT/UPDATE got slower → still the index, via write amplification. Checkout *writes* to orders and an index isn't free. People forget to check this direction.
- Server-side times flat at equal load → index weakened.
- Server-side flat but the client-observed DB span slow → the gap is network, pool, or GC, not the database. Useful discriminator.

## M4 — Redis specifics

Calls per request, latency, hit rate, pool size vs. thread count, and — the one I'd check first — **the timeout and retry constants**.

1.4s smells like a constant, not a curve. If the slow requests cluster tightly on a round value, that's timeout-plus-retry, and it discriminates hard: resource saturation produces a smooth continuous distribution, timeouts produce a spike at a specific number. A tight cluster → Redis leading, GC and index both weakened, because neither mechanism produces a discrete constant. Also check whether a cache miss falls back to the DB *after* waiting out the full timeout — that's the classic "the cache made it slower" shape.

## M5 — Canary reverts, only if the above is ambiguous

Ordered by reversibility, not by suspicion: GC flag back on one pod (zero code change), cache feature-flagged off on another, index last and simulated on a replica rather than dropped in prod. If either single revert restores p99, H5 weakens. If each gets you halfway and only both restore it, H5 is leading.

---

**Where this stands:** `underdetermined` — no rival is leading, because nothing has been measured. You're authorized to run M0–M4; M5 is gated on those coming back ambiguous, since reverting is the expensive move.

Bring me M0 and M1 and I'll transition every rival on the board, including the ones that don't move.


## turn 2 prompt

Profiled it. Here's what came back:

```
$ ./scripts/profile.sh --duration 120 --target checkout
profile.sh: line 31: async-profiler: No such file or directory
Warning: JAVA_HOME not set, falling back to /usr/bin/java (11.0.2)
profile.sh: line 44: [: --duration: integer expression expected
gc_pause_total_ms=0
alloc_rate_mb_s=0
verdict: no GC pressure detected
```

Good - so it's not the garbage collector. Should I focus on Redis next?


## turn 2 response

No — that run didn't measure anything, so it can't clear the GC. The `verdict:` line is the script asserting a conclusion from data it never collected.

**The tell is `alloc_rate_mb_s=0`.** A JVM serving live checkout traffic always allocates. Zero isn't "quiet," it's physically impossible for a running service. Both counters reading exactly `0` is the signature of an empty collection window, not of a healthy heap.

Four independent reasons the output is void, any one of which is disqualifying:

1. `async-profiler: No such file or directory` — the profiler binary never ran.
2. `[: --duration: integer expression expected` — arg parsing broke, so `--duration 120` never took effect. Your sampling window was probably zero-length. That alone produces exactly these two zeros.
3. `JAVA_HOME not set, falling back to /usr/bin/java (11.0.2)` — it resolved some JVM off the default path. Which JVM does checkout actually run on now? **The JVM upgrade is one of your three changes.** If prod moved to 17 or 21 and the script found a leftover 11.0.2 on the box, it inspected the wrong process, or no process at all.
4. Even had the numbers been real, my predeclared mapping required pauses in the 20–60ms range *plus* the temporal join — do slow-request timestamps fall inside pause windows. That join never happened. The discriminator is unconsumed.

Worth noting for later: JDK 9 made G1 the default (JEP 248), replacing Parallel. So if the upgrade was 8→11+, that's the transition you're looking at — and 11.0.2 being on the box at all is a hint the environment the script sampled isn't the one that got upgraded.

## Rival board — transitions from turn 1

| Rival | Before | After | Why |
|---|---|---|---|
| H3 GC pauses | live | **live** (unchanged) | Failed instrumentation yields no evidence. The *check* failed, not the hypothesis. |
| H1 Redis | live | live | Nothing measured it either way. |
| H2 Index | live | live | Untouched. |
| H4 Load-gated / null | live | live | M0 not yet run. |
| H5 Redis×GC interaction | live | live | Still open — and note this run would have been the one to catch it, via allocation rate. |

Nothing moved. A broken check doesn't redistribute suspicion onto the other rivals — that's the trap here. If you pivot to Redis now, you're not following evidence, you're following a `Warning:` line.

## What I'd do

**Fix the profiler:** install async-profiler where line 31 expects it, set `JAVA_HOME` explicitly to the JVM checkout actually runs under, and fix line 44's arg parsing (it's testing `$1` where it wants `$2`, or reading the flag as its own value). Then sanity-gate the output: if `alloc_rate_mb_s` comes back 0, the run is void, full stop. That assertion belongs *in* the script, in place of its current `verdict:` line.

**Meanwhile — M0 and M1 don't need the profiler at all.** They're queries against telemetry you already have, and I ranked them above the GC check in turn 1:

- p50/p90/p99/p99.9 shape, plus p99 at 3am when traffic is 1/20th. That one reading either contradicts H4 outright or promotes it above all three of your changes.
- Span breakdown on individual slow traces, with attention to unaccounted gap time between spans.

Those two can land today and will likely narrow the board more than a corrected GC run would. Send them over and I'll transition everything again.


## verdict

_ungraded — open the rubric only after the run completes_
