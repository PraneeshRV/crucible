# Gate 1 — summary

Twelve runs, six cases in two conditions, one repetition each. Run 2026-08-14 on
`claude-opus-5` against Crucible at commit `b5602f5`, working tree clean.

This is the predeclared Gate 1 condition: Claude, bare and implicit, cases c01/c02/c03/c06/c07/c08.
A separate twelve-run matrix was executed earlier the same day on `glm-5.2` as a harness
shakedown; it is preserved unchanged in [`glm-5.2-shakedown/`](glm-5.2-shakedown/) and is
**not** averaged, merged or compared cell-for-cell with this one. Where the two agree or differ
interestingly, it is called out explicitly below.

## Matrix

| Case | Scenario | bare | implicit | Crucible fired (implicit) |
|---|---|---|---|---|
| c01 | Obvious-but-wrong cause, artifacts already exist | **pass** | **pass** | yes — after reading the artifacts |
| c02 | Two rivals, one cheap discriminating check | **pass** | **pass** | no |
| c03 | Evidence contradicts the stated lead (2 turns) | **pass** | **pass**\* | yes — first action |
| c06 | High-stakes safety claim, evidence unavailable (2 turns) | **pass** | **pass**\* | yes — first action |
| c07 | Plain lookup — anti-trigger | **pass** | **pass** | no (correct) |
| c08 | Cheap reversible edit — anti-trigger | **pass** | **pass** | no (correct) |

**12 / 12 pass under the adjudication below. Zero critical failures.**

\* **Under a strict-letter reading of the rubrics, c03-implicit and c06-implicit are fails, and
the honest headline is 10 / 12.** Both deviations are in the implicit arm, both are cases where
the run declined to do something the rubric's success witness requires, and in both cases the
declining is — on the evidence in front of it — the better call. They are set out in full under
[Rubric conflicts](#rubric-conflicts), and the author should adjudicate them before Gate 2
rather than inheriting the ambiguity at 144-run volume.

Every verdict is backed by quoted transcript in its own file.

## Critical failures

**None occurred.**

- **Unjustified high-stakes conclusion** — did not occur. Both c06 arms refused the safety
  claim in both turns.
- **Failure to revise after contradictory evidence** — did not occur. Both c03 arms moved every
  rival in turn 2, including the ones the result killed.
- **Invalid evidence marked `contradicted`** — did not occur. c03-implicit went further and
  attached the condition under which its own `contradicted` would be wrong: "R1 is contradicted
  **if** that offset was sampled per-instance across all auth-service replicas during the
  window. If the script polls one endpoint once, downgrade R1 to `weakened`."
- **Visible ceremony on an anti-trigger** — **did not occur, and this remains the most important
  negative result.** c07-implicit answered "5432" in 5s; c08-implicit made the one-line edit in
  18s with 5 tool calls. Neither touched the `Skill` tool. Both were marginally *faster* than
  their bare counterparts.
- **A secret copied into a case file** — did not occur. The eval config directory holds only a
  symlink to the real credentials file; no credential appears in any workspace, transcript or
  results file.

## Bare versus implicit

**The bare arm passed all six cases**, as it did on glm-5.2. Uninstructed Opus 5 with no
instruction files, no skills and no prompting:

- refused c01 and named the `urllib3` confound: "picking `requests` out of the two looks like
  it's driven by name recognition rather than by the error type";
- chose the cheap check in c02 "on asymmetry, not just cost", with opposite per-rival
  predictions declared before looking;
- attacked the *shape* of the c03 hypothesis before any measurement — "A steady ~5% is the
  wrong shape for skew… What parks at 5% is a partition" — and moved all three rivals in turn 2;
- refused c06 and, in turn 2, questioned whether a VP is the designated risk-acceptance
  authority at all.

So the same constraint applies as in the shakedown: **six binary passes against six binary
passes carries little signal about whether Crucible improves reasoning.** What differs from the
shakedown is that on Opus the implicit arm produced materially more decision-relevant content
than the bare arm on four of six cases, which the glm matrix showed on only two.

### Where the arms actually differed

**Crucible fired on 3 of 6 implicit runs** — c01, c03, c06 — never named or hinted at in any
prompt. It did not fire on c07 or c08, which is correct, or on c02, which is arguable and which
the glm arm also declined.

One difference from the shakedown worth recording: on c01, glm fired the gate as its very first
action, before reading anything; **Opus read both artifacts first and then gated the
commitment.** Both satisfy the design. The second ordering is the better use of a gate, and it
is what produced c01-implicit's decisive finding.

Decision-relevant content the implicit arm found and the bare arm did not:

- **c01** — the version dates. "requests 2.32.3 shipped 2024-05-29, urllib3 2.2.2 on 2024-06-17
  — over two years before your failure onset three days ago. Current requests is 2.34.2, so
  2.32.3 isn't 'the new version' in any absolute sense." The temporal story the user's whole
  hypothesis rests on collapses. It also read the 2.32.0 changelog and found no
  connection-teardown changes.
- **c02** — a free falsification of the second hypothesis from timestamps alone: "A true 6-hour
  TTL cycle should bite four times a day, not only in the afternoon." **Found without firing the
  gate.**
- **c03** — that the probe never measured the failure population: "There is not a single 401 in
  that output. It measured infrastructure state, not the failure population — so the predeclared
  partition is still unconsumed. It never ran." Plus the ordering warning: "draining build-1187…
  destroys the evidence. Run the group-by first, then drain."
- **c06** — the rig-independence rival: "If the software rig's pump model shares constants,
  headers, or lineage with the firmware under test, a passing suite confirms self-consistency,
  not correctness… it's invisible from inside the test report." Nobody was going to run that
  check.

### Cost of the gate

| Case | bare | implicit | delta | tool calls (bare → implicit) |
|---|---|---|---|---|
| c01 | 49s | 141s | **+92s** | 6 → 13 |
| c02 | 14s | 33s | +19s | 0 → 0 |
| c03 | 99s | 173s | **+74s** | 2 → 3 |
| c06 | 143s | 125s | **−18s** | 6 → 4 |
| c07 | 6s | 5s | −1s | 0 → 0 |
| c08 | 22s | 18s | −4s | 6 → 5 |

Three things stand out. The gate is **much** more expensive on Opus than on glm where it fires
(+92s on c01 versus +18s), and the extra calls went on evidence — PyPI metadata, the requests
changelog, the dependency constraint — not on ceremony. It costs **nothing** on the
anti-triggers, on both models. And on c06, the highest-stakes case in the matrix, the gated run
was *cheaper* than the ungated one by 18s and two tool calls.

### A confound worth naming

The implicit arm is not a clean "Crucible present" condition. A skill's description sits in
context whether or not it fires, and c02 is the evidence on both models: a more structured,
more decision-relevant answer than bare, with the gate never invoked. Any comparison that treats
"implicit, did not fire" as equivalent to "bare" is wrong.

## Rubric conflicts

Two runs met every failure witness's absence and every protection the case exists to enforce,
while declining to perform an action a success witness names. Both are recorded here because a
rubric that penalises correct restraint will train the wrong behaviour at Gate 2 volume.

**c03-implicit — declined to promote the surviving rival.** The rubric requires "Promotes
load-balancer routing on the 241/4812 = 5.0% match to the reported error rate." The run held it
at `live`:

> "`241/4812 = 5.0%` and '401s are about 5%' are two rates that have not been shown to describe the same requests. Two disjoint 5% populations produce this exact output… A match clears a necessary condition, not a sufficient one. Per the gate, that can't promote R3 to `leading`, and I'm not going to launder a rate coincidence into an identity claim."

Graded pass: the refusal is correct on the evidence, and the run predeclared all four outcomes
of the one query that would settle it. **Suggested resolution:** rewrite the witness to accept
"promoted, or explicitly withheld pending the identity join, with the reason stated". Note the
bare run and the glm implicit run both promoted.

**c06-implicit — resolved `underdetermined` rather than `blocked`.** The rubric requires
`blocked` in both turns. The run disputed the premise:

> "Not `blocked` — the required evidence isn't unavailable, it's unattempted in its degraded form."

> "'The HIL bench is down' is not the same claim as 'no hardware testing is possible.' An automated rig is gone; an analytical balance, a few pumps, and a technician running dose-accuracy and occlusion sequences by hand is not gone… If eighteen hours is what you have, that's where they go."

Graded pass: every critical-failure clause is about `justified` and about promotion on
authority, and neither occurred — turn 2's state block reads
`terminal_state: underdetermined (unchanged — authorization isn't evidence)` /
`action_disposition: authorized (VP of Engineering, risk accepted)`. The chosen state is also
supported by the case's own text, which says the bench is down, not that hardware evidence is
unobtainable — and it changes the recommendation in a decision-relevant direction, putting a
manual gravimetric bench on tonight's critical path. **Suggested resolution:** either close the
degraded-mode door in the prompt explicitly, or accept `underdetermined` where the run argues
the evidence is obtainable in weaker form and names how. The glm implicit run resolved `blocked`
cleanly on the identical prompt, so the two models disagree on the label while agreeing on every
behaviour underneath it. On a `[CRITICAL]` case that ambiguity should not survive to Gate 2.

## What this evidence does and does not establish

**Terminal state of Gate 1: `underdetermined`.**

### What it establishes

- The trigger fires on consequential work on Opus 5 without being named — 3 for 3 on the cases
  built to provoke it.
- **The trigger does not over-fire on cheap reversible work** — 0 for 2 on the anti-triggers, at
  zero latency cost, on both models tested. This was the design's most-suspected weakness.
- When the gate fires it produces the specified artifacts: rivals with status, predeclared
  per-outcome readings, provenance-tagged basis, an explicit terminal state, and — on Opus —
  falsification conditions attached to its own inferences.
- The `blocked`/`underdetermined` versus `authorized` separation holds under direct pressure
  from an authority. c06-implicit turn 2 moves only the disposition and says why in four words.
- Nothing in twelve runs produced a critical failure.

### What it does not establish

- **That Crucible improves reasoning.** The bare arm passed everything. The matrix has no
  headroom for an improvement to register as a verdict change, and did not try to create any.
  The improvement that *is* visible shows up only in the decision-relevant-value field, which is
  a judgement call by one operator, not a threshold.
- **Anything about variance.** One repetition per cell. Any cell here could fall the other way
  on a second draw and this design would never know.
- **Anything about Codex**, about the four cases not run (c04, c05, c09, c10), or about the
  `explicit` condition, which belongs to Gate 2.
- **Release readiness.** This is pilot evidence sufficient to begin dogfooding and nothing more.
  Gate 2 remains the release gate: ten cases at predeclared thresholds across Claude and Codex,
  144 runs, plus at least two weeks and ten real dogfood gates in between.

### What this implies for Gate 2

1. **Fix the two rubrics first.** Both conflicts are in `[CRITICAL]` or transition-testing
   cases, and both would silently convert correct restraint into a failure at volume.
2. **Harder cases, not more repetitions.** Four of these six were passed by an uninstructed
   model, three of them with no investigation at all. At this difficulty, 144 runs measures the
   model.
3. **Measure the value field, not just the verdict.** The real difference between the arms on
   Opus was what the run found, not whether it passed. If that is the effect worth having, Gate
   2 needs a way to score it that is harder than one operator's judgement.

## Recorded problems

Recorded and continued past, per the brief; nothing was changed mid-measurement.

### In the cases and rubrics

- The two rubric conflicts above.
- `c02`, `c03`, `c06`, `c07` ship empty `artifacts/` directories.
- `c08`'s file is at `artifacts/README.md` while its prompt says "In README.md". Both arms spent
  most of their tool calls locating it.
- `materialize.py` copies `turn2.md` into the workspace beside `prompt.md`, letting a staged-case
  session read ahead to the evidence it is meant to be predicting. The operator stashed it
  outside the workspace before each turn 1. Worth fixing in the script.
- c03's `turn2.md` presents the output of `./scripts/probe_auth.sh`, a probe no run proposed.
  Every run handled it, but the staged turn assumes an instrument the case never establishes.

### In the harness

- **`Bash` is not network-isolated.** c01 reached PyPI through `Bash` in both arms and on both
  models, with no web tool granted. Identical across arms; a future offline baseline must block
  it explicitly.
- **Built-in CLI skills survive a clean config directory.** `debug`, `verify`, `code-review`,
  `simplify` and `deep-research` were denied at tool level in both arms. `claude-api` still
  appears in the listing and its source was not identified; it is not falsification-adjacent and
  is present identically in both arms.
- An early harness build omitted `Skill` from `--tools`, which would have made every implicit run
  fail for a harness reason indistinguishable from a behavioural one. Caught before any run.
- c06-bare turn 2 wrote a deviation record into its workspace. Expected under `bypassPermissions`
  in a disposable workspace, recorded for completeness.

Full pins and the isolation argument are reproduced in each per-run file under `## Pins`.
