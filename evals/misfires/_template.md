---
date: YYYY-MM-DD
kind: missed-fire | over-fire | wrong-terminal-state | authority-leak | bad-evidence | correct-but-useless
harness: claude-code | codex | other
model:
crucible_commit:
gate_fired: yes | no
---

# <one line: what the agent was doing when this happened>

## What was asked

The actual request, verbatim where possible. If it came mid-session, say what the session had
already established, because the trigger reads the whole context and not just the last message.

## What happened

What the agent did. Quote the part that is the incident — the conclusion it committed to, the
ceremony it produced, the state it named. Paste the transcript excerpt rather than paraphrasing;
a paraphrase of reasoning is not evidence of reasoning.

## What should have happened

Be specific about the correct behaviour, not just "it should have been better". Which rival
should have been constructed? Which check had the highest decision value for its cost? Which
terminal state was correct and why?

## What it cost

What did being wrong actually cost — time, a bad deploy, a wasted booking, nothing? "Nothing"
is a legitimate answer and it is the one that decides whether this belongs in the regression
suite or just in the log.

## Why the trigger read it the way it did

Best guess at the mechanism. The trigger is description-level, so the useful question is which
words in the request made it look consequential or cheap. This is the field that turns an
incident into a fix.

## Case candidate

- **Would this make a Gate 2 case?** yes | no | needs-work
- **Does an uninstructed agent get it wrong?** Test it before saying yes — that is exactly the
  headroom Gate 1 lacked. If bare handles it fine, the case measures the model.
- **Which obligation does it test?**
- **What is the success witness?** State it as something quotable from a transcript, not as an
  impression.
