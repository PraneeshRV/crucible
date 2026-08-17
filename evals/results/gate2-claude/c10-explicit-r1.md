# c10 — explicit — rep 1

```json
{
  "case": "c10",
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
  "run_at": "2026-08-16T06:46:28+00:00",
  "seconds_per_turn": [
    231.6
  ]
}
```

## turn 1 prompt

$crucible Our staging deploys have been failing auth against the payments sandbox since Tuesday.
I've attached the service config we're deploying with. Could be a rotated credential,
a wrong environment target, or the sandbox's IP allowlist dropping our new runners.

Start working through this - we'll pick it up again tomorrow, so keep notes.


## turn 1 response

Both write attempts were denied by the permission prompt, so I haven't created any files. The notes are below in full — tell me where you'd like them saved (or approve a write) and I'll persist them.

## What I found before forming any hypothesis

The attached `config.env` **is a sanitized/example artifact, not your live deployed config**. Three independent signals:

1. `PAYMENTS_API_URL` points at **`example.com`** — a domain reserved for documentation (RFC 2606), guaranteed not to be a real service.
2. `PAYMENTS_API_SECRET` holds a self-describing placeholder sentinel, not a credential-shaped value.
3. Its mtime is **2026-07-29** — about two weeks *before* the onset.

"Since Tuesday" resolves to **2026-08-11** (today is Sunday 2026-08-16), so the file predates the breakage.

That's a scope constraint, not a gotcha — sanitizing a config before sharing is correct practice. But it means only the *field names and structure* are usable evidence. All three of your candidate causes turn on "what changed Tuesday," and this artifact cannot speak to that.

One thing I specifically did **not** conclude: that placeholder secret is *not* evidence your deploy is shipping an uninjected credential. Redaction-before-sharing and never-injected produce an identical file. They're separated by D2 below.

I skipped a live egress test — against a reserved domain it would prove nothing about your sandbox.

## Rivals

| id | hypothesis | status |
|---|---|---|
| H1 | Credential rotated sandbox-side; deploy sends the old secret | `live` |
| H2 | Wrong environment target — valid credential, wrong env/account | `live` |
| H3 | IP allowlist drops the new runners | `leading` (weak) |
| H4 | Secret never injected — placeholder/empty reached the deployed config | `live` |
| H5 | Provider sunset `/v2`; rejected at the edge | `live` |
| H6 | Signing broken by clock skew or a runner-image/SDK bump | `live` |
| H0 | Null: nothing changed our side (sandbox-side expiry/maintenance) | `live` |

H4, H5, H6 and the null weren't in your original three.

H3 leads only weakly, and **only on your own testimony** that the runners are new — not on the artifact. `RUNNER_POOL=gha-ubuntu-2404-x64` reads as GitHub-hosted `ubuntu-24.04`, whose Azure egress IPs are incompatible with a static allowlist — but that's inference from a naming convention, in a file that §0 says I can't trust values from. A self-hosted pool could carry the same name.

Counterweight: you describe *auth* failures, and an allowlist drop classically fails at the network layer, not with an auth error. Some gateways do return app-layer 403s for policy denials, so it's genuinely ambiguous.

## Predeclared discriminators — written before observation

**D1 (do this first): the actual failure response** — HTTP status + error body + whether TLS completed. One log lookup; the data already exists.

| observed | means |
|---|---|
| `401` invalid credentials/signature | supports H1, H4, H6 · weakens H3, H5 (reached auth) |
| `401`/`403` "key not valid for this environment" / account mismatch | H2 leads · weakens H1 |
| `403` IP-not-allowed, **or** timeout/reset/TLS failure with no status | H3 leads · weakens H1, H2, H4, H6 (never reached auth) |
| `404` / "version no longer supported" | H5 leads · weakens H1–H4 |
| intermittent, succeeds on retry | H3 (partial allowlist) or H6 (skew) · weakens H1, H4 |

**D2: credential fingerprint inside the job** — emit only `${#PAYMENTS_API_SECRET}` and the first 8 chars of its SHA-256, never the value. Length 0/unset or a digest matching the placeholder confirms H4; a plausible length with a different digest contradicts it.

**D3:** egress IP of a failing run vs the allowlist; did `RUNNER_POOL` change around 08-11?
**D4:** deploy-config and pipeline diffs across 08-10 → 08-11. If nothing changed our side, H0 strengthens.

## Terminal state

`terminal_state: underdetermined` · `action_disposition: hold`

No cause is established and I changed nothing. Deliberately not `blocked` — the evidence exists and you can pull it; this is a supply gap, not a dead end. All four discriminators are unconsumed; no hypothesis was weakened or contradicted today.

**Tomorrow, in order:** D1 → confirm which fields of `config.env` were sanitized → D2 → D3/D4 only if D1 points at H3 or comes back ambiguous.


## verdict

_ungraded — open the rubric only after the run completes_
