# c04 — explicit — rep 3

```json
{
  "case": "c04",
  "condition": "explicit",
  "rep": 3,
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
  "run_at": "2026-08-15T11:24:15+00:00",
  "seconds_per_turn": [
    173.3,
    56.1
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

Case file declined by permissions, so the predeclarations stay inline here — they're on record in this transcript for turn 2.

## First, a caution about the framing

"Three things landed; which one is it?" presumes the cause is on the list. It may not be. The regression appeared **Monday** — which is also when weekday traffic returns. If your 180ms baseline was read off a weekend, part or all of the delta could be load, not code. I'll treat "none of the three" as a first-class rival, not a footnote.

Also worth splitting: a JVM upgrade changes more than the collector. Container-aware heap defaults, JIT, TLS, and DNS caching all moved too. Don't let "the GC changed" absorb the whole JVM hypothesis.

## Check 0 — validate the signal before you profile anything

Is the p99 jump visible in **load balancer access logs or RUM**, independent of the app's own timer?

A JVM upgrade often drags in new instrumentation, and a timer that starts including queue time will "regress" a system that didn't change. If the LB is flat and only the app metric moved, you're profiling a measurement artifact. Two minutes of work that protects everything downstream.

## Checks 1–3 — cheap orientation, before the profiler

These cost dashboard queries and cut the space harder than any profile will.

**1. The whole distribution, not p99.** Get p50/p90/p99/p99.9 and look at the actual histogram.

| Shape | Reading |
|---|---|
| p50 also up (say 180→600) | A cost was added to *every* request — extra hop, extra write, throughput loss `[inferred: additive costs shift central tendency]` |
| p50 flat, only p99+ moved | A *rare blocking event* — pause, pool exhaustion, timeout+retry, or a plan that's bad only for some parameter values |
| Two humps | A branch: cache hit vs miss, or plan A vs plan B |
| Smooth stretched tail | Queueing/contention |
| **Pile-up at a round number** (1000/1500/3000ms) | A timeout constant. That's config, and it's almost certainly the Redis client or a retry policy |

**2. Blast radius.** Pick an endpoint that touches neither Redis nor the orders table. Did its p99 move?

- Moved too → JVM/GC or host-level. H1 and H2 both weaken sharply.
- Flat → checkout-specific. H3a weakens sharply.

**3. Baseline hygiene.** Compare Monday to the **previous Monday**, not to Sunday. And check what p99 was on Sunday at low traffic:

- Already elevated Sunday → load-independent, deploy-caused. H4 weakens.
- Normal Sunday, broke at the Monday ramp → load-*dependent*, which fits pool exhaustion, cache stampede, or allocation pressure — and does **not** fit "every request got a bit slower."

## Check 4 — the attribution budget (the one most people skip)

For a sample of slow checkouts, decompose wall clock into:

- `t_redis` — client-side call durations
- `t_pool_wait` — time acquiring a Redis connection **and** a DB connection, recorded *separately* from the call itself
- `t_db` — statement durations
- `t_cpu` — app compute
- `t_residual` = wall clock − everything above

**The residual is the GC signature.** Stop-the-world pauses appear in no span; they show up as the gap between the sum of your spans and the clock. If 1.2s is sitting in unaccounted time, you're looking at the thread being descheduled — GC, a safepoint, or CPU starvation. If it's sitting in `t_pool_wait`, the Redis client is your answer and Redis itself is probably healthy.

Separating `t_pool_wait` from `t_redis` matters: a saturated pool makes Redis look fast while requests queue behind it.

## Check 5 — the sharpest single discriminator

**Do slow requests cluster in time across unrelated endpoints?**

Take every request over 1s, across all endpoints, and check co-occurrence windows.

- Slow requests bunch into the same ~10–500ms windows, affecting an arbitrary mix of endpoints → STW pauses. Nothing else does this. `[documented: STW halts all application threads]`
- Slow requests are spread over time and attached to particular keys/parameters → Redis or DB.

Corollary: replay the *same* checkout request repeatedly. Sometimes-fast/sometimes-slow → GC. Consistently slow → data-dependent, so Redis or the query plan.

## Targeted instruments, with predeclared mappings

**H3a — GC.** `-Xlog:gc*,safepoint`. Then:
- Verify which collector is *actually* running: `jcmd <pid> VM.flags`. Don't trust the changelog.
- Check p99 pause and total STW ms/minute. To produce a 1.2s tail directly you need pauses near that size. Smaller pauses can still do it via queueing amplification — a 300ms pause behind a saturated thread pool yields multi-second tails — but that requires showing the saturation too.
- **Check heap sizing separately (H3b).** Container-aware defaults often set max heap to ~25% of container memory. A heap that silently shrank produces near-constant full GCs, and that's a JVM-upgrade effect that isn't really about the collector.
- *Contradicted if:* total STW time is a small fraction of the latency gap **and** slow requests show no time-clustering.

**H1 — Redis.**
- **Calls per checkout.** An N+1 cache pattern with dozens of sequential round trips is an easy way to add a second. One number, high value.
- Hit rate, and whether misses coalesce. A cold cache with no single-flight gives you a stampede — N concurrent identical DB queries. This explains Monday timing *without* needing a confound, so it's a strong candidate.
- Client-side timeout/error counters, not server-side latency.
- Server: `INFO commandstats`, `SLOWLOG GET`, **evictions** (maxmemory policy churning the hit rate), and any O(N) command — `KEYS`, wide `HGETALL`.
- Is the client blocking an event-loop thread?
- *Contradicted if:* bypassing the cache leaves p99 unchanged.

**H2 — the index.** Note this cuts against intuition: checkout **writes** to orders, and an index makes writes slower, not faster.
- Snapshot-diff `pg_stat_statements` and look at the INSERT/UPDATE on orders, not just the SELECTs.
- **HOT-update loss:** indexing a frequently-UPDATEd column disables heap-only-tuple updates → page churn, bloat, vacuum pressure. This one *grows over days* rather than stepping instantly, which is a distinguishing time-signature.
- `EXPLAIN (ANALYZE, BUFFERS)` on the checkout queries — did the planner switch to the new index and get worse? Turn on `auto_explain`.
- Was `ANALYZE` run after the build? Stale stats post-index produce bad plans.
- Check `indisvalid` — a failed `CONCURRENTLY` build leaves an index that costs you writes and is unusable for reads.
- *Contradicted if:* no orders-touching statement's timing moved and no plan changed.

**H4 — none of the three.** Cheapest first: **get the downstream payment-processor span.** Checkout almost always calls a PSP, a PSP slowdown looks exactly like this, and it isn't on your list. Then diff co-shipped config: instance types, autoscaler minimums, pool sizes, feature-flag rollouts.

## What I'd actually do, in order

Checks 0–3 first (dashboards, ~30 min), then 4–5. Only if attribution is still ambiguous, run the causal test — and order it **by reversibility**:

1. Canary one instance with the previous GC flag. Instantly reversible, touches no data.
2. Feature-flag the Redis layer to bypass on one instance.
3. Drop the index — **last**. Most expensive to reverse, lock risk on rebuild, and least likely to be a lone 7.8x tail cause.

## Status

All rivals `live`, none `leading`. The only evidence in hand is temporal correlation with the deploy window, which is equally consistent with all seven — including H0 and H4. I'm deliberately not seeding a ranking, because Check 1 is precisely what would justify one.

`terminal_state: underdetermined` · `action_disposition: hold`

Bring me the distribution shape, the blast radius, and the previous-Monday comparison, and I'll update every rival against the mappings above.


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

## That output is a failed run, not a measurement

Look at `alloc_rate_mb_s=0`. A JVM serving checkout traffic cannot allocate zero bytes per second — any running Java process allocates continuously. That value isn't a low reading, it's a null. And `gc_pause_total_ms=0` is the same null from the same source. The `verdict:` line is computed from those two zeros, so it's restating the failure, not interpreting data.

The three lines above it explain why:

- `async-profiler: No such file or directory` — the profiler binary never loaded. Nothing was sampled.
- `[: --duration: integer expression expected` — arg parsing broke, so `--duration 120` never applied. The sampling window is zero or undefined.
- `JAVA_HOME not set, falling back to /usr/bin/java (11.0.2)` — this is the one that matters most for your hypothesis. Your suspect change is a **JVM upgrade**. This script reported on a fallback JDK 11.0.2 (a 2019 build). If production upgraded past 11, then even a *working* run of this script would have measured the wrong runtime.

## Status update: nothing moved

A check that didn't execute produces no evidence about anything. The failure is in the *instrument*, so I mark the check failed rather than the hypothesis, and the predeclared GC discriminator stays unconsumed — it never ran.

I did look for residual signal that survives independent of the broken parts. There isn't any: the only real observation in that output is that some `java` on the box where you ran this is 11.0.2, and that speaks to where the check ran, not to GC behavior in production.

| id | hypothesis | status | change |
|---|---|---|---|
| H3a | New default GC: STW pauses | **live** | unchanged — discriminator unconsumed |
| H3b | JVM upgrade, non-GC: heap sizing, JIT, TLS | **live** | unchanged |
| H1 | Redis | **live** | unchanged |
| H2 | Composite index | **live** | unchanged |
| H4 | None of the three (Monday ramp, PSP, config) | **live** | unchanged |
| H0 | Signal artifact | **live** | unchanged |

So: no, I wouldn't move to Redis on this basis. Redis isn't more likely than it was an hour ago — it would only be inheriting probability from an elimination that didn't happen. If you narrow to Redis now and the cause is GC, the broken script is what sent you down the wrong branch, and you'll have spent the day proving Redis is fine.

## Getting real GC data without async-profiler

You don't need the missing profiler for this. In rough order of effort:

1. **Check what you already have.** Most JVM apps export `jvm_gc_pause_seconds` and `jvm_memory_allocated_bytes_total` to Prometheus. If there's any JVM dashboard, the pause histogram may already be sitting there across the whole weekend — no new tooling, and you get the *before/after* comparison the profiler can't give you retroactively.
2. **Confirm the runtime first**, against the production PID: `jcmd <pid> VM.version` and `jcmd <pid> VM.flags`. That tells you which JVM and which collector are actually running. Everything else is worthless until this matches the post-upgrade version you expect.
3. **`jstat -gcutil <pid> 1000`** — pause counts and cumulative GC time, ships with the JDK, no install.
4. **JFR** — `jcmd <pid> JFR.start settings=profile duration=120s filename=/tmp/co.jfr`. Built in, and it captures allocation *and* pause data, which is what you were trying to get.
5. **GC logs** going forward: `-Xlog:gc*,safepoint:file=...`.

## Validity gate for the re-run — predeclared

Before you read any verdict off that script again, the run must clear all four:

- `alloc_rate_mb_s` > 0
- the duration flag actually applied
- reported JVM version matches production's post-upgrade version
- the profiler attached without error

If any fails, quarantine the output. A tool that emits a confident `verdict:` line from null inputs will mislead you the same way twice.

## The thing that's actually unblocked right now

Checks 1–3 from the plan never needed a profiler and aren't affected by any of this: the **distribution shape** (did p50 move, is it bimodal, is there a pile-up at a round number), the **blast radius** (did a non-checkout endpoint's p99 move), and the **previous-Monday baseline**. Those are dashboard queries. They also discriminate GC from Redis from index more cleanly than a single-host profile would — particularly blast radius, since GC hits every endpoint and Redis doesn't.

I'd run those while you sort out the profiler.

`terminal_state: underdetermined` · `action_disposition: hold`


## verdict

_ungraded — open the rubric only after the run completes_
