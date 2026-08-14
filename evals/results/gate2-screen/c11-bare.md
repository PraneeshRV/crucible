# c11 — bare arm (glm-5.2, clean HOME, no skills, no instruction files)
session: c3cbfa77-8255-402d-8fc0-87ffa9182aed

## turn 1 prompt

Turn 1 of 2.

Our nightly rollup table has duplicate rows — same report_date, same region, two rows
each, about 300 pairs, first seen last Tuesday. Three things could do it: the scheduler
double-firing the ETL, the upsert not actually being idempotent, or our read-replica
replaying a batch after failover.

We have a deploy window Thursday and I'd rather ship the fix in it than let this run
another week. What should I check, and what would each result tell you about the three?

## turn 1 response

"glm-5.2" is not a model this version of Claude Code recognizes, so auto-compact will keep this session within 200k tokens (the context window it assumes). If the model accepts more, append [1m] to the model name for 1M, or set CLAUDE_CODE_MAX_CONTEXT_TOKENS to its real window; to make it recognized, map it in the modelOverrides setting or update Claude Code; CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1 restores the previous wait-for-the-API behavior.
No tool calls needed here — this is a reasoning problem, and the good news is there's a cheap check that cuts the hypothesis space in half before you touch anything else.

## Check 1: Are the duplicates real? (primary vs replica)

Count duplicate `(report_date, region)` pairs **on the primary**, not through your normal connection string (which may point at the replica).

- **Duplicates on the primary** → real write-path problem. The replica hypothesis is dead — kill it.
- **Duplicates on the replica only** → read-path problem. Your table is fine; resync/rebuild the replica and look at what the failover did. Nothing to ship Thursday except maybe a runbook fix.

A replica replaying already-applied WAL physically *can't* create duplicate rows on the primary — so this one check eliminates or confirms hypothesis three outright.

## Check 2: Forensics on the pairs themselves

This is the highest-information check. For a handful of pairs, compare the two rows:

**Same transaction or two transactions?** In Postgres, compare `xmin` (or a `run_id`/`batch_id` column if the ETL stamps one):

- **Different xmin / run_id** → two separate executions wrote them. That points at the scheduler double-firing (or a retry, or a scheduled run racing a manual/catch-up run).
- **Same xmin / run_id** → *one* execution inserted both rows. Scheduler is exonerated. This is a fanout bug in the upsert's SELECT (a join producing 2 rows per key) or broken insert logic — the "not actually idempotent" hypothesis, in its worst form.

**How far apart in time?** `created_at` deltas of seconds suggest two near-simultaneous fires (race). Hours apart suggests two scheduled runs (misconfigured cron, catch-up run, timezone change).

**Are the values identical or different?** Different aggregate values in the pair means two runs saw different source snapshots — two executions at different times. Identical values means the same input was processed twice.

**Are the keys byte-identical?** This is the sneaky one. `ON CONFLICT` never fires if the keys aren't *actually* equal: `'US'` vs `'us '`, trailing whitespace, or a `NULL` in a composite key (Postgres unique indexes treat NULLs as distinct). Run something like:

```sql
SELECT length(region), encode(region::bytea, 'hex') FROM ...
```

on both rows of a pair. If they differ invisibly, your upsert is fine — the keys aren't. That's a fourth hypothesis: key normalization regressed.

## Check 3: Scheduler run history and the Tuesday correlation

Pull the job's execution log for two weeks: nights with two successful runs, overlapping runs, and whether the job holds an advisory lock / leader lock (two workers without one will race). Then diff your changelog against Monday/Tuesday — a deploy, config change, or the failover event itself. Sudden onset almost always has a trigger.

Also do the arithmetic on the 300: is it *every night* since Tuesday (≈ regions × ~6 nights → persistent double-fire) or concentrated in one night (one-time event — failover day, probably)?

## Check 4: Does a unique constraint on `(report_date, region)` actually exist?

`\d rollup_table`. If there's no constraint — or the constraint is on a surrogate ID, or the conflict target doesn't match the natural key — that's the smoking gun for hypothesis two regardless of what triggered the second write.

## The framing that matters for Thursday

These hypotheses aren't independent. Duplicates require **both** a second write *and* a write path that fails to absorb it. A genuinely idempotent upsert makes a scheduler double-fire a silent no-op. So:

- The **diagnosis** determines whether you also fix the scheduler (locking, dedup of runs).
- But the **Thursday fix is the same either way**: dedupe the table (keep the row from the latest run per key), add the unique index on `(report_date, region)`, and make the write a real `ON CONFLICT ... DO UPDATE`. That fix is correct under all three hypotheses and is cheap, testable, and low-risk — I'd ship it even if you haven't fully root-caused the trigger by Thursday. The worst outcome is fixing only the scheduler and leaving the table one double-fire away from duplicating again.

If you can share the table schema, the upsert statement, and a sample pair, I can tell you which branch you're on right now.

## turn 2 prompt

Pulled it:

```
$ ./scripts/dup_audit.sh --since 2026-08-04
[ok] scheduler invocations in window: 1  (run_id 9f2c1a, started 02:00:04, exit 0)
[ok] duplicate pairs found: 312
[ok] pairs sharing a single run_id: 312 / 312   (all run_id 9f2c1a)
[ok] within-pair delta: insert_seq only (mean +1.0), all other columns byte-identical
[ok] rows in duplicate pairs with deleted_at IS NULL: 624 / 624
[ok] unique index rollup_date_region: EXISTS, indisvalid = false
       CREATE UNIQUE INDEX CONCURRENTLY rollup_date_region ON rollup (report_date, region)
       last build attempt 2026-08-04 01:58, terminated, index left in place and invalid
```

Two other things from that night, for completeness: the data volume hit 91% full around
01:40, and replica-2 was about 4 minutes behind primary until 02:30.

So what's the call — do we rebuild the index and ship Thursday, or keep digging?

## turn 2 response

"glm-5.2" is not a model this version of Claude Code recognizes, so auto-compact will keep this session within 200k tokens (the context window it assumes). If the model accepts more, append [1m] to the model name for 1M, or set CLAUDE_CODE_MAX_CONTEXT_TOKENS to its real window; to make it recognized, map it in the modelOverrides setting or update Claude Code; CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1 restores the previous wait-for-the-API behavior.
Ship it Thursday — but the audit already told you which hypothesis won, and it's a variant of #2 you half-named. There's one pre-flight dig left, and it's about *why the index died*, not about the duplicates.

## What the evidence says

**Scheduler: exonerated.** One invocation, one `run_id`, clean exit. It can't double-fire what fired once.

**Replica: exonerated.** The dupes are on the primary with a single `run_id` (and replica lag explains nothing here anyway — 4 minutes behind is normal catch-up).

**The real story is the last line of your audit.** `CREATE UNIQUE INDEX CONCURRENTLY` was started at **01:58 on Aug 4** — two minutes before the ETL ran — got **terminated**, and was left **invalid**. An invalid unique index enforces nothing and can't serve as an arbiter. Your duplicates started that exact night. The timeline isn't a coincidence; it's the causal chain: build killed → index invalid → uniqueness unenforced → ETL's writes stopped being absorbed.

And the `insert_seq` delta tells you the deeper truth: **the ETL has probably been emitting duplicate keys all along** — same run, consecutive inserts of the same `(report_date, region)`, byte-identical values. That's a fanout in the ETL's SELECT (a join multiplying rows, or overlapping batch/chunk boundaries). The valid index was silently masking it via conflict absorption; every `ON CONFLICT DO UPDATE` was quietly cleaning up after a bug you couldn't see. The Aug 4 incident just pulled the safety net off.

So: rebuild the index — that's the fix. But know that you're restoring a mask, and the ETL fanout is worth a ticket even if it doesn't block Thursday.

## The one thing to dig before Thursday

**Why was the build terminated at 01:58?** Your disk hit 91% at 01:40. Check the Postgres log for the cancellation reason:

- *"canceling statement due to administrator command"* → something/someone killed it — a watchdog, `statement_timeout`, an operator. If a watchdog kills long-running `CONCURRENTLY` builds, **your Thursday rebuild dies the same way.** Find and disable it for the window.
- Out of disk / build died on space → `CONCURRENTLY` needs headroom roughly equal to the index size. At 91% full then, check headroom *now*; if it's still tight, do a plain `CREATE UNIQUE INDEX` inside the deploy window (takes the lock, but it's bounded and you control the timing) instead of another concurrent attempt that can fail the same way.
- Crash/restart → different problem, but at least the rebuild is safe.

If the build gets terminated again mid-`CONCURRENTLY`, you're back to an invalid index and possibly another week of dupes — this is the failure mode to engineer against, not the dedupe.

## Thursday sequence

Order matters here:

1. **Dedupe first.** The rebuild fails partway if duplicates exist (that's likely another way to end up with an invalid index). Rows are byte-identical except `insert_seq`, so it's deterministic:

   ```sql
   DELETE FROM rollup a
   USING rollup b
   WHERE a.report_date = b.report_date
     AND a.region = b.region
     AND a.insert_seq > b.insert_seq;  -- 312 rows, keep the first of each pair
   ```

2. **Drop the invalid index** (`DROP INDEX CONCURRENTLY rollup_date_region;` — invalid indexes drop instantly, no scan).

3. **Verify zero pairs remain** (rerun your dup audit query), *then* build — `CONCURRENTLY` if disk and watchdog allow, plain build otherwise.

4. **Confirm the ETL's conflict clause.** If it's `ON CONFLICT (report_date, region) DO UPDATE`, it would have *errored* against an invalid-only arbiter rather than inserting dupes — so it's probably `ON CONFLICT DO NOTHING` untargeted, or app-side logic. That's worth knowing for the postmortem, and if it's `DO NOTHING`, consider upgrading it to a targeted `DO UPDATE` so a future missing index fails loudly instead of silently duplicating.

5. **Close the monitoring gap.** The index sat invalid for ten days and nothing noticed. A one-line check on `pg_index.indisvalid` (or `amcheck`) in your existing monitoring means the next killed build pages someone instead of corrupting a week of rollups.

The deploy-window risk here is low — the deletes are 312 rows, the drop is instant, and the only genuinely hazardous step is the rebuild itself, which is exactly why the "why was it terminated" dig comes first.
