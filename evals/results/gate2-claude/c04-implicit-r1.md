# c04 — implicit — rep 1

```json
{
  "case": "c04",
  "condition": "implicit",
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
  "run_at": "2026-08-15T11:20:25+00:00",
  "seconds_per_turn": [
    136.4,
    85.3
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

The repo here is empty (just the prompt), so this is advice rather than something I can run against your code.

One framing note up front: "which of the three" may turn out to be the wrong question. A 7.8x p99 jump rarely comes from one operation getting 7.8x slower — it usually comes from a *small* additive cost pushing a pool across its saturation knee. Keep "one of the three added 25ms and Monday traffic did the rest" on the board as a fourth hypothesis, and note that "JVM upgrade" and "GC change" are two hypotheses, not one.

## Two cheap facts before you profile anything

**1. The full percentile family, and the shape of the histogram.**

- p50 flat, p99 blown → tail-only: GC pauses, a miss path, or queueing.
- p50 up proportionally → systemic: every request pays it. An extra network hop or a query plan flip.
- **Bimodal** — slow requests clustering at a specific value like ~1.0s or ~1.5s → that's a *timeout constant*, not organic slowness. Go straight to your Redis client timeout + retry config. Organic contention produces a smooth stretched tail, not a second mode.

**2. Are the slow requests clustered in time, or scattered?**

This is the single cleanest discriminator you have, and it's nearly free:

- **Clustered** — several requests all slow in the same 200ms window, then a clean stretch → a stop-the-world event. GC hits every in-flight thread simultaneously. Nothing about caching or indexes does that.
- **Scattered** but correlated with request *attributes* (cold key, large cart, particular customer) → miss path or query plan. Time-independent, input-dependent.

Also pin the onset precisely: did p99 step up at the Saturday deploy timestamp (and nobody looked until Monday), or at the Monday traffic ramp? Deploy-time onset at low traffic = code/config. Ramp-time onset = load-dependent, which reopens the queueing hypothesis and also fits cache eviction thrash that only starts when the working set exceeds `maxmemory`.

## The one recording to take

Since it's a JVM, **JFR** covers three suspects in a single low-overhead recording: `jdk.GCPhasePause`, `jdk.SafepointBegin`, `jdk.ObjectAllocationSample`, `jdk.SocketRead` (separates Redis from DB by port), `jdk.JavaMonitorEnter`. Pair it with **async-profiler in wall-clock mode** (`-e wall`) — not CPU mode. If the time is spent *waiting*, a CPU profile will show you a bored, healthy-looking application and tell you nothing.

Then get trace exemplars for actual p99 checkouts and subtract: if spans sum to 200ms but the request took 1.4s, the missing 1.2s is outside your instrumentation — STW pause, safepoint, or connection-pool acquisition. That gap is itself a measurement.

## Per suspect: what to measure and what each result means

**Redis caching layer**

Measure client-side p99 per call, **calls per checkout** (fan-out), pool wait time, timeout/retry counts; server-side `INFO commandstats`, `keyspace_hits`/`misses`, `evicted_keys`, `used_memory` vs `maxmemory`, `SLOWLOG`.

| Result | Reading |
|---|---|
| Hit rate low, and p99 requests are the misses | Additive: Redis round trip *plus* the DB work. Compare hit-path vs miss-path latency directly — that's the clean experiment. |
| Hit rate high but p99 still bad | Not the cache logic. Look at fan-out (50 sequential round trips at 2ms = 100ms, and the tail of each is far worse than 2ms) and pool exhaustion. |
| `evicted_keys` climbing from Monday morning | Cache too small for weekday working set; thrashing. Explains a Monday-specific onset cleanly. |
| Redis server-side sub-ms, client-side p99 high | It's the client, the pool, or the network. Check whether Redis is cross-AZ and whether TLS was added. |
| Latency spikes periodic, matching your TTL | Stampede — concurrent misses on a hot key all stampede the DB. |

**Composite index**

Checkout *writes* to `orders`, so measure INSERT/UPDATE latency on that table separately from reads. Diff `pg_stat_statements` across the weekend for mean/max/stddev, and use `auto_explain` to capture plans for the slow tail specifically — `EXPLAIN` in a shell shows you the plan for *your* parameters, not the tail's.

| Result | Reading |
|---|---|
| Reads flat, writes up | Index maintenance cost. In Postgres also check `n_tup_hot_upd`/`n_tup_upd` — if the index covers a column that gets updated, you've disabled HOT updates, which means more bloat and more autovacuum. This would usually move p50 too. |
| Plan changed, buffers/rows read jumped | Optimizer flipped to the new index and it's worse — bad selectivity estimate, or column order wrong for the predicate. |
| Query times and DB CPU both flat | Exonerated for latency. Test it properly by dropping the index on a replica and comparing plans. |
| Long request time, trivial query cost | Not the index — lock contention. Check wait events; checkout commonly contends on inventory rows. |

**JVM / GC**

Turn on `-Xlog:gc*,safepoint`. Measure pause duration distribution, **total STW time per minute**, allocation rate, promotion rate, and time-to-safepoint (a separate killer from GC itself).

The arithmetic test: does (pauses/min × pause duration) account for the fraction of requests in the tail? If your max pause is 20ms, GC is exonerated no matter what changed in the upgrade.

If you moved 8 → 11/17/21, that's ParallelGC → G1. G1 normally *lowers* max pause, so a 1.2s pause under G1 means something specific went wrong — grep the log for `to-space exhausted`, `Pause Full`, and `Humongous`. Humongous allocation is very plausible here: G1 treats any object ≥ 50% of region size specially, and checkout serializing large carts or payment payloads produces exactly those. Also verify actual `Runtime.maxMemory()` — upgrades silently change heap sizing when cgroup awareness or `MaxRAMPercentage` defaults shift.

**The interaction to watch for:** the Redis layer added serialization, which raises allocation rate and produces large byte arrays, which makes G1 behave worse. Suspects 1 and 3 can be jointly causal, and neither reverts cleanly on its own. If allocation rate jumped alongside the Redis rollout, that's your signal.

**Saturation (the fourth hypothesis)**

Measure utilization and queue depth on every pool — HTTP threads, DB connections, Redis connections. If you're near the knee, latency goes as roughly 1/(1−ρ) and a 25ms addition genuinely does produce a 1.2s tail. The tell is that queue *wait* time, not service time, is what grew.

## Then stop observing and vary one thing

Profiling gives you correlation. Two clean one-variable tests:

- **Flag the Redis layer off** for a slice of traffic. Usually the easiest of the three to toggle, so do it first.
- **Set `-XX:+UseParallelGC`** on one instance, same JVM version. This is the test that separates *GC change* from *JVM version change* — the upgrade also moved your JIT, TLS stack, and string handling, and you don't want to attribute those to the collector.

If neither moves p99, you're left with the index and the traffic ramp, and the plan diff from `auto_explain` will settle it.


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

Hold on — that run didn't measure anything. The verdict line is the script reporting on an empty dataset.

**`alloc_rate_mb_s=0` is not a possible reading from a live JVM.** A checkout service under load allocates on the order of hundreds of MB/s; even a mostly-idle JVM is well above zero. Two zeros together means the sample window was empty, not that the heap was quiet.

The three lines above the metrics explain why:

- `async-profiler: No such file or directory` — the profiler binary isn't installed. The profiling step never ran.
- `[: --duration: integer expression expected` — argument parsing is broken, so `120` never became the duration. `--target checkout` probably didn't take either. That's the most likely mechanism for the zeros: a zero-length collection window.
- `JAVA_HOME not set, falling back to /usr/bin/java (11.0.2)` — it used whatever JVM was on the default path. 11.0.2 is from January 2019. If your upgrade moved production to 17 or 21, this script wasn't even looking at the JVM under suspicion. Nothing in the output names a PID, so it's also unclear whether it attached to the checkout process at all.

So the GC is neither convicted nor exonerated — it's untested. Worth checking where this ran, too: an unprovisioned host with no `JAVA_HOME` and no profiler sounds more like a build box or a laptop than the production instance.

## You don't need async-profiler for any of this

Everything you need ships with the JDK. No install, no restart:

```bash
jps -lv                                   # find the real checkout PID + its flags
jcmd <pid> VM.version                     # what JVM is actually running it
jcmd <pid> VM.flags -all | grep -iE 'gc|heap'
```

That third command settles "the upgrade changed the default GC" as a runtime fact — you'll see `UseG1GC` or `UseParallelGC` directly, plus what `MaxHeapSize` actually resolved to, rather than inferring it from release notes.

Then the measurement itself:

```bash
jstat -gcutil <pid> 1000 120              # 120 samples, 1/sec: YGC/YGCT/FGC/FGCT
```

If `FGCT` climbs over those two minutes, you have full GCs and your answer. This alone would have replaced the entire failed script.

For the deep dive, JFR is built into JDK 11 — it covers GC, allocation, socket reads, and lock contention in one recording:

```bash
jcmd <pid> JFR.start duration=120s filename=/tmp/checkout.jfr settings=profile
```

If you want the GC log without a restart, JDK 11 also supports enabling it live:

```bash
jcmd <pid> VM.log output=/var/log/gc.log what='gc*,safepoint'
```

Note `safepoint` there — time-to-safepoint is a separate stall source that `gc_pause_total_ms` wouldn't capture even if it had been measured correctly.

## A floor for the next run

Before trusting any output, predeclare what a working measurement looks like — otherwise a null result is indistinguishable from a broken instrument:

- alloc rate > 0 (expect tens to hundreds of MB/s under load)
- nonzero sample count *and* nonzero elapsed duration, both reported
- the PID and JVM version it attached to, printed explicitly
- `YGC` count > 0 across 120s

Any of those missing or zero → the run is void regardless of what the verdict line says.

Worth fixing `profile.sh` while you're there: it should exit nonzero when the profiler binary is missing, validate that duration parsed to an integer, and refuse to print `verdict:` when the sample count is zero. A script that emits a confident verdict after its profiler failed to launch is worse than no script — it manufactures exactly the wrong kind of confidence.

## On Redis

Investigate it, yes — but in parallel, not because GC was cleared. And the Redis checks need no profiler either, so you can run them right now:

```bash
redis-cli INFO stats     # keyspace_hits/misses, evicted_keys, ops/sec
redis-cli INFO memory    # used_memory vs maxmemory
redis-cli SLOWLOG GET 25
```

Hit rate and `evicted_keys` will tell you quickly whether the cache is doing its job or thrashing.

The order I'd actually run things: `jcmd VM.flags` plus 60 seconds of `jstat` (two minutes of work, settles the GC question), then `redis-cli INFO`, then JFR only if neither converges.

One more caveat for later — even a correct null on GC pauses wouldn't fully clear suspect 3. "JVM upgrade" and "GC change" are separate hypotheses; the upgrade also moved your JIT, TLS defaults, and HTTP client internals. Restoring the old collector on one instance with the same JVM version is what separates them.


## verdict

_ungraded — open the rubric only after the run completes_
