---
commitment: <the conclusion or action being gated>
stakes: normal | high
state: open | justified | underdetermined | blocked
opened: YYYY-MM-DD
evidence_standard: <what must be true to establish the conclusion>
decision_authority: <who may authorize the action>
justified_if: <condition>
underdetermined_if: <condition>
blocked_if: <condition>
---

## Rivals

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| H1 | ... | leading | falsifiable |
| H2 | ... | live | falsifiable |
| H3 | ... | live | unfalsifiable |

## Predeclared checks

Written *before* observing, so a predicted transition is never tagged `measured` — the
observation has not happened yet.

| Check | Outcome | H1 | H2 | H3 | Cost/Risk/Rev | Changes action? |
|---|---|---|---|---|---|---|
| ... | A | weakened `[documented: <source>]` | leading `[inferred: <premises>]` | live `[guess]` | low/low/yes | yes |
| ... | B | leading `[inferred: <premises>]` | weakened `[documented: <source>]` | live `[guess]` | low/low/yes | yes |

## Evidence log

Every rival gets a transition line, including unchanged ones.

```
<date> ran <check> -> <result> [measured: <artifact/command>]. Test validity: <...>
  H1: live -> leading, because ... [documented: <source>]
  H2: leading -> weakened, because ... [inferred: <premises>]
  H3: live -> live, result does not discriminate it [inferred: <premises>]
```

If the check was invalid: quarantine the result, mark the *check* failed, leave the
discriminator unconsumed, and change no hypothesis status.

## Resolution

```
action_disposition: hold | authorized | declined
authorized_by: <authority or none>
stop_rule_invoked: <which of the four>
untested: <what was never checked>
```

The terminal state lives in the frontmatter `state:` field, so the two cannot drift.
Authority sets `action_disposition`, never `state:`.
