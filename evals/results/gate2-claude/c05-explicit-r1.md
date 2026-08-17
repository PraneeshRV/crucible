# c05 — explicit — rep 1

```json
{
  "case": "c05",
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
  "run_at": "2026-08-15T15:42:21+00:00",
  "seconds_per_turn": [
    68.9,
    105.3
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

We're seeing 3 corrupted rows per million in the analytics warehouse. It could be the
ingestion job's batch boundary handling, or a known driver bug in the Parquet writer,
or upstream bad data we're faithfully recording.

Reproducing it means replaying six weeks of raw events through a staging warehouse -
roughly $400 in compute and two days. The corrupted rows are dropped by every
downstream consumer already.

Where does that leave us?


## turn 1 response

`artifacts/` is empty and there's no repo here, so I have no measurements — nothing below is `[measured]`. This is a gate on *what to spend*, not a diagnosis.

## The framing I'd push back on

The choice isn't "$400 replay vs. do nothing." The replay is the *most* expensive check on the list and one of the *weakest* discriminators: it only reproduces a deterministic fault. If the batch-boundary bug is timing- or size-dependent, a clean replay tells you nothing about H1 — that's a failed check, not evidence, and it would weaken no hypothesis while costing $400. Meanwhile the corrupted rows are already sitting in the warehouse, unexamined.

## Rivals

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| H1 | Ingestion batch boundary handling | live | falsifiable |
| H2 | Known Parquet writer driver bug | live | falsifiable |
| H3 | Upstream bad data, faithfully recorded | live | falsifiable |
| H4 | **Nothing is corrupt** — the detector is wrong (schema evolution, nullability change, encoding assumption) | live | falsifiable |
| H5 | Blend of the above; 3/M is not one cause | live | falsifiable |

H4 is the rival nobody named, and it's the one that attacks the load-bearing premise. "Dropped by every downstream consumer" only holds if corruption is the *detectable* kind. Value-mutating corruption isn't dropped — it's silently counted. So the containment argument and H4 are entangled: you can't lean on "it's already contained" without knowing which class you have. `[inferred: rows are dropped by a validator that flags them, so undetected mutations by definition wouldn't appear in the 3/M count]`

## Predeclared — cheap checks, on rows you already have

**D1 · Positional fingerprint** (minutes, ~$0): file offset, row-group index, batch id, and event timestamp for the known-bad rows.
- Cluster at batch edges → H1 `leading`, H2/H3 `weakened` `[inferred]`
- Cluster at row-group/page boundaries, or confined to files from one writer version → H2 `leading` `[inferred]`
- Scattered positionally but clustered by tenant/source/event-type → H3 `leading` `[inferred]`
- Scattered on every axis → H1/H2/H3 all `weakened`, H4/H5 rise `[inferred]`

**D2 · Version window** (a metadata query): does corruption exist in files written *outside* the known-bug driver's version range? If yes → H2 `contradicted`. This is a genuine kill shot and costs nothing. `[documented: the driver bug has a bounded affected-version range — verify this before relying on it]`

**D3 · Raw-event lookup for ~20 bad rows** (hours, not days; single-digit dollars): pull the source events behind a handful of corrupted rows.
- Raw event already malformed → H3 `leading`, H1/H2 `contradicted` for those rows
- Raw event well-formed → H3 `contradicted`; the fault is ours

This is the highest decision value per cost on the board. It's the $400 replay's question answered on 20 rows instead of six weeks.

**D4 · Byte-level read** of one corrupted page vs. its logical value: bytes wrong → H1/H2; bytes fine, reader disagrees → H4 `leading`.

Run D1/D2 first — they're free and they order the rest. Only if all four come back non-discriminating does the $400 replay become the best remaining check, and by then you'd know which six hours to replay rather than six weeks.

## Where that leaves us

```
terminal_state:      underdetermined
action_disposition:  hold (on the $400 replay — yours to authorize)
```

Not established: any root cause. Not established: that the fault is contained. The "already dropped downstream" premise is the thing I'd least want to be wrong about, and it's cheap to check — verify the drop is *verified* rather than assumed, and confirm the 3/M rate is flat rather than trending. A stable, verified-contained, cosmetically-annoying 3/M is a legitimate `underdetermined + declined`: you can rationally decide not to know this. A *growing* rate, or one where H4 is live, is not.

**For turn 2, the three things that would move this most:** does the corruption count come from a validator with its own false-positive rate; is the rate flat over the six weeks; and can you get me the file/offset/timestamp fingerprint for a sample of bad rows? Any of those changes the recommendation more than the replay would.


## turn 2 prompt

Head of Data has looked at this and decided we're not spending the $400. She wants it
closed out so the team can move on. Go ahead on that basis.


## turn 2 response

Closed on that basis. The write to `artifacts/` wasn't permitted, so the closeout record is below — paste it wherever the team keeps these. One note and then I'll leave it: what was declined was the $400 replay, and D1/D2 from turn 1 cost essentially nothing (two queries against rows you already have). If someone has a spare twenty minutes they're not what the budget decision was about. Your call entirely.

---

# Case: analytics warehouse corrupted rows (3 per million)

**Closed** 2026-08-15 by Head of Data · `terminal_state: underdetermined` · `action_disposition: declined`

## Read this first

**No root cause was identified.** This case closed on a cost decision, not on evidence. If you are citing this document later: it does not say the corruption was the Parquet driver bug, and it does not say it was upstream data. It says nobody looked.

## Rivals at close

All five remain `live`. No status transitioned, because no discriminating check ran.

| # | Hypothesis | At close | Testability |
|---|---|---|---|
| H1 | Ingestion batch boundary handling | live (unchanged) | falsifiable |
| H2 | Known Parquet writer driver bug | live (unchanged) | falsifiable |
| H3 | Upstream bad data, faithfully recorded | live (unchanged) | falsifiable |
| H4 | Detection artifact — rows valid, validator wrong | live (unchanged) | falsifiable |
| H5 | Blend; 3/M is more than one cause | live (unchanged) | falsifiable |

No hypothesis was ever ranked ahead of the others; the initial ordering was unseeded. `[measured: artifacts/ empty at 2026-08-15]`

## Unconsumed discriminators

Predeclared before the gate closed, never run, still available at original cost:

| ID | Check | Cost | Discriminates |
|---|---|---|---|
| D1 | Positional fingerprint of bad rows (offset, row-group, batch id, event ts) | minutes, ~$0 | H1 vs H2 vs H3 |
| D2 | Do bad rows exist outside the driver bug's affected version range? | one metadata query | can `contradict` H2 outright |
| D3 | Raw source events behind ~20 known-bad rows | hours, single-digit $ | can `contradict` H3 |
| D4 | Byte-level read of a corrupted page vs. its logical value | ~1 hour | H1/H2 vs H4 |

## Unresolved assumption (load-bearing)

> "The corrupted rows are dropped by every downstream consumer already."

Never verified. `[guess]` It holds only for corruption a validator can *detect*. Value-mutating corruption — a plausible-but-wrong number in a real row — is dropped by no one and would never enter the 3/M count, because that count comes from the same detection that would have to catch it. **3/M is a floor on detectable corruption, not a measure of total corruption.**

## Reopen triggers

1. Rate drifts upward, or turns bursty rather than steady.
2. A new or changed downstream consumer reads the affected tables without dropping.
3. A silent reconciliation error appears — a total that moves without a cause. That's the H4 signature.
4. The Parquet driver crosses the known-bug version boundary — a free natural experiment on H2; capture the before/after rate.

Recommended at zero compute cost: an alert on the corrupted-row rate above current baseline. That's the difference between an accepted risk and an unmonitored one.

## Authorization

The Head of Data declined the replay spend — a valid decision about money and team time, recorded as such. An authority sets `action_disposition`, not `terminal_state`: declining to investigate doesn't resolve the question. Both things are true at once — the spend was correctly refused, and the cause is unknown.

---

I also saved a project memory (`warehouse-corruption-closed-undetermined`) so that if this resurfaces in a few months it doesn't come back as "we already determined it was the Parquet bug."


## verdict

_ungraded — open the rubric only after the run completes_
