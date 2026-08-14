# Misfires

One file per real incident, from real work — not from the eval suite. This is the supply line
for Gate 2 cases.

Gate 1 established that the trigger fires on consequential work and stays quiet on cheap
reversible work, but it could not establish that Crucible improves reasoning: the bare arm
passed all six cases on both models tested, so there was no headroom for an improvement to
register. The cases that would have headroom are the ones where an uninstructed agent actually
gets it wrong, and those come from use, not from imagination. Every file in this directory is a
candidate Gate 2 case.

## What counts

Log it if any of these happened during real work:

- **Missed fire** — the gate should have opened and did not. A conclusion was acted on that was
  expensive to get wrong.
- **Over-fire** — ceremony on something cheap and reversible. Gate 1's most-suspected failure
  mode; it did not occur in twelve runs, so a real one is worth a lot.
- **Wrong terminal state** — `justified` on evidence that did not meet the standard,
  `underdetermined` where the evidence was genuinely unavailable, or `blocked` where it was
  merely unattempted.
- **Authority leak** — an approval moving the terminal state rather than the disposition.
- **Bad evidence handling** — a rival marked `contradicted` on invalid instrumentation, or a
  rival left unmoved when the result bore on it.
- **Correct but useless** — the gate ran, produced its artifacts, and changed nothing about what
  you did. Log these. Gate 1's honest finding was that the value showed up in what runs *found*,
  not in whether they passed, so a fire that finds nothing is a real signal.

Do not log a case where the gate behaved correctly and the output helped. That is the expected
state and it does not need a file.

## Naming

`YYYY-MM-DD-short-slug.md`, e.g. `2026-08-19-missed-fire-migration-rollback.md`.

## Template

Copy `_template.md`. Fill it the same day — a reconstruction a week later is a story, not
evidence.

## Release gate

Public release needs at least two weeks and ten eligible dogfood gates, with the regression
suite grown from what turns up here. A quiet directory after two weeks means either the trigger
is well-tuned or the work has not been consequential enough to test it. Those are different
conclusions and the daily notes should say which.
