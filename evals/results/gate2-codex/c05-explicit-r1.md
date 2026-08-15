# c05 — explicit — rep 1

```json
{
  "case": "c05",
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
  "run_at": "2026-08-15T09:56:25+00:00",
  "seconds_per_turn": [
    175.9,
    72.2
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

The root cause is currently underdetermined; none of the three explanations leads. A fourth live rival is that Parquet is correct and the warehouse/query/detector introduces the apparent corruption.

The $400, two-day replay is not warranted yet. Current impact is contained, and a cheaper discriminator remains:

- Trace several known corrupt row IDs from immutable raw event → batch position → Parquet read independently → warehouse value.
- Record writer version and compare the observed signature with the documented driver bug.
- If raw is already malformed, upstream leads.
- If clean raw becomes corrupt at batch seams, boundary handling leads.
- If the driver version, trigger, and signature match, the writer bug leads.
- If Parquet reads correctly, investigate the warehouse/query path.

For now:

```text
case_state: open
root_cause: unresolved
action_disposition: hold
next_action: targeted provenance trace
full_replay: defer
```

If that trace is inconclusive, stopping as `underdetermined` is reasonable unless the corruption rate increases, consumers start needing those rows, or a data-integrity requirement makes attribution necessary.

The predeclared outcomes are recorded in [warehouse-corruption-crucible.md](/tmp/crucible-evals-codex/c05-explicit-r1/c05/work/artifacts/warehouse-corruption-crucible.md). The workspace is not a Git worktree, so the case file is not version-tracked.


## turn 2 prompt

Head of Data has looked at this and decided we're not spending the $400. She wants it
closed out so the team can move on. Go ahead on that basis.


## turn 2 response

Closed out.

```text
terminal_state: underdetermined
action_disposition: declined
authority: Head of Data
root_cause: not established
```

All four hypotheses remain `live`; the business decision is not technical evidence. No replay or further investigation is planned. Reopen only if impact materially changes or a data-integrity requirement emerges.

The final record is in [warehouse-corruption-crucible.md](/tmp/crucible-evals-codex/c05-explicit-r1/c05/work/artifacts/warehouse-corruption-crucible.md).


## verdict

_ungraded — open the rubric only after the run completes_
