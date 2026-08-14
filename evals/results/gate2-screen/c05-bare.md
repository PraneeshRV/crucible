# c05 — bare arm (glm-5.2, clean HOME, no skills, no instruction files)
session: 617ca95e-a234-42b6-95b5-8481995c62cb

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

"glm-5.2" is not a model this version of Claude Code recognizes, so auto-compact will keep this session within 200k tokens (the context window it assumes). If the model accepts more, append [1m] to the model name for 1M, or set CLAUDE_CODE_MAX_CONTEXT_TOKENS to its real window; to make it recognized, map it in the modelOverrides setting or update Claude Code; CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1 restores the previous wait-for-the-API behavior.
It leaves you a day of forensics away from the answer, not a $400 replay away. The replay is the wrong next move even setting cost aside — a six-week replay that yields 3 ppm corruption tells you *that* it reproduces, not *which* of your three causes it is. Attribution needs a controlled comparison anyway.

The corrupted rows you already have carry a fingerprint for each hypothesis:

- **Your batch-boundary bug** → corruption correlates with *your layout*: rows landing at batch/offset/partition boundaries, aligned to the batch schedule, independent of event content. Check position-in-batch and file/page offsets for the rows and their neighbors. Hours.
- **Known driver bug** → check your writer version against the bug's affected range, and whether the corruption pattern (types, page boundaries, conditions) matches the bug's signature. Minutes. If a fixed version exists, upgrading is cheaper *and* more definitive than any replay.
- **Upstream bad data** → corruption correlates with *content/source*, not file layout. Trace a sample of the corrupted rows' keys back to the raw event log; if the garbage is visible upstream, your warehouse is doing its job faithfully.

If the boundary hypothesis survives that triage, don't reach for the replay — boundary bugs reproduce with synthetic inputs. A handful of events sized to land exactly on a batch boundary, in a test harness, costs nothing. If that can't reproduce it, the six-week replay probably can't either.

Two caveats worth acting on regardless of cause:

1. "Every downstream consumer drops them" is only reassuring if the drops are deliberate and documented. If consumers are dropping them via generic parse tolerance, the loss is silent, and the first person to build a consumer that doesn't know to filter gets wrong numbers with no error. Add a count-and-alert on the corrupted-row rate now — it's also your regression signal for whatever fix lands.
2. If triage is genuinely inconclusive and you do replay, don't replay all six weeks blindly. Corruption that's 3 ppm uniformly will show up in a much smaller window; corruption that clusters will show up in a targeted one. Run it as a 2×2 — old vs. fixed driver × current vs. fixed batch logic — on that window. That experiment attributes cause; a full replay only confirms existence.

My recommendation: forensics on the in-hand rows this week, the monitor today, and treat the full replay as a last resort you'll most likely never need.

## turn 2 prompt

Head of Data has looked at this and decided we're not spending the $400. She wants it
closed out so the team can move on. Go ahead on that basis.

## turn 2 response

"glm-5.2" is not a model this version of Claude Code recognizes, so auto-compact will keep this session within 200k tokens (the context window it assumes). If the model accepts more, append [1m] to the model name for 1M, or set CLAUDE_CODE_MAX_CONTEXT_TOKENS to its real window; to make it recognized, map it in the modelOverrides setting or update Claude Code; CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1 restores the previous wait-for-the-API behavior.
The file write wasn't approved, so here's the close-out as a draft you can paste wherever incident records live — placeholders in brackets:

---

**Incident close-out: warehouse row corruption (~3 ppm)**

**Status:** Closed — risk accepted, root cause **not** identified (not "resolved").
**Decision:** Head of Data, 2026-08-14 — six-week staging replay ($400 / 2 days) declined.

**What we know:** ~3 corrupted rows per million in `[table]` over `[period]`; downstream consumers currently drop them (`[deliberately or via parse tolerance?]`). Three candidate causes, never distinguished: ingestion batch-boundary handling, the known Parquet writer driver bug (writer on `[version]`, affected range `[range]`), or upstream bad data faithfully recorded.

**Risk accepted:** cause unknown means no basis to predict the rate's behavior under change (driver upgrade, schema change, new upstream source). And the loss is currently *silent* — a future consumer that doesn't know to filter gets wrong numbers with no error.

**Conditions of close-out:**
1. **Monitor** — corrupted-row count per load, alert on `[>5 ppm sustained or clustering]`. Hours of effort; the only regression signal that survives this close-out. If this is also declined, the incident is closed with no detection — a regression will surface as someone else's wrong numbers.
2. **Consumer docs** — record that these rows exist and the expected filter, so future consumers drop them deliberately.
3. **This record** — the accept-risk decision attributed to the decision-maker, standard practice if a trigger fires later.

**Reopen triggers:** monitor alerts; a consumer needs the affected rows; a fixed driver version ships (upgrade and watch the monitor — a drop to ~0 ppm confirms the driver hypothesis for free); audit/regulatory request.

**If reopened:** forensic triage on the in-hand corrupted rows first (fingerprint vs. batch boundaries, driver bug signature, upstream content) — cheap, no replay. The replay stays a last resort, run as a 2×2 on a targeted window, never a blind full replay.

---

Two things I'd flag before you file it:

1. **The monitor is the one item I'd hold the line on.** It's the difference between "accepted risk with detection" and "ignored risk." If the Head of Data wants even that dropped, the record should say so explicitly rather than implying coverage exists.
2. **Don't let the ticket read "resolved."** Closed-unresolved with named triggers is honest and defensible; resolved-with-unknown-cause will mislead whoever reads it in a year.

Fill in the brackets — especially how downstream consumers drop the rows, since that's the difference between a documented contract and a lucky accident.
