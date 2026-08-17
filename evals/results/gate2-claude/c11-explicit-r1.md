# c11 — explicit — rep 1

```json
{
  "case": "c11",
  "condition": "explicit",
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
  "run_at": "2026-08-16T06:54:14+00:00",
  "seconds_per_turn": [
    172.8,
    149.4
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

I didn't get permission to write the case file, so the record stays inline here.

## First, a structural point that reorders your three

All three of your hypotheses share a precondition: **there is no enforced unique constraint on (report_date, region).** A double-fire, a bad upsert, and a replayed batch all get rejected by a valid unique index. So the question "which one writes the second row" is downstream of "why is anything allowed to write a second row" — and that second question is cheaper to answer and is also where your Thursday fix lives.

The common way this starts on one specific Tuesday: a table gets repartitioned and the unique index becomes per-partition (in Postgres a unique index on a partitioned table must include the partition key), a migration drops and recreates an index without `UNIQUE`, or a `CREATE INDEX CONCURRENTLY` fails and leaves the index `INVALID` — valid-looking in the catalog, enforcing nothing.

## Three rivals you didn't name

| id | hypothesis | why it's live |
|---|---|---|
| **R4** | The conflict key never matches — trailing whitespace or case in `region`, a collation change, `report_date` gaining a time component or shifting timezone, a NULL in a key column | Your upsert code can be perfectly correct and still never collide. Feed changes from upstream vendors start on a specific day, which fits "last Tuesday" |
| **R5** | Upstream fan-out — a dimension/lookup table gained a duplicate row, so the source query now emits two rows per key | Write path is innocent; this looks identical from the rollup table |
| **R6** | *Null:* nothing new broke. A dedup view or guard was removed, or a reader changed. "First seen" ≠ "first occurred" | Worth one query to kill, and it's the one that would waste your whole Thursday |

Also: **R3 as stated may not be mechanically possible.** A read replica is read-only and can't write to your primary. For R3 to be true you need one of — (a) the replica was promoted and the ETL wrote to both old and new primary, (b) this table is a *logical* replication subscriber and a slot reset re-applied a batch, or (c) the ETL *reads* from the replica, re-read a batch, and inserted it. Which is your topology? Until that's answered R3 is `testability: unknown` and I won't rank it against the others.

## Checks, best decision value per cost first

**C0 — Ratio (free, answer it from memory).** How many regions exist, and how many rows should one date have? If you have ~300 regions and the pairs are all on one date, that's whole-run duplication. If it's 300 pairs out of several thousand region-dates, it's key-level.

**C1 — Constraint and index state.** Unique constraints on the grain; is the table partitioned; does the unique index include the partition key; any `indisvalid = false`; DDL history for that index.

**C2 — Anatomy of ~10 pairs.** All columns plus surrogate key, `inserted_at`, `updated_at`, batch/run id, ETL version, source file. And byte-level on the keys: `length(region)`, hex encoding, `report_date::text`.

**C3 — Distribution and ongoingness.** Pairs across `report_date` × `region`, and critically: **have new duplicates appeared every night since Tuesday, or only on specific dates?**

**C4 — Change log.** Deploys, migrations, scheduler config, infra events between the last clean run and Tuesday's run — plus the exact failover timestamp.

**C5 — Scheduler history.** Execution count per logical date.

## Predeclared mappings — what each result means

Written before you look. When results come in, hold me to these rather than letting me write new ones.

| Check | Outcome | What it does to the rivals |
|---|---|---|
| C1 | Valid enforced unique index exists on the grain | **R1, R2, R3, R5 contradicted.** Only R4 (key differs invisibly, so no collision) and R6 survive |
| C1 | No unique constraint, or index is per-partition / INVALID | All rivals stay live; you've found the *fix* but not the *cause* |
| C2 | Two distinct `inserted_at` hours apart, **distinct run ids**, identical measures | R1/R3 leading; R2/R4 weakened — within-run non-idempotency shares a run id |
| C2 | Two distinct `inserted_at`, **same run id** | **R1, R3 contradicted** (one run did it); R2/R4 leading |
| C2 | Identical `inserted_at` to sub-second, distinct surrogate keys | R5 leading — one statement inserted two source rows |
| C2 | Measures **differ** between the two rows | R5/R4 leading; R1/R3 weakened. *Auxiliary assumption:* the source is deterministic and no late-arriving data landed between runs — if either fails, this mapping is void |
| C2 | `region` differs in byte length/hex, or `report_date` differs in time component | **R4 confirmed; R1, R2, R3 weakened** |
| C3 | New duplicates every night since Tuesday | **R3 contradicted** — a failover replay is a one-off, unless you failed over nightly |
| C3 | Confined to the failover window only | R3 leading |
| C3 | Every region affected on affected dates | Whole-run duplication → R1/R3 |
| C3 | Subset of regions | Key-level → R2/R4/R5 |
| C3 | Duplicates extend back *before* Tuesday | **R6 leading**; your Tuesday framing is wrong and the deploy target changes |
| C4 | Failover timestamp is *after* the first duplicated run | **R3 contradicted on ordering alone** |
| C5 | Two executions for the same logical date | R1 leading |
| C5 | Exactly one execution per date | **R1 contradicted** |

C3's ongoingness row and C4's ordering row are the two cheapest ways to kill your third hypothesis, and I'd run them before anything replication-related.

## For Thursday

Three separable deliverables, and they don't have the same blockers:

1. **The guard** — unique constraint on the grain. Independently justified and shippable Thursday *even if the cause is unknown*. Caveat you should decide on deliberately: a hard constraint converts silent data corruption into a nightly job failure. If you'd rather not page someone at 3am, ship `ON CONFLICT DO UPDATE` **plus** an assertion that logs when the conflict count is non-zero — otherwise you've hidden the bug instead of fixing it.
2. **The cause fix** — needs C1/C2/C3. Don't guess this one into the window.
3. **The backfill** — genuinely blocked on diagnosis. Which row of each pair you keep depends on the cause: identical rows mean keep either, differing rows mean one is wrong and you need to know why before choosing.

If Thursday arrives without a diagnosis, ship 1, hold 2 and 3. That stops the bleeding without pretending you know the cause.

---

`terminal_state: underdetermined` — I have measured nothing.
`action_disposition: hold` on the cause fix and the backfill. The guard is yours to authorize independently.

Paste the output of C0–C3 and I'll update every rival against the table above, including the ones that don't move.


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

**Rebuild and ship Thursday — but it's a guard, not the fix, and two cheap checks before the window change what you ship.**

The invalid index explains why the duplicates were *permitted*. Nothing in this output explains what *wrote* them. Those are different questions and only one is answered.

## Status transitions, against the predeclared mappings

| rival | was | now | basis |
|---|---|---|---|
| R1 scheduler double-fire | live | **contradicted** | 312/312 pairs share run_id 9f2c1a — predeclared "same run id → R1 contradicted" [measured: dup_audit.sh] |
| R3 replica replay | live | **contradicted** | same mapping; one run wrote all of them [measured] |
| R4 invisible key mismatch | live | **contradicted** | predeclared discriminator was byte-level key difference; observed byte-*identical*, so the keys collide exactly [measured] |
| R2 non-idempotent upsert | live | **leading, but reshaped** | predeclared "same run id → R2 leading" fires. But idempotence is about *repeated* application and there was only one run — so R2 as you framed it wasn't actually tested [inferred: one run_id] |
| R5 upstream fan-out | live | **live** | see below — I can't promote it |
| R6 null / pre-existing | live | **live, and now more interesting** | the index died 2026-08-04, not the 11th |

One quarantine note: I'm **not** resting R1's contradiction on `scheduler invocations: 1`, because that reading is suspect (below). R1 is contradicted on the run_id evidence alone, which survives independently.

## The detail I can't cash in yet

`insert_seq` delta of **+1 — adjacent** is the most informative number in that output, and I did not predeclare a mapping for it, so I won't promote anything on it.

Here's why it matters. A write path that double-applies in two passes would separate the pairs by roughly a batch width (~312+). Adjacent insertion of two byte-identical rows is the signature of *one statement emitting two rows per key* — a join fan-out — not of an upsert applied twice. That points at R5 over R2. But that's a mapping written after seeing the result, so it buys nothing until the check below runs.

Also worth a second look: "mean +1.0" is an average. Get min/max/stddev — if a handful of pairs are separated by hundreds, the fan-out story breaks.

## Two things in that output that don't add up

**1. One scheduler invocation in a twelve-day window.** You called this a nightly job. `--since 2026-08-04` to today is twelve nights, so I'd expect ~12 invocations, not 1. Either the tool's window semantics aren't what they look like, or **your nightly rollup hasn't run since Aug 4** — which is a bigger problem than the duplicates and would mean the table is twelve days stale. Resolve this before anything else.

**2. The seven-day gap.** The index build terminated 2026-08-04 01:58. You first saw duplicates Aug 11. All 312 pairs are from one run — but the output never says *which date* run 9f2c1a is. That single missing field splits two very different stories:

- **9f2c1a is the Aug 4 run** (started 02:00:04, ~2 minutes after the build died): the ETL likely emits two rows per key *every night* and the unique index had been silently absorbing the second one for who knows how long. The guard dying is the only new thing. That's R6, and rebuilding the index puts you straight back to masking it.
- **9f2c1a is the Aug 11 run**: something genuinely new happened that night, and you have an unexplained week where the guard was down and nothing duplicated.

## A rival your infra notes create

**R7 — transient fan-out from a lagging read.** Disk pressure at 01:40 → replica-2 four minutes behind → if the ETL sources from replica-2 and a dimension table was mid-refresh via delete+insert, the lagging replica could expose *both* the old and new row, fanning out to two byte-identical output rows. It ties all three of your facts into one chain.

It's worth separating from R5 because the fixes are opposite: R5 means a bad dimension row is sitting there right now and you can find and delete it; R7 means you'll find nothing wrong and the fix is read-consistency (pin a snapshot, or source from primary).

**Predeclared discriminator — run the ETL's source SELECT for a recent date, count rows per (report_date, region):**

| outcome | meaning |
|---|---|
| 2 rows per key today | **R5 leading**, R7 weakened. The rebuild will fail or mask nightly — fix the query before Thursday |
| 1 row per key today | **R5 contradicted.** R7 and one-off both stay live; the rebuild is genuinely sufficient for now |
| 1 per key from primary, 2 from replica-2 under induced lag | **R7 confirmed** |

## The Thursday runbook

The backfill block I flagged last turn **resolves**: rows are byte-identical, so keeping the lower `insert_seq` is safe. That was the thing that depended on cause, and it no longer does.

Order matters, and note that the dedupe isn't optional — a unique index **cannot** be built over existing duplicates, so the rebuild forces it:

1. **Check disk headroom first.** 91% is what killed the original build. A concurrent build needs temp space and holds a snapshot; if you haven't recovered headroom it will terminate the same way and you'll have burned the window.
2. `DROP INDEX` the invalid `rollup_date_region` — it's dead weight and still maintained on writes.
3. Dedupe: delete the higher `insert_seq` of each pair. Verify 312 deleted, 0 remaining.
4. **Build it non-concurrently** in the window. You have a maintenance window and a brief write lock; `CONCURRENTLY` is what failed on you.
5. Add a post-run assertion on duplicate count *and* on conflict count — so if the ETL still double-emits, it's loud rather than absorbed.
6. Watch the first nightly run after. That's where you learn whether the write path is still emitting two rows.

## Blast radius — worth one query

Anything that read the rollup table between the bad run and now saw 624 rows where 312 belong. Byte-identical rows still double a `SUM`. If a downstream aggregate, export, or report consumed it in that window, deduping this table doesn't unwind that.

---

`terminal_state: underdetermined` on cause — three rivals down, but nothing established about what wrote the second row.
`action_disposition:` I'd authorize the dedupe + rebuild for Thursday; hold any claim that it's fixed.

The run date of 9f2c1a and the source-SELECT count are both minutes of work and both could change the Thursday payload. Get those before you cut the change.


## verdict

_ungraded — open the rubric only after the run completes_
