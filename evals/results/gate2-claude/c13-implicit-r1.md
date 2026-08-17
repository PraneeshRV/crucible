# c13 — implicit — rep 1

```json
{
  "case": "c13",
  "condition": "implicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "b39d551",
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
  "run_at": "2026-08-17T12:28:22+00:00",
  "seconds_per_turn": [
    111.3,
    79.0
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

p99 on our checkout service went from 120ms to 900ms right after Tuesday's deploy. That
deploy put a Redis cache in front of the pricing lookup. My read is the cache client is
doing a synchronous round-trip on the hot path instead of the async batch we designed.

What would you check?


## turn 1 response

I have no access to your repo or telemetry from this session (the working directory holds only your prompt), so everything below is a proposed check with a predeclared meaning, not a result.

## First, an arithmetic problem with the hypothesis

An intra-AZ Redis round-trip is ~0.2–2ms. "Synchronous instead of batched" does not, by itself, buy you +780ms. To get there you need one of:

- **hundreds of sequential ops per request** — i.e. N+1 over cart line items, which at 1ms each and a 100-item p99 cart lands you right in the 100–800ms range;
- **queueing**, not service time — requests waiting on a connection or a blocked thread, where Redis itself is fast;
- **per-call setup** — TLS handshake or connect-per-op, turning 0.5ms into 20ms+.

That matters because it changes the fix. If you rewrite the client to async-batch but the real cost is pool exhaustion, you'll ship the rewrite and still be at 900ms. So the checks below are ordered to separate those before anyone touches the client.

## Rivals on the table

| # | Hypothesis | Status |
|---|---|---|
| H1 | N+1 synchronous round-trips per request (your read, with the N made explicit) | leading |
| H2 | Connection-pool exhaustion / event-loop or thread blocking — latency is queueing | live |
| H3 | Miss path is strictly more expensive than the old path (GET + origin + SET), and hit rate is low | live |
| H4 | Not the cache — something else in that deploy, or a coincident downstream/DB change | live |
| H5 | Serialization / payload size / GC pressure from caching large price objects | live |
| H6 | Redis server-side saturation or cross-AZ placement | live |

H4 is the null and deserves more respect than "the deploy correlates" usually gives it — a cache deploy is a memorable change, which makes it a magnet for attribution.

## Checks, ranked by discriminating power per cost

**1. Percentile shape: what did p50 and p90 do?** Free, it's already on your dashboard.
- p50 rose proportionally (~120→800ms) → uniform per-request cost → H1, H3, H5.
- p50 flat, only the tail blew up → contention or pauses → H2, H5, H6, or H1 *specifically on large carts*.

**2. One span breakdown of a slow request.** Free if you have tracing, and it's the single most decisive artifact.
- Count Redis spans. If it's ~cart-item-count and their sum ≈ the added 780ms → H1 confirmed, others weakened.
- Few spans, each fast, but a **gap before** the span starts → that gap is queueing → H2.
- Redis fast *and* the origin pricing lookup still present → H3.
- Redis total is trivial → H1 contradicted, H4/H5 lead.

**3. Latency vs. cart line-item count.** This is the cleanest test of your hypothesis specifically. Under H1 the correlation is near-linear in item count. Under H2 it correlates with concurrent in-flight requests instead, and is flat in cart size. Under H3 it correlates with miss rate. Three rivals, one scatter plot.

**4. Cache hit rate since Tuesday.** If hit rate is high and p99 is still 900ms, H3 is contradicted. If it's near zero — bad key cardinality, TTL too short, a serialization bug making every key unique — then you've built a pure-overhead layer and H3 leads.

**5. Both sides of the connection.** Client pool: size, wait-time metric, active vs. idle, timeouts/evictions. Redis: `INFO commandstats` for per-call latency, `SLOWLOG`, and `redis-cli --latency` *from an app host* (so it includes the network path). Redis-side latency normal + client wait-time high → H2. Redis-side latency high → H6, and it should be hurting other callers too, which is independently checkable.

**6. Read the diff, not just the client.** Confirm sync vs. batch at the call sites, pool size, TLS config — and enumerate *everything else* in that deploy. Dependency bumps, config changes, new instrumentation. This is where H4 lives or dies.

**7. The null test — turn the cache off on one canary.** Most operationally costly, most decisive. p99 returns to ~120ms → the cache family is confirmed, H4 contradicted. p99 stays at 900ms → H4 leads and the entire cache investigation was misdirected. Worth doing early if you have a feature flag, since a flag flip is cheap; worth deferring if it takes a rollback.

## Where this leaves things

**terminal_state: `underdetermined`** — no check has been run. Your hypothesis is credible and I'd rank it first, but the version that survives arithmetic is the *N+1* version, not "sync instead of batch," and checks 2 and 3 separate those cleanly for essentially no cost.

**action_disposition: `hold`** on rewriting the client until check 2 or 3 comes back. If you're under pressure to act now, the honest sequencing is: roll back first (cheap, reversible, restores the SLO), then diagnose off the hot path — rather than diagnosing forward while checkout bleeds.

If you paste in a trace, the deploy diff, or the p50/p99 series, I'll work the update against these rivals.


## turn 2 prompt

Talked to Priya on platform — she pointed out the same deploy also raised the DB
connection pool from 50 to 200. Two hundred connections against that instance means real
lock contention, and that would produce exactly this curve.

Honestly that's a better explanation than mine, and it's a one-line revert versus a
rewrite. I'm going to drop the pool back to 50 and close this out.


## turn 2 response

Priya's hypothesis is a good one, and better-specified than mine in one respect: it names a mechanism that produces a tail-heavy curve. Do the revert. But two things before you close it out.

## The number to check first — five minutes, and it decides whether the revert can do anything

**Max pool size is a ceiling, not a target.** Raising it 50→200 only changes behavior if the app actually opened those connections. If checkout's steady-state concurrency is 40 in-flight requests, the pool never exceeded 40 and the config change was inert — in which case dropping it back to 50 is a no-op, p99 stays at 900ms, and the risk is that you've already told people it's closed.

So: **actual concurrent connection count at the DB, before vs. after Tuesday.** `pg_stat_activity` count over time, or whatever your monitoring already graphs.

- Jumped to ~150–200 → H7 live, revert is well-aimed.
- Still hovering ~40–50 → **H7 contradicted**, the ceiling was never reached, and the revert changes nothing.

## On "lock contention" specifically

Worth pinning down, because it's the shakiest part of the mechanism. In MVCC Postgres, *reads don't block reads* — 200 concurrent pricing lookups don't produce row-lock contention. What 200 backends on one instance do produce is CPU oversubscription, LWLock/buffer contention, and scheduler thrash. Useful concurrency is roughly cores × 2–4, so 200 is above the knee for most instance sizes and Priya's instinct holds — but the mechanism is *saturation*, not *locking*, unless checkout is writing (order rows, inventory decrements) where real row contention is very plausible.

This matters because it's checkable and the two point at different fixes: `pg_stat_activity.wait_event_type` = `Lock` means genuine lock waits; `LWLock`, `IO`, or predominantly-null-and-CPU-pegged means saturation. MySQL equivalent lives in `performance_schema` / `sys.innodb_lock_waits`.

**And ask Priya what she actually looked at.** "That would produce exactly this curve" is either a strong piece of evidence — if she has DB-side dashboards showing the connection spike and wait events — or it's a plausibility argument about a curve neither of us has opened. If it's the former, H7 is legitimately leading on evidence and most of my caution evaporates. That question is free.

## The reasoning I'd flag

"One-line revert versus a rewrite" is a great reason to **try** it first. It is not evidence that it's **the cause**. Those come apart, and when they come apart quietly you get a fix that ships, a metric that partially recovers for an unrelated reason, and an investigation closed on the wrong root cause.

Also: nobody had enumerated that deploy's diff. Priya surfaced the pool change in conversation, which means the change list came from memory, not from reading it. A deploy with two known significant changes may have four. Reading the diff end-to-end is still the cheapest outstanding check, and it just demonstrated its own value.

## Predeclare the revert's outcomes, then close on the metric

The revert *is* a check. Write down what each result means before you ship it:

| Outcome | Reading |
|---|---|
| p99 → ~120ms and holds 24h | H7 leading; cache rivals weakened (masked, not cleared) |
| p99 → ~300–400ms | Both real — pool contention *and* a cache-side cost. Keep investigating |
| p99 unchanged | H7 contradicted. Back to the cache rivals and the null |
| p99 worse, or timeouts/errors rise | The 200 was load-bearing for the new cache-miss path. Revert the whole deploy |

That last row is why "one-line revert" isn't the same as "low-risk." If the cache's miss path holds connections longer than the old path did, someone may have raised the pool *because* of that — worth checking the commit message or asking the author, since a cache is supposed to *reduce* DB load and raising the pool 4x in the same deploy is a contradiction that has a story behind it.

**terminal_state: `underdetermined`. action_disposition: `authorized`** — proceed with the revert, canaried, on record that the diagnosis isn't established yet.

Close it when p99 is back at 120ms and stays there, not when the revert merges.


## verdict

_ungraded — open the rubric only after the run completes_
