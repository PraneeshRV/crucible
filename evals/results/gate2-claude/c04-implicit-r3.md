# c04 — implicit — rep 3

```json
{
  "case": "c04",
  "condition": "implicit",
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
  "run_at": "2026-08-15T11:19:36+00:00",
  "seconds_per_turn": [
    119.9,
    52.4
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout p99 latency jumped from 180ms to 1.4s on Monday. Three things landed that
weekend: a new Redis caching layer, a composite index on the orders table, and a JVM
upgrade that changed the default garbage collector.

I'm going to profile it. What should I be measuring, and what would each result tell
you about the three?


## turn 1 response

No code in this repo to ground against (just `prompt.md` and an empty `artifacts/`), so this is from the symptom description.

One structural thing before the measurement list: **the deploys landed over the weekend, but the jump showed up Monday.** That's the first business-day traffic. Two consequences — onset time can't discriminate between your three suspects (they all predate the load), and the failure is probably load-dependent rather than a flat per-request cost. Pull the weekend p99 first: if it was already at 400–600ms Saturday, you have a per-request regression amplified by concurrency; if it was flat at 180ms until Monday 9am, you have a saturation cliff (pool exhaustion, GC under allocation pressure, lock contention) that only exists above some throughput.

## The one measurement that splits the space

Get a distributed trace of checkout with spans for every Redis call, every SQL statement, and the request boundary. Then ask: **does the extra ~1.2s live inside a span, or in the gaps between spans?**

- **Inside a Redis span** → cache layer.
- **Inside a SQL span** → index (plan change or write contention).
- **In unattributed gaps** — time between the end of one span and the start of the next, or before the first span — → the runtime: GC pause, JIT, CPU starvation, or thread-pool queueing. Nothing downstream can explain time that isn't in a downstream call.

Do this per-instance, not aggregated. If the tail concentrates on a few pods, it's JVM-local state (GC, heap, connection pool). If it's uniform across pods, it's a shared dependency or a code path everyone executes.

## Shape of the distribution

Pull the full histogram, not just p99. Two questions:

- **Did p50 move?** p50 unchanged + p99 blown out = tail-only phenomenon (GC pauses, timeouts, stampede, lock contention). p50 also up, say 40ms→80ms = systematic added cost on every request, which points at the extra Redis hop or a uniformly worse query plan.
- **Is the tail smooth or a cliff?** This one matters a lot here. GC pauses and queueing produce a smooth continuous tail. A sharp pile-up of requests at a specific value means a *configured timeout*. And 1.4s is suspicious — it's very close to "1s client timeout plus retry plus overhead." Check your Redis client's command timeout and connection-acquire timeout, and your DB pool's `connectionTimeout`. If the histogram has a spike at ~1.0s or ~1.2s, you're looking at a timeout path, not a slow path, and that strongly favors the cache layer.

## Per suspect

**Redis cache layer**
Measure: hit ratio; client-observed latency per command vs. server-side latency (`INFO commandstats`, `latencystats`, `SLOWLOG`); connection pool wait time and saturation; payload sizes; whether the miss path is serialized behind a lock (stampede on hot-key expiry).
- Client-side latency ≫ server-side latency → the problem is pool contention or blocking on an event-loop thread, not Redis itself.
- Low hit ratio → p99 is the miss path, which is now strictly slower than before (Redis roundtrip *plus* the original DB query). Confirms the cache is a net loss but only explains a few tens of ms, not 1.2s.
- Periodic synchronized spikes → stampede on TTL expiry.
- Exonerated if: Redis spans are single-digit ms at p99 and hit ratio is high.

**Composite index on `orders`**
Checkout *writes* orders, so this cuts both ways.
Measure: `pg_stat_statements` for the checkout statements, before/after mean and stddev; `auto_explain` (or `EXPLAIN (ANALYZE, BUFFERS)`) on the actual checkout queries to look for a plan flip; write-path metrics — WAL volume, index page splits, lock waits, autovacuum activity on `orders`.
- Read query got slower and the plan changed → the planner picked the new index and it's worse (wrong leading column, low selectivity, or it lost an index-only scan). Diagnostic and reversible.
- Reads unchanged, INSERT/UPDATE on `orders` slower with lock waits → write amplification. This is the load-dependent story and fits the Monday onset well.
- Exonerated if: SQL spans are unchanged at p99 and plans are identical.

**JVM upgrade**
Measure: `-Xlog:gc*` with pause-time histograms, allocation rate, heap occupancy after collection, humongous allocation counts if it's G1. Cross-check against **non-checkout endpoints** — GC is process-wide, so if checkout regressed and nothing else did, GC is unlikely to be the whole story.
- Sum of pause time in a window ≈ the added tail latency, and unattributed trace gaps line up with pause timestamps → confirmed.
- Multiple concurrent requests slow *simultaneously*, independent of what they were doing → stop-the-world, which is GC's signature and nothing else's.
- Important caveat: **a JVM upgrade changes more than the collector.** Container heap ergonomics (`MaxRAMPercentage`, `UseContainerSupport`), DNS caching TTL, TLS defaults, HTTP client behavior. If GC logs look clean, don't clear the JVM — check whether the heap size it actually chose changed, and whether `networkaddress.cache.ttl` defaults shifted (that produces latency spikes that look nothing like GC).

## Two traps

**These interact.** A cache layer serializes objects into large byte arrays; in G1 those can become humongous allocations, which drive up GC pressure. The cache and the new collector can be *jointly* causal, in which case reverting either one alone fixes it — and you'll attribute the whole thing to whichever you flipped first. If a single revert fixes it, verify by re-enabling it with the other reverted.

**Your list of three may not be exhaustive.** The Monday onset is equally consistent with something that isn't on the list: a traffic-mix change, data volume crossing a threshold, or a downstream dependency that also deployed. Keep a fourth slot open until the trace accounts for the full 1.22s.

## Cheapest decisive flips, in order

1. **One canary pod with the old GC flags explicitly set** (`-XX:+UseParallelGC` or whatever you were on). Config-only, no code revert, and it isolates the collector from the rest of the JVM upgrade.
2. **Cache kill switch on a canary** — if p99 returns to 180ms, the cache is implicated.
3. **Index** can't be dropped as casually, but `EXPLAIN ANALYZE` plus `pg_stat_user_indexes` scan counts tell you whether the planner is even using it. If nothing scans it, it's only a write-path cost.

Run all three canaries under live Monday-level load; staging won't reproduce a saturation cliff.

If you can paste the trace waterfall or the GC log once you have it, I can help attribute the gap.


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

No — hold on. That run didn't measure anything. It's a failed execution, not a negative result.

(`scripts/profile.sh` isn't in this repo, so I'm reading the output rather than the source.)

Four independent failures in six lines:

1. **`async-profiler: No such file or directory`** — the profiler binary never executed. Whatever produced those numbers, it wasn't the profiler.
2. **`JAVA_HOME not set, falling back to /usr/bin/java (11.0.2)`** — it fell back to the CLI `java` on the box, which is not necessarily the JVM running your checkout service. GC stats have to come from the live process. And if your weekend upgrade moved you *to* 17 or 21, then 11.0.2 isn't even the version under investigation. Worth noting 11's default is already G1, so "the upgrade changed the default GC" only makes sense for particular version pairs — pin down which two.
3. **`[: --duration: integer expression expected`** at line 44 — argument parsing broke. `--duration 120` did not take effect. The sampling window was whatever the script falls back to, plausibly zero.
4. **`alloc_rate_mb_s=0`** — this is the one that settles it. A JVM serving live checkout traffic cannot have a zero allocation rate. Every request allocates. Zero is not a low number here, it's the absence of a measurement. `gc_pause_total_ms=0` is the same artifact.

The `verdict: no GC pressure detected` line is the script computing a conclusion from two zeros that mean "no data." It reads like a finding, which is what makes it dangerous.

So the garbage collector is exactly as suspect as it was before you ran this. Don't let "not GC" into your set of established facts.

## Getting the actual answer, without the broken script

The most direct check needs no profiler at all — read the collector off the live process:

```
jcmd -l                      # find the real service PID
jcmd <pid> VM.version        # which JVM is actually running
jcmd <pid> VM.flags          # actual collector + heap sizing in effect
```

`VM.flags` answers "did the default GC change" directly, and also shows whether the upgrade re-derived your heap size via container ergonomics.

Then for pause data:

```
jstat -gcutil <pid> 1s       # works immediately, no restart
```

or enable proper logging — `-Xlog:gc*,safepoint:file=/var/log/gc.log:time,uptime,level,tags` on next restart, or at runtime via `jcmd <pid> VM.log`. Include `safepoint`: a long time-to-safepoint stalls every thread and looks identical to a GC pause from the outside, but won't show up in GC pause totals.

If you do fix async-profiler, run it in wall-clock mode (`-e wall`), not the default CPU mode. You're chasing latency, and blocked-on-I/O time is invisible to CPU sampling.

And before trusting that script again, give it a positive control — point it at a JVM you know is thrashing and confirm it reports nonzero. Any tool that can emit a clean `verdict:` line from a run with three errors in it will do that again.

## On Redis

Yes, work Redis in parallel — that data comes from Redis (`INFO commandstats`, `latencystats`, `SLOWLOG`) and your client's pool metrics, so it isn't blocked on any of the broken JVM tooling. Just do it *alongside* GC, not instead of it.

The canary flips from before still stand and still need no profiler: one pod with the old collector set explicitly, one pod with the cache switched off. Given the tooling is unreliable, those may get you an answer faster than fixing the toolchain.


## verdict

_ungraded — open the rubric only after the run completes_
