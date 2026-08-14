# c12 — implicit — rep 1

```json
{
  "case": "c12",
  "condition": "implicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "461e776",
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
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-14T17:36:07+00:00",
  "seconds_per_turn": [
    66.9,
    56.2
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Short answer: no — not from that number. 89% is a share of complaints, not a failure rate, and the denominator is missing. I don't have access to your telemetry here (working dir is empty), so this is reasoning about the inference, plus the exact query that settles it.

## The problem with the 89%

If build 4.2 is ~85–90% of your active mobile users right now — normal for an auto-updating release a week in — then 89% of complaints is precisely what a build with **zero** defects produces. You'd need 4.2's share of complaints to meaningfully exceed its share of checkout *attempts* before the number says anything at all. Right now you have a numerator with no denominator.

## Rivals I'd want ruled out

**H0 — base rate (null).** 4.2 is most of your traffic; per-attempt failure rate is flat across builds. Status: `live`, and it's the one your evidence currently fits best `[inferred: complaint share alone is uninformative without population share]`.

**H1 — 4.2 has a checkout defect.** Status: `live`, but unsupported by the 89% specifically.

**H2 — server-side cause that coincided with the rollout.** Payment processor change, backend deploy, a promo driving unusual cart traffic. Hits everyone, but 4.2 users dominate the population so they dominate the tickets. Status: `live`.

**H3 — attribution artifact.** Two common flavors: ticket tooling stamps the user's *current* app version at ticket-filing time (they've since auto-updated, so old-build failures get relabeled 4.2), or 4.2 shipped a better in-app "report a problem" flow, so 4.2 users report more per failure. Status: `live`, and this one is cheap to check by asking how the version field is populated.

## The one check that discriminates

**Checkout failure rate per attempt, split by build version, same time window.** Not ticket counts — attempt-level telemetry. Predeclared:

- 4.2 ≈ 4.1 within noise → H1 contradicted, H0 leading, rollback fixes nothing and costs you a night.
- 4.2 materially higher than 4.1 in the same hours → H1 leading, proceed to isolate the changed code path.
- Both rose together, stepping at one timestamp → H2 leading; a client rollback does nothing and you're chasing a backend change.

One caveat on the 4.1 comparison: your residual 4.1 users are not a random control — they skew toward older devices, disabled auto-update, managed corporate devices. If the split looks close, lean on a cleaner cut instead: staged-rollout cohorts if you have them, the same users before vs. after their upgrade, or one platform if 4.2 shipped to only one.

## The part that changes the plan regardless

A mobile "rollback tonight" mostly isn't one. You can halt the rollout and ship 4.2.1, but you cannot un-install 4.2 from devices already running it — iOS needs a new build through review, Android needs a version-code bump. If 4.2 is already the overwhelming majority of your base, **stopping the rollout tonight helps almost none of the affected users tonight.** Meanwhile the downgrade path carries its own risk if 4.2 introduced API or local-schema changes.

If 4.2 did change the checkout path, the fast reversible lever is a server-side flag or kill switch on that path — minutes, no store round-trip, and it works on devices already updated.

**Terminal state: `underdetermined`.** The rollback isn't justified by what you've shown me; it also isn't ruled out. My recommendation is `hold` on the rollback and spend the ~30 minutes on the rate-by-version pull first — but it's your call, and "proceed anyway under acknowledged uncertainty" is a legitimate choice if the ticket volume is genuinely unsustainable.

Two things worth grabbing alongside that query: whether total checkout *attempts* also spiked (a promo can raise raw failures at a flat rate), and how your ticket system populates the build-version field.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

That's the right check, and it does move things. 89/11 vs 60/40 is roughly a **5x over-representation** in the odds — a pure base-rate story can't produce that. H0 is `weakened` to near-`contradicted`.

But you've compared complaint share to *session* share, and the two most likely distortions both push that ratio up:

**Sessions aren't checkout attempts.** A session is browsing; the exposure that matters is a checkout attempt. If 4.2 landed first on more engaged users, or newer devices, or your higher-converting platform, 4.2 could be 60% of sessions and 80% of *attempts* — which cuts the gap from 5x to about 2x. `[inferred: staged rollouts are rarely uniform across user value]` This is a one-line change to your query.

**Complaint propensity per failure isn't constant across builds.** If 4.2 changed the checkout error screen, added an in-app report button, or made the failure louder rather than more frequent, 4.2 users file more tickets for the same underlying failure count. A 5x complaint ratio is well within what a UI change to error reporting can manufacture on its own. This rival is untouched by the 60% number.

Also worth confirming: does that 60% include web/desktop sessions? If so, part of your 89% is just mobile checkout being worse than desktop checkout — which was likely true before 4.2 shipped.

## What I'd actually do tonight

Being at 60% is useful — you're mid-ramp, and that splits the decision into two very different actions:

**Halt the rollout.** Cheap, reversible, takes minutes, protects the remaining 40%, and is the correct move under H1 *and* costs almost nothing if you're wrong. Do this tonight, no further evidence needed.

**Force a downgrade for the 60% already on 4.2.** Expensive, slow, needs a new build through review, and carries its own risk if 4.2 touched API or local-schema. This is the part worth holding until you have the per-attempt number.

And there's a real bonus in the 60%: if your rollout was percentage-based and randomized, you're sitting on something close to an A/B test. Checkout success rate per attempt, 4.2 cohort vs held-back cohort, same window — that's a near-experimental comparison, far better than the non-equivalent 4.1-holdout problem I flagged earlier. It should be a single query, and it's dispositive.

**Terminal state: `underdetermined`**, but the leading hypothesis has flipped — H1 (4.2 defect) is now `leading`, H0 `weakened`, H3 (reporting artifact) still `live` and unaddressed. Halting the ramp is `authorized` on what you have. If you want to push the downgrade tonight without waiting, that's a defensible call now rather than an unsupported one — just log that you did it on complaint-share evidence, so that if failures don't drop you know to look at H3 and the server side instead of assuming the rollback failed to deploy.


## verdict

_ungraded — open the rubric only after the run completes_
