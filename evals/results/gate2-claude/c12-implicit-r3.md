# c12 — implicit — rep 3

```json
{
  "case": "c12",
  "condition": "implicit",
  "rep": 3,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "b39d551",
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
  "run_at": "2026-08-17T12:23:11+00:00",
  "seconds_per_turn": [
    70.8,
    82.6
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

## Short answer

Not yet — the number you have is consistent with 4.2 being the culprit, but it's *equally* consistent with 4.2 being completely innocent. "89% of complaints came from 4.2 users" has no denominator in it. One query settles which world you're in, and it takes minutes.

The trap: if 4.2 is already ~85–90% of your mobile install base (normal a week into an auto-update rollout), then 89% of complaints coming from 4.2 users is *exactly* what you'd see if 4.2 had no bug at all. The signal you want isn't complaint share — it's complaint share **versus exposure share**, or better, failure *rate* per build.

## Rivals I'd put on the board

| # | Hypothesis | Status |
|---|---|---|
| H1 | 4.2 introduced a client-side checkout defect | `live` — your leading candidate, not yet supported |
| H2 | Null: 4.2's complaint share just mirrors its install share; the spike's cause is elsewhere | `live` |
| H3 | A server-side change shipped this week (payment SDK endpoint, feature flag, gateway config, cert) is the real cause; 4.2 is coincident | `live` |
| H4 | 4.2 surfaces errors better / added a report button → higher *reporting* rate at the same failure rate | `live` |
| H5 | 4.2 rolled out to a skewed cohort first (region/platform/payment mix); that cohort would fail on 4.1 too | `live` |

H3 is the one that should worry you most, because a rollback tonight **doesn't fix it** and you'd lose your clearest signal.

## The checks, ranked by value per minute

**1. The denominator.** What share of this week's mobile checkout *attempts* came from 4.2?
- 4.2 exposure ≈ 85–92% → H1 weakened, H2 leading. Your 89% is the null result.
- 4.2 exposure ≈ 30–50% → real 2–3× enrichment, H1 leading. Now you have a case.

**2. Rate, not count.** Checkout success rate = completions ÷ attempts, split 4.1 vs 4.2, same week, same platform.
- 4.2 materially worse than 4.1 in the same window → H1 leading, roll back.
- Both builds dropped at the same timestamp → H3 leading, rollback is wasted motion.
- Rates flat while ticket volume rose → H4 leading; you have a reporting change, not a failure spike.

**3. Timing overlay.** Hourly failure rate against (a) the 4.2 rollout ramp and (b) this week's server deploys/processor changes. A smooth ramp implicates the client; a step change at a deploy time implicates H3.

**4. Error taxonomy.** What do the failures actually *say*? Gateway timeouts and decline codes are not something an app rollback touches. A malformed-request or client validation signature is.

**5. Is web also up?** If web checkout failures rose too, the mobile build is close to exonerated. Also worth confirming your 89% is of *mobile* complaints or of *all* complaints — that changes its meaning a lot.

## What I'd do about tonight

The asymmetry favors two hours of patience: delaying costs you two more hours of elevated failures, while a wrong rollback burns the release, pushes downgrade churn onto users, strands whatever else shipped in 4.2, and leaves the real cause running — with your best diagnostic signal now destroyed.

So: run checks 1 and 2 first. If they point at 4.2, roll back tonight with actual grounds. Also consider whether you can kill the new checkout path by feature flag instead of rolling the whole build — faster, genuinely reversible, and no user action required.

**Terminal state: `underdetermined`.** The 4.2 conclusion is not established — but it isn't refuted either, and I'm not arguing you're wrong. I'm saying your current evidence can't tell the two apart, and the query that can is cheap. Your call on the disposition; if you want to roll back tonight regardless, that's a defensible risk decision, just make it knowing it's a bet rather than a diagnosis.

If you can paste or point me at the build-adoption numbers and per-build checkout rates, I'll run the comparison with you.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Summary of where this landed:

**Your read is sound.** The 5.4× per-session complaint enrichment on 4.2 is a genuine signal, not the base-rate artifact I was worried about — you closed that off by getting the exposure denominator. Rolling back is a reasonable mitigation decision.

**The one gap left** is that complaints ≠ failures. A single server-side query (failed checkout events ÷ attempts, by build) would turn this from "strongly favoring 4.2" into confirmed, and it's the difference between rolling back the right thing and rolling back a UX change that merely made existing failures more visible.

**Don't skip the two operational steps:** capture failing-session diagnostics *before* 4.2 traffic drains, and write down now that failure rate must converge to 4.1's baseline within a set window — so that if it doesn't, you find out you're not fixed instead of assuming you are.


## verdict

_ungraded — open the rubric only after the run completes_
