# c04 — explicit — rep 1

```json
{
  "case": "c04",
  "condition": "explicit",
  "rep": 1,
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
  "run_at": "2026-08-15T11:24:01+00:00",
  "seconds_per_turn": [
    227.3,
    55.0
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

Write wasn't permitted, so here it is inline — which is fine, the skill prefers inline anyway.

## First, the thing worth saying before any of the three

Three changes in one weekend makes "exactly one is guilty" the *least* likely shape, and it's the assumption the question bakes in. Keep a fourth hypothesis alive:

- **Interaction:** Redis serialization raises allocation rate, and the new collector handles that rate worse. H1 and H3 are then the same bug — and whoever reverts either one first will see it "fix," and draw the wrong conclusion.
- **The upgrade changed more than the collector:** default heap sizing and detected CPU count also move across JVM versions. Diff `-XX:+PrintFlagsFinal` between old and new before blaming the GC specifically.
- **Not on the list at all:** Monday traffic level, thread-pool saturation, a downstream dependency, or a measurement artifact (edge p99 vs app p99).

Also pull p50 immediately. p50 flat with p99 exploding is the signature of queueing or a stall, not of per-request work getting uniformly slower — that alone reorders everything below.

## The core discriminator

Capture 50–100 traces **conditioned on `latency > 1s`** — not a random 1% sample; the tail *is* the phenomenon. Decompose each into app CPU / Redis / JDBC / unaccounted wall-clock.

| What you see | Points at |
|---|---|
| Extra time inside Redis spans | Redis |
| Extra time inside JDBC spans | Index |
| Extra time in **no span** — a gap, or every span uniformly dilated | GC |
| Extra app CPU with no hotspot | Throttling / queueing (the fourth) |
| Deficit doesn't reproduce in the captures | Instrumentation is invalid — no hypothesis moves |

A GC pause gets charged to whatever span happens to be open, or to nothing. That asymmetry is what makes the waterfall discriminating rather than merely descriptive.

## Two nearly-free independent axes

**Time-clustering.** Needs only timestamps and host IDs. If slow requests *clump* — all endpoints, all inputs, same instant — it's a process-wide stall (GC). If they *scatter* and track input (cart size, customer, cache miss), it's per-request work (Redis or DB). This is orthogonal to the waterfall, so it's real independent confirmation rather than a restatement.

**Tail shape.** Smooth heavy tail, or a spike at a round number? 1.4s sits near common timeout values. A *mode* at ~1000/1500ms means timeout+retry — that points hard at Redis and is near-impossible for GC, since pauses don't cluster on configured constants.

## Per-suspect: what confirms, what kills

**GC — check first, it's the cheapest.** `-Xlog:gc*` or JFR → max pause, pause time as % of wall clock, GC cause, allocation rate. Plus cgroup `throttled_usec` (concurrent collectors burn background CPU; under a tight limit that becomes throttling with no long individual pause).
- *Confirms:* max pause ≥ ~500ms, or summed pauses ≥ ~10% of wall clock in windows containing slow requests, with timestamps overlapping. Or: pauses individually small but constant — still GC, different fix.
- *Kills it:* max pause < 50ms and total < 2% across a window holding ≥20 tail requests, no throttling change.

**Redis.** Measure command RTT and **pool acquire wait as separate numbers** — that split is the whole point, and it's the step most often skipped. Plus calls-per-request, hit ratio, retry counters, `SLOWLOG`.
- *Confirms:* acquire wait p99 ≫ RTT p99 (900ms vs 2ms = pool exhaustion, not Redis). Or calls-per-request ≫ 1 × few-ms RTT ≈ your deficit (N+1 against the cache). Or retries > 0 with the tail at timeout × attempts.
- *Kills it:* Redis spans + pool wait < 50ms at p99, and slow requests aren't enriched for misses.
- Time the hit path and miss path separately — the miss path is now strictly longer than the old path was.

**Index.** `pg_stat_statements` diffed against a pre-deploy snapshot, with **reads and writes on `orders` separated** — checkout *writes* orders, and a new index is paid on every INSERT. Then `EXPLAIN (ANALYZE, BUFFERS)`, `idx_scan`, `indisvalid` (a failed `CREATE INDEX CONCURRENTLY` leaves an index that's maintained on writes but unusable for reads), and whether ANALYZE ran after creation.
- *Confirms:* INSERT p99 on orders up while SELECTs are flat — and `idx_scan = 0` strengthens it to all-cost-no-benefit. Or a SELECT's plan flipped to the new index and got slower.
- *Kills it:* DB time in tail traces unchanged, no statement whose mean rose.
- Useful asymmetry: if the app sees slow JDBC but the DB reports that statement as fast, the time is in driver/pool/network — not the index.

## Three traps that produce *no* evidence rather than negative evidence

1. **A CPU profiler cannot see GC stalls.** A sampling profiler in cpu mode samples running Java threads; during a stop-the-world pause there are none. "I profiled and found no hotspot" does **not** exonerate the GC. Use wall-clock mode, JFR, or just read the GC log.
2. **Don't reproduce in a load test.** Cache warmth, heap occupancy, and production data distribution won't carry over; a clean result there is invalid, not exculpatory.
3. **No averages.** A 2ms mean Redis latency is entirely compatible with a 1.2s p99 pool wait.

## One non-profiling move worth budgeting in parallel

Flip one canary host back to the old collector. Minutes, fully reversible, no data risk — the cheapest decisive test you have. Run it *after* reading the GC log so you don't spend it blind. Redis is similarly cheap if it's behind a flag (and if it isn't, that's worth knowing now). The index is the expensive one to undo — don't lead with dropping it; check `idx_scan` first.

Bring back the tail-trace waterfall, the GC pause histogram, and the pool-wait-vs-RTT split, and turn 2 should resolve this against predictions that are already on the record.


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

That run didn't measure anything. GC is not cleared, and the status of all three hypotheses is exactly where it was before you ran it.

**The tell is `alloc_rate_mb_s=0`.** A live JVM serving checkout traffic cannot have a zero allocation rate — that's not a low number, it's physically impossible for a running Java service. Zero here means "no samples collected," not "no allocation happened." `gc_pause_total_ms=0` is the same artifact, and `verdict:` is a string computed from two empty variables.

Four failures stacked, any one of which invalidates the run:

- `async-profiler: No such file or directory` — the profiler never attached. Nothing was sampled.
- `[: --duration: integer expression expected` at line 44 — your `--duration 120` was never applied. The sampling window was likely zero, which is the direct cause of the zeros downstream.
- `JAVA_HOME not set, falling back to /usr/bin/java (11.0.2)` — even had it attached, it was pointed at whatever JVM is on the box, not necessarily the process serving checkout.
- No latency window, no tail requests, no throttling data.

Compare against what I predeclared would kill the GC hypothesis: max pause < 50ms **and** total pause < 2% **and** across a window containing ≥20 tail requests **and** no throttling increase. None of those four were produced. The discriminator is unconsumed — it never ran, so it can't have come back negative.

The specific harm is that this is worse than getting no data at all: a false all-clear reorders your priors toward Redis, and you'd go spend a day there with the actual leading candidate silently still on the table.

**GC status: unchanged, still live.** Same for Redis and the index.

## Getting the measurement without async-profiler

You never needed it for this. Against the real production PID, on a host taking checkout traffic:

```
jcmd <pid> VM.flags | tr ' ' '\n' | grep -i gc     # which collector is ACTUALLY running
jstat -gcutil <pid> 1000 120                        # 120 samples of real GC activity
jcmd <pid> JFR.start duration=120s filename=/tmp/checkout.jfr settings=profile
```

All three ship with the JDK. `jstat` alone will answer the question in two minutes.

Also worth resolving while you're there: `jcmd <pid> VM.version` on the service. That 11.0.2 fallback is a loose thread — if the upgrade was 8 → 11, the default collector went Parallel → G1, which matches your description of the change. But confirm it rather than assume it; you're one command from knowing instead of inferring.

## On Redis

Run it in parallel, not instead. The pool-acquire-wait vs command-RTT split is cheap and independent of everything above, so there's no reason to serialize it behind the GC work. Just don't run it through `profile.sh` — the line 44 argument bug means any verdict that script emits about anything is untrustworthy until it's fixed. Fix the arg parsing and make it exit non-zero when the profiler is missing, rather than printing a verdict over empty data.

And the highest-value check from turn 1 is still untouched: the tail-conditioned trace waterfall. That one discriminates all three at once, and nothing that happened here affects it.


## verdict

_ungraded — open the rubric only after the run completes_
