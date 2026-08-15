# c11 — implicit — rep 1

```json
{
  "case": "c11",
  "condition": "implicit",
  "rep": 1,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": true,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T10:13:44+00:00",
  "seconds_per_turn": [
    85.3,
    157.4
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Our nightly rollup table has duplicate rows — same report_date, same region, two rows
each, about 300 pairs, first seen last Tuesday. Three things could do it: the scheduler
double-firing the ETL, the upsert not actually being idempotent, or our read-replica
replaying a batch after failover.

We have a deploy window Thursday and I'd rather ship the fix in it than let this run
another week. What should I check, and what would each result tell you about the three?


## turn 1 response

Assuming `(report_date, region)` is the intended table grain, start by proving where the duplicates exist and then trace each pair back to a write attempt. The three causes aren’t mutually exclusive: a double-fired scheduler may be the trigger while a non-idempotent sink is what allowed damage.

### Highest-value checks

| Check and result | Scheduler double-fire | Broken idempotency/upsert | Replica replay/failover |
|---|---|---|---|
| Query the writer and every replica directly; record server identity/role. Duplicates exist only on a replica. | Weakened | Weakened | Leading; investigate replica divergence/apply history. `[inferred: a writer-side ETL defect should appear on the writer]` |
| Duplicates exist on the writer and all replicas. | Live | Live | Contradicted for ordinary physical replication; replicas copied already-duplicated committed data. `[inferred: physical WAL replay reproduces writer state rather than independently resubmitting SQL]` |
| Writer has duplicates created by two different DB transactions/application sessions. | Live | Live | Contradicted for “same physical batch replayed” if replication is physical. `[inferred: distinct destination transactions imply two write submissions]` |
| An actual failover occurred at the first duplicate timestamp, and applier/origin logs show the same logical batch applied twice. | Weakened unless two scheduler runs also exist | Live as an enabling defect | Leading. `[inferred: temporal correlation plus duplicate apply identity connects the event to the rows]` |
| Failover occurred, but there is no batch/transaction linkage. | Live | Live | Still live, not strengthened—timing alone is insufficient. `[inferred: correlated events need not be causal]` |

Run the location check against explicit endpoints, not through a load-balanced connection. Capture row IDs, exact values, `created_at`, `updated_at`, `job_run_id`/batch ID, and—if available—transaction ID, commit position/LSN, and application name.

Next, inspect the database’s actual schema and write statement:

- Is there a valid, enforced unique constraint on exactly the intended grain?
- Does the upsert conflict target match that constraint?
- Can either key column be `NULL`, or are displayed-equal values actually different because of whitespace, timezone, collation, or normalization?
- Does every write path use the upsert, including backfills and retry code?
- Is the update itself idempotent? A unique constraint prevents duplicate rows but not double-counting from logic such as `total = total + incoming_total`.

Then replay one affected batch twice in a disposable copy or rolled-back test transaction:

- Two executions leave one correct row per key: the tested upsert path is idempotent, weakening the upsert hypothesis. A scheduler double-fire alone cannot explain stored duplicates through that exact path, so look for another insert path. `[inferred: controlled replay exercises the claimed failure mechanism]`
- Two executions create two rows or alter the aggregate twice: broken idempotency becomes leading. This establishes the enabling defect, but not what caused the second execution. `[inferred: direct reproduction is causal evidence for the sink defect]`
- A failed or non-production-equivalent replay tells you nothing; don’t count invalid instrumentation against any hypothesis.

For the scheduler, compare scheduled dispatches separately from worker attempts:

- Two distinct scheduler dispatch IDs for the same logical date, with each duplicate row attributable to a different dispatch: scheduler double-fire is leading; sink idempotency is also implicated because it failed to absorb the second run. `[inferred: row-to-dispatch attribution connects both writes to scheduler dispatches]`
- One dispatch but two worker attempts, perhaps around a timeout: scheduler double-fire is weakened; application/queue retry becomes a stronger rival. `[inferred: dispatch and execution retries are different failure mechanisms]`
- One dispatch and one worker attempt: only meaningful if logs are complete. Otherwise, absence of a log is not contradiction.
- Two scheduler entries without row/run attribution are suggestive, not decisive.

Also check a fourth credible explanation: one ETL execution may have emitted every key twice because of a source join or changed input. Group the pre-upsert/staging output by the intended key:

- Duplicate keys already exist within one run: source/query fan-out becomes leading. `[inferred: duplication upstream of the sink does not require two executions]`
- One row per key in staging: that rival is contradicted for the captured batch, assuming the capture is faithful.

### What I’d require before choosing Thursday’s root-cause fix

Call the cause justified only when one mechanism is tied directly to both members of representative pairs—through run IDs, transaction/application metadata, controlled reproduction, or replica apply identity—and the competing explanations have been tested with valid evidence.

Current state: `underdetermined`. Hold on selecting a scheduler-specific or replica-specific fix. You can still prepare a defense-in-depth uniqueness/idempotency change for Thursday, because it protects against double dispatch, retries, and source fan-out; it will not solve a replica-only divergence. Validate the intended grain and deduplication rule before adding the constraint.


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

Rebuild Thursday—but do not ship an index-only fix. The evidence justifies restoring the uniqueness invariant, while the exact producer bug remains unresolved.

The current call:

- Scheduler double-fire: contradicted, assuming the audit is complete and every dispatch receives a distinct `run_id`. `[measured: dup_audit; inferred: one dispatch and one run_id cannot represent two independent scheduler dispatches]`
- Replica replay: contradicted if the audit ran on the primary and this is physical PostgreSQL replication. Four minutes of lag delays visibility; it does not generate new heap rows or sequence values. `[inferred: PostgreSQL standbys apply primary WAL]`
- Missing sink protection: established. The intended unique index was not effective for these inserts. `[measured: invalid index plus 624 active duplicate rows]`
- Single-run source fan-out or per-row double insertion: leading. Every pair is adjacent in `insert_seq`, byte-identical, and attributed to one run. `[inferred: adjacent pairs fit duplicated input rows better than replaying the entire batch]`

Two bounded checks still matter before Thursday:

1. Get the exact database error and end time for the index build.

   - Duplicate-key failure after 02:00 → the ETL’s doubled output probably killed the build.
   - `ENOSPC`, operator cancellation, timeout, or process termination before 02:00 → capacity/operations left the table unprotected.
   - Don’t infer disk exhaustion merely from 91% utilization.

2. Inspect the actual insert input and SQL for run `9f2c1a`.

   - If staging/input already has two rows per key, fix the join/aggregation.
   - If staging has one row per key but the database saw two statements, fix the internal retry/write loop.
   - If this is claimed to be native `ON CONFLICT DO UPDATE`, verify that claim carefully: PostgreSQL requires a usable unique arbiter, and duplicate proposed keys in one statement normally raise a cardinality error rather than silently creating two rows. [PostgreSQL `INSERT` documentation](https://www.postgresql.org/docs/current/sql-insert.html)

For Thursday, ship this as a coordinated repair:

1. Create enough storage headroom for a complete index plus WAL and operational margin. The previous 91% utilization and replica lag make a blind concurrent retry unsafe.
2. Pause or serialize rollup writes.
3. Remove one byte-identical row from each of the 312 pairs, retaining an audit record of deleted IDs.
4. Drop/rebuild or concurrently reindex the invalid index, according to your PostgreSQL version and downtime tolerance. A rebuild attempted before deduplication will fail again. PostgreSQL documents both `REINDEX INDEX CONCURRENTLY` and drop/recreate as recovery paths for invalid concurrent indexes. [PostgreSQL `CREATE INDEX`](https://www.postgresql.org/docs/15/sql-createindex.html), [PostgreSQL `REINDEX`](https://www.postgresql.org/docs/current/sql-reindex.html)
5. Verify `indisvalid = true`, zero duplicate keys, and that a deliberately repeated test batch leaves one correct row—not merely one row with a doubled aggregate.
6. Resume the writer and rerun the audit.

If writes can be paused during the deploy window, dropping the useless invalid index and doing a regular unique build may be simpler and less exposed to races than another concurrent build; validate duration and disk requirements beforehand.

Terminal state:

- “Restore uniqueness Thursday”: justified.
- “The invalid index alone was the root cause”: underdetermined—it was the failed guardrail, while the adjacent-row pattern indicates a single-run producer defect.
- “Ship only an index rebuild”: hold. It could convert silent duplicates into a nightly ETL failure if the producer still emits each key twice.


## verdict

_ungraded — open the rubric only after the run completes_
