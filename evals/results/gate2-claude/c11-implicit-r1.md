# c11 — implicit — rep 1

```json
{
  "case": "c11",
  "condition": "implicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "e7b9f29",
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
  "run_at": "2026-08-16T06:51:21+00:00",
  "seconds_per_turn": [
    142.8,
    150.5
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

Working directory has only `prompt.md` — no schema, ETL code, or logs — so everything below is a plan for you to run, and every outcome→meaning mapping is *predeclared*, not measured. SQL is Postgres-flavored; I flag where MySQL differs.

## First, a reframe that changes what the checks are for

**Duplicate rows require a necessary condition: no enforced unique constraint on the dedupe key at write time.** None of your three rivals can produce duplicates on their own if `UNIQUE (report_date, region)` is present and valid. That makes constraint state the thing to check first — it partitions the hypothesis space rather than scoring one hypothesis.

**Your rivals #1 and #2 are not competitors — they're trigger and absorber.** A scheduler double-fire only causes damage *because* the upsert didn't absorb it. So finding two scheduler runs on Tuesday night does **not** clear the upsert; it convicts both. This matters for Thursday: a scheduler-only fix leaves the absorber missing.

Two rivals worth adding before you start, because they're cheap to test and would make all three of yours wrong:

- **R4 — key drift.** The rows aren't actually duplicates on the real key: `region` differs by case/whitespace, or `report_date` is a `timestamp`/`timestamptz` and the two rows differ in the time component or by a timezone offset. Common, and consistent with a sudden onset after a library/config change.
- **R5 — one-off replay.** Someone ran a manual backfill or a recovery rerun last Tuesday and nothing is ongoing. Arithmetic hint: Tuesday was Aug 11, so nights 11–16 = 6 runs; 300 pairs ÷ 6 ≈ 50 regions/night. If your region cardinality is ~50, this is recurring nightly. If it's ~300, it's a single date and one-off. Check that before anything else.

## Checks, in order of decision value per cost

### A. Shape of the duplicate set (~1 min, highest value)

```sql
SELECT report_date, count(*) AS dupe_rows, count(DISTINCT region) AS regions
FROM rollup GROUP BY report_date
HAVING count(*) > count(DISTINCT region) ORDER BY report_date;
```

| Result | Reading |
|---|---|
| Exactly one `report_date` affected | R5 leading; a one-off event. Weakens #1/#2 as *ongoing* faults `[inferred: a persistent defect would recur nightly]` |
| Every date since Aug 11, ~equal counts | Structural and ongoing → #2 or R4 leading, #1 live |
| Every date since Aug 11 *including dates before Aug 11 that got reprocessed* | Backfill replay over history → R5 + #3 live |

### B. Are they actually duplicates? (~2 min)

```sql
SELECT a.ctid, b.ctid, a.report_date::text, b.report_date::text,
       quote_literal(a.region), quote_literal(b.region), a.* , b.*
FROM rollup a JOIN rollup b
  ON a.report_date = b.report_date AND a.region = b.region AND a.ctid < b.ctid
LIMIT 20;
```
Cast to `text` and `quote_literal` the key deliberately — display formatting hides sub-second components and trailing whitespace.

| Result | Reading |
|---|---|
| Keys byte-identical, **all measure columns identical** | Same input processed twice → #1 or #3 leading; #2 is the absorber that failed `[inferred]` |
| Keys byte-identical, **measures differ** | Two runs over *different source snapshots* → #1 (runs at different times) leading; #3 live; pure replay of one batch weakened `[inferred: a replayed identical batch yields identical measures]` |
| Keys differ at full precision (case, whitespace, time component) | **R4 leading, #1/#2/#3 all weakened** — and your Thursday fix is a normalization/migration, not a scheduler or upsert change |

### C. Constraint and index state (~1 min)

```sql
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'rollup'::regclass;
SELECT indexrelid::regclass, indisunique, indisvalid, indisready, pg_get_indexdef(indexrelid)
FROM pg_index WHERE indrelid = 'rollup'::regclass;
```

| Result | Reading |
|---|---|
| No unique constraint on `(report_date, region)` ever existed | Necessary condition satisfied → **#2 leading**; #1/#3 demoted to *triggers*, not root cause |
| Unique constraint exists on a **wider** key (`+source`, `+tenant`, or a surrogate id) | #2 leading via a specific mechanism: the upsert's conflict target never matches. Fix is the key definition |
| Unique index exists but `indisvalid = false` | A concurrent index build failed — pair with check G; likely a Tuesday migration |
| Valid unique constraint on exactly `(report_date, region)` **and** duplicates still visible | Contradicts all three rivals *on this table* → you are reading a view/union, or reading the replica. Go straight to F |

### D. Row provenance (~5 min)

```sql
SELECT xmin, ctid, etl_run_id, created_at FROM rollup
WHERE (report_date, region) IN (...one dupe pair...);
```
`xmin` is the inserting transaction id; equal `xmin` means *one transaction wrote both rows*. (MySQL: use your `batch_id`/`created_at`, or `SHOW BINLOG EVENTS`.)

| Result | Reading |
|---|---|
| Same `xmin` / same transaction | **#1 contradicted** — a single run inserted twice. Points at fan-out in the ETL's source SELECT (a join multiplying rows) plus a missing constraint → #2 leading `[inferred: two separate scheduler firings cannot share a transaction id]` |
| Different `xmin`, timestamps minutes apart | #1 leading — two firings, likely a race or a retry-on-timeout |
| Different `xmin`, timestamps ~24h apart or on a retry-backoff boundary | Retry/replay semantics → #1 (retry variant) or #3 |
| Distinct `etl_run_id` values per row | #1 leading, and the run ids let you pull both runs' logs directly |
| Identical `etl_run_id` on both rows | #1 weakened; #2 leading |

### E. Scheduler execution history (~5 min)

Pull the executions of the ETL job for each night since Aug 11 from the scheduler's own audit log (not the ETL's logs — you want the *firing* record, including cancelled/retried attempts).

| Result | Reading |
|---|---|
| Exactly one firing per night | **#1 contradicted** `[predeclared]`; #2/R4 carry the weight |
| Two firings per night since Aug 11 | #1 confirmed as trigger — **but #2 remains live and unabsolved** |
| One firing, but with an internal retry after a timeout | #1 in its retry form; the real defect is non-idempotent retry → #2 |

### F. Primary vs. replica, and the failover timeline (~10 min)

Run the count from check A **against the primary directly**, then confirm your replication type.

| Result | Reading |
|---|---|
| Primary clean, replica shows dupes | #3 leading — and there's nothing to fix in the ETL |
| Both show dupes identically | **#3 contradicted as a *read-side* effect** `[inferred: a replica cannot introduce rows the primary lacks under physical streaming replication]`. #3 survives only in its *write-side* form: a promoted replica accepted a replayed ETL batch |
| Replication is physical/streaming | #3's read-side form is mechanically near-impossible — demote unless you use logical replication or a restore-and-promote |
| Failover event log shows no failover on Aug 11 | **#3 contradicted** |

### G. Change catalog for Aug 11 (~10 min, do in parallel)

Deploys, schema migrations, scheduler config edits, infra/failover events, dependency bumps — anything timestamped Tuesday. Onset correlation is weak evidence alone but sharply reranks: a migration touching this table's indexes elevates #2/C; a timezone or date-library bump elevates R4; a scheduler config change elevates #1; a failover elevates #3. If *nothing* changed Tuesday, all five rivals get weaker and you should suspect a data-side change (a new region code, a source system emitting a second feed).

## Signature summary

| Rival | Confirming signature | Contradicted by |
|---|---|---|
| #1 scheduler double-fire | Two firings/night in scheduler audit; different `xmin`; differing measures | One firing/night (E); same `xmin` (D) |
| #2 non-idempotent upsert | No/wider unique constraint (C); same `xmin` with two rows (D) | Valid unique constraint on exactly the key (C) |
| #3 replica replay | Primary clean + replica dirty (F); failover logged Aug 11 (G) | No failover Aug 11 (G); identical dupes on primary (F) |
| R4 key drift | Keys differ at full precision (B) | Byte-identical keys (B) |
| R5 one-off replay | Single `report_date` affected (A) | Dupes on every date since Aug 11 (A) |

## What I'd actually ship Thursday

A, B, C, and D are under 15 minutes total and will very likely resolve this before Tuesday, so you should be deciding on evidence, not on this table. But if you run out of time:

The **unique constraint plus a genuinely idempotent write** is the only fix that neutralizes #1, #2, #3, and #5 simultaneously — it's correct regardless of which rival wins, which makes it the safe thing to ship under uncertainty. Sequence it as: dedupe existing rows → `CREATE UNIQUE INDEX CONCURRENTLY` → verify `indisvalid` → then point the upsert's conflict target at it. Don't ship the constraint and the ETL change in the same irreversible step; if the dedupe missed a case the index build fails and you want that to fail loudly and separately.

Two caveats: if check B comes back as **R4 (key drift)**, this fix is *wrong* — a constraint over an unnormalized key won't collide and you'd ship a no-op while believing you were done. And decide explicitly which row of each pair survives dedupe (latest ingest, or recompute from source) — plus check whether downstream reports summed both rows, because if measures differ you have published numbers to correct.

---

**Status:** `#1 live` · `#2 live` · `#3 live` · `R4 live` · `R5 live` — all `testability: falsifiable`, none observed; nothing has been measured from my side.
**terminal_state:** `underdetermined` — no check has run.
**action_disposition:** `hold` — yours to set. Shipping the constraint on Thursday without running A–D is `underdetermined + authorized`, which is a defensible call here given the fix is correct under four of five rivals; the one thing that would make it a wasted window is R4, and check B rules that out in two minutes.


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

## The call

**Rebuild the index, but not as the fix, and not alone.** The audit contradicts two of your three rivals cleanly — and it re-specifies the third into a mechanism the index rebuild doesn't address. Shipping a bare rebuild on Thursday would convert silent duplication into a hard nightly-job failure.

The remaining digging is ~30–60 minutes, not another week. You can still ship Thursday.

## What the evidence settled

**#1 scheduler double-fire — `contradicted`.** Predeclared in check D: *"same transaction → #1 contradicted."* All 312 pairs carry one `run_id`. The decisive part is `insert_seq` delta: since deltas are ≥1 by construction, a mean of **exactly +1.0** across 312 pairs means every pair is *adjacent* in insert order. A second firing or a replay re-inserts the whole batch, so each pair's delta would be ≈312, not 1 `[inferred: batch-sequential insertion]`. The copies were emitted back-to-back inside one pass.

**#3 replica replay — `contradicted`.** Predeclared in check F: dupes carry primary-side `run_id`s from a primary-side run; replica-2 being 4 minutes behind is read lag, which cannot inject rows. No failover is in evidence — lag isn't failover.

**#2 non-idempotent upsert — `leading`, but re-specified.** Cross-run idempotency was never exercised; only one run happened. The actual mechanism is narrower and worse:

> **F1 (new, `leading`): the source SELECT fanned out — it returned each `(report_date, region)` twice — and nothing enforced uniqueness to catch it.**

Byte-identical payloads plus adjacency is the signature of a join multiplying rows against a duplicated join partner, not of a rerun.

## The part that decides Thursday: what is the write statement?

The run **exited 0**. If the write were `INSERT ... ON CONFLICT (report_date, region) DO UPDATE`, an invalid index cannot serve as the arbiter, and the statement would have failed with *"no unique or exclusion constraint matching the ON CONFLICT specification"* `[inferred: arbiter inference requires indisvalid]`. It didn't fail. So the write path is almost certainly one of:

- `INSERT ... ON CONFLICT DO NOTHING` **with no conflict target** — needs no arbiter index, raises nothing, dedupes nothing. Reads like an idempotent upsert in review.
- `MERGE` (PG15+) — a fan-out source inserts both rows silently.
- plain `INSERT`, or an upsert keyed on a surrogate id that never collides.

**This is why the rebuild is a landmine.** Under every one of those, a valid unique index turns the next fan-out into a unique-violation that aborts the nightly rollup. You'd trade silent bad data for a missing report — defensible as a deliberate choice, bad as a surprise at 02:00.

**Falsifiable prediction, worth 30 seconds:** `indisready` will come back **false**. The build died at 01:58, two minutes *before* the run; had it been `indisready = true`, the invalid index would still have been maintained and would have blocked the second insert. It didn't `[inferred]`. If `indisready` returns **true**, my model is wrong and you should stop and re-derive.

## Two things in that output that don't add up

1. **A 7-day gap.** The index went invalid **Aug 4 01:58**; you first saw dupes **Aug 11**. The output never states run 9f2c1a's *date*. If it's the Aug 4 run, the dupes were created Aug 4 and merely *noticed* Aug 11 — "first seen" is an observation event, not a creation event. If it's the Aug 11 run, then six nights ran clean with an invalid index, which means invalidity is **not sufficient** and something else changed on Aug 11. These lead to different fixes. Get the date.
2. **"scheduler invocations in window: 1"** over a 12-night window, for a *nightly* job. Either the script is scoped to invocations that touched duplicate rows (a mislabeled line), or eleven nightly runs never fired — a second, separate incident. Until that's resolved, treat that line as **invalid instrumentation: it weakens nothing.** My contradiction of #1 rests only on the row-level evidence (shared `run_id`, adjacency), which is independent of the scheduler log.

## Before Thursday (~30–60 min)

| Check | What it settles |
|---|---|
| Date of run 9f2c1a; full invocation list, unscoped | Resolves the 7-day gap and the "1 invocation" anomaly |
| `grep` the ETL for the actual write statement | Whether the rebuild causes a nightly abort |
| `SELECT indisready FROM pg_index WHERE indexrelid = 'rollup_date_region'::regclass` | Confirms or breaks the mechanism above |
| Re-run the ETL's source SELECT for one affected `report_date`, `GROUP BY (report_date, region) HAVING count(*) > 1` | **The crux.** Returns 2 → fan-out is live and reproducible, and you can see which join |
| Does the ETL read its *source* from replica-2? | If yes, the 4-min lag is a live suspect: a partially-applied dimension update makes both old and new rows visible, matching twice |
| Any soft-deleted rows sharing a key with live rows? | See below — this can fail Thursday's build on its own |
| Disk headroom now | The build died at 91% full; it will die again |

**The soft-delete trap.** The table has `deleted_at`, and the index definition has **no `WHERE` clause**. If the ETL ever soft-deletes and re-inserts a `(report_date, region)`, a full unique index rejects the re-insert. Two consequences: the Thursday build may fail on historical soft-deleted rows that have nothing to do with your 312 pairs, and even after a clean build you may have installed a constraint that breaks normal reprocessing. It probably wants to be `... WHERE deleted_at IS NULL`. Check before you build, not during the window.

## Thursday plan

Three changes, shipped together, in this order:

1. **Dedupe the 624 rows.** Payloads are byte-identical, so the choice is free — keep the lower `insert_seq`.
2. **Fix the write path** to a real conflict-targeted upsert (or make the fan-out impossible in the source query — fork below).
3. **Rebuild:** `DROP INDEX CONCURRENTLY` the invalid one and recreate, or `REINDEX INDEX CONCURRENTLY` — with the partial predicate if step 0 says you need it. Verify `indisvalid` after; a concurrent build that fails leaves you exactly where you started. Confirm disk headroom first.

The fork on step 2:

- **Source SELECT still returns 2 rows/key** → fan-out is a live defect. Fix the query (dedupe the join partner or `GROUP BY`) *and* fix the write path. The index is then a backstop, not the fix.
- **Source SELECT returns 1 row/key now** → the fan-out was transient, which fits the replica-lag story. The index plus a genuine upsert is the durable fix, but pin the ETL's source reads to the primary or add a lag guard, or it recurs on the next lag event.

**Do not ship only the rebuild.** It leaves the row-multiplying defect in place and arms it to page you instead.

One data-correctness item independent of all this: payloads are identical, so nothing was summed *inside* the rollup — but any downstream consumer that aggregates over this table has been double-counting the affected 312 keys since the run. Worth checking whether those numbers were published.

---

**Status:** `#1 contradicted` · `#3 contradicted` · `#2 leading (re-specified)` · `F1 leading` · `R4 contradicted` (payloads byte-identical) · `R5 weakened` (single run, but recurrence depends on whether the fan-out is live). Scheduler-log line **quarantined: invalid instrumentation**.
**terminal_state:** `underdetermined` — the mechanism is well-constrained, but the write path and the fan-out's liveness are both load-bearing for the fix and both unmeasured.
**action_disposition:** `hold` on the bare rebuild; the three-part change is `authorized` once the source-SELECT check comes back either way.


## verdict

_ungraded — open the rubric only after the run completes_
