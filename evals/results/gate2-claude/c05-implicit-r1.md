# c05 — implicit — rep 1

```json
{
  "case": "c05",
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
  "run_at": "2026-08-15T15:43:10+00:00",
  "seconds_per_turn": [
    126.3,
    97.3
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

We're seeing 3 corrupted rows per million in the analytics warehouse. It could be the
ingestion job's batch boundary handling, or a known driver bug in the Parquet writer,
or upstream bad data we're faithfully recording.

Reproducing it means replaying six weeks of raw events through a staging warehouse -
roughly $400 in compute and two days. The corrupted rows are dropped by every
downstream consumer already.

Where does that leave us?


## turn 1 response

## Short answer

The replay is the wrong thing to buy, but not because $400 is too much. It's because it probably doesn't discriminate.

All three of your hypotheses predict the same replay outcome: corruption reproduces. A batch-boundary bug reproduces (same batch geometry). A writer bug reproduces (same driver, same data). Faithfully-recorded bad data reproduces (that's what "faithful" means). So the modal result of two days and $400 is that you're exactly where you started, having confirmed only that the defect is a deterministic function of the input. `[inferred: each hypothesis is a deterministic input→output mechanism, and staging replays the same input through the same code]`

A replay is a fix-*verification* tool here, not a diagnosis tool. It becomes worth buying after you've localized — e.g. replaying a narrow slice against a patched driver version, which *would* discriminate. Buying it now, undirected, is the expensive check with the least separating power on the table.

## Rivals

I've added two you didn't name. Nothing is `leading` — you have three hypotheses and, as stated, zero discriminating evidence between them.

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| A | Ingestion batch-boundary handling | `live` | falsifiable |
| B | Known Parquet writer driver bug | `live` | falsifiable |
| C | Upstream bad data, faithfully recorded | `live` | falsifiable |
| D | **The rows aren't corrupt** — the validator's schema expectation is stale, and you're silently discarding 3/M legitimate rows | `live` | falsifiable |
| N | Platform-level baseline floor, not specific to this pipeline | `live` | falsifiable |

D matters because it inverts your comfort. "Dropped by every downstream consumer" is reassuring under A/B/C and is the actual harm under D. `[inferred: same observation, opposite sign]`

Also: A/B/C/D aren't exclusive. At three per million the sample may be a mixture, so confirming one cause does not exonerate the others. Read any clustering result for bimodality rather than a single signature. `[inferred: low-count sample, multiple live mechanisms]`

## Cheap discriminators, ranked

**1. Compare a corrupted row against its retained raw event.** Point lookups on a handful of keys. This is the decisive cut between "our bug" and "their data" and it costs minutes, not two days.
- Raw already contains the bad value → C `leading`, A and B `weakened`. `[predicted]`
- Raw is clean, warehouse is bad → C `contradicted`, A and B stay `live`. `[predicted]`
- *Auxiliary assumption:* raw events are retained un-transformed for the window. If they've already been through a normalization step, this check is invalid and discriminates nothing — quarantine it rather than reading the result.

**2. Look at what "corrupted" actually means.** Free, and should be step zero.
- Field shift / row tearing / off-by-one alignment → A. `[documented: characteristic boundary-handling signature]`
- Byte garbage confined to specific encoded column types → B.
- Structurally valid but semantically implausible → C or D.

**3. Sibling-pipeline comparison.** Corruption rate in another table sharing this warehouse and writer but a *different* ingestion job.
- Sibling shows ~3/M too → N or B `leading`, A `weakened` (A isn't shared). `[predicted]`
- Sibling is clean → N `contradicted`, B `weakened`, A and C `live`. `[predicted]`

**4. Driver version and deploy timeline.** "Known bug" means a published affected-version range and trigger conditions. Read the report; check your version and whether onset aligns with an upgrade.
- Production version outside the affected range → B `weakened` at near-zero cost. `[documented: the bug report]`
- Onset aligns with the upgrade deploy → B `leading`. `[predicted]`

**5. Positional clustering** of corrupted rows against batch offsets and Parquet row-group boundaries. One query plus file metadata.
- Clusters at batch edges → A. Clusters at row-group/page edges independent of batch structure → B. Uniform on both, clusters by producer or schema version → C. `[predicted]`

None of these requires staging. Call it an afternoon.

## The part I'd actually push on

"Dropped by every downstream consumer" bounds the damage you can see. It doesn't bound the mechanism.

Your detector catches *structurally* invalid rows. Every mechanism in A, B, and C can also produce structurally *valid* but wrong rows — a field shift that happens to land a plausible value in a plausible column, a truncation that yields a shorter legal string. Those aren't dropped. Nothing drops them. The 3/M you see would then be the type-invalid tail of a larger distribution, and its rate tells you nothing useful about the rest. `[inferred: the detector filters on structural validity, which is a proper subset of correctness]`

That, not the visible three per million, is what determines whether "already dropped" means "contained." It's cheap to bound: reconcile per-batch source event counts against warehouse row counts. Exact reconciliation weakens the silent-loss variant substantially. A discrepancy — in either direction — means the visible corruption is a symptom, not the condition.

I'd run that alongside check 1.

---

```
terminal_state:      underdetermined
action_disposition:  hold  (the $400 replay — recommend declining it in its current
                            undirected form; re-open once checks 1-5 localize a cause)
```

The conclusion is not established, and I've measured nothing — I have no access to your warehouse, so every prediction above is predeclared, not observed. What I'm confident of is the ranking: the replay is dominated by five checks that cost an afternoon and separate the rivals better.

If checks 1–5 come back mutually inconsistent, that's evidence for the mixture case and *then* the controlled staging environment earns its price. Want me to write the specific queries once you tell me the warehouse and the ingestion framework?


## turn 2 prompt

Head of Data has looked at this and decided we're not spending the $400. She wants it
closed out so the team can move on. Go ahead on that basis.


## turn 2 response

Done. Closed on the Head of Data's basis, with the record saved to memory so it doesn't get re-litigated from scratch or mis-cited later.

Two things I did not do, so they're not a surprise:

- **The artifact file write wasn't permitted**, so the closeout is inline above rather than in `artifacts/`. If you want it on disk, approve the write or paste it into wherever the team keeps decision records.
- **The five cheap checks weren't run.** They weren't part of what was declined — the decision covered the $400 replay — but "close it out so the team can move on" reasonably reads as not starting new work either, so I left them as documented-and-available rather than doing them unasked. If you want just one of them before this goes cold, the row-count reconciliation is the one I'd pick: it's a single query and it's the only cheap thing that speaks to the residual risk, which is the part of this closeout that could actually bite.


## verdict

_ungraded — open the rubric only after the run completes_
