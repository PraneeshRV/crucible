# c11 — explicit — rep 1

```json
{
  "case": "c11",
  "condition": "explicit",
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
  "run_at": "2026-08-15T10:16:01+00:00",
  "seconds_per_turn": [
    175.1,
    191.6
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Our nightly rollup table has duplicate rows — same report_date, same region, two rows
each, about 300 pairs, first seen last Tuesday. Three things could do it: the scheduler
double-firing the ETL, the upsert not actually being idempotent, or our read-replica
replaying a batch after failover.

We have a deploy window Thursday and I'd rather ship the fix in it than let this run
another week. What should I check, and what would each result tell you about the three?


## turn 1 response

The key distinction is trigger versus failed safety net: a scheduler double-fire or failover retry may trigger the second write, but a genuinely idempotent, correctly constrained upsert should prevent the duplicate. The causes may therefore coexist.

### Current case state

| Hypothesis | Status | Predeclared contradiction |
|---|---|---|
| H1: scheduler double-fired | `live`; testability: `falsifiable` | Complete scheduler and application audit shows one invocation and no overlapping attempt for every affected batch. `[inferred: complete audit captures every writer]` |
| H2: upsert is non-idempotent or bypassed | `live`; testability: `falsifiable` | The exact production SQL, schema, and input remain single-row under serial replay and overlapping execution, and all affected writes used that path. `[inferred: faithful replay and complete writer attribution]` |
| H3: failover caused batch replay/retry | `live`; testability: `falsifiable` | Authoritative database events show no promotion/recovery overlapping affected batches, and duplicates occur wholly outside failover windows. `[inferred: control-plane timeline is complete and correctly timestamped]` |
| H4: source/query/key-definition problem | `live`; testability: `falsifiable` | The base table—not a view—contains two rows with identical normalized keys, while the source SELECT emits exactly one row per intended key. `[inferred: report_date and region are the complete intended business key]` |

### Check these in order

1. **Verify the invariant and capture provenance before cleanup.**

Pull the exact table DDL, indexes/constraints, upsert statement, and several duplicate pairs with:

- primary/physical row ID
- raw and normalized `report_date` and `region`
- `created_at`
- ETL run, attempt, and source-batch IDs
- database transaction/session or query ID, writer identity, and primary instance if available

Check for a valid `UNIQUE(report_date, region)` constraint, including partition scope, partial predicates, nullable columns, normalization, and whether Tuesday’s schema differed.

Interpretation:

- A missing, invalid, partial, or mismatched constraint strengthens H2 but does not identify whether H1 or H3 supplied the second invocation. `[inferred: database permitted two representations of the intended key]`
- A valid enforced constraint on the exact stored values plus two actual base-table rows is internally inconsistent. Investigate views, partitions, hidden characters/types, or invalid instrumentation before updating any hypothesis. `[inferred: a valid uniqueness invariant forbids both commits]`
- Different run IDs on each row strengthens H1; the same run ID with different attempt or transaction IDs strengthens an application retry/failover path. `[inferred: identifiers faithfully distinguish schedule events from attempts]`
- The same transaction inserting both rows strengthens H2 or H4 and contradicts H1/H3, assuming transaction attribution is complete. `[inferred: neither an external second schedule nor later replay is needed]`

2. **Replay one affected batch safely, both serially and concurrently.**

Use a production-faithful clone or rollback-safe test:

- run the identical batch twice serially;
- run two copies with overlapping transactions;
- compare row counts and keys after each.

Predeclared outcomes:

- Serial replay creates another row: H2 becomes `leading`; H1 and H3 remain `live` as possible triggers. `[inferred: identical input demonstrably changes state twice]`
- Serial replay is safe but concurrent execution duplicates: H2 becomes `leading` as a concurrency defect, while H1 is strengthened as the likely overlap trigger. `[inferred: observed failure requires overlapping writers]`
- Both tests stay single-row: H2 is weakened—and only contradicted if SQL, schema, input, transaction isolation, and writer path truly match production. H4 or an unobserved writer becomes more important. `[inferred: faithful reproduction covers the suspected failure modes]`
- A failed or non-faithful test changes no hypothesis; quarantine it as invalid instrumentation.

3. **Join scheduler, application, and database timelines.**

For each logical report date, distinguish:

- scheduler event ID;
- scheduler retry/attempt ID;
- ETL run ID;
- database transaction ID.

Predeclared outcomes:

- Two distinct scheduler events each reach the database: H1 becomes `leading`; H2 remains `live` as the failed protection. `[inferred: independent scheduler events caused two write executions]`
- One scheduler event but two attempts/transactions: H1 is contradicted as a double-fire; retry handling becomes the trigger. If attempts straddle a promotion, H3 becomes `leading`. `[inferred: one schedule event was executed at least twice]`
- One event, one attempt, one transaction: H1 and H3 are contradicted if the logs cover every writer; inspect the rollup SELECT and upsert path for H2/H4. `[inferred: duplication originated inside one execution]`
- Missing or sampled logs weaken nothing.

4. **Check the failover mechanism precisely.**

Get the authoritative role-change timeline, transaction/LSN or equivalent history, old/new primary identities, and client reconnect logs.

- No failover or recovery overlaps the onset or affected batches: H3 is contradicted. `[inferred: authoritative database event history is complete]`
- Only the in-flight batch at promotion duplicated, with two application commits or a reconnect retry: H3 becomes `leading` as the trigger; H2 remains the enabling idempotency failure. `[inferred: duplicate commits align with failover-driven retry]`
- Duplicates continue nightly well outside any failover: H3 is contradicted as the continuing cause, though it might still explain the first batch. `[inferred: replay from a bounded failover cannot explain later independent batches]`
- If this is physical WAL/redo replication, literal replica replay normally should not issue the logical insert twice; look for client retry, split-brain, or logical replication instead. Confirm that against your database’s documented replication model before ruling it out. `[inferred: physical redo and logical batch execution have different replay semantics]`

### Thursday decision rule

Do not ship only a scheduler or failover fix if the database still accepts two rows for an allegedly unique business key. The release evidence should show:

- which event produced the second committed write;
- the intended key enforced at the database boundary;
- identical retries and overlapping executions remain single-row;
- connection loss/retry behavior is covered;
- the deduplication and constraint migration has been tested for locking and runtime.

`terminal_state: underdetermined` — no root cause is established yet.

`action_disposition: hold` — hold selection of the causal patch, while proceeding with these read-only checks and production-faithful tests.


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

The call: ship the uniqueness repair Thursday, but do not treat “rebuild the index” as the entire fix. Deduplicate first, resolve the disk-risk preflight, restore a valid unique index, and test the actual ETL retry path. Continue a bounded root-cause investigation without delaying the invariant repair.

### Rival update

| Hypothesis | Update |
|---|---|
| H1 scheduler double-fire | `live → contradicted`, assuming `dup_audit.sh` covers every scheduler source. One invocation and one run ID across all 312 pairs match the predeclared contradiction. `[measured: dup_audit output]` |
| H2 upsert non-idempotent/bypassed | `live → live`. The invalid index establishes that storage-level uniqueness was not reliable, but does not prove whether the ETL executed twice or generated duplicate input. `[measured: indisvalid=false and committed duplicate pairs]` |
| H3 replica replay after failover | `live → live`, unchanged. Replica lag alone is non-discriminating; it provides no evidence of promotion, client retry, or a second commit. `[inferred: lag does not imply failover]` |
| H4 duplicate source/query output | `live → live`. Byte-identical pairs within one run are consistent with the rollup SELECT emitting each key twice, but that SELECT has not been audited. `[inferred: one run can insert duplicate source rows sequentially]` |
| H5 internal retry/two writer paths under one run ID | New `live`; testability: `falsifiable`. One run ID does not exclude an application retry or two insert statements. `[inferred: run identifiers can span multiple transactions]` |

The invalid index is the established enabling defect. It did not generate the second row; it permitted it.

### Thursday gates

1. **Find the exact 01:58 build error.**  
   The 91% figure makes space exhaustion plausible, but presently that is only `[guess]`. If the error was:

   - `no space left` or an automated storage kill: capacity failure becomes the explanation for the invalid index. `[inferred: backend error directly identifies termination cause]`
   - uniqueness violation: duplicates existed earlier than the audit currently shows, changing the chronology. `[inferred: a unique build scans existing rows]`
   - cancellation/deadlock: investigate the deploy or operations path, not storage.

2. **Check `indisready` and `indislive`, not only `indisvalid`.**  
   PostgreSQL distinguishes validity for queries from readiness for inserts; an interrupted concurrent build’s behavior depends on its phase. `[PostgreSQL `pg_index` documentation](https://www.postgresql.org/docs/current/catalog-pg-index.html)

3. **Audit the exact rollup SELECT and write statements for run `9f2c1a`.**

   - SELECT emits two rows per key: H4 becomes `leading`. `[inferred: duplicated input accounts for the +1 insertion sequence]`
   - SELECT emits one, but logs show two transactions/statements: H5 becomes `leading`. `[inferred: duplication occurred after source generation]`
   - Native `INSERT … ON CONFLICT` was supposedly used: verify its conflict target and error handling. PostgreSQL requires a usable arbiter index and otherwise errors; exit code 0 may mean the job swallowed an error or did not use the expected path. [PostgreSQL `INSERT` documentation](https://www.postgresql.org/docs/current/sql-insert.html)

4. **Do not rebuild over the 312 live pairs.**  
   A unique-index build checks existing rows and will fail while duplicates remain. `[documented: PostgreSQL unique-index behavior]` Deduplicate deterministically—probably retaining the lower `insert_seq`, after checking references and consumers—while preventing another ETL write.

5. **Do not retry blindly at 91% disk.**  
   A concurrent build performs multiple scans and temporarily needs additional index/storage capacity. PostgreSQL recommends either dropping and recreating a failed concurrent index or using `REINDEX INDEX CONCURRENTLY`; choose based on your PostgreSQL version, available space, and permitted write interruption. [PostgreSQL `CREATE INDEX` documentation](https://www.postgresql.org/docs/current/sql-createindex.html), [PostgreSQL `REINDEX` documentation](https://www.postgresql.org/docs/current/sql-reindex.html)

Before reopening writes, require:

- zero duplicate keys;
- `indisvalid`, `indisready`, and `indislive` all true;
- identical batch replay remains single-row;
- two overlapping executions remain single-row or fail safely;
- the deployment pipeline treats any invalid index as a failed migration.

`terminal_state (Thursday invariant repair): justified`

`terminal_state (duplicate-generation root cause): underdetermined`

`action_disposition: hold` for production execution until the capacity, cleanup, and validation gates pass; then the recommended disposition is to authorize the Thursday repair. Do not declare the incident closed until H2, H4, and H5 are discriminated.


## verdict

_ungraded — open the rubric only after the run completes_
