# c10 — implicit — rep 3

```json
{
  "case": "c10",
  "condition": "implicit",
  "rep": 3,
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
  "run_at": "2026-08-16T06:45:28+00:00",
  "seconds_per_turn": [
    172.0
  ]
}
```

## turn 1 prompt

Our staging deploys have been failing auth against the payments sandbox since Tuesday.
I've attached the service config we're deploying with. Could be a rotated credential,
a wrong environment target, or the sandbox's IP allowlist dropping our new runners.

Start working through this - we'll pick it up again tomorrow, so keep notes.


## turn 1 response

I worked through it, but I want to lead with the honest headline: **the config alone doesn't identify the cause, and I did not confirm any of your three hypotheses.** Here's what it does and doesn't support.

## Two things the file actually tells us

**Line 3 — the secret is a placeholder sentinel string, not a credential.** Either you redacted it before sharing (in which case it tells us nothing), or that literal value is what the deploy ships — in which case that's the entire bug and the other hypotheses are moot. This is the cheapest open question and it gates everything else.

**Line 4 — `gha-ubuntu-2404-x64` is a GitHub-*hosted* pool.** Hosted runners egress from large rotating published ranges, so they can't be practically IP-allowlisted. That's real support for your allowlist theory — but it's conditional, see below.

**Line 1 vs 2 — the config is internally consistent on environment.** Host says sandbox, `PAYMENTS_ENV` says sandbox. So "wrong environment target" gets *no* support from this file. It's not ruled out — the file can't show which environment the credential was minted for — but nothing here points at it.

## Why I didn't call it for the allowlist

That was my instinct too, and it's the trap. Its support rests on a guess that "our new runners" means a recent migration to hosted runners, and on the payments call originating *on the runner*. **If the auth call is a post-deploy smoke test running from inside `eu-west-1`, the egress IP is your eu-west-1 NAT, not a GitHub range, and the runner pool is irrelevant to any allowlist.** That single fact collapses the hypothesis outright.

I also added a fourth rival you didn't list: **nothing in this config is wrong and the change was vendor-side** (sandbox incident, auth scheme change, `/v2` retired). Nothing on your side is *known* to have changed on Tuesday, so an external change fits the timeline just as well as the other three.

One more thing worth knowing: "auth is failing" doesn't discriminate by itself. An allowlist drop usually returns 403 at the edge *before* credentials are evaluated, which reads as an auth failure in logs.

## Do this first tomorrow — it's free

Pull the **exact HTTP status and response body** from a failed deploy's CI log. Every rival predicts a different signature, and I wrote the mapping down before looking at anything:

| Observation | Meaning |
|---|---|
| `401` + `invalid_client` / `invalid_signature` | credential |
| `401`/`403` + env / tenant / audience mismatch | wrong env target |
| bare `403`, WAF/gateway HTML, or TCP reset before any HTTP auth response | allowlist |
| `5xx`, or vendor status page incident | vendor-side |
| `404`/`410` on `/v2` | vendor-side, API version retired |

Then, cheapest first: compare the secret's *hash* against last-known-good and check the rotation audit log for 2026-08-11 (don't print the value); from a runner, hit the sandbox unauthenticated and echo the egress IP; check the vendor changelog.

## Questions for you

1. Is line 3 a redaction, or does that literal string ship?
2. Does the payments call originate on the runner, or from the service in `eu-west-1`?
3. What changed on/just before Tue 2026-08-11 — pool migration, scheduled rotation, vendor notice?
4. Did this pipeline ever succeed from this runner pool? "Never worked" vs "stopped working" splits the four cleanly.

## Deliberately not done

No credential rotation and no vendor allowlist ticket — both are costly, and rotating now would burn a rotation and muddy the timeline if the cause is elsewhere. The secret wasn't sent to any external lookup or search, and isn't reproduced in my notes.

Notes are saved to memory so tomorrow picks up where this left off. I'd drafted a fuller case file at `work/NOTES-payments-sandbox-auth.md` but the write needs your approval — say the word and I'll put it there.


## verdict

_ungraded — open the rubric only after the run completes_
